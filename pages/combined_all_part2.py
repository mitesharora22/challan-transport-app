# pages/combined_all_part2.py - WITH DASHBOARD ROUTING
import streamlit as st
import pandas as pd
import io
from datetime import datetime, date

# Import part1 to get functions
import pages.combined_all_part1 as part1

# Import shared utilities
from auth_utils import safe_rerun

# Import DB functions
from db import get_conn, get_party_list, compute_party_balance

# Import PDF functions
from utils.pdf_utils import bill_pdf, ledger_pdf

def run_app():
    """
    Runtime entrypoint - called from app.py after login
    """
    # Get render target and current page
    main_render = part1.get_main_render()
    page = st.session_state.get("combined_page", "home")

    # Router - direct page rendering
    if page == "dashboard":
        if st.session_state.get("role") == "ADMIN":
            part1.section_dashboard(main_render)
        else:
            st.error("❌ Access Denied: Operators cannot access Dashboard")
    elif page == "token":
        part1.section_token(main_render)
    elif page == "challan":
        part1.section_challan(main_render)
    elif page == "party":
        if st.session_state.get("role") == "ADMIN":
            part1.section_party(main_render)
        else:
            st.error("❌ Access Denied: Operators cannot access Party Master")
    elif page == "item_rate":
        if st.session_state.get("role") == "ADMIN":
            part1.section_item_rate(main_render)
        else:
            st.error("❌ Access Denied: Operators cannot access Item/Rate Master")
    elif page == "payments":
        if st.session_state.get("role") == "ADMIN":
            render_payments(main_render)
        else:
            st.error("❌ Access Denied")
    elif page == "billing":
        if st.session_state.get("role") == "ADMIN":
            render_billing(main_render)
        else:
            st.error("❌ Access Denied")
    elif page == "ledger":
        if st.session_state.get("role") == "ADMIN":
            render_ledger(main_render)
        else:
            st.error("❌ Access Denied")
    elif page == "reports":
        if st.session_state.get("role") == "ADMIN":
            render_reports(main_render)
        else:
            st.error("❌ Access Denied")
    elif page == "delivery":
        if st.session_state.get("role") == "ADMIN":
            render_delivery(main_render)
        else:
            st.error("❌ Access Denied")
    else:
        # Home page
        if st.session_state.get("role") == "ADMIN":
            main_render.title("👋 Admin Dashboard — Transport Management")
            main_render.write("Use the buttons below to open any section.")
            
            # Quick access grid with Dashboard button
            menu = [
                ("📊 Dashboard", "dashboard"),
                ("👥 Party Master", "party"),
                ("📦 Item / Rate Master", "item_rate"),
                ("📄 Token / Bilty", "token"),
                ("🚛 Challan / Loading", "challan"),
                ("💰 Payments", "payments"),
                ("🧾 Billing", "billing"),
                ("📚 Ledger", "ledger"),
                ("📊 Reports", "reports"),
            ]
            cols_per_row = 3
            for i in range(0, len(menu), cols_per_row):
                cols = main_render.columns(cols_per_row, gap="large")
                for j, (label, page_name) in enumerate(menu[i:i+cols_per_row]):
                    with cols[j]:
                        btn_key = f"admin_dashboard_btn_{page_name}"
                        if main_render.button(label, key=btn_key, use_container_width=True):
                            st.session_state["combined_page"] = page_name
                            safe_rerun()

            parties = get_party_list()
            if parties:
                main_render.success(f"Total Parties: {len(parties)}")
            else:
                main_render.info("👉 No parties yet. Add parties using Party Master.")
        else:
            main_render.info("👉 Use the menu to navigate")

# -------------------------
# SECTION: PAYMENTS
# -------------------------
def render_payments(area):
    area.title("💰 Payment Entry (Cash / Bank)")
    parties = get_party_list()
    if not parties:
        area.warning("पहले Party Master में Party बनाओ।")
        return
    party_map = {p[1]: p[0] for p in parties}
    party_name = area.selectbox("Party चुनें", list(party_map.keys()), key="payments_party")
    party_id = party_map[party_name]

    current_bal = compute_party_balance(party_id)
    area.info(f"Approx Current Balance: ₹ {current_bal:.2f}")

    with area.form("payment_form_area"):
        date_str = area.text_input("Date", value=datetime.now().strftime("%d/%m/%Y"), key="payment_date")
        amount = area.number_input("Amount", min_value=0.0, step=500.0, key="payment_amount")
        mode = area.selectbox("Payment Type", ["CASH", "BANK", "UPI", "CHEQUE"], key="payment_mode")
        remark = area.text_input("Remark (optional)", key="payment_remark")
        submitted = area.form_submit_button("💾 Save Payment")

        if submitted:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO payments (party_id, date, amount, mode, remark)
                VALUES (?,?,?,?,?)
            """, (party_id, date_str, amount, mode, remark))
            conn.commit()
            conn.close()
            area.success("Payment saved ✅")

    area.markdown("---")
    area.subheader("Recent Payments")
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT date, amount, mode, remark
        FROM payments
        WHERE party_id=?
        ORDER BY id DESC LIMIT 50
    """, conn, params=(party_id,))
    conn.close()
    area.dataframe(df, use_container_width=True)

