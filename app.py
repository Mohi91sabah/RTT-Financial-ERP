
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# ======================================================
# RTT FINANCIAL CONTROL SYSTEM
# Revenue / Expenses / Petty Cash / Employee Advances
# ======================================================

st.set_page_config(
    page_title="RTT Financial Control System",
    page_icon="💼",
    layout="wide"
)

DB_NAME = "rtt_financial_control.db"

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

conn = get_conn()
cur = conn.cursor()

# -----------------------------
# DATABASE TABLES
# -----------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS settings_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT UNIQUE NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings_sublocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location TEXT NOT NULL,
    sublocation TEXT NOT NULL,
    UNIQUE(location, sublocation)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_name TEXT UNIQUE NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS revenue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_date TEXT,
    invoice_no TEXT,
    client TEXT,
    location TEXT,
    sublocation TEXT,
    service_month TEXT,
    service_year INTEGER,
    description TEXT,
    amount REAL,
    status TEXT,
    notes TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_date TEXT,
    voucher_no TEXT,
    supplier_or_employee TEXT,
    location TEXT,
    sublocation TEXT,
    category TEXT,
    description TEXT,
    amount REAL,
    payment_method TEXT,
    status TEXT,
    notes TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS petty_cash (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT,
    voucher_no TEXT,
    employee TEXT,
    location TEXT,
    sublocation TEXT,
    purpose TEXT,
    category TEXT,
    cash_out REAL DEFAULT 0,
    cash_in REAL DEFAULT 0,
    status TEXT,
    notes TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS employee_advances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advance_date TEXT,
    employee_name TEXT,
    advance_type TEXT,
    location TEXT,
    sublocation TEXT,
    amount_given REAL DEFAULT 0,
    amount_returned REAL DEFAULT 0,
    status TEXT,
    notes TEXT
)
""")

conn.commit()

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def run_query(query, params=()):
    return pd.read_sql_query(query, conn, params=params)

def execute(query, params=()):
    cur.execute(query, params)
    conn.commit()

def get_list(table, column):
    df = run_query(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL AND {column} <> '' ORDER BY {column}")
    return df[column].tolist()

def get_sublocations(location):
    df = run_query(
        "SELECT sublocation FROM settings_sublocations WHERE location=? ORDER BY sublocation",
        (location,)
    )
    return df["sublocation"].tolist()

def money(value):
    try:
        return f"${float(value):,.2f}"
    except:
        return "$0.00"

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

EXPENSE_CATEGORIES = [
    "Fuel",
    "Materials",
    "Transportation",
    "Accommodation",
    "Tools",
    "Consumables",
    "Site Expense",
    "Office Expense",
    "Manpower",
    "Equipment",
    "Other"
]

ADVANCE_TYPES = [
    "Salary Advance",
    "Personal Advance",
    "Work Advance",
    "Procurement Advance",
    "Site Advance",
    "Other"
]

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("RTT Financial System")
page = st.sidebar.radio(
    "Select Page",
    [
        "Dashboard",
        "Revenue",
        "Expenses",
        "Petty Cash",
        "Employee Advances",
        "Settings",
        "Reports"
    ]
)

locations = get_list("settings_locations", "location")
employees = get_list("employees", "employee_name")

# ======================================================
# DASHBOARD
# ======================================================
if page == "Dashboard":
    st.title("💼 Financial Control Dashboard")

    revenue_df = run_query("SELECT * FROM revenue")
    expenses_df = run_query("SELECT * FROM expenses")
    petty_df = run_query("SELECT * FROM petty_cash")
    adv_df = run_query("SELECT * FROM employee_advances")

    total_revenue = revenue_df["amount"].sum() if not revenue_df.empty else 0
    total_expenses = expenses_df["amount"].sum() if not expenses_df.empty else 0
    net_profit = total_revenue - total_expenses
    profit_margin = (net_profit / total_revenue * 100) if total_revenue else 0

    total_cash_out = petty_df["cash_out"].sum() if not petty_df.empty else 0
    total_cash_in = petty_df["cash_in"].sum() if not petty_df.empty else 0
    petty_balance = total_cash_in - total_cash_out

    total_advances = adv_df["amount_given"].sum() if not adv_df.empty else 0
    total_returned = adv_df["amount_returned"].sum() if not adv_df.empty else 0
    outstanding_advances = total_advances - total_returned

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", money(total_revenue))
    c2.metric("Total Expenses", money(total_expenses))
    c3.metric("Net Profit", money(net_profit))
    c4.metric("Profit Margin", f"{profit_margin:.2f}%")

    st.divider()

    c5, c6, c7 = st.columns(3)
    c5.metric("Petty Cash Out", money(total_cash_out))
    c6.metric("Petty Cash In", money(total_cash_in))
    c7.metric("Petty Cash Net Balance", money(petty_balance))

    c8, c9, c10 = st.columns(3)
    c8.metric("Total Advances Given", money(total_advances))
    c9.metric("Total Advances Returned", money(total_returned))
    c10.metric("Outstanding Advances", money(outstanding_advances))

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue by Location")
        if not revenue_df.empty:
            chart_df = revenue_df.groupby("location", as_index=False)["amount"].sum()
            st.bar_chart(chart_df.set_index("location"))
        else:
            st.info("No revenue data yet.")

    with col2:
        st.subheader("Expenses by Category")
        if not expenses_df.empty:
            chart_df = expenses_df.groupby("category", as_index=False)["amount"].sum()
            st.bar_chart(chart_df.set_index("category"))
        else:
            st.info("No expenses data yet.")

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Petty Cash by Category")
        if not petty_df.empty:
            chart_df = petty_df.groupby("category", as_index=False)["cash_out"].sum()
            st.bar_chart(chart_df.set_index("category"))
        else:
            st.info("No petty cash data yet.")

    with col4:
        st.subheader("Outstanding Advances by Employee")
        if not adv_df.empty:
            adv_df["remaining"] = adv_df["amount_given"] - adv_df["amount_returned"]
            chart_df = adv_df.groupby("employee_name", as_index=False)["remaining"].sum()
            st.bar_chart(chart_df.set_index("employee_name"))
        else:
            st.info("No employee advances data yet.")

# ======================================================
# REVENUE
# ======================================================
elif page == "Revenue":
    st.title("🧾 Revenue Register")

    with st.form("revenue_form"):
        col1, col2, col3 = st.columns(3)

        invoice_date = col1.date_input("Invoice Date", value=date.today())
        invoice_no = col2.text_input("Invoice No")
        client = col3.text_input("Client")

        col4, col5, col6 = st.columns(3)
        location = col4.selectbox("Location", [""] + locations)
        sublocations = get_sublocations(location) if location else []
        sublocation = col5.selectbox("SubLocation", [""] + sublocations)
        service_month = col6.selectbox("Service Month", MONTHS)

        col7, col8 = st.columns(2)
        service_year = col7.number_input("Service Year", min_value=2020, max_value=2100, value=date.today().year)
        amount = col8.number_input("Amount", min_value=0.0, step=100.0)

        description = st.text_area("Description")
        status = st.selectbox("Status", ["Pending", "Submitted", "Approved", "Paid"])
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save Revenue")

        if submitted:
            execute("""
                INSERT INTO revenue
                (invoice_date, invoice_no, client, location, sublocation, service_month, service_year, description, amount, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(invoice_date), invoice_no, client, location, sublocation,
                service_month, service_year, description, amount, status, notes
            ))
            st.success("Revenue saved successfully.")

    st.subheader("Revenue Data")
    st.dataframe(run_query("SELECT * FROM revenue ORDER BY invoice_date DESC"), use_container_width=True)

