# pages/combined_all.py
# Complete combined Streamlit app: Sections 1..9 integrated into one file
# - Party Master
# - Item & Rate Master
# - Token / Bilty
# - Challan / Loading
# - Payments
# - Billing
# - Ledger
# - Reports
# - Delivery Entry
#
# Expects your existing modules: db, utils.pdf_utils, auth_utils (optional)
# Drop this file into pages/combined_all.py and import it from app.py

import streamlit as st
import pandas as pd
from datetime import datetime, date
import io

# Safe rerun helper — works across Streamlit versions
def safe_rerun():
    """
    Try the modern st.rerun(); if it's not available, try the older
    st.experimental_rerun(); if neither exist, stop the script.
    """
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            st.stop()

# DB helpers (your existing db.py)
from db import (
    init_db, get_conn, get_party_list, get_all_markas,
    create_token_in_db, get_pending_tokens, group_tokens_by_marka,
    create_challan, get_next_challan_no, create_user,
    verify_user, compute_party_balance
)

# PDF helpers (your existing utils/pdf_utils.py)
from utils.pdf_utils import challan_pdf, bill_pdf, ledger_pdf

# Centralized logout helper (if missing, fallback defined)
try:
    from auth_utils import do_logout
except Exception:
    def do_logout():
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["role"] = None
        st.session_state["office"] = None
        st.markdown("<style>[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)
        safe_rerun()

# initialize DB once
init_db()

# Page config
st.set_page_config(page_title="Transport Management — All Sections", layout="wide")

# -------------------------
# Session defaults
# -------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None
    st.session_state["office"] = None
    st.session_state.setdefault("combined_page", "home")

# -------------------------
# Helpers: hide/show default Streamlit sidebar
# -------------------------
def hide_default_sidebar():
    st.markdown("<style>[data-testid='stSidebar']{display:none !important;}</style>", unsafe_allow_html=True)

def show_default_sidebar():
    st.markdown("<style>[data-testid='stSidebar']{display:block !important;}</style>", unsafe_allow_html=True)

# -------------------------
# Operator left-panel menu
# -------------------------
def operator_left_panel():
    hide_default_sidebar()
    left_col, main_col = st.columns([1, 4], gap="small")
    with left_col:
        st.markdown("### 🚚 Operator Menu")
        if st.button("Token / Bilty", key="nav_token"):
            st.session_state["combined_page"] = "token"
            safe_rerun()
        if st.button("Challan / Loading", key="nav_challan"):
            st.session_state["combined_page"] = "challan"
            safe_rerun()
        st.markdown("---")
        if st.button("Home", key="nav_home_op"):
            st.session_state["combined_page"] = "home"
            safe_rerun()
        st.markdown("---")
        st.markdown(f"**User:** {st.session_state.get('username')}")
        st.markdown(f"**Office:** {st.session_state.get('office')}")
        if st.button("Logout", key="op_logout"):
            do_logout()
    return main_col

# -------------------------
# Admin top buttons (sidebar)
# -------------------------
def admin_top_buttons():
    st.sidebar.markdown("### 📋 Admin Menu")
    if st.sidebar.button("🏠 Home", use_container_width=True):
        st.session_state["combined_page"] = "home"
        safe_rerun()
    if st.sidebar.button("👥 Party Master", use_container_width=True):
        st.session_state["combined_page"] = "party"
        safe_rerun()
    if st.sidebar.button("📦 Item / Rate Master", use_container_width=True):
        st.session_state["combined_page"] = "item_rate"
        safe_rerun()
    if st.sidebar.button("📄 Token / Bilty", use_container_width=True):
        st.session_state["combined_page"] = "token"
        safe_rerun()
    if st.sidebar.button("🚛 Challan / Loading", use_container_width=True):
        st.session_state["combined_page"] = "challan"
        safe_rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("💰 Payments", use_container_width=True):
        st.session_state["combined_page"] = "payments"
        safe_rerun()
    if st.sidebar.button("🧾 Billing", use_container_width=True):
        st.session_state["combined_page"] = "billing"
        safe_rerun()
    if st.sidebar.button("📚 Ledger", use_container_width=True):
        st.session_state["combined_page"] = "ledger"
        safe_rerun()
    if st.sidebar.button("📊 Reports", use_container_width=True):
        st.session_state["combined_page"] = "reports"
        safe_rerun()
    if st.sidebar.button("📦 Delivery Entry", use_container_width=True):
        st.session_state["combined_page"] = "delivery"
        safe_rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        do_logout()

# -------------------------
# LOGIN / AUTH Handlers
# -------------------------
def admin_login_handler():
    username = st.session_state.get("admin_username", "").strip()
    password = st.session_state.get("admin_password", "")
    if not username or not password:
        st.error("Enter admin username & password.")
        return
    user = verify_user(username, password)
    if user and user.get("role") == "ADMIN":
        st.session_state["logged_in"] = True
        st.session_state["username"] = user["username"]
        st.session_state["role"] = "ADMIN"
        st.session_state["office"] = user.get("office_location")
        show_default_sidebar()
        safe_rerun()
    else:
        st.error("Invalid admin credentials")

def operator_login_handler():
    name = st.session_state.get("operator_name", "").strip() or "operator"
    route = st.session_state.get("operator_route_choice", "Mumbai → Delhi")
    office = "MUMBAI" if route == "Mumbai → Delhi" else "DELHI"
    st.session_state["logged_in"] = True
    st.session_state["username"] = name
    st.session_state["role"] = "OPERATOR"
    st.session_state["office"] = office
    hide_default_sidebar()
    safe_rerun()

# Ensure sidebar hidden on initial load before login
if not st.session_state.get("logged_in", False):
    hide_default_sidebar()

# ---------- LOGIN SCREEN ----------
if not st.session_state.get("logged_in", False):
    st.title("🔐 Login")
    role_choice = st.selectbox("Select role / Role chunen", ["Operator", "Admin"], index=0)

    if role_choice == "Admin":
        st.text_input("Username", key="admin_username")
        st.text_input("Password", type="password", key="admin_password")
        c1, c2 = st.columns([1, 1])
        with c1:
            st.button("Login as Admin", on_click=admin_login_handler)
        with c2:
            if st.button("Create default admin (admin/admin123)"):
                try:
                    create_user("admin", "admin123", role="ADMIN", office=None)
                    st.success("Default admin created (admin/admin123) if not present.")
                except Exception:
                    st.info("Default admin may already exist.")
        st.info("Admins must login with username & password.")
        st.stop()
    else:
        st.text_input("Operator name (optional)", key="operator_name", value="operator1")
        st.radio("Choose route (operator's office will be the FROM city)",
                 ("Mumbai → Delhi", "Delhi → Mumbai"),
                 key="operator_route_choice")
        c1, c2 = st.columns([1, 1])
        with c1:
            st.button("Login as Operator", on_click=operator_login_handler)
        with c2:
            if st.button("Create test operator account (operator1/operator123)"):
                try:
                    create_user("operator1", "operator123", role="OPERATOR", office="DELHI")
                    st.success("Operator 'operator1' created.")
                except Exception:
                    st.info("Operator may already exist.")
        st.caption("Operator quick login sets office automatically; operators do not need a password here.")
        st.stop()

# ---------- ROLE-SPECIFIC NAV / LAYOUT ----------
if st.session_state.get("role") == "OPERATOR":
    main_render = operator_left_panel()
else:
    show_default_sidebar()
    admin_top_buttons()
    main_render = st

# ---------- AFTER LOGIN HEADER (Show on all pages) ----------
colL, colR = st.columns([3, 1])
with colL:
    st.markdown(f"**User:** `{st.session_state.get('username', 'Guest')}` — **{st.session_state.get('role', 'N/A')}**")
    if st.session_state.get("office"):
        st.markdown(f"**Office:** `{st.session_state.get('office')}`")
with colR:
    if st.button("Logout", key="logout_top_page"):
        do_logout()

st.markdown("---")

# ---------- MAIN: route to appropriate section ----------
page = st.session_state.get("combined_page", "home")

# -------------------------
# SECTION: PARTY MASTER
# -------------------------
def section_party(render):
    render.title("👥 Party Master (Party Register)")
    render.info("यहाँ से Party add/update करें। नीचे simple form है।")

    with render.form("party_form"):
        party_name = render.text_input("Party Name *", key="party_name_input")
        address = render.text_area("Address", key="party_address")
        mobile = render.text_input("Mobile Number", key="party_mobile")
        gst_no = render.text_input("GST No. (optional)", key="party_gst")
        marka = render.text_input("Marka / Sign", key="party_marka")
        default_rate_per_kg = render.number_input("Default Rate per Kg (optional)", min_value=0.0, step=1.0, key="party_rate_kg")
        default_rate_per_parcel = render.number_input("Default Rate per Parcel (optional)", min_value=0.0, step=1.0, key="party_rate_parcel")
        submitted = render.form_submit_button("💾 Save Party")

        if submitted:
            if not party_name.strip():
                render.error("Party Name ज़रूरी है।")
            else:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR REPLACE INTO party_master
                    (id, party_name, address, mobile, gst_no, marka,
                     default_rate_per_kg, default_rate_per_parcel)
                    VALUES (
                        COALESCE((SELECT id FROM party_master WHERE party_name = ?), NULL),
                        ?,?,?,?,?,?,?
                    )
                """, (party_name, party_name, address, mobile, gst_no, marka,
                      default_rate_per_kg, default_rate_per_parcel))
                conn.commit()
                conn.close()
                render.success("Party saved successfully ✅")

    render.markdown("---")
    render.subheader("📋 Party List")
    conn = get_conn()
    df = pd.read_sql_query("SELECT party_name, mobile, gst_no, marka, default_rate_per_kg, default_rate_per_parcel FROM party_master ORDER BY party_name", conn)
    conn.close()
    render.dataframe(df, use_container_width=True)

# -------------------------
# SECTION: ITEM & RATE MASTER
# -------------------------
def section_item_rate(render):
    render.title("📦 Item & Rate Master")
    tab1, tab2 = render.tabs(["Item Master", "Rate Master"])

    with tab1:
        render.subheader("Item / Goods Type Master (Optional)")
        with render.form("item_form"):
            item_name = render.text_input("Item Name", key="item_name")
            desc = render.text_input("Description (optional)", key="item_desc")
            submitted = render.form_submit_button("💾 Save Item")
            if submitted:
                if not item_name.strip():
                    render.error("Item Name required.")
                else:
                    conn = get_conn()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT OR IGNORE INTO item_master (item_name, description)
                        VALUES (?, ?)
                    """, (item_name, desc))
                    conn.commit()
                    conn.close()
                    render.success("Item saved ✅")

        conn = get_conn()
        df_items = pd.read_sql_query("SELECT item_name, description FROM item_master ORDER BY item_name", conn)
        conn.close()
        render.dataframe(df_items, use_container_width=True)

    with tab2:
        render.subheader("Rate Master (Party + Route Wise)")
        parties = get_party_list()
        party_map = {p[1]: p[0] for p in parties} if parties else {}
        party_name = render.selectbox("Party (optional, blank = general)", [""] + list(party_map.keys()))
        from_city = render.text_input("From City (e.g., DELHI)", key="rate_from")
        to_city = render.text_input("To City (e.g., MUMBAI)", key="rate_to")
        rate_type = render.selectbox("Rate Type", ["KG", "PARCEL"], key="rate_type")
        rate_val = render.number_input("Rate", min_value=0.0, step=1.0, key="rate_val")

        if render.button("💾 Save Rate", key="save_rate_btn"):
            if not from_city.strip() or not to_city.strip():
                render.error("From और To दोनों ज़रूरी हैं।")
            else:
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO rate_master (party_id, from_city, to_city, rate_type, rate)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    party_map.get(party_name) if party_name else None,
                    from_city.upper().strip(),
                    to_city.upper().strip(),
                    rate_type,
                    rate_val
                ))
                conn.commit()
                conn.close()
                render.success("Rate saved ✅")

        conn = get_conn()
        df_rates = pd.read_sql_query("""
            SELECT
              COALESCE((SELECT party_name FROM party_master p WHERE p.id = r.party_id), 'ALL') AS party,
              from_city, to_city, rate_type, rate
            FROM rate_master r
            ORDER BY party, from_city, to_city
        """, conn)
        conn.close()
        render.dataframe(df_rates, use_container_width=True)

