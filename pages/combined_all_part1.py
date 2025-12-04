# pages/combined_all_part1.py - WITH DASHBOARD
import streamlit as st
import pandas as pd
from datetime import datetime, date
import io

# Import shared utilities
from auth_utils import safe_rerun, hide_default_sidebar, show_default_sidebar

# DB helpers
from db import (
    get_conn, get_party_list, get_all_markas,
    create_token_in_db, get_pending_tokens, group_tokens_by_marka,
    create_challan, get_next_challan_no
)

# -------------------------
# Navigation handlers
# -------------------------
def nav_to_page(page_name):
    """Navigate to a page"""
    st.session_state["combined_page"] = page_name

def get_main_render():
    """Return the right render area based on user role."""
    role = st.session_state.get("role")

    if role == "ADMIN":
        admin_top_buttons()
        return st  # render in main area
    else:
        hide_default_sidebar()
        return operator_left_panel()


# -------------------------
# Operator left-panel menu
# -------------------------
def operator_left_panel():
    hide_default_sidebar()
    left_col, main_col = st.columns([1, 4], gap="small")
    with left_col:
        st.markdown("### 🚚 Operator Menu")

        if st.button("Token / Bilty", key="op_btn_token", use_container_width=True):
            nav_to_page("token")
            safe_rerun()

        if st.button("Challan / Loading", key="op_btn_challan", use_container_width=True):
            nav_to_page("challan")
            safe_rerun()

        st.markdown("---")
        st.markdown(f"**User:** {st.session_state.get('username')}")
        st.markdown(f"**Office:** {st.session_state.get('office')}")

    return main_col


# -------------------------
# Admin sidebar menu
# -------------------------
def admin_top_buttons():
    st.sidebar.markdown("### 📋 Admin Menu")

    if st.sidebar.button("🏠 Home", key="admin_btn_home", use_container_width=True):
        nav_to_page("home")
        safe_rerun()
    
    if st.sidebar.button("📊 Dashboard", key="admin_btn_dashboard", use_container_width=True):
        nav_to_page("dashboard")
        safe_rerun()

    if st.sidebar.button("👥 Party Master", key="admin_btn_party", use_container_width=True):
        nav_to_page("party")
        safe_rerun()

    if st.sidebar.button("📦 Item / Rate Master", key="admin_btn_item_rate", use_container_width=True):
        nav_to_page("item_rate")
        safe_rerun()

    if st.sidebar.button("📄 Token / Bilty", key="admin_btn_token", use_container_width=True):
        nav_to_page("token")
        safe_rerun()

    if st.sidebar.button("🚛 Challan / Loading", key="admin_btn_challan", use_container_width=True):
        nav_to_page("challan")
        safe_rerun()

    st.sidebar.markdown("---")

    if st.sidebar.button("💰 Payments", key="admin_btn_payments", use_container_width=True):
        nav_to_page("payments")
        safe_rerun()

    if st.sidebar.button("🧾 Billing", key="admin_btn_billing", use_container_width=True):
        nav_to_page("billing")
        safe_rerun()

    if st.sidebar.button("📚 Ledger", key="admin_btn_ledger", use_container_width=True):
        nav_to_page("ledger")
        safe_rerun()

    if st.sidebar.button("📊 Reports", key="admin_btn_reports", use_container_width=True):
        nav_to_page("reports")
        safe_rerun()

    if st.sidebar.button("📦 Delivery Entry", key="admin_btn_delivery", use_container_width=True):
        nav_to_page("delivery")
        safe_rerun()