# -------------------------
# SECTION: BILLING
# -------------------------
def render_billing(area):
    area.title("🧾 Billing (Party-wise)")
    area.info("किसी party के लिए date range चुनकर Bill बना सकते हैं।")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, party_name FROM party_master ORDER BY party_name")
    parties = cur.fetchall()
    conn.close()

    if not parties:
        area.error("❌ No parties found. Add parties first.")
        return

    party_map = {p[1]: p[0] for p in parties}
    party_name = area.selectbox("Select Party", list(party_map.keys()), key="billing_party")
    party_id = party_map[party_name]

    col1, col2 = area.columns(2)
    with col1:
        start_dt = area.date_input("From Date", date.today().replace(day=1), key="bill_from")
    with col2:
        end_dt = area.date_input("To Date", date.today(), key="bill_to")

    old_balance = area.number_input("Old Balance (₹)", value=0.0, step=100.0, key="bill_old_bal")

    if start_dt > end_dt:
        area.error("❌ From Date cannot be greater than To Date.")
        return

    if area.button("🔍 Show Bill", type="primary", key="show_bill_btn"):
        conn = get_conn()
        df = pd.read_sql_query("""
            SELECT 
                t.id AS token_no,
                t.date_time,
                t.weight,
                t.pkgs AS packages,
                t.amount,
                t.from_city,
                t.to_city
            FROM tokens t
            WHERE t.party_id = ?
              AND t.status IN ('PENDING', 'LOADED')
            ORDER BY t.date_time
        """, conn, params=(party_id,))
        conn.close()

        if df.empty:
            area.warning("No records for this party.")
            return

        df["dt"] = pd.to_datetime(df["date_time"], errors="coerce")
        df = df[df["dt"].notna()].copy()
        df["d"] = df["dt"].dt.date

        mask = (df["d"] >= start_dt) & (df["d"] <= end_dt)
        df = df[mask]

        if df.empty:
            area.warning("No records in this date range.")
            return

        df_show = df[["token_no", "date_time", "from_city", "to_city", "weight", "packages", "amount"]]
        area.dataframe(df_show, use_container_width=True)

        total_weight = df["weight"].sum()
        total_pack = df["packages"].sum()
        total_amt = df["amount"].sum()

        area.subheader("📌 Totals")
        area.write(f"**Total Weight:** {total_weight}")
        area.write(f"**Total Packages:** {total_pack}")
        area.write(f"**Total Amount:** ₹{total_amt}")

        rows = []
        for _, r in df.iterrows():
            rows.append({
                "token_no": r["token_no"],
                "datetime": r["date_time"],
                "from_city": r["from_city"],
                "to_city": r["to_city"],
                "weight": r["weight"],
                "packages": r["packages"],
                "amount": r["amount"],
            })

        header = {
            "party_name": party_name,
            "from_date": start_dt.strftime("%d-%m-%Y"),
            "to_date": end_dt.strftime("%d-%m-%Y"),
            "total_weight": total_weight,
            "total_pkgs": total_pack,
            "total_amount": total_amt,
            "old_balance": old_balance,
        }

        pdf_buf = bill_pdf(header, rows)
        area.download_button(
            "⬇️ Download Bill PDF",
            data=pdf_buf,
            file_name=f"BILL_{party_name.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

        excel_buf = io.BytesIO()
        df_show.to_excel(excel_buf, index=False, engine="openpyxl")
        excel_buf.seek(0)
        area.download_button(
            "⬇️ Download Excel",
            data=excel_buf,
            file_name=f"BILL_{party_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# -------------------------
# SECTION: LEDGER
# -------------------------
def render_ledger(area):
    area.title("📚 Party Ledger")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, party_name FROM party_master ORDER BY party_name")
    parties = cur.fetchall()
    conn.close()

    if not parties:
        area.error("❌ Add Party first.")
        return

    party_map = {p[1]: p[0] for p in parties}
    party_name = area.selectbox("Select Party", list(party_map.keys()), key="ledger_party")
    party_id = party_map[party_name]

    opening_balance = area.number_input("Opening Balance (₹)", value=0.0, step=100.0, key="ledger_opening")

    col1, col2 = area.columns(2)
    with col1:
        start_dt = area.date_input("From Date", date.today().replace(day=1), key="ledger_from")
    with col2:
        end_dt = area.date_input("To Date", date.today(), key="ledger_to")

    if start_dt > end_dt:
        area.error("❌ From Date cannot be after To Date.")
        return

    if area.button("📄 Show Ledger", type="primary", key="show_ledger_btn"):
        conn = get_conn()
        tokens = pd.read_sql_query("""
            SELECT t.date_time, t.id AS token_no, t.amount, t.party_id
            FROM tokens t
            WHERE t.party_id = ?
            ORDER BY t.date_time
        """, conn, params=(party_id,))

        payments = pd.read_sql_query("""
            SELECT date, amount, mode, remark
            FROM payments
            WHERE party_id = ?
            ORDER BY date
        """, conn, params=(party_id,))
        conn.close()

        rows = []
        if not tokens.empty:
            tokens["dt"] = pd.to_datetime(tokens["date_time"], errors="coerce")
            tokens = tokens[tokens["dt"].notna()]
            tokens["d"] = tokens["dt"].dt.date
            tokens = tokens[(tokens["d"] >= start_dt) & (tokens["d"] <= end_dt)]
            for _, r in tokens.iterrows():
                rows.append({
                    "date": r["d"].strftime("%d-%m-%Y"),
                    "type": "TOKEN",
                    "details": f"Token #{r['token_no']}",
                    "debit": r["amount"],
                    "credit": 0,
                })

        if not payments.empty:
            payments["dt"] = pd.to_datetime(payments["date"], errors="coerce", dayfirst=True)
            payments = payments[payments["dt"].notna()]
            payments["d"] = payments["dt"].dt.date
            payments = payments[(payments["d"] >= start_dt) & (payments["d"] <= end_dt)]
            for _, r in payments.iterrows():
                desc = f"Payment ({r['mode']})"
                if r["remark"]:
                    desc += f" - {r['remark']}"
                rows.append({
                    "date": r["d"].strftime("%d-%m-%Y"),
                    "type": "PAYMENT",
                    "details": desc,
                    "debit": 0,
                    "credit": r["amount"],
                })

        if not rows:
            area.warning("No transactions.")
            return

        ledger_df = pd.DataFrame(rows)
        ledger_df["date_sort"] = pd.to_datetime(ledger_df["date"], dayfirst=True)
        ledger_df.sort_values("date_sort", inplace=True)

        balance = opening_balance
        balances = []
        for _, r in ledger_df.iterrows():
            balance += r["debit"] - r["credit"]
            balances.append(balance)
        ledger_df["balance"] = balances
        ledger_df.drop(columns=["date_sort"], inplace=True)

        area.dataframe(ledger_df, use_container_width=True)

        header = {
            "party_name": party_name,
            "from_date": start_dt.strftime("%d-%m-%Y"),
            "to_date": end_dt.strftime("%d-%m-%Y"),
            "opening_balance": opening_balance,
            "closing_balance": float(balance)
        }

        pdf_buf = ledger_pdf(header, ledger_df.to_dict(orient="records"))
        area.download_button(
            "⬇️ Download Ledger PDF",
            data=pdf_buf,
            file_name=f"Ledger_{party_name.replace(' ','_')}.pdf",
            mime="application/pdf"
        )

        excel_buf = io.BytesIO()
        ledger_df.to_excel(excel_buf, index=False, engine="openpyxl")
        excel_buf.seek(0)
        area.download_button(
            "⬇️ Download Excel",
            data=excel_buf,
            file_name=f"Ledger_{party_name.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# -------------------------
# SECTION: REPORTS
# -------------------------
def render_reports(area):
    area.title("📊 Reports")
    conn = get_conn()

    tokens = pd.read_sql_query("""
        SELECT t.id AS token_no, t.date_time, p.party_name, t.weight, t.pkgs AS packages, t.amount
        FROM tokens t
        LEFT JOIN party_master p ON p.id = t.party_id
    """, conn)

    payments = pd.read_sql_query("SELECT party_id, date, amount FROM payments", conn)
    parties = pd.read_sql_query("SELECT id, party_name FROM party_master", conn)
    conn.close()

    if not tokens.empty:
        tokens["dt"] = pd.to_datetime(tokens["date_time"], errors="coerce")
        tokens = tokens[tokens["dt"].notna()]
        tokens["d"] = tokens["dt"].dt.date

    if not payments.empty:
        payments["dt"] = pd.to_datetime(payments["date"], errors="coerce", dayfirst=True)
        payments = payments[payments["dt"].notna()]

    tab1, tab2 = area.tabs(["📅 Daily Booking", "💰 Outstanding"])

    with tab1:
        area.subheader("📅 Daily Booking")
        col1, col2 = area.columns(2)
        with col1:
            start_dt = area.date_input("From Date", date.today().replace(day=1), key="rep_from")
        with col2:
            end_dt = area.date_input("To Date", date.today(), key="rep_to")

        if start_dt > end_dt:
            area.error("Invalid date range.")
        else:
            if tokens.empty:
                area.warning("No booking data.")
            else:
                df = tokens[(tokens["d"] >= start_dt) & (tokens["d"] <= end_dt)]
                if df.empty:
                    area.warning("No records in range.")
                else:
                    grp = df.groupby("d").agg(
                        tokens=("token_no", "count"),
                        weight=("weight", "sum"),
                        amount=("amount", "sum")
                    ).reset_index()
                    grp["d"] = grp["d"].apply(lambda x: x.strftime("%d-%m-%Y"))
                    area.dataframe(grp.rename(columns={"d": "Date", "tokens": "Tokens", "weight": "Total Weight", "amount": "Total Amount"}), use_container_width=True)

    with tab2:
        area.subheader("💰 Outstanding by Party")
        if tokens.empty and payments.empty:
            area.warning("Not enough data.")
        else:
            tok_sum = tokens.groupby("party_name")["amount"].sum() if not tokens.empty else pd.Series(dtype="float64")
            pay_sum = pd.Series(dtype="float64")
            if not payments.empty and not parties.empty:
                pay_sum = payments.merge(parties, left_on="party_id", right_on="id").groupby("party_name")["amount"].sum()
            out_df = pd.DataFrame({"Total Billing": tok_sum, "Payments": pay_sum}).fillna(0)
            out_df["Outstanding"] = out_df["Total Billing"] - out_df["Payments"]
            area.dataframe(out_df, use_container_width=True)

# -------------------------
# SECTION: DELIVERY ENTRY
# -------------------------
def render_delivery(area):
    area.title("📦 Delivery Entry (Token Delivery Update)")
    area.info("यहाँ से Delivered माल का entry करें।")

    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT t.id AS token_id, t.date_time, p.party_name, t.from_city, t.to_city, t.weight, t.amount
        FROM tokens t
        LEFT JOIN party_master p ON p.id = t.party_id
        WHERE t.status='LOADED'
        ORDER BY t.date_time
    """, conn)
    conn.close()

    if df.empty:
        area.warning("कोई Loaded token नहीं मिला।")
        return

    token_ids = df["token_id"].tolist()
    token_id = area.selectbox("Select Token No", token_ids, key="delivery_token_select")
    selected_row = df[df["token_id"] == token_id].iloc[0]

    area.write("### Token Details")
    area.write(f"**Party:** {selected_row.party_name}")
    area.write(f"**From → To:** {selected_row.from_city} → {selected_row.to_city}")
    area.write(f"**Weight:** {selected_row.weight} KG")
    area.write(f"**Amount:** ₹ {selected_row.amount}")

    delivery_date = area.date_input("Delivery Date", datetime.now(), key="delivery_date")
    receiver_name = area.text_input("Receiver Name", key="delivery_receiver")
    signature_file = area.file_uploader("Signature (Optional)", type=["png", "jpg", "jpeg"], key="delivery_signature")

    if area.button("✔ Update Delivery", key="update_delivery_btn"):
        signature_path = None
        if signature_file:
            file_name = f"signature_{token_id}.png"
            with open(file_name, "wb") as f:
                f.write(signature_file.getbuffer())
            signature_path = file_name

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO delivery_log (token_id, delivery_date, receiver_name, signature) VALUES (?, ?, ?, ?)",
                   (token_id, delivery_date.strftime("%d-%m-%Y"), receiver_name, signature_path))
        cur.execute("UPDATE tokens SET status='DELIVERED' WHERE id=?", (token_id,))
        conn.commit()
        conn.close()
        area.success("🚚 Delivery Updated Successfully!")