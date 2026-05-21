
import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

st.set_page_config(page_title="RTT Financial ERP - Supabase", page_icon="💼", layout="wide")

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

def init_db():
    sql_list = [
        """CREATE TABLE IF NOT EXISTS settings_locations (
            id SERIAL PRIMARY KEY, location TEXT UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS settings_sublocations (
            id SERIAL PRIMARY KEY, location TEXT NOT NULL, sublocation TEXT NOT NULL,
            UNIQUE(location, sublocation)
        )""",
        """CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY, employee_name TEXT UNIQUE NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS revenue (
            id SERIAL PRIMARY KEY, invoice_date DATE, invoice_no TEXT, client TEXT,
            location TEXT, sublocation TEXT, service_month TEXT, service_year INTEGER,
            description TEXT, amount NUMERIC DEFAULT 0, status TEXT, notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY, payment_date DATE, voucher_no TEXT,
            supplier_or_employee TEXT, location TEXT, sublocation TEXT, category TEXT,
            description TEXT, amount NUMERIC DEFAULT 0, payment_method TEXT, status TEXT,
            notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS petty_cash (
            id SERIAL PRIMARY KEY, transaction_date DATE, voucher_no TEXT, employee TEXT,
            location TEXT, sublocation TEXT, purpose TEXT, category TEXT,
            cash_out NUMERIC DEFAULT 0, cash_in NUMERIC DEFAULT 0, status TEXT, notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS employee_advances (
            id SERIAL PRIMARY KEY, advance_date DATE, employee_name TEXT, advance_type TEXT,
            location TEXT, sublocation TEXT, amount_given NUMERIC DEFAULT 0,
            amount_returned NUMERIC DEFAULT 0, status TEXT, notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    ]
    for sql in sql_list:
        execute(sql)

init_db()

def money(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return "$0.00"

def get_list(table, col):
    try:
        df = query(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} <> '' ORDER BY {col}")
        return df[col].tolist()
    except Exception:
        return []

def get_sublocations(location):
    if not location:
        return []
    df = query("SELECT sublocation FROM settings_sublocations WHERE location=%s ORDER BY sublocation", (location,))
    return df["sublocation"].tolist()

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
EXPENSE_CATEGORIES = ["Fuel","Materials","Transportation","Accommodation","Tools","Consumables","Site Expense","Office Expense","Manpower","Equipment","Other"]
ADVANCE_TYPES = ["Salary Advance","Personal Advance","Work Advance","Procurement Advance","Site Advance","Other"]

locations = get_list("settings_locations", "location")
employees = get_list("employees", "employee_name")

st.sidebar.title("RTT Financial ERP")
page = st.sidebar.radio("Select Page", ["Dashboard","Revenue","Expenses","Petty Cash","Employee Advances","Settings","Reports"])

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

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Revenue", money(total_revenue))
    c2.metric("Total Expenses", money(total_expenses))
    c3.metric("Net Profit", money(net_profit))
    c4.metric("Profit Margin", f"{margin:.2f}%")

    c5,c6,c7 = st.columns(3)
    c5.metric("Petty Cash Out", money(cash_out))
    c6.metric("Petty Cash In", money(cash_in))
    c7.metric("Petty Cash Balance", money(cash_in - cash_out))

    c8,c9,c10 = st.columns(3)
    c8.metric("Advances Given", money(adv_given))
    c9.metric("Advances Returned", money(adv_returned))
    c10.metric("Outstanding Advances", money(adv_given - adv_returned))

    st.divider()
    col1,col2 = st.columns(2)
    with col1:
        st.subheader("Revenue by Location")
        if not revenue_df.empty:
            st.bar_chart(revenue_df.groupby("location")["amount"].sum())
    with col2:
        st.subheader("Expenses by Category")
        if not expenses_df.empty:
            st.bar_chart(expenses_df.groupby("category")["amount"].sum())

elif page == "Revenue":
    st.title("🧾 Revenue Register")
    with st.form("revenue_form"):
        c1,c2,c3 = st.columns(3)
        invoice_date = c1.date_input("Invoice Date", date.today())
        invoice_no = c2.text_input("Invoice No")
        client = c3.text_input("Client")
        c4,c5,c6 = st.columns(3)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("SubLocation", [""] + get_sublocations(location))
        service_month = c6.selectbox("Service Month", MONTHS)
        c7,c8 = st.columns(2)
        service_year = c7.number_input("Service Year", 2020, 2100, date.today().year)
        amount = c8.number_input("Amount", min_value=0.0, step=100.0)
        description = st.text_area("Description")
        status = st.selectbox("Status", ["Pending","Submitted","Approved","Paid"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Revenue"):
            execute("""INSERT INTO revenue
            (invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount, status, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount, status, notes))
            st.success("Revenue saved.")
    st.dataframe(query("SELECT * FROM revenue ORDER BY invoice_date DESC"), use_container_width=True)

