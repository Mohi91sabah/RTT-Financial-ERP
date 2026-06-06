import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import date

# =====================================================
# RTT Financial ERP - Full Improved Version with Charts
# =====================================================

st.set_page_config(page_title="RTT Financial ERP", page_icon="💼", layout="wide")

APP_USERNAME = st.secrets["credentials"]["username"]
APP_PASSWORD = st.secrets["credentials"]["password"]
DB_URL = st.secrets["DB_URL"]

DEFAULT_LOCATIONS = [
    "BGCG_23", "BGC_23", "ROOG_23", "ROOM_23", "ROOESP_23", "ROOP_23",
    "Camp_23", "HO_23", "WQ1_23", "TOTAL_25", "MITAS", "KRK-BP-25"
]

DEFAULT_SUBLOCATIONS = [
    "GRLBG_23", "ZBR_23", "UQ_23", "MANPR_23", "SPAS_23", "EX_23",
    "QUR_23", "BNGL-25", "NR-NGL_25", "GRLRO_23", "EITAR_23", "MPTAR_23",
    "EISP_23", "MPSP_23", "MPMNT_23", "CMNT_23", "EIMNT_23", "EIESP_23",
    "PWRI_23", "PWRI2_23", "DG02_PWD", "QAWPT_23", "MWP_23", "FFF_23",
    "CPSs_23", "FLWLN_23", "RTPFL_23", "CMSN_23", "KBR_23", "WOD_23",
    "E&I-MAJ", "Kiosk-25", "OHTL_25", "CmpSB_23", "MWS_23", "HO_SB_23",
    "WQ1SB_23", "GRLTOT_25", "MITSOHTL", "GRL-KR-BP-25"
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
EXPENSE_CATEGORIES = [
    "Fuel", "Materials", "Transportation", "Accommodation", "Tools", "Consumables",
    "Site Expense", "Office Expense", "Manpower", "Equipment", "Other"
]
ADVANCE_TYPES = ["Salary Advance", "Personal Advance", "Work Advance", "Procurement Advance", "Site Advance", "Other"]
PAYMENT_METHODS = ["Cash", "Bank Transfer", "Cheque", "Other"]
ATTACH_TYPES = ["pdf", "jpg", "jpeg", "png", "xlsx", "xls", "docx", "doc"]


# =====================================================
# DATABASE
# =====================================================

@st.cache_resource(show_spinner=False)
def get_conn():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    return conn


def clear_app_cache():
    st.cache_data.clear()


def execute(sql, params=(), return_id=False):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            new_id = cur.fetchone()[0] if return_id else None
        conn.commit()
        clear_app_cache()
        return new_id
    except Exception:
        conn.rollback()
        raise


@st.cache_data(ttl=60, show_spinner=False)
def query(sql, params=()):
    conn = get_conn()
    return pd.read_sql_query(sql, conn, params=params)


def query_no_cache(sql, params=()):
    conn = get_conn()
    return pd.read_sql_query(sql, conn, params=params)


def init_db():
    sql_list = [
        """CREATE TABLE IF NOT EXISTS settings_locations (
            id SERIAL PRIMARY KEY,
            location TEXT UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS settings_sublocations (
            id SERIAL PRIMARY KEY,
            sublocation TEXT UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            employee_name TEXT UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS revenue (
            id SERIAL PRIMARY KEY,
            invoice_date DATE,
            invoice_no TEXT,
            client TEXT,
            location TEXT,
            sublocation TEXT,
            service_month TEXT,
            service_year INTEGER,
            description TEXT,
            amount NUMERIC DEFAULT 0,
            amount_iqd NUMERIC DEFAULT 0,
            amount_usd NUMERIC DEFAULT 0,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            payment_date DATE,
            voucher_no TEXT,
            supplier_or_employee TEXT,
            location TEXT,
            sublocation TEXT,
            category TEXT,
            description TEXT,
            amount NUMERIC DEFAULT 0,
            amount_iqd NUMERIC DEFAULT 0,
            amount_usd NUMERIC DEFAULT 0,
            payment_method TEXT,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS petty_cash (
            id SERIAL PRIMARY KEY,
            transaction_date DATE,
            voucher_no TEXT,
            employee TEXT,
            location TEXT,
            sublocation TEXT,
            purpose TEXT,
            category TEXT,
            cash_out NUMERIC DEFAULT 0,
            cash_in NUMERIC DEFAULT 0,
            cash_out_iqd NUMERIC DEFAULT 0,
            cash_out_usd NUMERIC DEFAULT 0,
            cash_in_iqd NUMERIC DEFAULT 0,
            cash_in_usd NUMERIC DEFAULT 0,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS employee_advances (
            id SERIAL PRIMARY KEY,
            advance_date DATE,
            employee_name TEXT,
            advance_type TEXT,
            location TEXT,
            sublocation TEXT,
            amount_given NUMERIC DEFAULT 0,
            amount_returned NUMERIC DEFAULT 0,
            amount_given_iqd NUMERIC DEFAULT 0,
            amount_given_usd NUMERIC DEFAULT 0,
            amount_returned_iqd NUMERIC DEFAULT 0,
            amount_returned_usd NUMERIC DEFAULT 0,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS client_payments (
            id SERIAL PRIMARY KEY,
            receipt_date DATE,
            receipt_no TEXT,
            client TEXT,
            revenue_id INTEGER,
            amount_iqd NUMERIC DEFAULT 0,
            amount_usd NUMERIC DEFAULT 0,
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS supplier_payments (
            id SERIAL PRIMARY KEY,
            payment_date DATE,
            payment_no TEXT,
            supplier TEXT,
            expense_id INTEGER,
            amount_iqd NUMERIC DEFAULT 0,
            amount_usd NUMERIC DEFAULT 0,
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS attachments (
            id SERIAL PRIMARY KEY,
            module TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            file_name TEXT,
            file_type TEXT,
            file_data BYTEA,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]

    for sql in sql_list:
        execute(sql)

    alter_list = [
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS location TEXT",
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS sublocation TEXT",
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS service_month TEXT",
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS service_year INTEGER",
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS amount_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS amount_usd NUMERIC DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS location TEXT",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS sublocation TEXT",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS amount_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS amount_usd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS location TEXT",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS sublocation TEXT",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_out_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_out_usd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_in_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_in_usd NUMERIC DEFAULT 0",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS location TEXT",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS sublocation TEXT",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS amount_given_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS amount_given_usd NUMERIC DEFAULT 0",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS amount_returned_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS amount_returned_usd NUMERIC DEFAULT 0",
    ]

    for sql in alter_list:
        execute(sql)

    execute("UPDATE revenue SET amount_usd = COALESCE(amount, 0) WHERE COALESCE(amount_usd, 0)=0 AND COALESCE(amount, 0)<>0")
    execute("UPDATE expenses SET amount_usd = COALESCE(amount, 0) WHERE COALESCE(amount_usd, 0)=0 AND COALESCE(amount, 0)<>0")
    execute("UPDATE petty_cash SET cash_out_usd = COALESCE(cash_out, 0) WHERE COALESCE(cash_out_usd, 0)=0 AND COALESCE(cash_out, 0)<>0")
    execute("UPDATE petty_cash SET cash_in_usd = COALESCE(cash_in, 0) WHERE COALESCE(cash_in_usd, 0)=0 AND COALESCE(cash_in, 0)<>0")
    execute("UPDATE employee_advances SET amount_given_usd = COALESCE(amount_given, 0) WHERE COALESCE(amount_given_usd, 0)=0 AND COALESCE(amount_given, 0)<>0")
    execute("UPDATE employee_advances SET amount_returned_usd = COALESCE(amount_returned, 0) WHERE COALESCE(amount_returned_usd, 0)=0 AND COALESCE(amount_returned, 0)<>0")


def seed_default_settings():
    for loc in DEFAULT_LOCATIONS:
        execute(
            "INSERT INTO settings_locations (location) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM settings_locations WHERE location=%s)",
            (loc.strip(), loc.strip())
        )
    for sub in DEFAULT_SUBLOCATIONS:
        execute(
            "INSERT INTO settings_sublocations (sublocation) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM settings_sublocations WHERE sublocation=%s)",
            (sub.strip(), sub.strip())
        )


# =====================================================
# HELPERS
# =====================================================

def money_usd(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"


def money_iqd(x):
    try:
        return f"{float(x):,.0f} IQD"
    except Exception:
        return "0 IQD"


def amount_value(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def safe_date(value):
    if pd.isna(value) or value == "":
        return date.today()
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return date.today()


def option_index(options, value):
    value = "" if pd.isna(value) else str(value)
    return options.index(value) if value in options else 0


def get_list(table, col):
    try:
        df = query(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} <> '' ORDER BY {col}")
        return df[col].dropna().astype(str).tolist()
    except Exception:
        return []


def download_excel_button(df, file_name, label="Download Excel"):
    if df is None or df.empty:
        return
    output_path = f"/tmp/{file_name}"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    with open(output_path, "rb") as f:
        st.download_button(label, f, file_name=file_name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def show_chart(fig):
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)


# =====================================================
# LOGIN
# =====================================================

def login_page():
    st.title("🔐 RTT Financial ERP Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if username == APP_USERNAME and password == APP_PASSWORD:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success("Login successful.")
            st.rerun()
        else:
            st.error("Invalid username or password.")


def logout_button():
    st.sidebar.write(f"Logged in as: **{st.session_state.get('username', '')}**")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.rerun()


# =====================================================
# ATTACHMENTS
# =====================================================

def save_attachment(module, record_id, uploaded_file):
    if uploaded_file is not None and record_id:
        execute(
            """INSERT INTO attachments (module, record_id, file_name, file_type, file_data)
               VALUES (%s,%s,%s,%s,%s)""",
            (module, int(record_id), uploaded_file.name, uploaded_file.type, psycopg2.Binary(uploaded_file.getvalue())),
        )


def attachment_uploader(key):
    return st.file_uploader("Upload Supporting Document", type=ATTACH_TYPES, key=key)


def show_attachments(module, record_id):
    st.markdown("**Supporting Documents**")
    files = query_no_cache(
        """SELECT id, file_name, file_type, file_data, uploaded_at
           FROM attachments
           WHERE module=%s AND record_id=%s
           ORDER BY uploaded_at DESC""",
        (module, int(record_id)),
    )

    if files.empty:
        st.info("No supporting documents uploaded.")
        return

    for _, row in files.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"📎 {row['file_name']} — {row['uploaded_at']}")
        c2.download_button(
            "Download",
            data=bytes(row["file_data"]),
            file_name=row["file_name"],
            mime=row["file_type"],
            key=f"download_{module}_{record_id}_{row['id']}",
        )
        if c3.button("Delete", key=f"delete_attachment_{module}_{record_id}_{row['id']}"):
            execute("DELETE FROM attachments WHERE id=%s", (int(row["id"]),))
            st.success("Document deleted successfully.")
            st.rerun()


def add_attachment_to_existing(module, record_id):
    with st.expander("➕ Add another supporting document"):
        uploaded = attachment_uploader(f"extra_attach_{module}_{record_id}")
        if st.button("Upload Document", key=f"upload_extra_{module}_{record_id}"):
            if uploaded is None:
                st.warning("Please choose a document first.")
            else:
                save_attachment(module, record_id, uploaded)
                st.success("Document uploaded.")
                st.rerun()


# =====================================================
# CRUD HELPERS
# =====================================================

def crud_single_column(title, table, id_col, value_col, label):
    st.subheader(title)
    with st.expander(f"➕ Add {label}", expanded=True):
        with st.form(f"add_{table}"):
            new_value = st.text_input(f"New {label}")
            if st.form_submit_button(f"Add {label}") and new_value.strip():
                execute(
                    f"INSERT INTO {table} ({value_col}) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM {table} WHERE {value_col}=%s)",
                    (new_value.strip(), new_value.strip()),
                )
                st.success(f"{label} added successfully.")
                st.rerun()

    df = query(f"SELECT {id_col}, {value_col} FROM {table} ORDER BY {value_col}")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not df.empty:
        selected_id = st.selectbox(
            f"Select {label} to edit/delete",
            df[id_col].tolist(),
            format_func=lambda x: df.loc[df[id_col] == x, value_col].iloc[0],
            key=f"select_{table}",
        )
        current_value = df.loc[df[id_col] == selected_id, value_col].iloc[0]
        c1, c2 = st.columns(2)
        with c1:
            with st.form(f"edit_{table}"):
                edited_value = st.text_input(f"Edit {label}", value=current_value)
                if st.form_submit_button("Update") and edited_value.strip():
                    execute(f"UPDATE {table} SET {value_col}=%s WHERE {id_col}=%s", (edited_value.strip(), selected_id))
                    st.success("Updated successfully.")
                    st.rerun()
        with c2:
            st.warning("Delete only if not needed.")
            if st.button(f"Delete selected {label}", key=f"delete_{table}"):
                execute(f"DELETE FROM {table} WHERE {id_col}=%s", (selected_id,))
                st.success("Deleted successfully.")
                st.rerun()


def record_crud(table, date_col, order_col, form_renderer, update_sql, delete_sql, label):
    st.subheader(f"✏️ Edit / Delete {label}")
    df = query(f"SELECT * FROM {table} ORDER BY {order_col} DESC, id DESC LIMIT 300")
    if df.empty:
        st.info(f"No {label.lower()} records found yet.")
        return

    st.caption("Showing latest 300 records only.")
    st.dataframe(df, use_container_width=True, hide_index=True)

    def display_record(row_id):
        row = df[df["id"] == row_id].iloc[0]
        main_date = row.get(date_col, "")
        main_ref = row.get("invoice_no", row.get("voucher_no", row.get("receipt_no", row.get("payment_no", row.get("employee_name", "")))))
        usd = row.get("amount_usd", row.get("cash_out_usd", row.get("amount_given_usd", 0)))
        iqd = row.get("amount_iqd", row.get("cash_out_iqd", row.get("amount_given_iqd", 0)))
        return f"ID {row_id} | {main_date} | {main_ref} | {money_usd(usd)} | {money_iqd(iqd)}"

    selected_id = st.selectbox(
        f"Select {label} record",
        df["id"].tolist(),
        format_func=display_record,
        key=f"select_{table}_record"
    )
    record = df[df["id"] == selected_id].iloc[0]
    show_attachments(table, selected_id)
    add_attachment_to_existing(table, selected_id)
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.form(f"edit_{table}_record"):
            values = form_renderer(record)
            if st.form_submit_button(f"Update {label}"):
                execute(update_sql, (*values, selected_id))
                st.success(f"{label} updated successfully.")
                st.rerun()
    with c2:
        st.warning("Delete is permanent.")
        confirm = st.checkbox(f"I confirm deleting selected {label}", key=f"confirm_delete_{table}")
        if st.button(f"Delete {label}", key=f"delete_{table}_record", disabled=not confirm):
            execute("DELETE FROM attachments WHERE module=%s AND record_id=%s", (table, int(selected_id)))
            execute(delete_sql, (selected_id,))
            st.success(f"{label} and its supporting documents deleted successfully.")
            st.rerun()


# =====================================================
# FORMS
# =====================================================

def revenue_fields(record=None, prefix=""):
    record = record if record is not None else {}
    c1, c2, c3 = st.columns(3)
    invoice_date = c1.date_input("Invoice Date", safe_date(record.get("invoice_date", date.today())), key=f"{prefix}invoice_date")
    invoice_no = c2.text_input("Invoice No", value=str(record.get("invoice_no", "") or ""), key=f"{prefix}invoice_no")
    client = c3.text_input("Client", value=str(record.get("client", "") or ""), key=f"{prefix}client")
    c4, c5, c6 = st.columns(3)
    location = c4.selectbox("Location", [""] + locations, index=option_index([""] + locations, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", [""] + sublocations, index=option_index([""] + sublocations, record.get("sublocation", "")), key=f"{prefix}sublocation")
    service_month = c6.selectbox("Service Month", MONTHS, index=option_index(MONTHS, record.get("service_month", MONTHS[0])), key=f"{prefix}service_month")
    c7, c8, c9 = st.columns(3)
    service_year = c7.number_input("Service Year", 2020, 2100, int(record.get("service_year", date.today().year) or date.today().year), key=f"{prefix}service_year")
    amount_iqd = c8.number_input("Invoice Amount IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_iqd", 0)), key=f"{prefix}amount_iqd")
    amount_usd = c9.number_input("Invoice Amount USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_usd", 0)), key=f"{prefix}amount_usd")
    description = st.text_area("Description", value=str(record.get("description", "") or ""), key=f"{prefix}description")
    status_options = ["Pending", "Submitted", "Approved", "Partially Paid", "Paid"]
    status = st.selectbox("Status", status_options, index=option_index(status_options, record.get("status", "Pending")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount_iqd, amount_usd, status, notes


def expense_fields(record=None, prefix=""):
    record = record if record is not None else {}
    c1, c2, c3 = st.columns(3)
    payment_date = c1.date_input("Invoice / Expense Date", safe_date(record.get("payment_date", date.today())), key=f"{prefix}payment_date")
    voucher_no = c2.text_input("Supplier Invoice / Voucher No", value=str(record.get("voucher_no", "") or ""), key=f"{prefix}voucher_no")
    supplier_or_employee = c3.text_input("Supplier / Employee", value=str(record.get("supplier_or_employee", "") or ""), key=f"{prefix}supplier_or_employee")
    c4, c5, c6 = st.columns(3)
    location = c4.selectbox("Location", [""] + locations, index=option_index([""] + locations, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", [""] + sublocations, index=option_index([""] + sublocations, record.get("sublocation", "")), key=f"{prefix}sublocation")
    category = c6.selectbox("Category", EXPENSE_CATEGORIES, index=option_index(EXPENSE_CATEGORIES, record.get("category", EXPENSE_CATEGORIES[0])), key=f"{prefix}category")
    c7, c8, c9 = st.columns(3)
    amount_iqd = c7.number_input("Supplier Invoice Amount IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_iqd", 0)), key=f"{prefix}amount_iqd")
    amount_usd = c8.number_input("Supplier Invoice Amount USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_usd", 0)), key=f"{prefix}amount_usd")
    payment_method = c9.selectbox("Payment Method", PAYMENT_METHODS, index=option_index(PAYMENT_METHODS, record.get("payment_method", "Cash")), key=f"{prefix}payment_method")
    description = st.text_area("Description", value=str(record.get("description", "") or ""), key=f"{prefix}description")
    status_options = ["Pending", "Partially Paid", "Paid", "Cancelled"]
    status = st.selectbox("Status", status_options, index=option_index(status_options, record.get("status", "Pending")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount_iqd, amount_usd, payment_method, status, notes


def petty_fields(record=None, prefix=""):
    record = record if record is not None else {}
    c1, c2, c3 = st.columns(3)
    transaction_date = c1.date_input("Transaction Date", safe_date(record.get("transaction_date", date.today())), key=f"{prefix}transaction_date")
    voucher_no = c2.text_input("Voucher No", value=str(record.get("voucher_no", "") or ""), key=f"{prefix}voucher_no")
    employee = c3.selectbox("Employee", [""] + employees, index=option_index([""] + employees, record.get("employee", "")), key=f"{prefix}employee")
    c4, c5, c6 = st.columns(3)
    location = c4.selectbox("Location", [""] + locations, index=option_index([""] + locations, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", [""] + sublocations, index=option_index([""] + sublocations, record.get("sublocation", "")), key=f"{prefix}sublocation")
    category = c6.selectbox("Category", EXPENSE_CATEGORIES, index=option_index(EXPENSE_CATEGORIES, record.get("category", EXPENSE_CATEGORIES[0])), key=f"{prefix}category")
    purpose = st.text_area("Purpose", value=str(record.get("purpose", "") or ""), key=f"{prefix}purpose")
    c7, c8 = st.columns(2)
    cash_out_iqd = c7.number_input("Cash Out IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("cash_out_iqd", 0)), key=f"{prefix}cash_out_iqd")
    cash_out_usd = c8.number_input("Cash Out USD", min_value=0.0, step=100.0, value=amount_value(record.get("cash_out_usd", 0)), key=f"{prefix}cash_out_usd")
    c9, c10 = st.columns(2)
    cash_in_iqd = c9.number_input("Cash In IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("cash_in_iqd", 0)), key=f"{prefix}cash_in_iqd")
    cash_in_usd = c10.number_input("Cash In USD", min_value=0.0, step=100.0, value=amount_value(record.get("cash_in_usd", 0)), key=f"{prefix}cash_in_usd")
    status = st.selectbox("Status", ["Open", "Pending", "Closed"], index=option_index(["Open", "Pending", "Closed"], record.get("status", "Open")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out_iqd, cash_out_usd, cash_in_iqd, cash_in_usd, status, notes


def advance_fields(record=None, prefix=""):
    record = record if record is not None else {}
    c1, c2, c3 = st.columns(3)
    advance_date = c1.date_input("Advance Date", safe_date(record.get("advance_date", date.today())), key=f"{prefix}advance_date")
    employee_name = c2.selectbox("Employee Name", [""] + employees, index=option_index([""] + employees, record.get("employee_name", "")), key=f"{prefix}employee_name")
    advance_type = c3.selectbox("Advance Type", ADVANCE_TYPES, index=option_index(ADVANCE_TYPES, record.get("advance_type", ADVANCE_TYPES[0])), key=f"{prefix}advance_type")
    c4, c5 = st.columns(2)
    location = c4.selectbox("Location", [""] + locations, index=option_index([""] + locations, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", [""] + sublocations, index=option_index([""] + sublocations, record.get("sublocation", "")), key=f"{prefix}sublocation")
    c6, c7 = st.columns(2)
    amount_given_iqd = c6.number_input("Amount Given IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_given_iqd", 0)), key=f"{prefix}amount_given_iqd")
    amount_given_usd = c7.number_input("Amount Given USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_given_usd", 0)), key=f"{prefix}amount_given_usd")
    c8, c9 = st.columns(2)
    amount_returned_iqd = c8.number_input("Amount Returned IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_returned_iqd", 0)), key=f"{prefix}amount_returned_iqd")
    amount_returned_usd = c9.number_input("Amount Returned USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_returned_usd", 0)), key=f"{prefix}amount_returned_usd")
    status = st.selectbox("Status", ["Open", "Partially Returned", "Closed"], index=option_index(["Open", "Partially Returned", "Closed"], record.get("status", "Open")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return advance_date, employee_name, advance_type, location, sublocation, amount_given_iqd, amount_given_usd, amount_returned_iqd, amount_returned_usd, status, notes


# =====================================================
# PAYMENT OPTIONS AND STATUS UPDATE
# =====================================================

def get_revenue_options():
    return query("""
        SELECT r.id, r.invoice_no, r.client, r.location, r.sublocation, r.service_month, r.service_year,
               r.amount_iqd, r.amount_usd,
               COALESCE(p.paid_iqd,0) AS received_iqd,
               COALESCE(p.paid_usd,0) AS received_usd,
               r.amount_iqd-COALESCE(p.paid_iqd,0) AS balance_iqd,
               r.amount_usd-COALESCE(p.paid_usd,0) AS balance_usd
        FROM revenue r
        LEFT JOIN (
            SELECT revenue_id, SUM(amount_iqd) paid_iqd, SUM(amount_usd) paid_usd
            FROM client_payments GROUP BY revenue_id
        ) p ON p.revenue_id = r.id
        ORDER BY r.invoice_date DESC, r.id DESC
    """)


def get_expense_options():
    return query("""
        SELECT e.id, e.voucher_no, e.supplier_or_employee, e.location, e.sublocation, e.category,
               e.amount_iqd, e.amount_usd,
               COALESCE(p.paid_iqd,0) AS paid_iqd,
               COALESCE(p.paid_usd,0) AS paid_usd,
               e.amount_iqd-COALESCE(p.paid_iqd,0) AS balance_iqd,
               e.amount_usd-COALESCE(p.paid_usd,0) AS balance_usd
        FROM expenses e
        LEFT JOIN (
            SELECT expense_id, SUM(amount_iqd) paid_iqd, SUM(amount_usd) paid_usd
            FROM supplier_payments GROUP BY expense_id
        ) p ON p.expense_id = e.id
        ORDER BY e.payment_date DESC, e.id DESC
    """)


def update_revenue_status(revenue_id):
    df = query("""
        SELECT r.amount_iqd, r.amount_usd,
               COALESCE(SUM(p.amount_iqd),0) AS paid_iqd,
               COALESCE(SUM(p.amount_usd),0) AS paid_usd
        FROM revenue r
        LEFT JOIN client_payments p ON p.revenue_id=r.id
        WHERE r.id=%s
        GROUP BY r.id, r.amount_iqd, r.amount_usd
    """, (revenue_id,))
    if df.empty:
        return
    r = df.loc[0]
    inv_total = float(r["amount_iqd"] or 0) + float(r["amount_usd"] or 0)
    paid_total = float(r["paid_iqd"] or 0) + float(r["paid_usd"] or 0)
    status = "Pending" if paid_total <= 0 else ("Paid" if paid_total >= inv_total else "Partially Paid")
    execute("UPDATE revenue SET status=%s WHERE id=%s", (status, revenue_id))


def update_expense_status(expense_id):
    df = query("""
        SELECT e.amount_iqd, e.amount_usd,
               COALESCE(SUM(p.amount_iqd),0) AS paid_iqd,
               COALESCE(SUM(p.amount_usd),0) AS paid_usd
        FROM expenses e
        LEFT JOIN supplier_payments p ON p.expense_id=e.id
        WHERE e.id=%s
        GROUP BY e.id, e.amount_iqd, e.amount_usd
    """, (expense_id,))
    if df.empty:
        return
    r = df.loc[0]
    inv_total = float(r["amount_iqd"] or 0) + float(r["amount_usd"] or 0)
    paid_total = float(r["paid_iqd"] or 0) + float(r["paid_usd"] or 0)
    status = "Pending" if paid_total <= 0 else ("Paid" if paid_total >= inv_total else "Partially Paid")
    execute("UPDATE expenses SET status=%s WHERE id=%s", (status, expense_id))


def client_payment_fields(record=None, prefix=""):
    record = record if record is not None else {}
    rev_df = get_revenue_options()
    c1, c2, c3 = st.columns(3)
    receipt_date = c1.date_input("Receipt Date", safe_date(record.get("receipt_date", date.today())), key=f"{prefix}receipt_date")
    receipt_no = c2.text_input("Receipt No", value=str(record.get("receipt_no", "") or ""), key=f"{prefix}receipt_no")
    client = c3.text_input("Client", value=str(record.get("client", "") or ""), key=f"{prefix}client")
    revenue_id = None
    if not rev_df.empty:
        ids = rev_df["id"].tolist()
        def rev_label(x):
            r = rev_df[rev_df["id"] == x].iloc[0]
            return f"{r['invoice_no']} | {r['client']} | {r['location']} / {r['sublocation']} | Balance: {money_usd(r['balance_usd'])} / {money_iqd(r['balance_iqd'])}"
        revenue_id = st.selectbox("Related Revenue Invoice", ids, index=ids.index(record.get("revenue_id")) if record.get("revenue_id") in ids else 0, format_func=rev_label, key=f"{prefix}revenue_id")
    else:
        st.warning("No revenue invoices found. Add Revenue first.")
    c4, c5, c6 = st.columns(3)
    amount_iqd = c4.number_input("Received IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_iqd", 0)), key=f"{prefix}amount_iqd")
    amount_usd = c5.number_input("Received USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_usd", 0)), key=f"{prefix}amount_usd")
    payment_method = c6.selectbox("Payment Method", PAYMENT_METHODS, index=option_index(PAYMENT_METHODS, record.get("payment_method", "Bank Transfer")), key=f"{prefix}payment_method")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return receipt_date, receipt_no, client, revenue_id, amount_iqd, amount_usd, payment_method, notes


def supplier_payment_fields(record=None, prefix=""):
    record = record if record is not None else {}
    exp_df = get_expense_options()
    c1, c2, c3 = st.columns(3)
    payment_date = c1.date_input("Payment Date", safe_date(record.get("payment_date", date.today())), key=f"{prefix}payment_date")
    payment_no = c2.text_input("Payment Voucher No", value=str(record.get("payment_no", "") or ""), key=f"{prefix}payment_no")
    supplier = c3.text_input("Supplier", value=str(record.get("supplier", "") or ""), key=f"{prefix}supplier")
    expense_id = None
    if not exp_df.empty:
        ids = exp_df["id"].tolist()
        def exp_label(x):
            r = exp_df[exp_df["id"] == x].iloc[0]
            return f"{r['voucher_no']} | {r['supplier_or_employee']} | {r['location']} / {r['sublocation']} | Balance: {money_usd(r['balance_usd'])} / {money_iqd(r['balance_iqd'])}"
        expense_id = st.selectbox("Related Supplier Invoice / Expense", ids, index=ids.index(record.get("expense_id")) if record.get("expense_id") in ids else 0, format_func=exp_label, key=f"{prefix}expense_id")
    else:
        st.warning("No expense invoices found. Add Expenses first.")
    c4, c5, c6 = st.columns(3)
    amount_iqd = c4.number_input("Paid IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_iqd", 0)), key=f"{prefix}amount_iqd")
    amount_usd = c5.number_input("Paid USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_usd", 0)), key=f"{prefix}amount_usd")
    payment_method = c6.selectbox("Payment Method", PAYMENT_METHODS, index=option_index(PAYMENT_METHODS, record.get("payment_method", "Cash")), key=f"{prefix}payment_method")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return payment_date, payment_no, supplier, expense_id, amount_iqd, amount_usd, payment_method, notes


# =====================================================
# STARTUP
# =====================================================

init_db()

if "settings_seeded" not in st.session_state:
    seed_default_settings()
    st.session_state["settings_seeded"] = True

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
    st.stop()

locations = get_list("settings_locations", "location")
sublocations = get_list("settings_sublocations", "sublocation")
employees = get_list("employees", "employee_name")

st.sidebar.title("RTT Financial ERP")
logout_button()

page = st.sidebar.radio(
    "Select Page",
    [
        "Dashboard", "Revenue", "Client Payments", "Expenses", "Supplier Payments",
        "Petty Cash", "Employee Advances", "Settings", "Reports"
    ],
)


# =====================================================
# DASHBOARD
# =====================================================

if page == "Dashboard":
    st.title("💼 Financial Control Dashboard")

    totals = query("""
        SELECT
            COALESCE((SELECT SUM(amount_iqd) FROM revenue),0) AS revenue_iqd,
            COALESCE((SELECT SUM(amount_usd) FROM revenue),0) AS revenue_usd,
            COALESCE((SELECT SUM(amount_iqd) FROM client_payments),0) AS collected_iqd,
            COALESCE((SELECT SUM(amount_usd) FROM client_payments),0) AS collected_usd,
            COALESCE((SELECT SUM(amount_iqd) FROM expenses),0) AS expenses_iqd,
            COALESCE((SELECT SUM(amount_usd) FROM expenses),0) AS expenses_usd,
            COALESCE((SELECT SUM(amount_iqd) FROM supplier_payments),0) AS paid_iqd,
            COALESCE((SELECT SUM(amount_usd) FROM supplier_payments),0) AS paid_usd,
            COALESCE((SELECT SUM(cash_out_iqd) FROM petty_cash),0) AS cash_out_iqd,
            COALESCE((SELECT SUM(cash_out_usd) FROM petty_cash),0) AS cash_out_usd,
            COALESCE((SELECT SUM(cash_in_iqd) FROM petty_cash),0) AS cash_in_iqd,
            COALESCE((SELECT SUM(cash_in_usd) FROM petty_cash),0) AS cash_in_usd,
            COALESCE((SELECT SUM(amount_given_iqd) FROM employee_advances),0) AS adv_given_iqd,
            COALESCE((SELECT SUM(amount_given_usd) FROM employee_advances),0) AS adv_given_usd,
            COALESCE((SELECT SUM(amount_returned_iqd) FROM employee_advances),0) AS adv_returned_iqd,
            COALESCE((SELECT SUM(amount_returned_usd) FROM employee_advances),0) AS adv_returned_usd
    """)
    t = totals.loc[0]

    st.subheader("Accounts Receivable - Clients")
    c1, c2, c3 = st.columns(3)
    c1.metric("Client Invoices IQD", money_iqd(t["revenue_iqd"]))
    c2.metric("Collected IQD", money_iqd(t["collected_iqd"]))
    c3.metric("Receivable Balance IQD", money_iqd(t["revenue_iqd"] - t["collected_iqd"]))
    c4, c5, c6 = st.columns(3)
    c4.metric("Client Invoices USD", money_usd(t["revenue_usd"]))
    c5.metric("Collected USD", money_usd(t["collected_usd"]))
    c6.metric("Receivable Balance USD", money_usd(t["revenue_usd"] - t["collected_usd"]))

    st.subheader("Accounts Payable - Suppliers")
    c7, c8, c9 = st.columns(3)
    c7.metric("Supplier Invoices IQD", money_iqd(t["expenses_iqd"]))
    c8.metric("Paid IQD", money_iqd(t["paid_iqd"]))
    c9.metric("Payable Balance IQD", money_iqd(t["expenses_iqd"] - t["paid_iqd"]))
    c10, c11, c12 = st.columns(3)
    c10.metric("Supplier Invoices USD", money_usd(t["expenses_usd"]))
    c11.metric("Paid USD", money_usd(t["paid_usd"]))
    c12.metric("Payable Balance USD", money_usd(t["expenses_usd"] - t["paid_usd"]))

    st.subheader("Profit and Cash View")
    c13, c14 = st.columns(2)
    c13.metric("Net Profit by Invoice IQD", money_iqd(t["revenue_iqd"] - t["expenses_iqd"]))
    c14.metric("Net Profit by Invoice USD", money_usd(t["revenue_usd"] - t["expenses_usd"]))
    c15, c16 = st.columns(2)
    net_cash_iqd = (t["collected_iqd"] + t["cash_in_iqd"]) - (t["paid_iqd"] + t["cash_out_iqd"] + t["adv_given_iqd"] - t["adv_returned_iqd"])
    net_cash_usd = (t["collected_usd"] + t["cash_in_usd"]) - (t["paid_usd"] + t["cash_out_usd"] + t["adv_given_usd"] - t["adv_returned_usd"])
    c15.metric("Net Cash Flow IQD", money_iqd(net_cash_iqd))
    c16.metric("Net Cash Flow USD", money_usd(net_cash_usd))

    st.divider()
    st.subheader("📊 Financial Charts")

    chart1, chart2 = st.columns(2)
    with chart1:
        receivable_chart = query("""
            SELECT COALESCE(location, 'Unknown') AS location,
                   SUM(amount_iqd) AS invoices_iqd,
                   SUM(amount_usd) AS invoices_usd
            FROM revenue
            GROUP BY location
            ORDER BY invoices_iqd DESC
        """)
        if not receivable_chart.empty and receivable_chart[["invoices_iqd", "invoices_usd"]].sum().sum() > 0:
            fig = px.bar(receivable_chart, x="location", y="invoices_iqd", title="Revenue / Receivable IQD by Location", text_auto=True)
            show_chart(fig)
        else:
            st.info("No revenue data for chart.")

    with chart2:
        payable_chart = query("""
            SELECT COALESCE(location, 'Unknown') AS location,
                   SUM(amount_iqd) AS expenses_iqd,
                   SUM(amount_usd) AS expenses_usd
            FROM expenses
            GROUP BY location
            ORDER BY expenses_iqd DESC
        """)
        if not payable_chart.empty and payable_chart[["expenses_iqd", "expenses_usd"]].sum().sum() > 0:
            fig = px.bar(payable_chart, x="location", y="expenses_iqd", title="Expenses / Payable IQD by Location", text_auto=True)
            show_chart(fig)
        else:
            st.info("No expense data for chart.")

    chart3, chart4 = st.columns(2)
    with chart3:
        monthly_chart = query("""
            SELECT TO_CHAR(invoice_date, 'YYYY-MM') AS month,
                   SUM(amount_iqd) AS revenue_iqd,
                   SUM(amount_usd) AS revenue_usd
            FROM revenue
            WHERE invoice_date IS NOT NULL
            GROUP BY month
            ORDER BY month
        """)
        if not monthly_chart.empty and monthly_chart[["revenue_iqd", "revenue_usd"]].sum().sum() > 0:
            fig = px.line(monthly_chart, x="month", y="revenue_iqd", markers=True, title="Monthly Revenue IQD")
            show_chart(fig)
        else:
            st.info("No monthly revenue data.")

    with chart4:
        expense_category_chart = query("""
            SELECT COALESCE(category, 'Unknown') AS category,
                   SUM(amount_iqd) AS expenses_iqd
            FROM expenses
            GROUP BY category
            ORDER BY expenses_iqd DESC
        """)
        if not expense_category_chart.empty and expense_category_chart["expenses_iqd"].sum() > 0:
            fig = px.pie(expense_category_chart, names="category", values="expenses_iqd", title="Expenses by Category IQD")
            show_chart(fig)
        else:
            st.info("No expense category data.")

    chart5, chart6 = st.columns(2)
    with chart5:
        cash_chart = pd.DataFrame({
            "Item": ["Collected IQD", "Paid IQD", "Petty Cash Out IQD", "Advances Net IQD"],
            "Amount": [float(t["collected_iqd"]), float(t["paid_iqd"]), float(t["cash_out_iqd"]), float(t["adv_given_iqd"] - t["adv_returned_iqd"])]
        })
        if cash_chart["Amount"].sum() > 0:
            fig = px.bar(cash_chart, x="Item", y="Amount", title="Cash Movement IQD", text_auto=True)
            show_chart(fig)
        else:
            st.info("No cash movement data.")

    with chart6:
        profit_chart = pd.DataFrame({
            "Item": ["Revenue IQD", "Expenses IQD", "Net Profit IQD"],
            "Amount": [float(t["revenue_iqd"]), float(t["expenses_iqd"]), float(t["revenue_iqd"] - t["expenses_iqd"])]
        })
        if abs(profit_chart["Amount"]).sum() > 0:
            fig = px.bar(profit_chart, x="Item", y="Amount", title="Profit View IQD", text_auto=True)
            show_chart(fig)
        else:
            st.info("No profit data.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Receivable by Client / Location")
        df_receivable = query("""
            SELECT r.client, r.location, r.sublocation,
                   SUM(r.amount_iqd) AS invoices_iqd,
                   SUM(r.amount_usd) AS invoices_usd,
                   COALESCE(SUM(p.amount_iqd),0) AS collected_iqd,
                   COALESCE(SUM(p.amount_usd),0) AS collected_usd,
                   SUM(r.amount_iqd)-COALESCE(SUM(p.amount_iqd),0) AS balance_iqd,
                   SUM(r.amount_usd)-COALESCE(SUM(p.amount_usd),0) AS balance_usd
            FROM revenue r
            LEFT JOIN client_payments p ON p.revenue_id=r.id
            GROUP BY r.client, r.location, r.sublocation
            ORDER BY balance_iqd DESC, balance_usd DESC
        """)
        st.dataframe(df_receivable, use_container_width=True, hide_index=True)
    with col2:
        st.subheader("Payable by Supplier / Location")
        df_payable = query("""
            SELECT e.supplier_or_employee, e.location, e.sublocation,
                   SUM(e.amount_iqd) AS invoices_iqd,
                   SUM(e.amount_usd) AS invoices_usd,
                   COALESCE(SUM(p.amount_iqd),0) AS paid_iqd,
                   COALESCE(SUM(p.amount_usd),0) AS paid_usd,
                   SUM(e.amount_iqd)-COALESCE(SUM(p.amount_iqd),0) AS balance_iqd,
                   SUM(e.amount_usd)-COALESCE(SUM(p.amount_usd),0) AS balance_usd
            FROM expenses e
            LEFT JOIN supplier_payments p ON p.expense_id=e.id
            GROUP BY e.supplier_or_employee, e.location, e.sublocation
            ORDER BY balance_iqd DESC, balance_usd DESC
        """)
        st.dataframe(df_payable, use_container_width=True, hide_index=True)


# =====================================================
# REVENUE
# =====================================================

elif page == "Revenue":
    st.title("🧾 Revenue Register")
    tab_add, tab_manage = st.tabs(["➕ Add Revenue", "✏️ Edit / Delete Revenue"])
    with tab_add:
        with st.form("revenue_form"):
            values = revenue_fields(prefix="add_rev_")
            uploaded = attachment_uploader("rev_attachment")
            if st.form_submit_button("Save Revenue"):
                new_id = execute("""INSERT INTO revenue (
                        invoice_date, invoice_no, client, location, sublocation, service_month, service_year,
                        description, amount_iqd, amount_usd, status, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", values, return_id=True)
                save_attachment("revenue", new_id, uploaded)
                st.success("Revenue saved.")
                st.rerun()
    with tab_manage:
        record_crud("revenue", "invoice_date", "invoice_date", lambda record: revenue_fields(record, prefix="edit_rev_"),
            """UPDATE revenue SET invoice_date=%s, invoice_no=%s, client=%s, location=%s, sublocation=%s,
                service_month=%s, service_year=%s, description=%s, amount_iqd=%s, amount_usd=%s, status=%s, notes=%s WHERE id=%s""",
            "DELETE FROM revenue WHERE id=%s", "Revenue")

elif page == "Client Payments":
    st.title("💰 Client Payments / Collections")
    tab_add, tab_manage = st.tabs(["➕ Add Client Payment", "✏️ Edit / Delete Client Payments"])
    with tab_add:
        with st.form("client_payment_form"):
            values = client_payment_fields(prefix="add_cp_")
            uploaded = attachment_uploader("client_payment_attachment")
            if st.form_submit_button("Save Client Payment"):
                new_id = execute("""INSERT INTO client_payments (
                        receipt_date, receipt_no, client, revenue_id, amount_iqd, amount_usd, payment_method, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", values, return_id=True)
                save_attachment("client_payments", new_id, uploaded)
                if values[3]:
                    update_revenue_status(values[3])
                st.success("Client payment saved and invoice balance updated.")
                st.rerun()
    with tab_manage:
        record_crud("client_payments", "receipt_date", "receipt_date", lambda record: client_payment_fields(record, prefix="edit_cp_"),
            """UPDATE client_payments SET receipt_date=%s, receipt_no=%s, client=%s, revenue_id=%s,
                amount_iqd=%s, amount_usd=%s, payment_method=%s, notes=%s WHERE id=%s""",
            "DELETE FROM client_payments WHERE id=%s", "Client Payment")

elif page == "Expenses":
    st.title("💸 Expenses / Supplier Invoices")
    tab_add, tab_manage = st.tabs(["➕ Add Expense", "✏️ Edit / Delete Expenses"])
    with tab_add:
        with st.form("expenses_form"):
            values = expense_fields(prefix="add_exp_")
            uploaded = attachment_uploader("expense_attachment")
            if st.form_submit_button("Save Expense"):
                new_id = execute("""INSERT INTO expenses (
                        payment_date, voucher_no, supplier_or_employee, location, sublocation, category,
                        description, amount_iqd, amount_usd, payment_method, status, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", values, return_id=True)
                save_attachment("expenses", new_id, uploaded)
                st.success("Expense saved.")
                st.rerun()
    with tab_manage:
        record_crud("expenses", "payment_date", "payment_date", lambda record: expense_fields(record, prefix="edit_exp_"),
            """UPDATE expenses SET payment_date=%s, voucher_no=%s, supplier_or_employee=%s,
                location=%s, sublocation=%s, category=%s, description=%s, amount_iqd=%s, amount_usd=%s,
                payment_method=%s, status=%s, notes=%s WHERE id=%s""",
            "DELETE FROM expenses WHERE id=%s", "Expense")

elif page == "Supplier Payments":
    st.title("🏦 Supplier Payments")
    tab_add, tab_manage = st.tabs(["➕ Add Supplier Payment", "✏️ Edit / Delete Supplier Payments"])
    with tab_add:
        with st.form("supplier_payment_form"):
            values = supplier_payment_fields(prefix="add_sp_")
            uploaded = attachment_uploader("supplier_payment_attachment")
            if st.form_submit_button("Save Supplier Payment"):
                new_id = execute("""INSERT INTO supplier_payments (
                        payment_date, payment_no, supplier, expense_id, amount_iqd, amount_usd, payment_method, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", values, return_id=True)
                save_attachment("supplier_payments", new_id, uploaded)
                if values[3]:
                    update_expense_status(values[3])
                st.success("Supplier payment saved and supplier balance updated.")
                st.rerun()
    with tab_manage:
        record_crud("supplier_payments", "payment_date", "payment_date", lambda record: supplier_payment_fields(record, prefix="edit_sp_"),
            """UPDATE supplier_payments SET payment_date=%s, payment_no=%s, supplier=%s, expense_id=%s,
                amount_iqd=%s, amount_usd=%s, payment_method=%s, notes=%s WHERE id=%s""",
            "DELETE FROM supplier_payments WHERE id=%s", "Supplier Payment")

elif page == "Petty Cash":
    st.title("💵 Petty Cash Register")
    tab_add, tab_manage = st.tabs(["➕ Add Petty Cash", "✏️ Edit / Delete Petty Cash"])
    with tab_add:
        with st.form("petty_cash_form"):
            values = petty_fields(prefix="add_petty_")
            uploaded = attachment_uploader("petty_attachment")
            if st.form_submit_button("Save Petty Cash"):
                new_id = execute("""INSERT INTO petty_cash (
                        transaction_date, voucher_no, employee, location, sublocation, purpose, category,
                        cash_out_iqd, cash_out_usd, cash_in_iqd, cash_in_usd, status, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", values, return_id=True)
                save_attachment("petty_cash", new_id, uploaded)
                st.success("Petty cash saved.")
                st.rerun()
    with tab_manage:
        record_crud("petty_cash", "transaction_date", "transaction_date", lambda record: petty_fields(record, prefix="edit_petty_"),
            """UPDATE petty_cash SET transaction_date=%s, voucher_no=%s, employee=%s, location=%s, sublocation=%s,
                purpose=%s, category=%s, cash_out_iqd=%s, cash_out_usd=%s, cash_in_iqd=%s, cash_in_usd=%s,
                status=%s, notes=%s WHERE id=%s""",
            "DELETE FROM petty_cash WHERE id=%s", "Petty Cash")

elif page == "Employee Advances":
    st.title("👤 Employee Advances / Loans")
    tab_add, tab_manage = st.tabs(["➕ Add Advance", "✏️ Edit / Delete Advances"])
    with tab_add:
        with st.form("advances_form"):
            values = advance_fields(prefix="add_adv_")
            uploaded = attachment_uploader("advance_attachment")
            if st.form_submit_button("Save Advance"):
                new_id = execute("""INSERT INTO employee_advances (
                        advance_date, employee_name, advance_type, location, sublocation, amount_given_iqd,
                        amount_given_usd, amount_returned_iqd, amount_returned_usd, status, notes
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", values, return_id=True)
                save_attachment("employee_advances", new_id, uploaded)
                st.success("Advance saved.")
                st.rerun()
    with tab_manage:
        record_crud("employee_advances", "advance_date", "advance_date", lambda record: advance_fields(record, prefix="edit_adv_"),
            """UPDATE employee_advances SET advance_date=%s, employee_name=%s, advance_type=%s, location=%s, sublocation=%s,
                amount_given_iqd=%s, amount_given_usd=%s, amount_returned_iqd=%s, amount_returned_usd=%s,
                status=%s, notes=%s WHERE id=%s""",
            "DELETE FROM employee_advances WHERE id=%s", "Advance")

elif page == "Settings":
    st.title("⚙️ Settings / Master Data")
    tab1, tab2, tab3 = st.tabs(["Locations", "Sub-Locations", "Employees"])
    with tab1:
        crud_single_column("Location List", "settings_locations", "id", "location", "Location")
    with tab2:
        crud_single_column("Sub-Location List", "settings_sublocations", "id", "sublocation", "Sub-Location")
    with tab3:
        crud_single_column("Employee List", "employees", "id", "employee_name", "Employee")


# =====================================================
# REPORTS
# =====================================================

elif page == "Reports":
    st.title("📊 Reports")
    report_type = st.selectbox("Select Report", [
        "Monthly Profitability", "Accounts Receivable", "Accounts Payable", "Client Statement", "Supplier Statement",
        "Petty Cash Summary", "Employee Advances Summary", "Revenue by Location", "Expenses by Location"
    ])

    if report_type == "Monthly Profitability":
        rev = query("""SELECT TO_CHAR(invoice_date, 'YYYY-MM') AS month, SUM(amount_iqd) revenue_iqd, SUM(amount_usd) revenue_usd FROM revenue GROUP BY month ORDER BY month""")
        exp = query("""SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month, SUM(amount_iqd) expenses_iqd, SUM(amount_usd) expenses_usd FROM expenses GROUP BY month ORDER BY month""")
        cp = query("""SELECT TO_CHAR(receipt_date, 'YYYY-MM') AS month, SUM(amount_iqd) collected_iqd, SUM(amount_usd) collected_usd FROM client_payments GROUP BY month ORDER BY month""")
        sp = query("""SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month, SUM(amount_iqd) paid_iqd, SUM(amount_usd) paid_usd FROM supplier_payments GROUP BY month ORDER BY month""")
        report = rev.merge(exp, on="month", how="outer").merge(cp, on="month", how="outer").merge(sp, on="month", how="outer").fillna(0)
        report["profit_iqd"] = report["revenue_iqd"] - report["expenses_iqd"]
        report["profit_usd"] = report["revenue_usd"] - report["expenses_usd"]
        report["cash_flow_iqd"] = report["collected_iqd"] - report["paid_iqd"]
        report["cash_flow_usd"] = report["collected_usd"] - report["paid_usd"]
        st.dataframe(report, use_container_width=True, hide_index=True)
        if not report.empty:
            fig = px.line(report, x="month", y=["revenue_iqd", "expenses_iqd", "profit_iqd", "cash_flow_iqd"], markers=True, title="Monthly Profitability IQD")
            show_chart(fig)
        download_excel_button(report, "monthly_profitability.xlsx")

    elif report_type == "Accounts Receivable":
        report = query("""
            SELECT r.client, r.location, r.sublocation, r.service_month, r.service_year, r.invoice_no, r.invoice_date,
                   r.description, r.amount_iqd AS invoice_iqd, r.amount_usd AS invoice_usd,
                   COALESCE(SUM(p.amount_iqd),0) AS received_iqd, COALESCE(SUM(p.amount_usd),0) AS received_usd,
                   r.amount_iqd-COALESCE(SUM(p.amount_iqd),0) AS balance_iqd,
                   r.amount_usd-COALESCE(SUM(p.amount_usd),0) AS balance_usd, r.status
            FROM revenue r LEFT JOIN client_payments p ON p.revenue_id=r.id
            GROUP BY r.id, r.client, r.location, r.sublocation, r.service_month, r.service_year, r.invoice_no, r.invoice_date, r.description, r.amount_iqd, r.amount_usd, r.status
            ORDER BY r.client, r.location, r.sublocation, r.invoice_date
        """)
        st.dataframe(report, use_container_width=True, hide_index=True)
        download_excel_button(report, "accounts_receivable.xlsx")

    elif report_type == "Accounts Payable":
        report = query("""
            SELECT e.supplier_or_employee AS supplier, e.location, e.sublocation, e.category, e.voucher_no, e.payment_date,
                   e.description, e.amount_iqd AS invoice_iqd, e.amount_usd AS invoice_usd,
                   COALESCE(SUM(p.amount_iqd),0) AS paid_iqd, COALESCE(SUM(p.amount_usd),0) AS paid_usd,
                   e.amount_iqd-COALESCE(SUM(p.amount_iqd),0) AS balance_iqd,
                   e.amount_usd-COALESCE(SUM(p.amount_usd),0) AS balance_usd, e.status
            FROM expenses e LEFT JOIN supplier_payments p ON p.expense_id=e.id
            GROUP BY e.id, e.supplier_or_employee, e.location, e.sublocation, e.category, e.voucher_no, e.payment_date, e.description, e.amount_iqd, e.amount_usd, e.status
            ORDER BY e.supplier_or_employee, e.location, e.sublocation, e.payment_date
        """)
        st.dataframe(report, use_container_width=True, hide_index=True)
        download_excel_button(report, "accounts_payable.xlsx")

    elif report_type == "Client Statement":
        client_list = get_list("revenue", "client")
        selected = st.selectbox("Select Client", client_list) if client_list else ""
        if selected:
            inv = query("""SELECT invoice_date AS date, invoice_no AS ref, 'Invoice' AS type, location, sublocation, service_month, service_year, amount_iqd AS debit_iqd, amount_usd AS debit_usd, 0 AS credit_iqd, 0 AS credit_usd, description FROM revenue WHERE client=%s""", (selected,))
            pay = query("""SELECT cp.receipt_date AS date, cp.receipt_no AS ref, 'Payment Received' AS type, r.location, r.sublocation, r.service_month, r.service_year, 0 AS debit_iqd, 0 AS debit_usd, cp.amount_iqd AS credit_iqd, cp.amount_usd AS credit_usd, cp.notes AS description FROM client_payments cp LEFT JOIN revenue r ON r.id=cp.revenue_id WHERE cp.client=%s""", (selected,))
            statement = pd.concat([inv, pay], ignore_index=True).sort_values("date").fillna(0)
            statement["balance_iqd"] = statement["debit_iqd"].cumsum() - statement["credit_iqd"].cumsum()
            statement["balance_usd"] = statement["debit_usd"].cumsum() - statement["credit_usd"].cumsum()
            st.dataframe(statement, use_container_width=True, hide_index=True)
            download_excel_button(statement, "client_statement.xlsx")

    elif report_type == "Supplier Statement":
        supplier_list = get_list("expenses", "supplier_or_employee")
        selected = st.selectbox("Select Supplier", supplier_list) if supplier_list else ""
        if selected:
            inv = query("""SELECT payment_date AS date, voucher_no AS ref, 'Supplier Invoice' AS type, location, sublocation, category, amount_iqd AS debit_iqd, amount_usd AS debit_usd, 0 AS credit_iqd, 0 AS credit_usd, description FROM expenses WHERE supplier_or_employee=%s""", (selected,))
            pay = query("""SELECT sp.payment_date AS date, sp.payment_no AS ref, 'Payment Paid' AS type, e.location, e.sublocation, e.category, 0 AS debit_iqd, 0 AS debit_usd, sp.amount_iqd AS credit_iqd, sp.amount_usd AS credit_usd, sp.notes AS description FROM supplier_payments sp LEFT JOIN expenses e ON e.id=sp.expense_id WHERE sp.supplier=%s""", (selected,))
            statement = pd.concat([inv, pay], ignore_index=True).sort_values("date").fillna(0)
            statement["outstanding_iqd"] = statement["debit_iqd"].cumsum() - statement["credit_iqd"].cumsum()
            statement["outstanding_usd"] = statement["debit_usd"].cumsum() - statement["credit_usd"].cumsum()
            st.dataframe(statement, use_container_width=True, hide_index=True)
            download_excel_button(statement, "supplier_statement.xlsx")

    elif report_type == "Petty Cash Summary":
        report = query("""SELECT employee, location, sublocation, category, SUM(cash_out_iqd) AS cash_out_iqd, SUM(cash_out_usd) AS cash_out_usd, SUM(cash_in_iqd) AS cash_in_iqd, SUM(cash_in_usd) AS cash_in_usd, SUM(cash_in_iqd)-SUM(cash_out_iqd) AS balance_iqd, SUM(cash_in_usd)-SUM(cash_out_usd) AS balance_usd FROM petty_cash GROUP BY employee, location, sublocation, category ORDER BY employee, location, sublocation, category""")
        st.dataframe(report, use_container_width=True, hide_index=True)
        download_excel_button(report, "petty_cash_summary.xlsx")

    elif report_type == "Employee Advances Summary":
        report = query("""SELECT employee_name, advance_type, location, sublocation, SUM(amount_given_iqd) AS given_iqd, SUM(amount_given_usd) AS given_usd, SUM(amount_returned_iqd) AS returned_iqd, SUM(amount_returned_usd) AS returned_usd, SUM(amount_given_iqd)-SUM(amount_returned_iqd) AS outstanding_iqd, SUM(amount_given_usd)-SUM(amount_returned_usd) AS outstanding_usd FROM employee_advances GROUP BY employee_name, advance_type, location, sublocation ORDER BY employee_name, location, sublocation""")
        st.dataframe(report, use_container_width=True, hide_index=True)
        download_excel_button(report, "employee_advances_summary.xlsx")

    elif report_type == "Revenue by Location":
        report = query("""SELECT location, sublocation, service_month, service_year, client, SUM(amount_iqd) AS revenue_iqd, SUM(amount_usd) AS revenue_usd, COUNT(*) AS invoices_count FROM revenue GROUP BY location, sublocation, service_month, service_year, client ORDER BY service_year, service_month, location, sublocation, client""")
        st.dataframe(report, use_container_width=True, hide_index=True)
        if not report.empty:
            fig = px.bar(report, x="location", y="revenue_iqd", color="client", title="Revenue by Location IQD", text_auto=True)
            show_chart(fig)
        download_excel_button(report, "revenue_by_location.xlsx")

    elif report_type == "Expenses by Location":
        report = query("""SELECT location, sublocation, category, supplier_or_employee, SUM(amount_iqd) AS expenses_iqd, SUM(amount_usd) AS expenses_usd, COUNT(*) AS expenses_count FROM expenses GROUP BY location, sublocation, category, supplier_or_employee ORDER BY location, sublocation, category, supplier_or_employee""")
        st.dataframe(report, use_container_width=True, hide_index=True)
        if not report.empty:
            fig = px.bar(report, x="location", y="expenses_iqd", color="category", title="Expenses by Location IQD", text_auto=True)
            show_chart(fig)
        download_excel_button(report, "expenses_by_location.xlsx")
