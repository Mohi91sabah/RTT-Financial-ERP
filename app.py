import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.set_page_config(page_title="RTT Financial ERP", page_icon="💼", layout="wide")

APP_USERNAME = st.secrets["credentials"]["username"]
APP_PASSWORD = st.secrets["credentials"]["password"]
DB_URL = st.secrets["DB_URL"]


@st.cache_resource(show_spinner=False)
def get_conn():
    return psycopg2.connect(DB_URL)


def clear_app_cache():
    st.cache_data.clear()


def execute(sql, params=()):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        clear_app_cache()
    except Exception:
        conn.rollback()
        raise


@st.cache_data(ttl=60, show_spinner=False)
def query(sql, params=()):
    conn = get_conn()
    return pd.read_sql_query(sql, conn, params=params)


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

ADVANCE_TYPES = [
    "Salary Advance", "Personal Advance", "Work Advance",
    "Procurement Advance", "Site Advance", "Other"
]


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
    ]

    for sql in sql_list:
        execute(sql)

    alter_list = [
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS amount_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS amount_usd NUMERIC DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS amount_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS amount_usd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_out_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_out_usd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_in_iqd NUMERIC DEFAULT 0",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS cash_in_usd NUMERIC DEFAULT 0",
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
        execute("""
            INSERT INTO settings_locations (location)
            SELECT %s WHERE NOT EXISTS (
                SELECT 1 FROM settings_locations WHERE location = %s
            )
        """, (loc.strip(), loc.strip()))

    for sub in DEFAULT_SUBLOCATIONS:
        execute("""
            INSERT INTO settings_sublocations (sublocation)
            SELECT %s WHERE NOT EXISTS (
                SELECT 1 FROM settings_sublocations WHERE sublocation = %s
            )
        """, (sub.strip(), sub.strip()))


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


def crud_single_column(title, table, id_col, value_col, label):
    st.subheader(title)

    with st.expander(f"➕ Add {label}", expanded=True):
        with st.form(f"add_{table}"):
            new_value = st.text_input(f"New {label}")
            if st.form_submit_button(f"Add {label}"):
                if new_value.strip():
                    execute(
                        f"""
                        INSERT INTO {table} ({value_col})
                        SELECT %s WHERE NOT EXISTS (
                            SELECT 1 FROM {table} WHERE {value_col} = %s
                        )
                        """,
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
                if st.form_submit_button("Update"):
                    execute(f"UPDATE {table} SET {value_col}=%s WHERE {id_col}=%s", (edited_value.strip(), selected_id))
                    st.success("Updated successfully.")
                    st.rerun()

        with c2:
            st.warning("Delete only if this item is not needed anymore.")
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
        main_ref = row.get("invoice_no", row.get("voucher_no", row.get("employee_name", "")))
        usd = row.get("amount_usd", row.get("cash_out_usd", row.get("amount_given_usd", 0)))
        iqd = row.get("amount_iqd", row.get("cash_out_iqd", row.get("amount_given_iqd", 0)))
        return f"ID {row_id} | {main_date} | {main_ref} | {money_usd(usd)} | {money_iqd(iqd)}"

    selected_id = st.selectbox(
        f"Select {label} record",
        df["id"].tolist(),
        format_func=display_record,
        key=f"select_{table}_record",
    )

    record = df[df["id"] == selected_id].iloc[0]

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
            execute(delete_sql, (selected_id,))
            st.success(f"{label} deleted successfully.")
            st.rerun()


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
    amount_iqd = c8.number_input("Amount IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_iqd", 0)), key=f"{prefix}amount_iqd")
    amount_usd = c9.number_input("Amount USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_usd", 0)), key=f"{prefix}amount_usd")

    description = st.text_area("Description", value=str(record.get("description", "") or ""), key=f"{prefix}description")
    status_options = ["Pending", "Submitted", "Approved", "Paid"]
    status = st.selectbox("Status", status_options, index=option_index(status_options, record.get("status", "Pending")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")

    return invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount_iqd, amount_usd, status, notes


def expense_fields(record=None, prefix=""):
    record = record if record is not None else {}

    c1, c2, c3 = st.columns(3)
    payment_date = c1.date_input("Payment Date", safe_date(record.get("payment_date", date.today())), key=f"{prefix}payment_date")
    voucher_no = c2.text_input("Voucher No", value=str(record.get("voucher_no", "") or ""), key=f"{prefix}voucher_no")
    supplier_or_employee = c3.text_input("Supplier / Employee", value=str(record.get("supplier_or_employee", "") or ""), key=f"{prefix}supplier_or_employee")

    c4, c5, c6 = st.columns(3)
    location = c4.selectbox("Location", [""] + locations, index=option_index([""] + locations, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", [""] + sublocations, index=option_index([""] + sublocations, record.get("sublocation", "")), key=f"{prefix}sublocation")
    category = c6.selectbox("Category", EXPENSE_CATEGORIES, index=option_index(EXPENSE_CATEGORIES, record.get("category", EXPENSE_CATEGORIES[0])), key=f"{prefix}category")

    c7, c8, c9 = st.columns(3)
    amount_iqd = c7.number_input("Amount IQD", min_value=0.0, step=1000.0, value=amount_value(record.get("amount_iqd", 0)), key=f"{prefix}amount_iqd")
    amount_usd = c8.number_input("Amount USD", min_value=0.0, step=100.0, value=amount_value(record.get("amount_usd", 0)), key=f"{prefix}amount_usd")
    payment_method = c9.selectbox("Payment Method", ["Cash", "Bank Transfer", "Cheque", "Other"], key=f"{prefix}payment_method")

    description = st.text_area("Description", value=str(record.get("description", "") or ""), key=f"{prefix}description")
    status_options = ["Pending", "Paid", "Cancelled"]
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

    status = st.selectbox("Status", ["Open", "Pending", "Closed"], key=f"{prefix}status")
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

    status = st.selectbox("Status", ["Open", "Partially Returned", "Closed"], key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")

    return advance_date, employee_name, advance_type, location, sublocation, amount_given_iqd, amount_given_usd, amount_returned_iqd, amount_returned_usd, status, notes


if "db_initialized" not in st.session_state:
    init_db()
    seed_default_settings()
    st.session_state["db_initialized"] = True

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
    ["Dashboard", "Revenue", "Expenses", "Petty Cash", "Employee Advances", "Settings", "Reports"],
)


if page == "Dashboard":
    st.title("💼 Financial Control Dashboard")

    totals = query("""
        SELECT
            COALESCE((SELECT SUM(amount_iqd) FROM revenue), 0) AS revenue_iqd,
            COALESCE((SELECT SUM(amount_usd) FROM revenue), 0) AS revenue_usd,
            COALESCE((SELECT SUM(amount_iqd) FROM expenses), 0) AS expenses_iqd,
            COALESCE((SELECT SUM(amount_usd) FROM expenses), 0) AS expenses_usd,
            COALESCE((SELECT SUM(cash_out_iqd) FROM petty_cash), 0) AS cash_out_iqd,
            COALESCE((SELECT SUM(cash_out_usd) FROM petty_cash), 0) AS cash_out_usd,
            COALESCE((SELECT SUM(cash_in_iqd) FROM petty_cash), 0) AS cash_in_iqd,
            COALESCE((SELECT SUM(cash_in_usd) FROM petty_cash), 0) AS cash_in_usd,
            COALESCE((SELECT SUM(amount_given_iqd) FROM employee_advances), 0) AS adv_given_iqd,
            COALESCE((SELECT SUM(amount_given_usd) FROM employee_advances), 0) AS adv_given_usd,
            COALESCE((SELECT SUM(amount_returned_iqd) FROM employee_advances), 0) AS adv_returned_iqd,
            COALESCE((SELECT SUM(amount_returned_usd) FROM employee_advances), 0) AS adv_returned_usd
    """)

    t = totals.loc[0]

    st.subheader("Revenue / Expenses")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue IQD", money_iqd(t["revenue_iqd"]))
    c2.metric("Total Expenses IQD", money_iqd(t["expenses_iqd"]))
    c3.metric("Net Profit IQD", money_iqd(t["revenue_iqd"] - t["expenses_iqd"]))

    c4, c5, c6 = st.columns(3)
    c4.metric("Total Revenue USD", money_usd(t["revenue_usd"]))
    c5.metric("Total Expenses USD", money_usd(t["expenses_usd"]))
    c6.metric("Net Profit USD", money_usd(t["revenue_usd"] - t["expenses_usd"]))

    st.subheader("Petty Cash")
    c7, c8, c9 = st.columns(3)
    c7.metric("Petty Cash Balance IQD", money_iqd(t["cash_in_iqd"] - t["cash_out_iqd"]))
    c8.metric("Petty Cash Balance USD", money_usd(t["cash_in_usd"] - t["cash_out_usd"]))
    c9.metric("Cash Out USD", money_usd(t["cash_out_usd"]))

    st.subheader("Employee Advances")
    c10, c11 = st.columns(2)
    c10.metric("Outstanding Advances IQD", money_iqd(t["adv_given_iqd"] - t["adv_returned_iqd"]))
    c11.metric("Outstanding Advances USD", money_usd(t["adv_given_usd"] - t["adv_returned_usd"]))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue by Location - USD")
        rev_loc = query("""
            SELECT COALESCE(location, 'Unspecified') AS location, SUM(amount_usd) AS amount_usd
            FROM revenue
            GROUP BY location
            ORDER BY amount_usd DESC
            LIMIT 20
        """)
        if not rev_loc.empty:
            st.bar_chart(rev_loc.set_index("location")["amount_usd"])

    with col2:
        st.subheader("Expenses by Category - USD")
        exp_cat = query("""
            SELECT COALESCE(category, 'Unspecified') AS category, SUM(amount_usd) AS amount_usd
            FROM expenses
            GROUP BY category
            ORDER BY amount_usd DESC
            LIMIT 20
        """)
        if not exp_cat.empty:
            st.bar_chart(exp_cat.set_index("category")["amount_usd"])


elif page == "Revenue":
    st.title("🧾 Revenue Register")
    tab_add, tab_manage = st.tabs(["➕ Add Revenue", "✏️ Edit / Delete Revenue"])

    with tab_add:
        with st.form("revenue_form"):
            values = revenue_fields(prefix="add_rev_")
            if st.form_submit_button("Save Revenue"):
                execute(
                    """INSERT INTO revenue
                    (invoice_date, invoice_no, client, location, sublocation, service_month, service_year,
                    description, amount_iqd, amount_usd, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Revenue saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="revenue",
            date_col="invoice_date",
            order_col="invoice_date",
            form_renderer=lambda record: revenue_fields(record, prefix="edit_rev_"),
            update_sql="""UPDATE revenue SET
                invoice_date=%s, invoice_no=%s, client=%s, location=%s, sublocation=%s,
                service_month=%s, service_year=%s, description=%s,
                amount_iqd=%s, amount_usd=%s, status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM revenue WHERE id=%s",
            label="Revenue",
        )


elif page == "Expenses":
    st.title("💸 Expenses Register")
    tab_add, tab_manage = st.tabs(["➕ Add Expense", "✏️ Edit / Delete Expenses"])

    with tab_add:
        with st.form("expenses_form"):
            values = expense_fields(prefix="add_exp_")
            if st.form_submit_button("Save Expense"):
                execute(
                    """INSERT INTO expenses
                    (payment_date, voucher_no, supplier_or_employee, location, sublocation, category,
                    description, amount_iqd, amount_usd, payment_method, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Expense saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="expenses",
            date_col="payment_date",
            order_col="payment_date",
            form_renderer=lambda record: expense_fields(record, prefix="edit_exp_"),
            update_sql="""UPDATE expenses SET
                payment_date=%s, voucher_no=%s, supplier_or_employee=%s, location=%s, sublocation=%s,
                category=%s, description=%s, amount_iqd=%s, amount_usd=%s,
                payment_method=%s, status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM expenses WHERE id=%s",
            label="Expense",
        )


elif page == "Petty Cash":
    st.title("💵 Petty Cash Register")
    tab_add, tab_manage = st.tabs(["➕ Add Petty Cash", "✏️ Edit / Delete Petty Cash"])

    with tab_add:
        with st.form("petty_cash_form"):
            values = petty_fields(prefix="add_petty_")
            if st.form_submit_button("Save Petty Cash"):
                execute(
                    """INSERT INTO petty_cash
                    (transaction_date, voucher_no, employee, location, sublocation, purpose, category,
                    cash_out_iqd, cash_out_usd, cash_in_iqd, cash_in_usd, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Petty cash saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="petty_cash",
            date_col="transaction_date",
            order_col="transaction_date",
            form_renderer=lambda record: petty_fields(record, prefix="edit_petty_"),
            update_sql="""UPDATE petty_cash SET
                transaction_date=%s, voucher_no=%s, employee=%s, location=%s, sublocation=%s,
                purpose=%s, category=%s, cash_out_iqd=%s, cash_out_usd=%s,
                cash_in_iqd=%s, cash_in_usd=%s, status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM petty_cash WHERE id=%s",
            label="Petty Cash",
        )


elif page == "Employee Advances":
    st.title("👤 Employee Advances / Loans")
    tab_add, tab_manage = st.tabs(["➕ Add Advance", "✏️ Edit / Delete Advances"])

    with tab_add:
        with st.form("advances_form"):
            values = advance_fields(prefix="add_adv_")
            if st.form_submit_button("Save Advance"):
                execute(
                    """INSERT INTO employee_advances
                    (advance_date, employee_name, advance_type, location, sublocation,
                    amount_given_iqd, amount_given_usd, amount_returned_iqd, amount_returned_usd,
                    status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Advance saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="employee_advances",
            date_col="advance_date",
            order_col="advance_date",
            form_renderer=lambda record: advance_fields(record, prefix="edit_adv_"),
            update_sql="""UPDATE employee_advances SET
                advance_date=%s, employee_name=%s, advance_type=%s, location=%s, sublocation=%s,
                amount_given_iqd=%s, amount_given_usd=%s,
                amount_returned_iqd=%s, amount_returned_usd=%s,
                status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM employee_advances WHERE id=%s",
            label="Advance",
        )


elif page == "Settings":
    st.title("⚙️ Settings / Master Data")
    tab1, tab2, tab3 = st.tabs(["Locations", "Sub-Locations", "Employees"])

    with tab1:
        crud_single_column("Location List", "settings_locations", "id", "location", "Location")

    with tab2:
        crud_single_column("Sub-Location List", "settings_sublocations", "id", "sublocation", "Sub-Location")

    with tab3:
        crud_single_column("Employee List", "employees", "id", "employee_name", "Employee")


elif page == "Reports":
    st.title("📊 Reports")

    report_type = st.selectbox(
        "Select Report",
        [
            "Monthly Profitability",
            "Location Profitability",
            "Sub-Location Profitability",
            "Petty Cash Summary",
            "Employee Advances Summary",
        ],
    )

    if report_type == "Monthly Profitability":
        rev = query("""
            SELECT TO_CHAR(invoice_date, 'YYYY-MM') AS month,
            SUM(amount_iqd) AS revenue_iqd,
            SUM(amount_usd) AS revenue_usd
            FROM revenue
            GROUP BY month
            ORDER BY month
        """)

        exp = query("""
            SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month,
            SUM(amount_iqd) AS expenses_iqd,
            SUM(amount_usd) AS expenses_usd
            FROM expenses
            GROUP BY month
            ORDER BY month
        """)

        report = pd.merge(rev, exp, on="month", how="outer").fillna(0)
        report["net_profit_iqd"] = report["revenue_iqd"] - report["expenses_iqd"]
        report["net_profit_usd"] = report["revenue_usd"] - report["expenses_usd"]

        st.dataframe(report, use_container_width=True, hide_index=True)

    elif report_type == "Location Profitability":
        rev = query("""
            SELECT location, SUM(amount_iqd) AS revenue_iqd, SUM(amount_usd) AS revenue_usd
            FROM revenue GROUP BY location
        """)
        exp = query("""
            SELECT location, SUM(amount_iqd) AS expenses_iqd, SUM(amount_usd) AS expenses_usd
            FROM expenses GROUP BY location
        """)
        report = pd.merge(rev, exp, on="location", how="outer").fillna(0)
        report["net_profit_iqd"] = report["revenue_iqd"] - report["expenses_iqd"]
        report["net_profit_usd"] = report["revenue_usd"] - report["expenses_usd"]
        st.dataframe(report, use_container_width=True, hide_index=True)

    elif report_type == "Sub-Location Profitability":
        rev = query("""
            SELECT sublocation, SUM(amount_iqd) AS revenue_iqd, SUM(amount_usd) AS revenue_usd
            FROM revenue GROUP BY sublocation
        """)
        exp = query("""
            SELECT sublocation, SUM(amount_iqd) AS expenses_iqd, SUM(amount_usd) AS expenses_usd
            FROM expenses GROUP BY sublocation
        """)
        report = pd.merge(rev, exp, on="sublocation", how="outer").fillna(0)
        report["net_profit_iqd"] = report["revenue_iqd"] - report["expenses_iqd"]
        report["net_profit_usd"] = report["revenue_usd"] - report["expenses_usd"]
        st.dataframe(report, use_container_width=True, hide_index=True)

    elif report_type == "Petty Cash Summary":
        st.dataframe(
            query("""
                SELECT employee, location, sublocation, category,
                SUM(cash_out_iqd) AS cash_out_iqd,
                SUM(cash_out_usd) AS cash_out_usd,
                SUM(cash_in_iqd) AS cash_in_iqd,
                SUM(cash_in_usd) AS cash_in_usd,
                SUM(cash_in_iqd)-SUM(cash_out_iqd) AS balance_iqd,
                SUM(cash_in_usd)-SUM(cash_out_usd) AS balance_usd
                FROM petty_cash
                GROUP BY employee, location, sublocation, category
            """),
            use_container_width=True,
            hide_index=True,
        )

    elif report_type == "Employee Advances Summary":
        st.dataframe(
            query("""
                SELECT employee_name, advance_type, location, sublocation,
                SUM(amount_given_iqd) AS given_iqd,
                SUM(amount_given_usd) AS given_usd,
                SUM(amount_returned_iqd) AS returned_iqd,
                SUM(amount_returned_usd) AS returned_usd,
                SUM(amount_given_iqd)-SUM(amount_returned_iqd) AS outstanding_iqd,
                SUM(amount_given_usd)-SUM(amount_returned_usd) AS outstanding_usd
                FROM employee_advances
                GROUP BY employee_name, advance_type, location, sublocation
            """),
            use_container_width=True,
            hide_index=True,
        )
