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
# LOGIN CONFIGURATION
# -------------------------
APP_USERNAME = "RTT@work26"
APP_PASSWORD = "RTT@MSN91"

# -------------------------
# DATABASE CONNECTION
# -------------------------
DB_URL = st.secrets["DB_URL"]


def get_conn():
    return psycopg2.connect(DB_URL)


def execute(sql, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    cur.close()
    conn.close()


def query(sql, params=()):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


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
        execute("INSERT INTO settings_locations (location) VALUES (%s) ON CONFLICT (location) DO NOTHING", (loc.strip(),))

    for sub in DEFAULT_SUBLOCATIONS:
        execute("INSERT INTO settings_sublocations (sublocation) VALUES (%s) ON CONFLICT (sublocation) DO NOTHING", (sub.strip(),))


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
                            f"INSERT INTO {table} ({value_col}) VALUES (%s) ON CONFLICT ({value_col}) DO NOTHING",
                            (new_value.strip(),),
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


# -------------------------
# START APP
# -------------------------
init_db()
seed_default_settings()

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
    revenue_df = query("SELECT * FROM revenue")
    expenses_df = query("SELECT * FROM expenses")
    petty_df = query("SELECT * FROM petty_cash")
    adv_df = query("SELECT * FROM employee_advances")

    total_revenue = float(revenue_df["amount"].sum()) if not revenue_df.empty else 0
    total_expenses = float(expenses_df["amount"].sum()) if not expenses_df.empty else 0
    net_profit = total_revenue - total_expenses
    margin = (net_profit / total_revenue * 100) if total_revenue else 0

    cash_out = float(petty_df["cash_out"].sum()) if not petty_df.empty else 0
    cash_in = float(petty_df["cash_in"].sum()) if not petty_df.empty else 0
    adv_given = float(adv_df["amount_given"].sum()) if not adv_df.empty else 0
    adv_returned = float(adv_df["amount_returned"].sum()) if not adv_df.empty else 0

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
        if not revenue_df.empty:
            st.bar_chart(revenue_df.groupby("location")["amount"].sum())
    with col2:
        st.subheader("Expenses by Category")
        if not expenses_df.empty:
            st.bar_chart(expenses_df.groupby("category")["amount"].sum())


# -------------------------
# REVENUE
# -------------------------
elif page == "Revenue":
    st.title("🧾 Revenue Register")
    with st.form("revenue_form"):
        c1, c2, c3 = st.columns(3)
        invoice_date = c1.date_input("Invoice Date", date.today())
        invoice_no = c2.text_input("Invoice No")
        client = c3.text_input("Client")

        c4, c5, c6 = st.columns(3)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("Sub-Location", [""] + sublocations)
        service_month = c6.selectbox("Service Month", MONTHS)

        c7, c8 = st.columns(2)
        service_year = c7.number_input("Service Year", 2020, 2100, date.today().year)
        amount = c8.number_input("Amount", min_value=0.0, step=100.0)

        description = st.text_area("Description")
        status = st.selectbox("Status", ["Pending", "Submitted", "Approved", "Paid"])
        notes = st.text_area("Notes")

        if st.form_submit_button("Save Revenue"):
            execute(
                """INSERT INTO revenue
                (invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount, status, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount, status, notes),
            )
            st.success("Revenue saved.")
            st.rerun()

    st.dataframe(query("SELECT * FROM revenue ORDER BY invoice_date DESC"), use_container_width=True)


# -------------------------
# EXPENSES
# -------------------------
elif page == "Expenses":
    st.title("💸 Expenses Register")
    with st.form("expenses_form"):
        c1, c2, c3 = st.columns(3)
        payment_date = c1.date_input("Payment Date", date.today())
        voucher_no = c2.text_input("Voucher No")
        supplier_or_employee = c3.text_input("Supplier / Employee")

        c4, c5, c6 = st.columns(3)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("Sub-Location", [""] + sublocations)
        category = c6.selectbox("Category", EXPENSE_CATEGORIES)

        c7, c8 = st.columns(2)
        amount = c7.number_input("Amount", min_value=0.0, step=100.0)
        payment_method = c8.selectbox("Payment Method", ["Cash", "Bank Transfer", "Cheque", "Other"])

        description = st.text_area("Description")
        status = st.selectbox("Status", ["Pending", "Paid", "Cancelled"])
        notes = st.text_area("Notes")

        if st.form_submit_button("Save Expense"):
            execute(
                """INSERT INTO expenses
                (payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount, payment_method, status, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount, payment_method, status, notes),
            )
            st.success("Expense saved.")
            st.rerun()

    st.dataframe(query("SELECT * FROM expenses ORDER BY payment_date DESC"), use_container_width=True)


# -------------------------
# PETTY CASH
# -------------------------
elif page == "Petty Cash":
    st.title("💵 Petty Cash Register")
    with st.form("petty_cash_form"):
        c1, c2, c3 = st.columns(3)
        transaction_date = c1.date_input("Transaction Date", date.today())
        voucher_no = c2.text_input("Voucher No")
        employee = c3.selectbox("Employee", [""] + employees)

        c4, c5, c6 = st.columns(3)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("Sub-Location", [""] + sublocations)
        category = c6.selectbox("Category", EXPENSE_CATEGORIES)

        purpose = st.text_area("Purpose")
        c7, c8 = st.columns(2)
        cash_out = c7.number_input("Cash Out", min_value=0.0, step=100.0)
        cash_in = c8.number_input("Cash In", min_value=0.0, step=100.0)
        status = st.selectbox("Status", ["Open", "Pending", "Closed"])
        notes = st.text_area("Notes")

        if st.form_submit_button("Save Petty Cash"):
            execute(
                """INSERT INTO petty_cash
                (transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out, cash_in, status, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out, cash_in, status, notes),
            )
            st.success("Petty cash saved.")
            st.rerun()

    st.dataframe(query("SELECT * FROM petty_cash ORDER BY transaction_date DESC"), use_container_width=True)


# -------------------------
# EMPLOYEE ADVANCES
# -------------------------
elif page == "Employee Advances":
    st.title("👤 Employee Advances / Loans")
    with st.form("advances_form"):
        c1, c2, c3 = st.columns(3)
        advance_date = c1.date_input("Advance Date", date.today())
        employee_name = c2.selectbox("Employee Name", [""] + employees)
        advance_type = c3.selectbox("Advance Type", ADVANCE_TYPES)

        c4, c5 = st.columns(2)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("Sub-Location", [""] + sublocations)

        c6, c7 = st.columns(2)
        amount_given = c6.number_input("Amount Given", min_value=0.0, step=100.0)
        amount_returned = c7.number_input("Amount Returned", min_value=0.0, step=100.0)
        status = st.selectbox("Status", ["Open", "Partially Returned", "Closed"])
        notes = st.text_area("Notes")

        if st.form_submit_button("Save Advance"):
            execute(
                """INSERT INTO employee_advances
                (advance_date, employee_name, advance_type, location, sublocation, amount_given, amount_returned, status, notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (advance_date, employee_name, advance_type, location, sublocation, amount_given, amount_returned, status, notes),
            )
            st.success("Advance saved.")
            st.rerun()

    df = query("SELECT * FROM employee_advances ORDER BY advance_date DESC")
    if not df.empty:
        df["remaining_balance"] = df["amount_given"] - df["amount_returned"]
    st.dataframe(df, use_container_width=True)


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
