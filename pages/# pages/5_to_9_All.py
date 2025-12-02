# pages/5_to_9_All.py
import streamlit as st
import pandas as pd
from datetime import datetime, date
import io

from db import (
    init_db, get_conn, get_party_list, compute_party_balance,
    get_pending_tokens, group_tokens_by_marka, create_challan, get_next_challan_no,
    get_all_markas, create_token_in_db
)
from utils.pdf_utils import bill_pdf, ledger_pdf, challan_pdf
from auth_utils import do_logout

init_db()
st.set_page_config(page_title="Payments | Billing | Ledger | Reports | Delivery", layout="wide")

# ---------------- Access control ----------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("कृपया पहले login करें।")
    st.stop()

# -------------------------
# Sidebar helpers
# -------------------------
def hide_default_sidebar():
    st.markdown("<style>[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)

# ---------------- Layout decision ----------------
is_operator = st.session_state.get("role") == "OPERATOR"

# -------------------------
# Top logout for all roles
# -------------------------
colL, colR = st.columns([3, 1])
with colL:
    st.markdown(f"**User:** `{st.session_state['username']}` — **{st.session_state['role']}**")
    if st.session_state.get("office"):
        st.markdown(f"**Office:** `{st.session_state['office']}`")

with colR:
    if st.button("Logout", key="logout_top"):
        do_logout()

# If operator: hide default sidebar and render left-panel
if is_operator:
    hide_default_sidebar()
    left_col, main_col = st.columns([1, 5], gap="small")
    with left_col:
        st.markdown("### 🚚 Operator Menu")
        
        if st.button("Token / Bilty", key="btn_token"):
            st.switch_page("pages/3_Token_Bilty.py")
        
        if st.button("Challan / Loading", key="btn_challan"):
            st.switch_page("pages/4_Challan_Loading.py")
        
        st.markdown("---")
        
        if st.button("Home", key="btn_home"):
            st.switch_page("app.py")
        
        st.markdown("---")
        
        # Internal navigation
        subpage = st.radio("Open:", ["Payments", "Billing", "Ledger", "Reports", "Delivery Entry"], index=0, key="subpage_radio")
        
        st.markdown("---")
        st.markdown(f"**User:** {st.session_state.get('username')}")
        st.markdown(f"**Office:** {st.session_state.get('office')}")
        
        if st.button("Logout", key="logout_operator"):
            do_logout()
    
    render = main_col
else:
    # Admin: keep default sidebar visible
    render = st
    subpage = render.radio("Open:", ["Payments", "Billing", "Ledger", "Reports", "Delivery Entry"], index=0, key="subpage_radio")

# ---------- Payments ----------
def render_payments(area):
    area.title("💰 Payment Entry (Cash / Bank)")
    parties = get_party_list()
    if not parties:
        area.warning("पहले Party Master में Party बनाओ।")
        return
    party_map = {p[1]: p[0] for p in parties}
    party_name = area.selectbox("Party चुनें", list(party_map.keys()))
    party_id = party_map[party_name]

    current_bal = compute_party_balance(party_id)
    area.info(f"Approx Current Balance: ₹ {current_bal:.2f}")

    with area.form("payment_form"):
        date_str = area.text_input("Date", value=datetime.now().strftime("%d/%m/%Y"))
        amount = area.number_input("Amount", min_value=0.0, step=500.0)
        mode = area.selectbox("Payment Type", ["CASH", "BANK", "UPI", "CHEQUE"])
        remark = area.text_input("Remark (optional)")
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

# ---------- Billing ----------
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
    party_name = area.selectbox("Select Party", list(party_map.keys()))
    party_id = party_map[party_name]

    col1, col2 = area.columns(2)
    with col1:
        start_dt = area.date_input("From Date", date.today().replace(day=1))
    with col2:
        end_dt = area.date_input("To Date", date.today())

    old_balance = area.number_input("Old Balance (₹)", value=0.0, step=100.0)

    if start_dt > end_dt:
        area.error("❌ From Date cannot be greater than To Date.")
        return

    if area.button("🔍 Show Bill", type="primary"):
        conn = get_conn()
        # ✅ FIXED: Use date_time instead of datetime, pkgs instead of packages
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

        # ✅ FIXED: Parse date_time column
        df["dt"] = pd.to_datetime(df["date_time"], errors="coerce")
        df = df[df["dt"].notna()].copy()
        df["d"] = df["dt"].dt.date

        mask = (df["d"] >= start_dt) & (df["d"] <= end_dt)
        df = df[mask]

        if df.empty:
            area.warning("No records in this date range.")
            return

        df_show = df[[
            "token_no", "date_time", "from_city", "to_city",
            "weight", "packages", "amount"
        ]]
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

# ---------- Ledger ----------
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
    party_name = area.selectbox("Select Party", list(party_map.keys()))
    party_id = party_map[party_name]

    opening_balance = area.number_input("Opening Balance (₹)", value=0.0, step=100.0)

    col1, col2 = area.columns(2)
    with col1:
        start_dt = area.date_input("From Date", date.today().replace(day=1))
    with col2:
        end_dt = area.date_input("To Date", date.today())

    if start_dt > end_dt:
        area.error("❌ From Date cannot be after To Date.")
        return

    if area.button("📄 Show Ledger", type="primary"):
        conn = get_conn()
        # ✅ FIXED: Use date_time
        tokens = pd.read_sql_query("""
            SELECT 
                t.date_time,
                t.id AS token_no,
                t.amount
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

# ---------- Reports ----------
def render_reports(area):
    area.title("📊 Reports")
    conn = get_conn()
    
    # ✅ FIXED: Use date_time and pkgs, JOIN with party_master
    tokens = pd.read_sql_query("""
        SELECT 
            t.id AS token_no,
            t.date_time,
            p.party_name,
            t.weight,
            t.pkgs AS packages,
            t.amount
        FROM tokens t
        LEFT JOIN party_master p ON p.id = t.party_id
    """, conn)
    
    payments = pd.read_sql_query("""
        SELECT party_id, date, amount
        FROM payments
    """, conn)
    
    parties = pd.read_sql_query("""
        SELECT id, party_name
        FROM party_master
    """, conn)
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
                    area.dataframe(
                        grp.rename(columns={
                            "d":"Date",
                            "tokens":"Tokens",
                            "weight":"Total Weight",
                            "amount":"Total Amount"
                        }), 
                        use_container_width=True
                    )
    
    with tab2:
        area.subheader("💰 Outstanding by Party")
        if tokens.empty and payments.empty:
            area.warning("Not enough data.")
        else:
            tok_sum = tokens.groupby("party_name")["amount"].sum() if not tokens.empty else pd.Series(dtype="float64")
            pay_sum = pd.Series(dtype="float64")
            if not payments.empty:
                pay_sum = payments.merge(parties, left_on="party_id", right_on="id").groupby("party_name")["amount"].sum()
            out_df = pd.DataFrame({"Total Billing": tok_sum, "Payments": pay_sum}).fillna(0)
            out_df["Outstanding"] = out_df["Total Billing"] - out_df["Payments"]
            area.dataframe(out_df, use_container_width=True)

# ---------- Delivery Entry ----------
def render_delivery(area):
    area.title("📦 Delivery Entry (Token Delivery Update)")
    area.info("यहाँ से Delivered माल का entry करें।")

    conn = get_conn()
    # ✅ FIXED: Use date_time
    df = pd.read_sql_query("""
        SELECT 
            t.id AS token_id,
            t.date_time,
            p.party_name,
            t.from_city,
            t.to_city,
            t.weight,
            t.amount
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
    token_id = area.selectbox("Select Token No", token_ids)
    selected_row = df[df["token_id"] == token_id].iloc[0]

    area.write("### Token Details")
    area.write(f"**Party:** {selected_row.party_name}")
    area.write(f"**From → To:** {selected_row.from_city} → {selected_row.to_city}")
    area.write(f"**Weight:** {selected_row.weight} KG")
    area.write(f"**Amount:** ₹ {selected_row.amount}")

    delivery_date = area.date_input("Delivery Date", datetime.now())
    receiver_name = area.text_input("Receiver Name")
    signature_file = area.file_uploader("Signature (Optional)", type=["png", "jpg", "jpeg"])

    if area.button("✔ Update Delivery"):
        signature_path = None
        if signature_file:
            file_name = f"signature_{token_id}.png"
            with open(file_name, "wb") as f:
                f.write(signature_file.getbuffer())
            signature_path = file_name

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO delivery_log (token_id, delivery_date, receiver_name, signature)
            VALUES (?, ?, ?, ?)
        """, (token_id, delivery_date.strftime("%d-%m-%Y"), receiver_name, signature_path))
        cur.execute("UPDATE tokens SET status='DELIVERED' WHERE id=?", (token_id,))
        conn.commit()
        conn.close()
        area.success("🚚 Delivery Updated Successfully!")

# ------------- Render requested subpage -------------
if subpage == "Payments":
    render_payments(render)
elif subpage == "Billing":
    render_billing(render)
elif subpage == "Ledger":
    render_ledger(render)
elif subpage == "Reports":
    render_reports(render)
elif subpage == "Delivery Entry":
    render_delivery(render)
else:
    render.title("Select an option from left")