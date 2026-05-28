import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

# =====================================================
# RTT Financial ERP - Supabase Version
# Updated: Login + Locations/Sub-Locations + CRUD Settings
# =====================================================

st.set_page_config(page_title="RTT Financial ERP", page_icon="💼", layout="wide")

# -------------------------
# LOGIN CONFIGURATION - FROM STREAMLIT SECRETS
# -------------------------
APP_USERNAME = st.secrets["credentials"]["username"]
APP_PASSWORD = st.secrets["credentials"]["password"]

# -------------------------
# DATABASE CONNECTION
# -------------------------
DB_URL = st.secrets["DB_URL"]


@st.cache_resource(show_spinner=False)
def get_conn():
    # One reusable connection reduces Supabase connection overhead and makes page navigation faster.
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


# -------------------------
# DEFAULT SETTINGS DATA
# -------------------------
DEFAULT_LOCATIONS = [
    "BGCG_23", "BGC_23", "ROOG_23", "ROOM_23", "ROOESP_23", "ROOP_23",
    "Camp_23", "HO_23", "WQ1_23", "TOTAL_25", "MITAS", "KRK-BP-25"
]

DEFAULT_SUBLOCATIONS = [
    "GRLBG_23", "ZBR_23", "KAZ_23", "UQ_23", "MANPR_23", "SPAS_23", "EX_23",
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


# -------------------------
# DATABASE INITIALIZATION
# -------------------------
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
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    for sql in sql_list:
        execute(sql)

    # Fix old database design if it had location column inside sublocations table.
    try:
        execute("ALTER TABLE settings_sublocations ADD COLUMN IF NOT EXISTS sublocation TEXT")
    except Exception:
        pass


def seed_default_settings():
    for loc in DEFAULT_LOCATIONS:
        execute("""
            INSERT INTO settings_locations (location)
            SELECT %s
            WHERE NOT EXISTS (
                SELECT 1 FROM settings_locations WHERE location = %s
            )
        """, (loc.strip(), loc.strip()))

    for sub in DEFAULT_SUBLOCATIONS:
        execute("""
            INSERT INTO settings_sublocations (sublocation)
            SELECT %s
            WHERE NOT EXISTS (
                SELECT 1 FROM settings_sublocations WHERE sublocation = %s
            )
        """, (sub.strip(), sub.strip()))


# -------------------------
# HELPER FUNCTIONS
# -------------------------
def money(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"


def get_list(table, col):
    try:
        df = query(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} <> '' ORDER BY {col}")
        return df[col].dropna().astype(str).tolist()
    except Exception:
        return []


def login_page():
    st.title("🔐 RTT Financial ERP Login")
    st.info("Please enter username and password to access the system.")

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
                    try:
                        execute(
                            f"""
                            INSERT INTO {table} ({value_col})
                            SELECT %s
                            WHERE NOT EXISTS (
                                SELECT 1 FROM {table} WHERE {value_col} = %s
                            )
                            """,
                            (new_value.strip(), new_value.strip()),
                        )
                        st.success(f"{label} added successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add {label}: {e}")
                else:
                    st.warning("Please enter a value.")

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
                    if edited_value.strip():
                        try:
                            execute(f"UPDATE {table} SET {value_col}=%s WHERE {id_col}=%s", (edited_value.strip(), selected_id))
                            st.success("Updated successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not update: {e}")
                    else:
                        st.warning("Value cannot be empty.")

        with c2:
            st.warning("Delete only if this item is not needed anymore.")
            if st.button(f"Delete selected {label}", key=f"delete_{table}"):
                try:
                    execute(f"DELETE FROM {table} WHERE {id_col}=%s", (selected_id,))
                    st.success("Deleted successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete: {e}")


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


def amount_value(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def record_crud(table, title, date_col, order_col, form_renderer, update_sql, delete_sql, label):
    st.subheader(f"✏️ Edit / Delete {label}")
    df = query(f"SELECT * FROM {table} ORDER BY {order_col} DESC, id DESC LIMIT 300")

    if df.empty:
        st.info(f"No {label.lower()} records found yet.")
        return

    st.caption("Showing latest 300 records only to keep the app fast.")
    st.dataframe(df, use_container_width=True, hide_index=True)

    def display_record(row_id):
        row = df[df["id"] == row_id].iloc[0]
        main_date = row.get(date_col, "")
        main_ref = row.get("invoice_no", row.get("voucher_no", row.get("employee_name", "")))
        main_amount = row.get("amount", row.get("cash_out", row.get("amount_given", 0)))
        return f"ID {row_id} | {main_date} | {main_ref} | {money(main_amount)}"

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
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox("Location", loc_options, index=option_index(loc_options, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", sub_options, index=option_index(sub_options, record.get("sublocation", "")), key=f"{prefix}sublocation")
    service_month = c6.selectbox("Service Month", MONTHS, index=option_index(MONTHS, record.get("service_month", MONTHS[0])), key=f"{prefix}service_month")
    c7, c8 = st.columns(2)
    service_year = c7.number_input("Service Year", 2020, 2100, int(record.get("service_year", date.today().year) or date.today().year), key=f"{prefix}service_year")
    amount = c8.number_input("Amount", min_value=0.0, step=100.0, value=amount_value(record.get("amount", 0)), key=f"{prefix}amount")
    description = st.text_area("Description", value=str(record.get("description", "") or ""), key=f"{prefix}description")
    status_options = ["Pending", "Submitted", "Approved", "Paid"]
    status = st.selectbox("Status", status_options, index=option_index(status_options, record.get("status", "Pending")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount, status, notes


def expense_fields(record=None, prefix=""):
    record = record if record is not None else {}
    c1, c2, c3 = st.columns(3)
    payment_date = c1.date_input("Payment Date", safe_date(record.get("payment_date", date.today())), key=f"{prefix}payment_date")
    voucher_no = c2.text_input("Voucher No", value=str(record.get("voucher_no", "") or ""), key=f"{prefix}voucher_no")
    supplier_or_employee = c3.text_input("Supplier / Employee", value=str(record.get("supplier_or_employee", "") or ""), key=f"{prefix}supplier_or_employee")
    c4, c5, c6 = st.columns(3)
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox("Location", loc_options, index=option_index(loc_options, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", sub_options, index=option_index(sub_options, record.get("sublocation", "")), key=f"{prefix}sublocation")
    category = c6.selectbox("Category", EXPENSE_CATEGORIES, index=option_index(EXPENSE_CATEGORIES, record.get("category", EXPENSE_CATEGORIES[0])), key=f"{prefix}category")
    c7, c8 = st.columns(2)
    amount = c7.number_input("Amount", min_value=0.0, step=100.0, value=amount_value(record.get("amount", 0)), key=f"{prefix}amount")
    pm_options = ["Cash", "Bank Transfer", "Cheque", "Other"]
    payment_method = c8.selectbox("Payment Method", pm_options, index=option_index(pm_options, record.get("payment_method", "Cash")), key=f"{prefix}payment_method")
    description = st.text_area("Description", value=str(record.get("description", "") or ""), key=f"{prefix}description")
    status_options = ["Pending", "Paid", "Cancelled"]
    status = st.selectbox("Status", status_options, index=option_index(status_options, record.get("status", "Pending")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount, payment_method, status, notes


def petty_fields(record=None, prefix=""):
    record = record if record is not None else {}
    c1, c2, c3 = st.columns(3)
    transaction_date = c1.date_input("Transaction Date", safe_date(record.get("transaction_date", date.today())), key=f"{prefix}transaction_date")
    voucher_no = c2.text_input("Voucher No", value=str(record.get("voucher_no", "") or ""), key=f"{prefix}voucher_no")
    emp_options = [""] + employees
    employee = c3.selectbox("Employee", emp_options, index=option_index(emp_options, record.get("employee", "")), key=f"{prefix}employee")
    c4, c5, c6 = st.columns(3)
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox("Location", loc_options, index=option_index(loc_options, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", sub_options, index=option_index(sub_options, record.get("sublocation", "")), key=f"{prefix}sublocation")
    category = c6.selectbox("Category", EXPENSE_CATEGORIES, index=option_index(EXPENSE_CATEGORIES, record.get("category", EXPENSE_CATEGORIES[0])), key=f"{prefix}category")
    purpose = st.text_area("Purpose", value=str(record.get("purpose", "") or ""), key=f"{prefix}purpose")
    c7, c8 = st.columns(2)
    cash_out = c7.number_input("Cash Out", min_value=0.0, step=100.0, value=amount_value(record.get("cash_out", 0)), key=f"{prefix}cash_out")
    cash_in = c8.number_input("Cash In", min_value=0.0, step=100.0, value=amount_value(record.get("cash_in", 0)), key=f"{prefix}cash_in")
    status_options = ["Open", "Pending", "Closed"]
    status = st.selectbox("Status", status_options, index=option_index(status_options, record.get("status", "Open")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out, cash_in, status, notes


def advance_fields(record=None, prefix=""):
    record = record if record is not None else {}
    c1, c2, c3 = st.columns(3)
    advance_date = c1.date_input("Advance Date", safe_date(record.get("advance_date", date.today())), key=f"{prefix}advance_date")
    emp_options = [""] + employees
    employee_name = c2.selectbox("Employee Name", emp_options, index=option_index(emp_options, record.get("employee_name", "")), key=f"{prefix}employee_name")
    advance_type = c3.selectbox("Advance Type", ADVANCE_TYPES, index=option_index(ADVANCE_TYPES, record.get("advance_type", ADVANCE_TYPES[0])), key=f"{prefix}advance_type")
    c4, c5 = st.columns(2)
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox("Location", loc_options, index=option_index(loc_options, record.get("location", "")), key=f"{prefix}location")
    sublocation = c5.selectbox("Sub-Location", sub_options, index=option_index(sub_options, record.get("sublocation", "")), key=f"{prefix}sublocation")
    c6, c7 = st.columns(2)
    amount_given = c6.number_input("Amount Given", min_value=0.0, step=100.0, value=amount_value(record.get("amount_given", 0)), key=f"{prefix}amount_given")
    amount_returned = c7.number_input("Amount Returned", min_value=0.0, step=100.0, value=amount_value(record.get("amount_returned", 0)), key=f"{prefix}amount_returned")
    status_options = ["Open", "Partially Returned", "Closed"]
    status = st.selectbox("Status", status_options, index=option_index(status_options, record.get("status", "Open")), key=f"{prefix}status")
    notes = st.text_area("Notes", value=str(record.get("notes", "") or ""), key=f"{prefix}notes")
    return advance_date, employee_name, advance_type, location, sublocation, amount_given, amount_returned, status, notes


# -------------------------
# START APP
# -------------------------
# Run database setup only once per app session. Running it on every page change slows the app.
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


# -------------------------
# DASHBOARD
# -------------------------
if page == "Dashboard":
    st.title("💼 Financial Control Dashboard")

    # Fast dashboard: use SQL summaries instead of loading full tables.
    totals = query("""
        SELECT
            COALESCE((SELECT SUM(amount) FROM revenue), 0) AS total_revenue,
            COALESCE((SELECT SUM(amount) FROM expenses), 0) AS total_expenses,
            COALESCE((SELECT SUM(cash_out) FROM petty_cash), 0) AS cash_out,
            COALESCE((SELECT SUM(cash_in) FROM petty_cash), 0) AS cash_in,
            COALESCE((SELECT SUM(amount_given) FROM employee_advances), 0) AS adv_given,
            COALESCE((SELECT SUM(amount_returned) FROM employee_advances), 0) AS adv_returned
    """)

    total_revenue = float(totals.loc[0, "total_revenue"])
    total_expenses = float(totals.loc[0, "total_expenses"])
    net_profit = total_revenue - total_expenses
    margin = (net_profit / total_revenue * 100) if total_revenue else 0
    cash_out = float(totals.loc[0, "cash_out"])
    cash_in = float(totals.loc[0, "cash_in"])
    adv_given = float(totals.loc[0, "adv_given"])
    adv_returned = float(totals.loc[0, "adv_returned"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", money(total_revenue))
    c2.metric("Total Expenses", money(total_expenses))
    c3.metric("Net Profit", money(net_profit))
    c4.metric("Profit Margin", f"{margin:.2f}%")

    c5, c6, c7 = st.columns(3)
    c5.metric("Petty Cash Out", money(cash_out))
    c6.metric("Petty Cash In", money(cash_in))
    c7.metric("Petty Cash Balance", money(cash_in - cash_out))

    c8, c9, c10 = st.columns(3)
    c8.metric("Advances Given", money(adv_given))
    c9.metric("Advances Returned", money(adv_returned))
    c10.metric("Outstanding Advances", money(adv_given - adv_returned))

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue by Location")
        rev_loc = query("""
            SELECT COALESCE(location, 'Unspecified') AS location, SUM(amount) AS amount
            FROM revenue
            GROUP BY location
            ORDER BY amount DESC
            LIMIT 20
        """)
        if not rev_loc.empty:
            st.bar_chart(rev_loc.set_index("location")["amount"])
    with col2:
        st.subheader("Expenses by Category")
        exp_cat = query("""
            SELECT COALESCE(category, 'Unspecified') AS category, SUM(amount) AS amount
            FROM expenses
            GROUP BY category
            ORDER BY amount DESC
            LIMIT 20
        """)
        if not exp_cat.empty:
            st.bar_chart(exp_cat.set_index("category")["amount"])


# -------------------------
# REVENUE
# -------------------------
elif page == "Revenue":
    st.title("🧾 Revenue Register")
    tab_add, tab_manage = st.tabs(["➕ Add Revenue", "✏️ Edit / Delete Revenue"])

    with tab_add:
        with st.form("revenue_form"):
            values = revenue_fields(prefix="add_rev_")
            if st.form_submit_button("Save Revenue"):
                execute(
                    """INSERT INTO revenue
                    (invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Revenue saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="revenue",
            title="Revenue",
            date_col="invoice_date",
            order_col="invoice_date",
            form_renderer=lambda record: revenue_fields(record, prefix="edit_rev_"),
            update_sql="""UPDATE revenue SET
                invoice_date=%s, invoice_no=%s, client=%s, location=%s, sublocation=%s,
                service_month=%s, service_year=%s, description=%s, amount=%s, status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM revenue WHERE id=%s",
            label="Revenue",
        )

# -------------------------
# EXPENSES
# -------------------------
elif page == "Expenses":
    st.title("💸 Expenses Register")
    tab_add, tab_manage = st.tabs(["➕ Add Expense", "✏️ Edit / Delete Expenses"])

    with tab_add:
        with st.form("expenses_form"):
            values = expense_fields(prefix="add_exp_")
            if st.form_submit_button("Save Expense"):
                execute(
                    """INSERT INTO expenses
                    (payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount, payment_method, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Expense saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="expenses",
            title="Expenses",
            date_col="payment_date",
            order_col="payment_date",
            form_renderer=lambda record: expense_fields(record, prefix="edit_exp_"),
            update_sql="""UPDATE expenses SET
                payment_date=%s, voucher_no=%s, supplier_or_employee=%s, location=%s, sublocation=%s,
                category=%s, description=%s, amount=%s, payment_method=%s, status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM expenses WHERE id=%s",
            label="Expense",
        )

# -------------------------
# PETTY CASH
# -------------------------
elif page == "Petty Cash":
    st.title("💵 Petty Cash Register")
    tab_add, tab_manage = st.tabs(["➕ Add Petty Cash", "✏️ Edit / Delete Petty Cash"])

    with tab_add:
        with st.form("petty_cash_form"):
            values = petty_fields(prefix="add_petty_")
            if st.form_submit_button("Save Petty Cash"):
                execute(
                    """INSERT INTO petty_cash
                    (transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out, cash_in, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Petty cash saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="petty_cash",
            title="Petty Cash",
            date_col="transaction_date",
            order_col="transaction_date",
            form_renderer=lambda record: petty_fields(record, prefix="edit_petty_"),
            update_sql="""UPDATE petty_cash SET
                transaction_date=%s, voucher_no=%s, employee=%s, location=%s, sublocation=%s,
                purpose=%s, category=%s, cash_out=%s, cash_in=%s, status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM petty_cash WHERE id=%s",
            label="Petty Cash",
        )

# -------------------------
# EMPLOYEE ADVANCES
# -------------------------
elif page == "Employee Advances":
    st.title("👤 Employee Advances / Loans")
    tab_add, tab_manage = st.tabs(["➕ Add Advance", "✏️ Edit / Delete Advances"])

    with tab_add:
        with st.form("advances_form"):
            values = advance_fields(prefix="add_adv_")
            if st.form_submit_button("Save Advance"):
                execute(
                    """INSERT INTO employee_advances
                    (advance_date, employee_name, advance_type, location, sublocation, amount_given, amount_returned, status, notes)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    values,
                )
                st.success("Advance saved.")
                st.rerun()

    with tab_manage:
        record_crud(
            table="employee_advances",
            title="Employee Advances",
            date_col="advance_date",
            order_col="advance_date",
            form_renderer=lambda record: advance_fields(record, prefix="edit_adv_"),
            update_sql="""UPDATE employee_advances SET
                advance_date=%s, employee_name=%s, advance_type=%s, location=%s, sublocation=%s,
                amount_given=%s, amount_returned=%s, status=%s, notes=%s
                WHERE id=%s""",
            delete_sql="DELETE FROM employee_advances WHERE id=%s",
            label="Advance",
        )

# -------------------------
# SETTINGS - FULL CRUD
# -------------------------
elif page == "Settings":
    st.title("⚙️ Settings / Master Data")
    st.info("From this page you can add, edit, and delete Locations, Sub-Locations, and Employees.")

    tab1, tab2, tab3 = st.tabs(["Locations", "Sub-Locations", "Employees"])

    with tab1:
        crud_single_column("Location List", "settings_locations", "id", "location", "Location")

    with tab2:
        crud_single_column("Sub-Location List", "settings_sublocations", "id", "sublocation", "Sub-Location")

    with tab3:
        crud_single_column("Employee List", "employees", "id", "employee_name", "Employee")


# -------------------------
# REPORTS
# -------------------------
elif page == "Reports":
    st.title("📊 Reports")
    report_type = st.selectbox(
        "Select Report",
        ["Monthly Profitability", "Location Profitability", "Sub-Location Profitability", "Petty Cash Summary", "Employee Advances Summary"],
    )

    if report_type == "Monthly Profitability":
        rev = query("SELECT TO_CHAR(invoice_date, 'YYYY-MM') AS month, SUM(amount) AS revenue FROM revenue GROUP BY month ORDER BY month")
        exp = query("SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month, SUM(amount) AS expenses FROM expenses GROUP BY month ORDER BY month")
        report = pd.merge(rev, exp, on="month", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        st.dataframe(report, use_container_width=True)
        if not report.empty:
            st.bar_chart(report.set_index("month")[["revenue", "expenses", "net_profit"]])

    elif report_type == "Location Profitability":
        rev = query("SELECT location, SUM(amount) AS revenue FROM revenue GROUP BY location")
        exp = query("SELECT location, SUM(amount) AS expenses FROM expenses GROUP BY location")
        report = pd.merge(rev, exp, on="location", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        st.dataframe(report, use_container_width=True)

    elif report_type == "Sub-Location Profitability":
        rev = query("SELECT sublocation, SUM(amount) AS revenue FROM revenue GROUP BY sublocation")
        exp = query("SELECT sublocation, SUM(amount) AS expenses FROM expenses GROUP BY sublocation")
        report = pd.merge(rev, exp, on="sublocation", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        st.dataframe(report, use_container_width=True)

    elif report_type == "Petty Cash Summary":
        st.dataframe(
            query(
                """SELECT employee, location, sublocation, category,
                SUM(cash_out) AS total_cash_out,
                SUM(cash_in) AS total_cash_in,
                SUM(cash_in)-SUM(cash_out) AS net_balance
                FROM petty_cash
                GROUP BY employee, location, sublocation, category"""
            ),
            use_container_width=True,
        )

    elif report_type == "Employee Advances Summary":
        st.dataframe(
            query(
                """SELECT employee_name, advance_type, location, sublocation,
                SUM(amount_given) AS total_given,
                SUM(amount_returned) AS total_returned,
                SUM(amount_given)-SUM(amount_returned) AS outstanding_balance
                FROM employee_advances
                GROUP BY employee_name, advance_type, location, sublocation"""
            ),
            use_container_width=True,
        )