# -------------------------
# SECTION: TOKEN / BILTY
# -------------------------
def section_token(render):
    render.title("📄 Token / Bilty Generation")
    render.info("यहाँ से आप आसानी से Token (Bilty) बना सकते हैं — Marka पहले, बाकी auto-fill।")

    # Determine route based on user office
    office = st.session_state.get("office")
    if st.session_state.get("role") == "OPERATOR":
        if office == "DELHI":
            from_city, to_city = "DELHI", "MUMBAI"
        elif office == "MUMBAI":
            from_city, to_city = "MUMBAI", "DELHI"
        else:
            from_city, to_city = "DELHI", "MUMBAI"
        render.markdown(f"**Route (auto):** {from_city} ➜ {to_city}")
    else:
        from_city = render.selectbox("From City (Select)", ["DELHI", "MUMBAI"], key="token_from")
        to_city = "MUMBAI" if from_city == "DELHI" else "DELHI"
        render.markdown(f"**To City (auto):** {to_city}")

    # fetch marka list
    markas = get_all_markas()
    if not markas:
        render.error("❌ कोई Marka मौजूद नहीं है — पहले Party Master में Marka डालें।")
        return

    # build options as searchable strings
    options = [f"{m['marka']}  —  {m['party_name']}" for m in markas]
    selected_opt = render.selectbox("Marka (मार्का) — select / search", options, index=0, key="token_marka_select")
    sel_index = options.index(selected_opt)
    selected_marka = markas[sel_index]["marka"]
    selected_party_id = markas[sel_index]["party_id"]
    selected_party_name = markas[sel_index]["party_name"]

    render.text_input("Party (पार्टी)", value=selected_party_name, disabled=True, key="token_party_disp")

    render.markdown("---")
    col1, col2 = render.columns(2)
    with col1:
        weight = render.number_input("Weight (KG) / वजन (KG)", min_value=0.0, step=0.5, value=0.0, key="token_weight")
        packages = render.number_input("Packages / पार्सल", min_value=1, step=1, value=1, key="token_packages")
    with col2:
        rate = render.number_input("Rate / दर (per KG)", min_value=0.0, step=0.5, value=0.0, key="token_rate")
        driver_mobile = render.text_input("Driver Mobile (optional)", key="token_driver_mobile")

    amount = weight * rate
    render.markdown(f"**Amount / राशि:** ₹ {amount:.2f}")

    if render.button("➕ Create Token (टोकन बनाओ)", key="create_token_btn"):
        token_no = create_token_in_db(
            marka=selected_marka,
            party_id=selected_party_id,
            weight=weight,
            pkgs=int(packages),
            rate=rate,
            rate_type=None,
            driver_mobile=driver_mobile,
            from_city=from_city,
            to_city=to_city
        )
        render.success(f"✅ Token created — Token No: {token_no}")

        # prepare token dict for PDF
        timestamp = datetime.utcnow().isoformat()
        token_for_pdf = {
            "id": token_no,
            "datetime": timestamp,
            "party_name": selected_party_name,
            "marka": selected_marka,
            "from_city": from_city,
            "to_city": to_city,
            "weight": weight,
            "rate": rate,
            "amount": amount,
            "packages": packages,
            "driver_mobile": driver_mobile
        }

        # generate PDF inline (simple)
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(300, 800, "TOKEN / BILTY")
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, 760, f"Token No: {token_for_pdf['id']}")
        c.setFont("Helvetica", 12)
        y = 730
        rows = [
            ("Date/Time", token_for_pdf["datetime"]),
            ("Party", token_for_pdf["party_name"]),
            ("Marka", token_for_pdf["marka"]),
            ("Route", f"{token_for_pdf['from_city']} ➜ {token_for_pdf['to_city']}"),
            ("Weight (KG)", token_for_pdf["weight"]),
            ("Packages", token_for_pdf["packages"]),
            ("Rate", token_for_pdf["rate"]),
            ("Amount (₹)", token_for_pdf["amount"]),
            ("Driver Mobile", token_for_pdf["driver_mobile"] or "-"),
        ]
        for label, val in rows:
            c.drawString(50, y, f"{label}: {val}")
            y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y - 10, "Thank you")
        c.showPage()
        c.save()
        buffer.seek(0)

        render.download_button(
            label="📥 Download Token PDF",
            data=buffer,
            file_name=f"TOKEN_{token_no}.pdf",
            mime="application/pdf"
        )

