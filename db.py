# db.py
import sqlite3
import hashlib
from datetime import datetime
import os

# Store DB next to this file so it's consistent regardless of current working dir
DB_PATH = os.path.join(os.path.dirname(__file__), "tms.db")


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # -----------------------------------------------------
    # 1) PARTY MASTER
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS party_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_name TEXT UNIQUE,
        address TEXT,
        mobile TEXT,
        gst_no TEXT,
        marka TEXT,
        default_rate_per_kg REAL,
        default_rate_per_parcel REAL
    )
    """)

    # -----------------------------------------------------
    # 2) ITEM MASTER
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS item_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE,
        description TEXT
    )
    """)

    # -----------------------------------------------------
    # 3) RATE MASTER (ROUTE WISE)
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rate_master (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id INTEGER,
        from_city TEXT,
        to_city TEXT,
        rate_type TEXT,
        rate REAL,
        FOREIGN KEY(party_id) REFERENCES party_master(id)
    )
    """)

    # -----------------------------------------------------
    # 4) TOKENS / BILTY TABLE
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_no INTEGER,
        date_time TEXT,
        party_id INTEGER,
        consignor TEXT,
        consignee TEXT,
        marka TEXT,
        from_city TEXT,
        to_city TEXT,
        weight REAL,
        pkgs INTEGER,
        rate REAL,
        rate_type TEXT,
        amount REAL,
        truck_no TEXT,
        driver_name TEXT,
        driver_mobile TEXT,
        status TEXT,
        challan_id INTEGER,
        bill_id INTEGER,
        FOREIGN KEY(party_id) REFERENCES party_master(id)
    )
    """)

    # -----------------------------------------------------
    # 5) CHALLAN MASTER
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_no INTEGER,
        date TEXT,
        from_city TEXT,
        to_city TEXT,
        truck_no TEXT,
        driver_name TEXT,
        driver_mobile TEXT,
        hire REAL,
        loading_hamali REAL,
        unloading_hamali REAL,
        other_exp REAL,
        balance REAL
    )
    """)

    # -----------------------------------------------------
    # 6) CHALLAN-TOKEN MAPPING TABLE
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challan_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challan_id INTEGER,
        token_id INTEGER,
        FOREIGN KEY(challan_id) REFERENCES challan(id),
        FOREIGN KEY(token_id) REFERENCES tokens(id)
    )
    """)

    # -----------------------------------------------------
    # 7) BILLS / INVOICE TABLE
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_no INTEGER,
        party_id INTEGER,
        from_date TEXT,
        to_date TEXT,
        subtotal REAL,
        gst_percent REAL,
        gst_amount REAL,
        total REAL,
        created_at TEXT,
        FOREIGN KEY(party_id) REFERENCES party_master(id)
    )
    """)

    # -----------------------------------------------------
    # 8) PAYMENTS TABLE
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id INTEGER,
        date TEXT,
        amount REAL,
        mode TEXT,
        remark TEXT,
        FOREIGN KEY(party_id) REFERENCES party_master(id)
    )
    """)

    # -----------------------------------------------------
    # 9) DELIVERY LOG TABLE
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS delivery_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_id INTEGER,
        delivery_date TEXT,
        receiver_name TEXT,
        signature TEXT,
        FOREIGN KEY(token_id) REFERENCES tokens(id)
    )
    """)

    # -----------------------------------------------------
    # 10) USERS TABLE (AUTH)
    # -----------------------------------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        office_location TEXT,
        created_at TEXT
    )
    """)

    conn.commit()

    # seed default admin if not exists
    cur.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
    if cur.fetchone()[0] == 0:
        pw_hash = hash_pw("admin123")
        cur.execute(
            "INSERT INTO users (username, password_hash, role, office_location, created_at) VALUES (?, ?, ?, ?, ?)",
            ("admin", pw_hash, "ADMIN", None, datetime.utcnow().isoformat())
        )
        conn.commit()

    conn.close()


# ---------------------------------------------------------
# PASSWORD HASHING & USER HELPERS
# ---------------------------------------------------------
def hash_pw(plain_text: str):
    """Return sha256 hex digest of the plain_text password."""
    return hashlib.sha256(plain_text.encode()).hexdigest()


def create_user(username: str, password: str, role: str = "OPERATOR", office: str = None):
    """Create a user and return new user id.

    Raises:
        ValueError: if username already exists.
    """
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role, office_location, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, hash_pw(password), role, office, datetime.utcnow().isoformat())
        )
        conn.commit()
        user_id = cur.lastrowid
    except sqlite3.IntegrityError as e:
        conn.rollback()
        conn.close()
        raise ValueError(f"User '{username}' already exists") from e
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return user_id