# ======================================================
# EXPENSES
# ======================================================
elif page == "Expenses":
    st.title("💸 Expenses Register")

    with st.form("expenses_form"):
        col1, col2, col3 = st.columns(3)

        payment_date = col1.date_input("Payment Date", value=date.today())
        voucher_no = col2.text_input("Voucher No")
        supplier_or_employee = col3.text_input("Supplier / Employee")

        col4, col5, col6 = st.columns(3)
        location = col4.selectbox("Location", [""] + locations)
        sublocations = get_sublocations(location) if location else []
        sublocation = col5.selectbox("SubLocation", [""] + sublocations)
        category = col6.selectbox("Category", EXPENSE_CATEGORIES)

        col7, col8 = st.columns(2)
        amount = col7.number_input("Amount", min_value=0.0, step=100.0)
        payment_method = col8.selectbox("Payment Method", ["Cash", "Bank Transfer", "Cheque", "Other"])

        description = st.text_area("Description")
        status = st.selectbox("Status", ["Pending", "Paid", "Cancelled"])
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save Expense")

        if submitted:
            execute("""
                INSERT INTO expenses
                (payment_date, voucher_no, supplier_or_employee, location, sublocation, category, description, amount, payment_method, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(payment_date), voucher_no, supplier_or_employee, location, sublocation,
                category, description, amount, payment_method, status, notes
            ))
            st.success("Expense saved successfully.")

    st.subheader("Expenses Data")
    st.dataframe(run_query("SELECT * FROM expenses ORDER BY payment_date DESC"), use_container_width=True)

# ======================================================
# PETTY CASH
# ======================================================
elif page == "Petty Cash":
    st.title("💵 Petty Cash Register")

    with st.form("petty_cash_form"):
        col1, col2, col3 = st.columns(3)

        transaction_date = col1.date_input("Transaction Date", value=date.today())
        voucher_no = col2.text_input("Voucher No")
        employee = col3.selectbox("Employee", [""] + employees)

        col4, col5, col6 = st.columns(3)
        location = col4.selectbox("Location", [""] + locations)
        sublocations = get_sublocations(location) if location else []
        sublocation = col5.selectbox("SubLocation", [""] + sublocations)
        category = col6.selectbox("Category", EXPENSE_CATEGORIES)

        purpose = st.text_area("Purpose")

        col7, col8 = st.columns(2)
        cash_out = col7.number_input("Cash Out", min_value=0.0, step=100.0)
        cash_in = col8.number_input("Cash In", min_value=0.0, step=100.0)

        status = st.selectbox("Status", ["Open", "Pending", "Closed"])
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save Petty Cash Transaction")

        if submitted:
            execute("""
                INSERT INTO petty_cash
                (transaction_date, voucher_no, employee, location, sublocation, purpose, category, cash_out, cash_in, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(transaction_date), voucher_no, employee, location, sublocation,
                purpose, category, cash_out, cash_in, status, notes
            ))
            st.success("Petty cash transaction saved successfully.")

    st.subheader("Petty Cash Data")
    df = run_query("SELECT * FROM petty_cash ORDER BY transaction_date DESC")
    if not df.empty:
        df["net_movement"] = df["cash_in"] - df["cash_out"]
    st.dataframe(df, use_container_width=True)