elif page == "Expenses":
    st.title("💸 Expenses Register")
    with st.form("expenses_form"):
        c1,c2,c3 = st.columns(3)
        payment_date = c1.date_input("Payment Date", date.today())
        voucher_no = c2.text_input("Voucher No")
        supplier_or_employee = c3.text_input("Supplier / Employee")
        c4,c5,c6 = st.columns(3)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("SubLocation", [""] + get_sublocations(location))
        category = c6.selectbox("Category", EXPENSE_CATEGORIES)
        c7,c8 = st.columns(2)
        amount = c7.number_input("Amount", min_value=0.0, step=100.0)
        payment_method = c8.selectbox("Payment Method", ["Cash","Bank Transfer","Cheque","Other"])
        description = st.text_area("Description")
        status = st.selectbox("Status", ["Pending","Paid","Cancelled"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Expense"):
            execute("""INSERT INTO expenses
            (payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount, payment_method, status, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount, payment_method, status, notes))
            st.success("Expense saved.")
    st.dataframe(query("SELECT * FROM expenses ORDER BY payment_date DESC"), use_container_width=True)

elif page == "Petty Cash":
    st.title("💵 Petty Cash Register")
    with st.form("petty_cash_form"):
        c1,c2,c3 = st.columns(3)
        transaction_date = c1.date_input("Transaction Date", date.today())
        voucher_no = c2.text_input("Voucher No")
        employee = c3.selectbox("Employee", [""] + employees)
        c4,c5,c6 = st.columns(3)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("SubLocation", [""] + get_sublocations(location))
        category = c6.selectbox("Category", EXPENSE_CATEGORIES)
        purpose = st.text_area("Purpose")
        c7,c8 = st.columns(2)
        cash_out = c7.number_input("Cash Out", min_value=0.0, step=100.0)
        cash_in = c8.number_input("Cash In", min_value=0.0, step=100.0)
        status = st.selectbox("Status", ["Open","Pending","Closed"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Petty Cash"):
            execute("""INSERT INTO petty_cash
            (transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out, cash_in, status, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out, cash_in, status, notes))
            st.success("Petty cash saved.")
    st.dataframe(query("SELECT * FROM petty_cash ORDER BY transaction_date DESC"), use_container_width=True)

elif page == "Employee Advances":
    st.title("👤 Employee Advances / Loans")
    with st.form("advances_form"):
        c1,c2,c3 = st.columns(3)
        advance_date = c1.date_input("Advance Date", date.today())
        employee_name = c2.selectbox("Employee Name", [""] + employees)
        advance_type = c3.selectbox("Advance Type", ADVANCE_TYPES)
        c4,c5 = st.columns(2)
        location = c4.selectbox("Location", [""] + locations)
        sublocation = c5.selectbox("SubLocation", [""] + get_sublocations(location))
        c6,c7 = st.columns(2)
        amount_given = c6.number_input("Amount Given", min_value=0.0, step=100.0)
        amount_returned = c7.number_input("Amount Returned", min_value=0.0, step=100.0)
        status = st.selectbox("Status", ["Open","Partially Returned","Closed"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Save Advance"):
            execute("""INSERT INTO employee_advances
            (advance_date, employee_name, advance_type, location, sublocation, amount_given, amount_returned, status, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (advance_date, employee_name, advance_type, location, sublocation, amount_given, amount_returned, status, notes))
            st.success("Advance saved.")
    df = query("SELECT * FROM employee_advances ORDER BY advance_date DESC")
    if not df.empty:
        df["remaining_balance"] = df["amount_given"] - df["amount_returned"]
    st.dataframe(df, use_container_width=True)

elif page == "Settings":
    st.title("⚙️ Settings")
    with st.form("add_location"):
        new_location = st.text_input("New Location")
        if st.form_submit_button("Add Location") and new_location.strip():
            try:
                execute("INSERT INTO settings_locations (location) VALUES (%s)", (new_location.strip(),))
                st.success("Location added.")
            except Exception:
                st.warning("Location already exists.")
    with st.form("add_sublocation"):
        location = st.selectbox("Location", [""] + locations)
        new_sublocation = st.text_input("New SubLocation")
        if st.form_submit_button("Add SubLocation") and location and new_sublocation.strip():
            try:
                execute("INSERT INTO settings_sublocations (location, sublocation) VALUES (%s,%s)", (location, new_sublocation.strip()))
                st.success("SubLocation added.")
            except Exception:
                st.warning("SubLocation already exists.")
    with st.form("add_employee"):
        new_employee = st.text_input("New Employee")
        if st.form_submit_button("Add Employee") and new_employee.strip():
            try:
                execute("INSERT INTO employees (employee_name) VALUES (%s)", (new_employee.strip(),))
                st.success("Employee added.")
            except Exception:
                st.warning("Employee already exists.")
    c1,c2,c3 = st.columns(3)
    c1.dataframe(query("SELECT * FROM settings_locations"), use_container_width=True)
    c2.dataframe(query("SELECT * FROM settings_sublocations"), use_container_width=True)
    c3.dataframe(query("SELECT * FROM employees"), use_container_width=True)

elif page == "Reports":
    st.title("📊 Reports")
    report_type = st.selectbox("Select Report", ["Monthly Profitability","Location Profitability","Petty Cash Summary","Employee Advances Summary"])
    if report_type == "Monthly Profitability":
        rev = query("SELECT TO_CHAR(invoice_date, 'YYYY-MM') AS month, SUM(amount) AS revenue FROM revenue GROUP BY month ORDER BY month")
        exp = query("SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month, SUM(amount) AS expenses FROM expenses GROUP BY month ORDER BY month")
        report = pd.merge(rev, exp, on="month", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        st.dataframe(report, use_container_width=True)
        if not report.empty:
            st.bar_chart(report.set_index("month")[["revenue","expenses","net_profit"]])
    elif report_type == "Location Profitability":
        rev = query("SELECT location, SUM(amount) AS revenue FROM revenue GROUP BY location")
        exp = query("SELECT location, SUM(amount) AS expenses FROM expenses GROUP BY location")
        report = pd.merge(rev, exp, on="location", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        st.dataframe(report, use_container_width=True)
    elif report_type == "Petty Cash Summary":
        st.dataframe(query("""SELECT employee, category, SUM(cash_out) AS total_cash_out, SUM(cash_in) AS total_cash_in,
        SUM(cash_in)-SUM(cash_out) AS net_balance FROM petty_cash GROUP BY employee, category"""), use_container_width=True)
    elif report_type == "Employee Advances Summary":
        st.dataframe(query("""SELECT employee_name, advance_type, SUM(amount_given) AS total_given,
        SUM(amount_returned) AS total_returned, SUM(amount_given)-SUM(amount_returned) AS outstanding_balance
        FROM employee_advances GROUP BY employee_name, advance_type"""), use_container_width=True)