# -------------------------
# SECTION: CHALLAN / LOADING
# -------------------------
def section_challan(render):
    render.title("🚛 Challan / Loading")
    render.info("Pending tokens चुनकर challan बनाओ — Operator के लिए Route auto होगा।")

    # Determine route
    office = st.session_state.get("office")
    if st.session_state.get("role") == "OPERATOR":
        if office == "DELHI":
            from_city, to_city = "DELHI", "MUMBAI"
        elif office == "MUMBAI":
            from_city, to_city = "MUMBAI", "DELHI"
        else:
            from_city, to_city = None, None
        render.markdown(f"**Route (auto):** {from_city} ➜ {to_city}" if from_city else "Route: —")
    else:
        from_city = render.selectbox("From City", ["DELHI", "MUMBAI"], key="challan_from")
        to_city = "MUMBAI" if from_city == "DELHI" else "DELHI"
        render.markdown(f"To City (auto): {to_city}")

    # fetch pending tokens for this route
    pending = get_pending_tokens(from_city=from_city, to_city=to_city) if from_city else get_pending_tokens()
    if not pending:
        render.warning("अभी कोई pending token नहीं है।")
        return

    grouped = group_tokens_by_marka(pending)

    render.subheader("Select Tokens (Grouped by Marka)")
    selected_token_ids = []
    for grp in grouped:
        render.markdown(f"### Marka: {grp['marka']}")
        for t in grp["tokens"]:
            label = f"Token {t['token_no']} | {t.get('weight',0)}kg | ₹{t.get('amount',0):.2f}"
            checked = render.checkbox(label, key=f"t_{t['id']}")
            if checked:
                selected_token_ids.append(t["id"])

    if not selected_token_ids:
        render.info("कम से कम 1 token select करें।")
        return

    # Auto-prefill from/to from first selected token
    first = next((t for t in pending if t["id"] in selected_token_ids), None)
    if first:
        from_city = first["from_city"]
        to_city = first["to_city"]

    render.markdown("---")
    render.subheader("Challan Details")
    challan_no = get_next_challan_no()
    render.text_input("Challan No (Auto)", value=str(challan_no), disabled=True, key="challan_no_disp")
    date_str = render.text_input("Challan Date", value=datetime.now().strftime("%d/%m/%Y"), key="challan_date")

    col1, col2 = render.columns(2)
    with col1:
        from_city_disp = render.text_input("From City", value=from_city, disabled=True, key="challan_from_disp")
        truck_no = render.text_input("Truck No.", key="challan_truck")
    with col2:
        to_city_disp = render.text_input("To City", value=to_city, disabled=True, key="challan_to_disp")
        driver_name = render.text_input("Driver Name", key="challan_driver_name")

    col3, col4 = render.columns(2)
    with col3:
        driver_mobile = render.text_input("Driver Mobile", key="challan_driver_mobile")
        hire = render.number_input("Hire (गाड़ी भाड़ा)", min_value=0.0, value=0.0, key="challan_hire")
    with col4:
        loading_hamali = render.number_input("Loading Hamali", min_value=0.0, value=0.0, key="challan_loading")
        unloading_hamali = render.number_input("Unloading Hamali", min_value=0.0, value=0.0, key="challan_unloading")

    other_exp = render.number_input("Other Expenses", min_value=0.0, value=0.0, key="challan_other")

    # Calculate totals
    total_weight = sum(t.get("weight",0) or 0 for t in pending if t["id"] in selected_token_ids)
    total_amount = sum(t.get("amount",0) or 0 for t in pending if t["id"] in selected_token_ids)
    render.markdown(f"**Total Weight:** {total_weight} kg — **Total Amount:** ₹ {total_amount:.2f}")

    if render.button("✅ Create Challan & Download PDF", key="create_challan_btn"):
        # create challan via db helper
        challan_no_created = create_challan(
            token_ids=selected_token_ids,
            from_city=from_city,
            to_city=to_city,
            truck_no=truck_no,
            driver_name=driver_name,
            driver_mobile=driver_mobile,
            hire=hire,
            loading_hamali=loading_hamali,
            unloading_hamali=unloading_hamali,
            other_exp=other_exp
        )

        # prepare rows for challan_pdf
        rows = []
        for t in pending:
            if t["id"] in selected_token_ids:
                rows.append({"token_no": t.get("token_no"), "weight": t.get("weight",0), "amount": t.get("amount",0), "party_name": t.get("party_name","")})

        challan_data = {
            "challan_no": challan_no_created,
            "date": date_str,
            "from_city": from_city,
            "to_city": to_city,
            "truck_no": truck_no,
            "driver_name": driver_name,
            "driver_mobile": driver_mobile,
            "hire": hire,
            "loading_hamali": loading_hamali,
            "unloading_hamali": unloading_hamali,
            "other_exp": other_exp,
            "balance": total_amount - (hire + loading_hamali + unloading_hamali + other_exp)
        }

        pdf_buf = challan_pdf(challan_data, rows)

        render.success(f"✅ Challan {challan_no_created} तैयार हो गया!")
        render.download_button(
            "⬇️ Download Challan PDF",
            data=pdf_buf,
            file_name=f"CHALLAN_{challan_no_created}.pdf",
            mime="application/pdf"
        )

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
            SELECT 
                t.date_time,
                t.id AS token_no,
                t.amount,
                t.party_id
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
                            "d": "Date",
                            "tokens": "Tokens",
                            "weight": "Total Weight",
                            "amount": "Total Amount"
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
        cur.execute("""
            INSERT INTO delivery_log (token_id, delivery_date, receiver_name, signature)
            VALUES (?, ?, ?, ?)
        """, (token_id, delivery_date.strftime("%d-%m-%Y"), receiver_name, signature_path))
        cur.execute("UPDATE tokens SET status='DELIVERED' WHERE id=?", (token_id,))
        conn.commit()
        conn.close()
        area.success("🚚 Delivery Updated Successfully!")

# -------------------------
# ROUTER: call the right section
# -------------------------
if page == "token":
    section_token(main_render)
elif page == "challan":
    section_challan(main_render)
elif page == "party":
    if st.session_state.get("role") == "ADMIN":
        section_party(main_render)
    else:
        st.error("❌ Access Denied: Operators cannot access Party Master")
elif page == "item_rate":
    if st.session_state.get("role") == "ADMIN":
        section_item_rate(main_render)
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
    # Default to Token page for operators; admin gets home summary
    if st.session_state.get("role") == "OPERATOR":
        st.session_state["combined_page"] = "token"
        safe_rerun()
    else:
        st.title("👋 Welcome to Transport Management — All Sections")
        st.write("Use the sidebar to navigate to any section. This unified file contains all admin/operator pages.")
        parties = get_party_list()
        if parties:
            st.success(f"Total Parties: {len(parties)}")
        else:
            st.info("👉 First add parties in Party Master.")