# ======================================================
# EMPLOYEE ADVANCES
# ======================================================
elif page == "Employee Advances":
    st.title("👤 Employee Advances / Loans")

    with st.form("advances_form"):
        col1, col2, col3 = st.columns(3)

        advance_date = col1.date_input("Advance Date", value=date.today())
        employee_name = col2.selectbox("Employee Name", [""] + employees)
        advance_type = col3.selectbox("Advance Type", ADVANCE_TYPES)

        col4, col5 = st.columns(2)
        location = col4.selectbox("Location", [""] + locations)
        sublocations = get_sublocations(location) if location else []
        sublocation = col5.selectbox("SubLocation", [""] + sublocations)

        col6, col7 = st.columns(2)
        amount_given = col6.number_input("Amount Given", min_value=0.0, step=100.0)
        amount_returned = col7.number_input("Amount Returned", min_value=0.0, step=100.0)

        status = st.selectbox("Status", ["Open", "Partially Returned", "Closed"])
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save Advance")

        if submitted:
            execute("""
                INSERT INTO employee_advances
                (advance_date, employee_name, advance_type, location, sublocation, amount_given, amount_returned, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(advance_date), employee_name, advance_type, location, sublocation,
                amount_given, amount_returned, status, notes
            ))
            st.success("Employee advance saved successfully.")

    st.subheader("Employee Advances Data")
    df = run_query("SELECT * FROM employee_advances ORDER BY advance_date DESC")
    if not df.empty:
        df["remaining_balance"] = df["amount_given"] - df["amount_returned"]
    st.dataframe(df, use_container_width=True)

# ======================================================
# SETTINGS
# ======================================================
elif page == "Settings":
    st.title("⚙️ Settings")

    st.subheader("Add Location")
    with st.form("location_form"):
        new_location = st.text_input("Location Name")
        if st.form_submit_button("Add Location"):
            if new_location.strip():
                try:
                    execute("INSERT INTO settings_locations (location) VALUES (?)", (new_location.strip(),))
                    st.success("Location added.")
                except sqlite3.IntegrityError:
                    st.warning("Location already exists.")

    st.subheader("Add SubLocation")
    with st.form("sublocation_form"):
        location = st.selectbox("Select Location", [""] + locations)
        new_sublocation = st.text_input("SubLocation Name")
        if st.form_submit_button("Add SubLocation"):
            if location and new_sublocation.strip():
                try:
                    execute(
                        "INSERT INTO settings_sublocations (location, sublocation) VALUES (?, ?)",
                        (location, new_sublocation.strip())
                    )
                    st.success("SubLocation added.")
                except sqlite3.IntegrityError:
                    st.warning("SubLocation already exists for this location.")

    st.subheader("Add Employee")
    with st.form("employee_form"):
        new_employee = st.text_input("Employee Name")
        if st.form_submit_button("Add Employee"):
            if new_employee.strip():
                try:
                    execute("INSERT INTO employees (employee_name) VALUES (?)", (new_employee.strip(),))
                    st.success("Employee added.")
                except sqlite3.IntegrityError:
                    st.warning("Employee already exists.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("Locations")
        st.dataframe(run_query("SELECT * FROM settings_locations"), use_container_width=True)
    with col2:
        st.write("SubLocations")
        st.dataframe(run_query("SELECT * FROM settings_sublocations"), use_container_width=True)
    with col3:
        st.write("Employees")
        st.dataframe(run_query("SELECT * FROM employees"), use_container_width=True)

# ======================================================
# REPORTS
# ======================================================
elif page == "Reports":
    st.title("📊 Reports")

    report_type = st.selectbox(
        "Select Report",
        [
            "Monthly Profitability",
            "Location Profitability",
            "Petty Cash Summary",
            "Employee Advances Summary"
        ]
    )

    if report_type == "Monthly Profitability":
        revenue_df = run_query("SELECT invoice_date, amount FROM revenue")
        expenses_df = run_query("SELECT payment_date, amount FROM expenses")

        if not revenue_df.empty:
            revenue_df["month"] = pd.to_datetime(revenue_df["invoice_date"]).dt.to_period("M").astype(str)
            rev = revenue_df.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "revenue"})
        else:
            rev = pd.DataFrame(columns=["month", "revenue"])

        if not expenses_df.empty:
            expenses_df["month"] = pd.to_datetime(expenses_df["payment_date"]).dt.to_period("M").astype(str)
            exp = expenses_df.groupby("month", as_index=False)["amount"].sum().rename(columns={"amount": "expenses"})
        else:
            exp = pd.DataFrame(columns=["month", "expenses"])

        report = pd.merge(rev, exp, on="month", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        report["profit_margin_%"] = report.apply(
            lambda x: (x["net_profit"] / x["revenue"] * 100) if x["revenue"] else 0,
            axis=1
        )

        st.dataframe(report.sort_values("month"), use_container_width=True)
        if not report.empty:
            st.bar_chart(report.set_index("month")[["revenue", "expenses", "net_profit"]])

    elif report_type == "Location Profitability":
        rev = run_query("SELECT location, SUM(amount) AS revenue FROM revenue GROUP BY location")
        exp = run_query("SELECT location, SUM(amount) AS expenses FROM expenses GROUP BY location")
        report = pd.merge(rev, exp, on="location", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        report["profit_margin_%"] = report.apply(
            lambda x: (x["net_profit"] / x["revenue"] * 100) if x["revenue"] else 0,
            axis=1
        )
        st.dataframe(report, use_container_width=True)
        if not report.empty:
            st.bar_chart(report.set_index("location")[["revenue", "expenses", "net_profit"]])

    elif report_type == "Petty Cash Summary":
        df = run_query("""
            SELECT employee, category,
                   SUM(cash_out) AS total_cash_out,
                   SUM(cash_in) AS total_cash_in,
                   SUM(cash_in) - SUM(cash_out) AS net_balance
            FROM petty_cash
            GROUP BY employee, category
        """)
        st.dataframe(df, use_container_width=True)

    elif report_type == "Employee Advances Summary":
        df = run_query("""
            SELECT employee_name, advance_type,
                   SUM(amount_given) AS total_given,
                   SUM(amount_returned) AS total_returned,
                   SUM(amount_given) - SUM(amount_returned) AS outstanding_balance
            FROM employee_advances
            GROUP BY employee_name, advance_type
        """)
        st.dataframe(df, use_container_width=True)