def get_user(username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, office_location, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "role": row[2],
        "office_location": row[3],
        "password_hash": row[4]
    }


def verify_user(username: str, password: str):
    u = get_user(username)
    if not u:
        return None
    if u["password_hash"] == hash_pw(password):
        return {"id": u["id"], "username": u["username"], "role": u["role"], "office_location": u["office_location"]}
    return None


# ---------------------------------------------------------
# GET NEXT AUTO NUMBERS
# ---------------------------------------------------------
def get_next_token_no():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(token_no), 0) + 1 FROM tokens")
    nxt = cur.fetchone()[0]
    conn.close()
    return nxt


def get_next_challan_no():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(challan_no), 0) + 1 FROM challan")
    nxt = cur.fetchone()[0]
    conn.close()
    return nxt


def get_next_bill_no():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(bill_no), 0) + 1 FROM bills")
    nxt = cur.fetchone()[0]
    conn.close()
    return nxt


# ---------------------------------------------------------
# PARTY LIST HELPER
# ---------------------------------------------------------
def get_party_list():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, party_name, marka FROM party_master ORDER BY party_name")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------
# PARTY BALANCE = TOTAL TOKENS - TOTAL PAYMENTS
# ---------------------------------------------------------
def compute_party_balance(party_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COALESCE(SUM(amount),0) FROM tokens WHERE party_id=?", 
                (party_id,))
    token_total = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE party_id=?", 
                (party_id,))
    paid = cur.fetchone()[0]

    conn.close()
    return token_total - paid


# =========================================================
# MARKA & TOKEN HELPERS
# =========================================================
def get_all_markas():
    """
    Return a list of ALL markas with associated party info.
    One party can have multiple markas (comma-separated in DB).
    Each item: {'marka': str, 'party_id': int, 'party_name': str}
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, party_name, marka 
        FROM party_master 
        WHERE marka IS NOT NULL AND TRIM(marka) <> '' 
        ORDER BY party_name, marka
    """)
    rows = cur.fetchall()
    conn.close()
    
    out = []
    for r in rows:
        party_id, party_name, marka_field = r
        # Split comma-separated markas
        if marka_field and ',' in marka_field:
            markas = [m.strip() for m in marka_field.split(',') if m.strip()]
            for single_marka in markas:
                out.append({
                    'marka': single_marka, 
                    'party_id': party_id, 
                    'party_name': party_name
                })
        else:
            # Single marka
            out.append({
                'marka': marka_field, 
                'party_id': party_id, 
                'party_name': party_name
            })
    return out


def create_token_in_db(marka: str, party_id: int, weight: float, pkgs: int, rate: float,
                       rate_type: str = None, driver_mobile: str = None, from_city: str = None,
                       to_city: str = None, consignor: str = None, consignee: str = None):
    """
    Inserts a token (bilty) with minimal required fields.
    Returns inserted token_no (integer).
    """
    token_no = get_next_token_no()
    now = datetime.utcnow().isoformat()
    amount = (weight or 0.0) * (rate or 0.0)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tokens (token_no, date_time, party_id, consignor, consignee, marka, from_city, to_city,
                            weight, pkgs, rate, rate_type, amount, driver_mobile, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (token_no, now, party_id, consignor, consignee, marka, from_city, to_city,
          weight, pkgs, rate, rate_type, amount, driver_mobile, "PENDING"))
    conn.commit()
    conn.close()
    return token_no


def get_pending_tokens(from_city: str = None, to_city: str = None):
    """
    Returns list of pending tokens (status = 'PENDING') with party names.
    Each item is a dict with token fields including party_name.
    Case-insensitive matching for from/to city to avoid missed rows.
    """
    conn = get_conn()
    cur = conn.cursor()

    if from_city and to_city:
        cur.execute("""
            SELECT t.id, t.token_no, t.date_time, t.party_id, t.marka, 
                   t.from_city, t.to_city, t.weight, t.pkgs, t.rate, t.amount,
                   COALESCE(p.party_name, 'Unknown') as party_name
            FROM tokens t
            LEFT JOIN party_master p ON t.party_id = p.id
            WHERE t.status = 'PENDING' 
              AND UPPER(t.from_city) = UPPER(?) 
              AND UPPER(t.to_city) = UPPER(?)
            ORDER BY t.marka, t.token_no
        """, (from_city, to_city))
    elif from_city:
        cur.execute("""
            SELECT t.id, t.token_no, t.date_time, t.party_id, t.marka, 
                   t.from_city, t.to_city, t.weight, t.pkgs, t.rate, t.amount,
                   COALESCE(p.party_name, 'Unknown') as party_name
            FROM tokens t
            LEFT JOIN party_master p ON t.party_id = p.id
            WHERE t.status = 'PENDING' AND UPPER(t.from_city) = UPPER(?)
            ORDER BY t.marka, t.token_no
        """, (from_city,))
    else:
        cur.execute("""
            SELECT t.id, t.token_no, t.date_time, t.party_id, t.marka, 
                   t.from_city, t.to_city, t.weight, t.pkgs, t.rate, t.amount,
                   COALESCE(p.party_name, 'Unknown') as party_name
            FROM tokens t
            LEFT JOIN party_master p ON t.party_id = p.id
            WHERE t.status = 'PENDING'
            ORDER BY t.marka, t.token_no
        """)

    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "token_no": r[1],
            "date_time": r[2],
            "party_id": r[3],
            "marka": r[4],
            "from_city": r[5],
            "to_city": r[6],
            "weight": r[7],
            "pkgs": r[8],
            "rate": r[9],
            "amount": r[10],
            "party_name": r[11]  # CRITICAL: party_name included
        })
    return out