# -------------------------
# SECTION: INTERACTIVE DASHBOARD
# -------------------------
def section_dashboard(render):
    render.title("📊 Transport Management Dashboard")
    render.info("Real-time insights and analytics with interactive visualizations")

    # Filters
    col_f1, col_f2 = render.columns(2)
    with col_f1:
        date_range = render.selectbox("Date Range", 
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Month"],
            key="dash_date_range")
    with col_f2:
        route_filter = render.selectbox("Route Filter",
            ["All Routes", "Delhi → Mumbai", "Mumbai → Delhi"],
            key="dash_route")

    render.markdown("---")

    # Generate dummy data
    def generate_dashboard_data():
        from datetime import timedelta
        dates = [(datetime.now() - timedelta(days=i)).strftime("%d %b") for i in range(6, -1, -1)]
        
        daily_data = pd.DataFrame({
            'Date': dates,
            'Tokens': [45, 52, 38, 61, 48, 35, 28],
            'Weight (kg)': [2800, 3200, 2400, 3800, 3000, 2100, 1700],
            'Revenue (₹)': [68000, 78000, 58000, 92000, 72000, 51000, 41000]
        })
        
        status_data = pd.DataFrame({
            'Status': ['Pending', 'Loaded', 'In Transit', 'Delivered'],
            'Count': [45, 78, 92, 132]
        })
        
        route_data = pd.DataFrame({
            'Route': ['Delhi → Mumbai', 'Mumbai → Delhi', 'Delhi → Pune', 'Mumbai → Bangalore'],
            'Tokens': [145, 132, 45, 25]
        })
        
        top_parties = pd.DataFrame({
            'Party': ['ABC Logistics', 'XYZ Traders', 'PQR Enterprises', 'LMN Industries', 'RST Corporation'],
            'Tokens': [85, 72, 64, 58, 45],
            'Revenue': [245000, 198000, 176000, 164000, 142000],
            'Outstanding': [45000, 22000, 0, 38000, 15000]
        })
        
        return daily_data, status_data, route_data, top_parties

    daily_data, status_data, route_data, top_parties = generate_dashboard_data()

    # KPI Cards
    kpi1, kpi2, kpi3, kpi4 = render.columns(4)
    
    with kpi1:
        render.markdown("""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 10px; color: white; text-align: center;'>
                <h4 style='margin:0; font-size:14px;'>💰 Total Revenue</h4>
                <h1 style='margin:10px 0; font-size:32px;'>₹4.6L</h1>
                <p style='margin:0; font-size:12px;'>↑ 12.5% from last week</p>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi2:
        render.markdown("""
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        padding: 20px; border-radius: 10px; color: white; text-align: center;'>
                <h4 style='margin:0; font-size:14px;'>📦 Total Tokens</h4>
                <h1 style='margin:10px 0; font-size:32px;'>307</h1>
                <p style='margin:0; font-size:12px;'>↑ 8.3% from last week</p>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi3:
        render.markdown("""
            <div style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                        padding: 20px; border-radius: 10px; color: white; text-align: center;'>
                <h4 style='margin:0; font-size:14px;'>🚛 Active Trucks</h4>
                <h1 style='margin:10px 0; font-size:32px;'>45</h1>
                <p style='margin:0; font-size:12px;'>↓ 2.1% from last week</p>
            </div>
        """, unsafe_allow_html=True)
    
    with kpi4:
        render.markdown("""
            <div style='background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); 
                        padding: 20px; border-radius: 10px; color: white; text-align: center;'>
                <h4 style='margin:0; font-size:14px;'>👥 Active Parties</h4>
                <h1 style='margin:10px 0; font-size:32px;'>28</h1>
                <p style='margin:0; font-size:12px;'>↑ 5.7% from last week</p>
            </div>
        """, unsafe_allow_html=True)

    render.markdown("---")

    # Charts Row 1
    chart_col1, chart_col2 = render.columns(2)
    
    with chart_col1:
        render.subheader("📈 Daily Booking Trend")
        render.line_chart(daily_data.set_index('Date')[['Tokens', 'Revenue (₹)']])
    
    with chart_col2:
        render.subheader("📦 Token Status Distribution")
        render.bar_chart(status_data.set_index('Status'))

    # Charts Row 2
    chart_col3, chart_col4 = render.columns(2)
    
    with chart_col3:
        render.subheader("🗺️ Route-wise Distribution")
        render.bar_chart(route_data.set_index('Route'))
    
    with chart_col4:
        render.subheader("💹 Top 5 Parties by Tokens")
        render.bar_chart(top_parties.set_index('Party')['Tokens'])

    render.markdown("---")

    # Top Parties Table
    render.subheader("👥 Top 5 Parties Details")
    
    # Format the dataframe for display
    display_df = top_parties.copy()
    display_df['Revenue'] = display_df['Revenue'].apply(lambda x: f"₹{x/1000:.0f}K")
    display_df['Outstanding'] = display_df['Outstanding'].apply(lambda x: f"₹{x/1000:.0f}K")
    display_df['Status'] = display_df['Outstanding'].apply(
        lambda x: '🟢 Clear' if x == '₹0K' else '🟡 Pending' if int(x.replace('₹','').replace('K','')) < 30 else '🔴 High'
    )
    
    render.dataframe(display_df, use_container_width=True, height=250)

    render.markdown("---")

    # Additional Metrics
    metric_col1, metric_col2, metric_col3 = render.columns(3)
    
    with metric_col1:
        render.metric(
            label="⏱️ Avg Delivery Time",
            value="2.4 days",
            delta="-0.3 days"
        )
    
    with metric_col2:
        render.metric(
            label="😊 Customer Satisfaction",
            value="94.2%",
            delta="2.1%"
        )
    
    with metric_col3:
        render.metric(
            label="🚛 Fleet Utilization",
            value="87.5%",
            delta="4.2%"
        )


# -------------------------
# SECTION: PARTY MASTER
# -------------------------
def section_party(render):
    render.title("👥 Party Master (Party Register)")
    render.info("यहाँ से Party add/update करें। Multiple Markas के लिए comma से अलग करें।")

    with render.form("party_form"):
        party_name = render.text_input("Party Name *", key="party_name_input")
        address = render.text_area("Address", key="party_address")
        mobile = render.text_input("Mobile Number", key="party_mobile")
        gst_no = render.text_input("GST No. (optional)", key="party_gst")
        
        marka = render.text_area(
            "Marka / Sign (Multiple markas: comma-separated)", 
            key="party_marka",
            help="Example: ABC, XYZ, 123"
        )
        
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
    df = pd.read_sql_query("SELECT party_name, mobile, marka, default_rate_per_kg FROM party_master ORDER BY party_name", conn)
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

    markas = get_all_markas()
    if not markas:
        render.error("❌ कोई Marka मौजूद नहीं है — पहले Party Master में Marka डालें।")
        return

    options = [f"{m['marka']}  —  {m['party_name']}" for m in markas]
    
    selected_opt = render.selectbox(
        "Marka (मार्का) — select / search", 
        options, 
        index=0, 
        key="token_marka_select"
    )
    
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

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(300, 800, "TOKEN / BILTY")
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, 760, f"Token No: {token_no}")
        c.setFont("Helvetica", 12)
        y = 730
        rows = [
            ("Date/Time", datetime.utcnow().isoformat()),
            ("Party", selected_party_name),
            ("Marka", selected_marka),
            ("Route", f"{from_city} ➜ {to_city}"),
            ("Weight (KG)", weight),
            ("Packages", packages),
            ("Rate", rate),
            ("Amount (₹)", amount),
            ("Driver Mobile", driver_mobile or "-"),
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

    total_weight = sum(t.get("weight",0) or 0 for t in pending if t["id"] in selected_token_ids)
    total_amount = sum(t.get("amount",0) or 0 for t in pending if t["id"] in selected_token_ids)
    render.markdown(f"**Total Weight:** {total_weight} kg — **Total Amount:** ₹ {total_amount:.2f}")

    if render.button("✅ Create Challan", key="create_challan_btn"):
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

        try:
            from utils.pdf_utils import challan_pdf
            rows = []
            for t in pending:
                if t["id"] in selected_token_ids:
                    rows.append({
                        "token_no": t.get("token_no"),
                        "weight": t.get("weight",0),
                        "amount": t.get("amount",0),
                        "party_name": t.get("party_name","")
                    })

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
        except ImportError:
            render.success(f"✅ Challan {challan_no_created} created! (PDF generation not available)")