def group_tokens_by_marka(tokens_list):
    """
    Accepts list of tokens (dicts) and returns grouped list:
    [{'marka': 'X', 'tokens': [ ... ]}, ...]
    """
    grouped = {}
    for t in tokens_list:
        m = t.get('marka') or "UNKNOWN"
        grouped.setdefault(m, []).append(t)
    out = []
    for k in sorted(grouped.keys()):
        out.append({"marka": k, "tokens": grouped[k]})
    return out


# =========================================================
# CHALLAN HELPERS
# =========================================================
def create_challan(token_ids: list, from_city: str, to_city: str, truck_no: str,
                   driver_name: str, driver_mobile: str, hire: float = 0.0,
                   loading_hamali: float = 0.0, unloading_hamali: float = 0.0, other_exp: float = 0.0):
    """
    Creates a challan with given token ids.
    Marks tokens as LOADED and creates mapping entries.
    Returns challan_no (int).
    """
    if not token_ids:
        raise ValueError("No tokens provided for challan creation")

    conn = get_conn()
    cur = conn.cursor()
    placeholder = ",".join(["?"] * len(token_ids))
    cur.execute(f"SELECT COALESCE(SUM(amount),0), COALESCE(SUM(weight),0) FROM tokens WHERE id IN ({placeholder})", tuple(token_ids))
    totals = cur.fetchone()
    total_amount = totals[0] or 0.0
    total_weight = totals[1] or 0.0

    challan_no = get_next_challan_no()
    today = datetime.utcnow().date().isoformat()
    balance = total_amount - ((hire or 0.0) + (loading_hamali or 0.0) + (unloading_hamali or 0.0) + (other_exp or 0.0))

    cur.execute("""
        INSERT INTO challan (challan_no, date, from_city, to_city, truck_no, driver_name, driver_mobile,
                             hire, loading_hamali, unloading_hamali, other_exp, balance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (challan_no, today, from_city, to_city, truck_no, driver_name, driver_mobile,
          hire, loading_hamali, unloading_hamali, other_exp, balance))
    challan_id = cur.lastrowid

    for tid in token_ids:
        cur.execute("INSERT INTO challan_tokens (challan_id, token_id) VALUES (?, ?)", (challan_id, tid))
        cur.execute("UPDATE tokens SET status = ?, challan_id = ? WHERE id = ?", ("LOADED", challan_id, tid))

    conn.commit()
    conn.close()
    return challan_no


# =========================================================
# DELIVERY HELPERS
# =========================================================
def mark_token_delivered(token_id: int, receiver_name: str = None, signature_text: str = None):
    """
    Mark a token as delivered and log delivery.
    """
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute("UPDATE tokens SET status = ? WHERE id = ?", ("DELIVERED", token_id))

    cur.execute("""
        INSERT INTO delivery_log (token_id, delivery_date, receiver_name, signature)
        VALUES (?, ?, ?, ?)
    """, (token_id, now, receiver_name, signature_text))

    conn.commit()
    conn.close()


# =========================================================
# OTHER HELPERS
# =========================================================
def get_token_by_token_no(token_no: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, token_no, party_id, marka, status, amount, weight, pkgs, from_city, to_city FROM tokens WHERE token_no = ?", (token_no,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r[0],
        "token_no": r[1],
        "party_id": r[2],
        "marka": r[3],
        "status": r[4],
        "amount": r[5],
        "weight": r[6],
        "pkgs": r[7],
        "from_city": r[8],
        "to_city": r[9]
    }