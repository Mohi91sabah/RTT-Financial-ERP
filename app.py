"""
RTT Financial ERP - Production-Enhanced Version
================================================
Enhancements: Security, Performance, UX, Maintainability, Audit Logging
"""

import streamlit as st
import psycopg2
import psycopg2.extras
import psycopg2.pool
import pandas as pd
from datetime import date, datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any, Callable
from contextlib import contextmanager
import hashlib
import secrets
import re
import json
import io
import csv
import time
from functools import wraps

# =====================================================
# CONFIGURATION & SECURITY
# =====================================================

st.set_page_config(
    page_title="RTT Financial ERP",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Security: Use st.secrets for ALL sensitive data. Fallback only for local dev.
def get_secret(key: str, fallback: Optional[str] = None) -> str:
    """Safely retrieve secrets with fallback for local development only."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        if fallback:
            st.warning(f"⚠️ Using fallback for '{key}'. Configure secrets.toml for production!")
            return fallback
        raise RuntimeError(f"Missing required secret: {key}")


# Hash passwords with salt using PBKDF2 (industry standard)
def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash password with random salt. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    hash_val = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()
    return hash_val, salt


def verify_password(password: str, hash_val: str, salt: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password, salt)[0] == hash_val


# SECURITY: Store hashed credentials in secrets.toml, not plaintext
# Example secrets.toml:
# [credentials]
# username = "RTT@work26"
# password_hash = "..."  # Pre-computed hash
# password_salt = "..."
#
# To generate hash: run `python -c "from app import hash_password; print(hash_password('your_password'))"`

APP_USERNAME = get_secret("credentials.username", "RTT@work26")
# For migration: if secrets has hash, use it; otherwise hash the plaintext password once
if "credentials.password_hash" in st.secrets and "credentials.password_salt" in st.secrets:
    APP_PASSWORD_HASH = st.secrets["credentials.password_hash"]
    APP_PASSWORD_SALT = st.secrets["credentials.password_salt"]
else:
    # One-time migration: hash the plaintext password
    APP_PASSWORD_HASH, APP_PASSWORD_SALT = hash_password(get_secret("credentials.password", "RTT@MSN91"))


# Database connection pool (prevents connection leaks, handles concurrency)
DB_URL = get_secret("DB_URL")

@st.cache_resource(show_spinner=False)
def get_connection_pool():
    """Create a threaded connection pool for concurrent access."""
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DB_URL,
        # Connection health checks
        connect_timeout=10,
        options="-c statement_timeout=30000",  # 30s query timeout
    )


@contextmanager
def get_db_connection():
    """Context manager for safe database connection handling."""
    pool = get_connection_pool()
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise DatabaseError(f"Database error: {e}") from e
    finally:
        if conn:
            conn.commit()
            pool.putconn(conn)


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


def clear_app_cache():
    """Clear all cached data."""
    st.cache_data.clear()


# =====================================================
# INPUT VALIDATION & SANITIZATION
# =====================================================

# Whitelist allowed table/column names to prevent SQL injection
ALLOWED_TABLES = {
    "settings_locations", "settings_sublocations", "employees",
    "revenue", "expenses", "petty_cash", "employee_advances", "audit_log"
}

ALLOWED_COLUMNS = {
    "id", "location", "sublocation", "employee_name",
    "invoice_date", "invoice_no", "client", "service_month", "service_year",
    "description", "amount", "status", "notes", "created_at",
    "payment_date", "voucher_no", "supplier_or_employee", "category",
    "payment_method", "transaction_date", "employee", "purpose", "cash_out", "cash_in",
    "advance_date", "advance_type", "amount_given", "amount_returned"
}


def validate_identifier(name: str, allowed_set: set) -> str:
    """Validate SQL identifiers against whitelist."""
    if name not in allowed_set:
        raise ValueError(f"Invalid identifier: {name}")
    return name


def sanitize_text(text: Any, max_length: int = 500) -> str:
    """Sanitize user text input."""
    if text is None or pd.isna(text):
        return ""
    text = str(text).strip()
    # Remove potentially dangerous characters
    text = re.sub(r'[<>]', '', text)
    return text[:max_length]


def validate_amount(value: Any) -> float:
    """Validate and convert amount to float."""
    try:
        amount = float(value or 0)
        if amount < 0:
            raise ValueError("Amount cannot be negative")
        if amount > 999_999_999.99:
            raise ValueError("Amount exceeds maximum allowed")
        return round(amount, 2)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid amount: {e}")


# =====================================================
# AUDIT LOGGING
# =====================================================

def log_audit(action: str, table: str, record_id: Optional[int] = None,
              details: Optional[dict] = None, user: Optional[str] = None):
    """Log all data modifications for accountability."""
    user = user or st.session_state.get("username", "unknown")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO audit_log (action, table_name, record_id, user_name, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, (action, table, record_id, user,
                      json.dumps(details) if details else None))
    except Exception as e:
        # Audit failure should not break the app, but should be visible
        st.toast(f"⚠️ Audit log failed: {e}", icon="🚨")


# =====================================================
# DATABASE OPERATIONS (Parameterized, Safe)
# =====================================================

def execute(sql: str, params: Tuple = (), audit_action: Optional[str] = None,
            audit_table: Optional[str] = None, audit_id: Optional[int] = None) -> None:
    """
    Execute SQL with proper parameterization and audit logging.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if audit_action:
                # Get last inserted ID if applicable
                if "INSERT" in sql.upper() and "RETURNING" not in sql.upper():
                    cur.execute("SELECT LASTVAL()")
                    last_id = cur.fetchone()[0]
                else:
                    last_id = audit_id
                log_audit(audit_action, audit_table or "unknown", last_id)

    clear_app_cache()


def execute_returning(sql: str, params: Tuple = ()) -> int:
    """Execute INSERT and return the generated ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            result = cur.fetchone()[0]
            return result


@st.cache_data(ttl=60, show_spinner=False)
def query(sql: str, params: Tuple = ()) -> pd.DataFrame:
    """Execute safe parameterized query with caching."""
    with get_db_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def query_single(sql: str, params: Tuple = ()) -> Optional[Any]:
    """Execute query returning single value."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
            return result[0] if result else None


# =====================================================
# DEFAULT SETTINGS DATA
# =====================================================

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
STATUS_OPTIONS = {
    "revenue": ["Pending", "Submitted", "Approved", "Paid"],
    "expenses": ["Pending", "Paid", "Cancelled"],
    "petty_cash": ["Open", "Pending", "Closed"],
    "advances": ["Open", "Partially Returned", "Closed"]
}


# =====================================================
# DATABASE INITIALIZATION
# =====================================================

def init_db():
    """Initialize database with all required tables."""
    sql_statements = [
        """CREATE TABLE IF NOT EXISTS settings_locations (
            id SERIAL PRIMARY KEY,
            location TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS settings_sublocations (
            id SERIAL PRIMARY KEY,
            sublocation TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            employee_name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            amount NUMERIC(15,2) DEFAULT 0 CHECK (amount >= 0),
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT
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
            amount NUMERIC(15,2) DEFAULT 0 CHECK (amount >= 0),
            payment_method TEXT,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT
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
            cash_out NUMERIC(15,2) DEFAULT 0 CHECK (cash_out >= 0),
            cash_in NUMERIC(15,2) DEFAULT 0 CHECK (cash_in >= 0),
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS employee_advances (
            id SERIAL PRIMARY KEY,
            advance_date DATE,
            employee_name TEXT,
            advance_type TEXT,
            location TEXT,
            sublocation TEXT,
            amount_given NUMERIC(15,2) DEFAULT 0 CHECK (amount_given >= 0),
            amount_returned NUMERIC(15,2) DEFAULT 0 CHECK (amount_returned >= 0),
            status TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_id INTEGER,
            user_name TEXT,
            details JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        # Indexes for performance
        """CREATE INDEX IF NOT EXISTS idx_revenue_date ON revenue(invoice_date)""",
        """CREATE INDEX IF NOT EXISTS idx_revenue_location ON revenue(location)""",
        """CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(payment_date)""",
        """CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)""",
        """CREATE INDEX IF NOT EXISTS idx_petty_date ON petty_cash(transaction_date)""",
        """CREATE INDEX IF NOT EXISTS idx_advances_employee ON employee_advances(employee_name)""",
        """CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)""",
    ]

    for sql in sql_statements:
        try:
            execute(sql)
        except Exception as e:
            st.error(f"DB Init Error: {e}")
            raise

    # Migration: Add updated_at/updated_by columns if missing (backward compatibility)
    migration_statements = [
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE revenue ADD COLUMN IF NOT EXISTS updated_by TEXT",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS updated_by TEXT",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE petty_cash ADD COLUMN IF NOT EXISTS updated_by TEXT",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE employee_advances ADD COLUMN IF NOT EXISTS updated_by TEXT",
    ]
    for sql in migration_statements:
        try:
            execute(sql)
        except Exception:
            pass  # Column might already exist


def seed_default_settings():
    """Seed default locations and sublocations if tables are empty."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Atomic upsert using ON CONFLICT
            for loc in DEFAULT_LOCATIONS:
                cur.execute("""
                    INSERT INTO settings_locations (location)
                    VALUES (%s)
                    ON CONFLICT (location) DO NOTHING
                """, (loc.strip(),))

            for sub in DEFAULT_SUBLOCATIONS:
                cur.execute("""
                    INSERT INTO settings_sublocations (sublocation)
                    VALUES (%s)
                    ON CONFLICT (sublocation) DO NOTHING
                """, (sub.strip(),))


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def money(x: Any) -> str:
    """Format number as currency."""
    try:
        return f"${float(x):,.2f}"
    except (ValueError, TypeError):
        return "$0.00"


def get_list(table: str, col: str) -> List[str]:
    """Safely get distinct values from a table column."""
    # Validate against whitelist
    safe_table = validate_identifier(table, ALLOWED_TABLES)
    safe_col = validate_identifier(col, ALLOWED_COLUMNS)

    try:
        df = query(
            f"SELECT DISTINCT {safe_col} FROM {safe_table} WHERE {safe_col} IS NOT NULL AND {safe_col} <> '' ORDER BY {safe_col}"
        )
        return df[safe_col].dropna().astype(str).tolist()
    except Exception as e:
        st.error(f"Error loading {col}: {e}")
        return []


def safe_date(value: Any) -> date:
    """Safely convert value to date."""
    if pd.isna(value) or value == "" or value is None:
        return date.today()
    try:
        return pd.to_datetime(value).date()
    except (ValueError, TypeError):
        return date.today()


def option_index(options: List[str], value: Any) -> int:
    """Get index of value in options list."""
    value = "" if pd.isna(value) else str(value)
    return options.index(value) if value in options else 0


def amount_value(value: Any) -> float:
    """Safely convert to float amount."""
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def current_user() -> str:
    """Get current logged-in username."""
    return st.session_state.get("username", "unknown")


# =====================================================
# AUTHENTICATION
# =====================================================

def login_page():
    """Enhanced login with rate limiting and secure password verification."""
    st.title("🔐 RTT Financial ERP Login")
    st.info("Please enter your credentials to access the system.")

    # Rate limiting
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
        st.session_state.last_attempt_time = 0

    # Lockout after 5 failed attempts for 5 minutes
    if st.session_state.login_attempts >= 5:
        time_since_last = time.time() - st.session_state.last_attempt_time
        if time_since_last < 300:
            remaining = int(300 - time_since_last)
            st.error(f"⛔ Account locked. Please try again in {remaining} seconds.")
            st.stop()
        else:
            st.session_state.login_attempts = 0

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        st.session_state.last_attempt_time = time.time()

        if username != APP_USERNAME:
            st.session_state.login_attempts += 1
            remaining = 5 - st.session_state.login_attempts
            st.error(f"Invalid username or password. {remaining} attempts remaining.")
            return

        if not verify_password(password, APP_PASSWORD_HASH, APP_PASSWORD_SALT):
            st.session_state.login_attempts += 1
            remaining = 5 - st.session_state.login_attempts
            st.error(f"Invalid username or password. {remaining} attempts remaining.")
            log_audit("LOGIN_FAILED", "system", user=username)
            return

        # Success
        st.session_state.login_attempts = 0
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.session_state["login_time"] = datetime.now().isoformat()
        log_audit("LOGIN_SUCCESS", "system", user=username)
        st.success("✅ Login successful!")
        st.rerun()


def logout_button():
    """Enhanced logout with session cleanup."""
    st.sidebar.write(f"Logged in as: **{current_user()}**")
    st.sidebar.caption(f"Session started: {st.session_state.get('login_time', 'N/A')[:10]}")

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        log_audit("LOGOUT", "system", user=current_user())
        for key in ["logged_in", "username", "login_time", "login_attempts"]:
            st.session_state.pop(key, None)
        st.rerun()


# =====================================================
# DATA EXPORT UTILITIES
# =====================================================

def export_to_csv(df: pd.DataFrame, filename: str) -> bytes:
    """Convert DataFrame to CSV bytes."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def export_to_excel(df: pd.DataFrame, filename: str) -> bytes:
    """Convert DataFrame to Excel bytes."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Data")
    return buffer.getvalue()


def render_export_buttons(df: pd.DataFrame, prefix: str):
    """Render export buttons for a DataFrame."""
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download CSV",
            export_to_csv(df, f"{prefix}.csv"),
            file_name=f"{prefix}_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "📥 Download Excel",
            export_to_excel(df, f"{prefix}.xlsx"),
            file_name=f"{prefix}_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# =====================================================
# CRUD COMPONENTS (Reusable, Safe)
# =====================================================

def crud_single_column(title: str, table: str, id_col: str, value_col: str, label: str):
    """
    Reusable CRUD component for single-column lookup tables.
    Now with validation, audit logging, and export.
    """
    st.subheader(title)

    # Add new
    with st.expander(f"➕ Add {label}", expanded=False):
        with st.form(f"add_{table}"):
            new_value = st.text_input(f"New {label}", max_chars=100)
            col1, col2 = st.columns([1, 3])
            with col1:
                submitted = st.form_submit_button(f"Add {label}", use_container_width=True)

            if submitted:
                clean_value = sanitize_text(new_value)
                if not clean_value:
                    st.warning("Please enter a value.")
                else:
                    try:
                        execute(
                            f"""
                            INSERT INTO {validate_identifier(table, ALLOWED_TABLES)} ({validate_identifier(value_col, ALLOWED_COLUMNS)})
                            VALUES (%s)
                            ON CONFLICT ({validate_identifier(value_col, ALLOWED_COLUMNS)}) DO NOTHING
                            """,
                            (clean_value,),
                            audit_action="CREATE",
                            audit_table=table,
                        )
                        st.success(f"✅ {label} '{clean_value}' added successfully.")
                        log_audit("CREATE", table, details={"value": clean_value})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add {label}: {e}")

    # Display list with search
    df = query(f"""
        SELECT {validate_identifier(id_col, ALLOWED_COLUMNS)}, {validate_identifier(value_col, ALLOWED_COLUMNS)}
        FROM {validate_identifier(table, ALLOWED_TABLES)}
        ORDER BY {validate_identifier(value_col, ALLOWED_COLUMNS)}
    """)

    if df.empty:
        st.info(f"No {label.lower()} records found.")
        return

    # Search filter
    search = st.text_input(f"🔍 Search {label.lower()}", key=f"search_{table}")
    if search:
        df = df[df[value_col].astype(str).str.contains(search, case=False, na=False)]

    st.dataframe(df, use_container_width=True, hide_index=True)
    render_export_buttons(df, f"{label.lower()}_list")

    if df.empty:
        return

    # Edit/Delete
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
            edited_value = st.text_input(f"Edit {label}", value=current_value, max_chars=100)
            if st.form_submit_button("💾 Update", use_container_width=True):
                clean_edit = sanitize_text(edited_value)
                if not clean_edit:
                    st.warning("Value cannot be empty.")
                else:
                    try:
                        execute(
                            f"UPDATE {validate_identifier(table, ALLOWED_TABLES)} SET {validate_identifier(value_col, ALLOWED_COLUMNS)}=%s WHERE {validate_identifier(id_col, ALLOWED_COLUMNS)}=%s",
                            (clean_edit, selected_id),
                            audit_action="UPDATE",
                            audit_table=table,
                        )
                        log_audit("UPDATE", table, selected_id, {"old": current_value, "new": clean_edit})
                        st.success("✅ Updated successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update: {e}")

    with c2:
        st.warning("⚠️ Delete is permanent and cannot be undone.")
        confirm = st.checkbox(f"I confirm deleting '{current_value}'", key=f"confirm_delete_{table}")
        if st.button(f"🗑️ Delete {label}", key=f"delete_{table}", disabled=not confirm, use_container_width=True):
            try:
                execute(
                    f"DELETE FROM {validate_identifier(table, ALLOWED_TABLES)} WHERE {validate_identifier(id_col, ALLOWED_COLUMNS)}=%s",
                    (selected_id,),
                    audit_action="DELETE",
                    audit_table=table,
                )
                log_audit("DELETE", table, selected_id, {"value": current_value})
                st.success("✅ Deleted successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not delete: {e}")


def record_crud(table: str, title: str, date_col: str, order_col: str,
                form_renderer: Callable, update_sql: str, delete_sql: str, label: str):
    """
    Reusable record CRUD with pagination, filtering, and audit logging.
    """
    st.subheader(f"✏️ Edit / Delete {label}")

    # Filters
    with st.expander("🔍 Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            date_from = st.date_input("From", value=None, key=f"filter_from_{table}")
        with col2:
            date_to = st.date_input("To", value=None, key=f"filter_to_{table}")
        with col3:
            status_filter = st.multiselect(
                "Status",
                options=STATUS_OPTIONS.get(table, ["All"]),
                default=[],
                key=f"filter_status_{table}"
            )

    # Build query dynamically but safely
    base_query = f"SELECT * FROM {validate_identifier(table, ALLOWED_TABLES)} WHERE 1=1"
    params = []

    if date_from:
        base_query += f" AND {date_col} >= %s"
        params.append(date_from)
    if date_to:
        base_query += f" AND {date_col} <= %s"
        params.append(date_to)
    if status_filter:
        placeholders = ",".join(["%s"] * len(status_filter))
        base_query += f" AND status IN ({placeholders})"
        params.extend(status_filter)

    base_query += f" ORDER BY {order_col} DESC, id DESC LIMIT 300"

    df = query(base_query, tuple(params))

    if df.empty:
        st.info(f"No {label.lower()} records found.")
        return

    st.caption(f"Showing {len(df)} records (max 300). Use filters to narrow results.")
    st.dataframe(df, use_container_width=True, hide_index=True)
    render_export_buttons(df, f"{label.lower()}_records")

    def display_record(row_id: int) -> str:
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
            if st.form_submit_button(f"💾 Update {label}", use_container_width=True):
                try:
                    # Add updated_by and updated_at
                    execute(update_sql, (*values, current_user(), selected_id))
                    log_audit("UPDATE", table, selected_id, {"updated_by": current_user()})
                    st.success(f"✅ {label} updated successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

    with c2:
        st.warning("⚠️ Delete is permanent.")
        confirm = st.checkbox(f"I confirm deleting this {label}", key=f"confirm_delete_{table}")
        if st.button(f"🗑️ Delete {label}", key=f"delete_{table}_record", disabled=not confirm, use_container_width=True):
            try:
                execute(delete_sql, (selected_id,), audit_action="DELETE", audit_table=table)
                log_audit("DELETE", table, selected_id)
                st.success(f"✅ {label} deleted successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")


# =====================================================
# FORM FIELD RENDERERS
# =====================================================

def revenue_fields(record: Optional[pd.Series] = None, prefix: str = "") -> Tuple:
    """Render revenue form fields."""
    record = record if record is not None else {}

    c1, c2, c3 = st.columns(3)
    invoice_date = c1.date_input(
        "Invoice Date",
        safe_date(record.get("invoice_date", date.today())),
        key=f"{prefix}invoice_date"
    )
    invoice_no = c2.text_input(
        "Invoice No",
        value=sanitize_text(record.get("invoice_no", "")),
        max_chars=50,
        key=f"{prefix}invoice_no"
    )
    client = c3.text_input(
        "Client",
        value=sanitize_text(record.get("client", "")),
        max_chars=100,
        key=f"{prefix}client"
    )

    c4, c5, c6 = st.columns(3)
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox(
        "Location",
        loc_options,
        index=option_index(loc_options, record.get("location", "")),
        key=f"{prefix}location"
    )
    sublocation = c5.selectbox(
        "Sub-Location",
        sub_options,
        index=option_index(sub_options, record.get("sublocation", "")),
        key=f"{prefix}sublocation"
    )
    service_month = c6.selectbox(
        "Service Month",
        MONTHS,
        index=option_index(MONTHS, record.get("service_month", MONTHS[0])),
        key=f"{prefix}service_month"
    )

    c7, c8 = st.columns(2)
    service_year = c7.number_input(
        "Service Year",
        2020, 2100,
        int(record.get("service_year", date.today().year) or date.today().year),
        key=f"{prefix}service_year"
    )
    amount = c8.number_input(
        "Amount",
        min_value=0.0,
        step=100.0,
        value=amount_value(record.get("amount", 0)),
        format="%.2f",
        key=f"{prefix}amount"
    )

    description = st.text_area(
        "Description",
        value=sanitize_text(record.get("description", ""), max_length=1000),
        max_chars=1000,
        key=f"{prefix}description"
    )
    status = st.selectbox(
        "Status",
        STATUS_OPTIONS["revenue"],
        index=option_index(STATUS_OPTIONS["revenue"], record.get("status", "Pending")),
        key=f"{prefix}status"
    )
    notes = st.text_area(
        "Notes",
        value=sanitize_text(record.get("notes", ""), max_length=1000),
        max_chars=1000,
        key=f"{prefix}notes"
    )

    return (
        invoice_date, invoice_no, client, location, sublocation,
        service_month, service_year, description, amount, status, notes
    )


def expense_fields(record: Optional[pd.Series] = None, prefix: str = "") -> Tuple:
    """Render expense form fields."""
    record = record if record is not None else {}

    c1, c2, c3 = st.columns(3)
    payment_date = c1.date_input(
        "Payment Date",
        safe_date(record.get("payment_date", date.today())),
        key=f"{prefix}payment_date"
    )
    voucher_no = c2.text_input(
        "Voucher No",
        value=sanitize_text(record.get("voucher_no", "")),
        max_chars=50,
        key=f"{prefix}voucher_no"
    )
    supplier_or_employee = c3.text_input(
        "Supplier / Employee",
        value=sanitize_text(record.get("supplier_or_employee", "")),
        max_chars=100,
        key=f"{prefix}supplier_or_employee"
    )

    c4, c5, c6 = st.columns(3)
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox(
        "Location",
        loc_options,
        index=option_index(loc_options, record.get("location", "")),
        key=f"{prefix}location"
    )
    sublocation = c5.selectbox(
        "Sub-Location",
        sub_options,
        index=option_index(sub_options, record.get("sublocation", "")),
        key=f"{prefix}sublocation"
    )
    category = c6.selectbox(
        "Category",
        EXPENSE_CATEGORIES,
        index=option_index(EXPENSE_CATEGORIES, record.get("category", EXPENSE_CATEGORIES[0])),
        key=f"{prefix}category"
    )

    c7, c8 = st.columns(2)
    amount = c7.number_input(
        "Amount",
        min_value=0.0,
        step=100.0,
        value=amount_value(record.get("amount", 0)),
        format="%.2f",
        key=f"{prefix}amount"
    )
    pm_options = ["Cash", "Bank Transfer", "Cheque", "Other"]
    payment_method = c8.selectbox(
        "Payment Method",
        pm_options,
        index=option_index(pm_options, record.get("payment_method", "Cash")),
        key=f"{prefix}payment_method"
    )

    description = st.text_area(
        "Description",
        value=sanitize_text(record.get("description", ""), max_length=1000),
        max_chars=1000,
        key=f"{prefix}description"
    )
    status = st.selectbox(
        "Status",
        STATUS_OPTIONS["expenses"],
        index=option_index(STATUS_OPTIONS["expenses"], record.get("status", "Pending")),
        key=f"{prefix}status"
    )
    notes = st.text_area(
        "Notes",
        value=sanitize_text(record.get("notes", ""), max_length=1000),
        max_chars=1000,
        key=f"{prefix}notes"
    )

    return (
        payment_date, voucher_no, supplier_or_employee, location, sublocation,
        category, description, amount, payment_method, status, notes
    )


def petty_fields(record: Optional[pd.Series] = None, prefix: str = "") -> Tuple:
    """Render petty cash form fields."""
    record = record if record is not None else {}

    c1, c2, c3 = st.columns(3)
    transaction_date = c1.date_input(
        "Transaction Date",
        safe_date(record.get("transaction_date", date.today())),
        key=f"{prefix}transaction_date"
    )
    voucher_no = c2.text_input(
        "Voucher No",
        value=sanitize_text(record.get("voucher_no", "")),
        max_chars=50,
        key=f"{prefix}voucher_no"
    )
    emp_options = [""] + employees
    employee = c3.selectbox(
        "Employee",
        emp_options,
        index=option_index(emp_options, record.get("employee", "")),
        key=f"{prefix}employee"
    )

    c4, c5, c6 = st.columns(3)
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox(
        "Location",
        loc_options,
        index=option_index(loc_options, record.get("location", "")),
        key=f"{prefix}location"
    )
    sublocation = c5.selectbox(
        "Sub-Location",
        sub_options,
        index=option_index(sub_options, record.get("sublocation", "")),
        key=f"{prefix}sublocation"
    )
    category = c6.selectbox(
        "Category",
        EXPENSE_CATEGORIES,
        index=option_index(EXPENSE_CATEGORIES, record.get("category", EXPENSE_CATEGORIES[0])),
        key=f"{prefix}category"
    )

    purpose = st.text_area(
        "Purpose",
        value=sanitize_text(record.get("purpose", ""), max_length=1000),
        max_chars=1000,
        key=f"{prefix}purpose"
    )

    c7, c8 = st.columns(2)
    cash_out = c7.number_input(
        "Cash Out",
        min_value=0.0,
        step=100.0,
        value=amount_value(record.get("cash_out", 0)),
        format="%.2f",
        key=f"{prefix}cash_out"
    )
    cash_in = c8.number_input(
        "Cash In",
        min_value=0.0,
        step=100.0,
        value=amount_value(record.get("cash_in", 0)),
        format="%.2f",
        key=f"{prefix}cash_in"
    )

    status = st.selectbox(
        "Status",
        STATUS_OPTIONS["petty_cash"],
        index=option_index(STATUS_OPTIONS["petty_cash"], record.get("status", "Open")),
        key=f"{prefix}status"
    )
    notes = st.text_area(
        "Notes",
        value=sanitize_text(record.get("notes", ""), max_length=1000),
        max_chars=1000,
        key=f"{prefix}notes"
    )

    return (
        transaction_date, voucher_no, employee, location, sublocation,
        purpose, category, cash_out, cash_in, status, notes
    )


def advance_fields(record: Optional[pd.Series] = None, prefix: str = "") -> Tuple:
    """Render employee advance form fields."""
    record = record if record is not None else {}

    c1, c2, c3 = st.columns(3)
    advance_date = c1.date_input(
        "Advance Date",
        safe_date(record.get("advance_date", date.today())),
        key=f"{prefix}advance_date"
    )
    emp_options = [""] + employees
    employee_name = c2.selectbox(
        "Employee Name",
        emp_options,
        index=option_index(emp_options, record.get("employee_name", "")),
        key=f"{prefix}employee_name"
    )
    advance_type = c3.selectbox(
        "Advance Type",
        ADVANCE_TYPES,
        index=option_index(ADVANCE_TYPES, record.get("advance_type", ADVANCE_TYPES[0])),
        key=f"{prefix}advance_type"
    )

    c4, c5 = st.columns(2)
    loc_options = [""] + locations
    sub_options = [""] + sublocations
    location = c4.selectbox(
        "Location",
        loc_options,
        index=option_index(loc_options, record.get("location", "")),
        key=f"{prefix}location"
    )
    sublocation = c5.selectbox(
        "Sub-Location",
        sub_options,
        index=option_index(sub_options, record.get("sublocation", "")),
        key=f"{prefix}sublocation"
    )

    c6, c7 = st.columns(2)
    amount_given = c6.number_input(
        "Amount Given",
        min_value=0.0,
        step=100.0,
        value=amount_value(record.get("amount_given", 0)),
        format="%.2f",
        key=f"{prefix}amount_given"
    )
    amount_returned = c7.number_input(
        "Amount Returned",
        min_value=0.0,
        step=100.0,
        value=amount_value(record.get("amount_returned", 0)),
        format="%.2f",
        key=f"{prefix}amount_returned"
    )

    status = st.selectbox(
        "Status",
        STATUS_OPTIONS["advances"],
        index=option_index(STATUS_OPTIONS["advances"], record.get("status", "Open")),
        key=f"{prefix}status"
    )
    notes = st.text_area(
        "Notes",
        value=sanitize_text(record.get("notes", ""), max_length=1000),
        max_chars=1000,
        key=f"{prefix}notes"
    )

    return (
        advance_date, employee_name, advance_type, location, sublocation,
        amount_given, amount_returned, status, notes
    )


# =====================================================
# APP INITIALIZATION
# =====================================================

if "db_initialized" not in st.session_state:
    try:
        init_db()
        seed_default_settings()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        st.stop()

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login_page()
    st.stop()

# Load reference data
locations = get_list("settings_locations", "location")
sublocations = get_list("settings_sublocations", "sublocation")
employees = get_list("employees", "employee_name")

st.sidebar.title("💼 RTT Financial ERP")
logout_button()

page = st.sidebar.radio(
    "Select Page",
    ["Dashboard", "Revenue", "Expenses", "Petty Cash", "Employee Advances", "Settings", "Reports", "Audit Log"],
)


# =====================================================
# DASHBOARD
# =====================================================

if page == "Dashboard":
    st.title("💼 Financial Control Dashboard")

    # Key metrics with SQL summaries
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

    # Metrics with color indicators
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", money(total_revenue), delta=None)
    c2.metric("Total Expenses", money(total_expenses), delta=None)
    delta_profit = money(net_profit) if net_profit >= 0 else f"-{money(abs(net_profit))}"
    c3.metric("Net Profit", delta_profit, delta=f"{margin:.1f}% margin")
    c4.metric("Profit Margin", f"{margin:.2f}%")

    c5, c6, c7 = st.columns(3)
    c5.metric("Petty Cash Out", money(cash_out))
    c6.metric("Petty Cash In", money(cash_in))
    c7.metric("Petty Cash Balance", money(cash_in - cash_out),
              delta="Positive" if cash_in > cash_out else "Negative",
              delta_color="normal" if cash_in > cash_out else "inverse")

    c8, c9, c10 = st.columns(3)
    c8.metric("Advances Given", money(adv_given))
    c9.metric("Advances Returned", money(adv_returned))
    c10.metric("Outstanding Advances", money(adv_given - adv_returned),
               delta_color="inverse")

    st.divider()

    # Charts
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
            st.bar_chart(rev_loc.set_index("location")["amount"], use_container_width=True)
        else:
            st.info("No revenue data available.")

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
            st.bar_chart(exp_cat.set_index("category")["amount"], use_container_width=True)
        else:
            st.info("No expense data available.")

    # Recent activity
    st.divider()
    st.subheader("📋 Recent Activity")
    recent = query("""
        SELECT 'Revenue' as type, invoice_date as date, client as ref, amount, status, created_at
        FROM revenue
        UNION ALL
        SELECT 'Expense' as type, payment_date as date, voucher_no as ref, amount, status, created_at
        FROM expenses
        UNION ALL
        SELECT 'Petty Cash' as type, transaction_date as date, voucher_no as ref, cash_out as amount, status, created_at
        FROM petty_cash
        UNION ALL
        SELECT 'Advance' as type, advance_date as date, employee_name as ref, amount_given as amount, status, created_at
        FROM employee_advances
        ORDER BY created_at DESC
        LIMIT 10
    """)
    if not recent.empty:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity.")


# =====================================================
# REVENUE
# =====================================================

elif page == "Revenue":
    st.title("🧾 Revenue Register")
    tab_add, tab_manage = st.tabs(["➕ Add Revenue", "✏️ Edit / Delete Revenue"])

    with tab_add:
        with st.form("revenue_form"):
            values = revenue_fields(prefix="add_rev_")
            if st.form_submit_button("💾 Save Revenue", use_container_width=True):
                try:
                    execute(
                        """INSERT INTO revenue
                        (invoice_date, invoice_no, client, location, sublocation,
                         service_month, service_year, description, amount, status, notes, updated_by)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (*values, current_user()),
                        audit_action="CREATE",
                        audit_table="revenue",
                    )
                    st.success("✅ Revenue saved successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

    with tab_manage:
        record_crud(
            table="revenue",
            title="Revenue",
            date_col="invoice_date",
            order_col="invoice_date",
            form_renderer=lambda record: revenue_fields(record, prefix="edit_rev_"),
            update_sql="""UPDATE revenue SET
                invoice_date=%s, invoice_no=%s, client=%s, location=%s, sublocation=%s,
                service_month=%s, service_year=%s, description=%s, amount=%s, status=%s, notes=%s,
                updated_by=%s, updated_at=NOW()
                WHERE id=%s""",
            delete_sql="DELETE FROM revenue WHERE id=%s",
            label="Revenue",
        )


# =====================================================
# EXPENSES
# =====================================================

elif page == "Expenses":
    st.title("💸 Expenses Register")
    tab_add, tab_manage = st.tabs(["➕ Add Expense", "✏️ Edit / Delete Expenses"])

    with tab_add:
        with st.form("expenses_form"):
            values = expense_fields(prefix="add_exp_")
            if st.form_submit_button("💾 Save Expense", use_container_width=True):
                try:
                    execute(
                        """INSERT INTO expenses
                        (payment_date, voucher_no, supplier_or_employee, location, sublocation,
                         category, description, amount, payment_method, status, notes, updated_by)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (*values, current_user()),
                        audit_action="CREATE",
                        audit_table="expenses",
                    )
                    st.success("✅ Expense saved successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

    with tab_manage:
        record_crud(
            table="expenses",
            title="Expenses",
            date_col="payment_date",
            order_col="payment_date",
            form_renderer=lambda record: expense_fields(record, prefix="edit_exp_"),
            update_sql="""UPDATE expenses SET
                payment_date=%s, voucher_no=%s, supplier_or_employee=%s, location=%s, sublocation=%s,
                category=%s, description=%s, amount=%s, payment_method=%s, status=%s, notes=%s,
                updated_by=%s, updated_at=NOW()
                WHERE id=%s""",
            delete_sql="DELETE FROM expenses WHERE id=%s",
            label="Expense",
        )


# =====================================================
# PETTY CASH
# =====================================================

elif page == "Petty Cash":
    st.title("💵 Petty Cash Register")
    tab_add, tab_manage = st.tabs(["➕ Add Petty Cash", "✏️ Edit / Delete Petty Cash"])

    with tab_add:
        with st.form("petty_cash_form"):
            values = petty_fields(prefix="add_petty_")
            if st.form_submit_button("💾 Save Petty Cash", use_container_width=True):
                try:
                    execute(
                        """INSERT INTO petty_cash
                        (transaction_date, voucher_no, employee, location, sublocation,
                         purpose, category, cash_out, cash_in, status, notes, updated_by)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (*values, current_user()),
                        audit_action="CREATE",
                        audit_table="petty_cash",
                    )
                    st.success("✅ Petty cash saved successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

    with tab_manage:
        record_crud(
            table="petty_cash",
            title="Petty Cash",
            date_col="transaction_date",
            order_col="transaction_date",
            form_renderer=lambda record: petty_fields(record, prefix="edit_petty_"),
            update_sql="""UPDATE petty_cash SET
                transaction_date=%s, voucher_no=%s, employee=%s, location=%s, sublocation=%s,
                purpose=%s, category=%s, cash_out=%s, cash_in=%s, status=%s, notes=%s,
                updated_by=%s, updated_at=NOW()
                WHERE id=%s""",
            delete_sql="DELETE FROM petty_cash WHERE id=%s",
            label="Petty Cash",
        )


# =====================================================
# EMPLOYEE ADVANCES
# =====================================================

elif page == "Employee Advances":
    st.title("👤 Employee Advances / Loans")
    tab_add, tab_manage = st.tabs(["➕ Add Advance", "✏️ Edit / Delete Advances"])

    with tab_add:
        with st.form("advances_form"):
            values = advance_fields(prefix="add_adv_")
            if st.form_submit_button("💾 Save Advance", use_container_width=True):
                try:
                    execute(
                        """INSERT INTO employee_advances
                        (advance_date, employee_name, advance_type, location, sublocation,
                         amount_given, amount_returned, status, notes, updated_by)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (*values, current_user()),
                        audit_action="CREATE",
                        audit_table="employee_advances",
                    )
                    st.success("✅ Advance saved successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Save failed: {e}")

    with tab_manage:
        record_crud(
            table="employee_advances",
            title="Employee Advances",
            date_col="advance_date",
            order_col="advance_date",
            form_renderer=lambda record: advance_fields(record, prefix="edit_adv_"),
            update_sql="""UPDATE employee_advances SET
                advance_date=%s, employee_name=%s, advance_type=%s, location=%s, sublocation=%s,
                amount_given=%s, amount_returned=%s, status=%s, notes=%s,
                updated_by=%s, updated_at=NOW()
                WHERE id=%s""",
            delete_sql="DELETE FROM employee_advances WHERE id=%s",
            label="Advance",
        )


# =====================================================
# SETTINGS
# =====================================================

elif page == "Settings":
    st.title("⚙️ Settings / Master Data")
    st.info("Manage Locations, Sub-Locations, and Employees. All changes are logged.")

    tab1, tab2, tab3 = st.tabs(["📍 Locations", "🏢 Sub-Locations", "👥 Employees"])

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

    report_type = st.selectbox(
        "Select Report",
        [
            "Monthly Profitability",
            "Location Profitability",
            "Sub-Location Profitability",
            "Petty Cash Summary",
            "Employee Advances Summary",
            "Custom Query"
        ],
    )

    if report_type == "Monthly Profitability":
        rev = query("""
            SELECT TO_CHAR(invoice_date, 'YYYY-MM') AS month, SUM(amount) AS revenue
            FROM revenue
            GROUP BY month
            ORDER BY month
        """)
        exp = query("""
            SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month, SUM(amount) AS expenses
            FROM expenses
            GROUP BY month
            ORDER BY month
        """)
        report = pd.merge(rev, exp, on="month", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        report["margin_pct"] = (report["net_profit"] / report["revenue"] * 100).where(report["revenue"] > 0, 0)

        st.dataframe(report, use_container_width=True)
        render_export_buttons(report, "monthly_profitability")

        if not report.empty:
            st.bar_chart(report.set_index("month")[["revenue", "expenses", "net_profit"]])

    elif report_type == "Location Profitability":
        rev = query("SELECT COALESCE(location, 'Unspecified') as location, SUM(amount) AS revenue FROM revenue GROUP BY location")
        exp = query("SELECT COALESCE(location, 'Unspecified') as location, SUM(amount) AS expenses FROM expenses GROUP BY location")
        report = pd.merge(rev, exp, on="location", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        st.dataframe(report, use_container_width=True)
        render_export_buttons(report, "location_profitability")

    elif report_type == "Sub-Location Profitability":
        rev = query("SELECT COALESCE(sublocation, 'Unspecified') as sublocation, SUM(amount) AS revenue FROM revenue GROUP BY sublocation")
        exp = query("SELECT COALESCE(sublocation, 'Unspecified') as sublocation, SUM(amount) AS expenses FROM expenses GROUP BY sublocation")
        report = pd.merge(rev, exp, on="sublocation", how="outer").fillna(0)
        report["net_profit"] = report["revenue"] - report["expenses"]
        st.dataframe(report, use_container_width=True)
        render_export_buttons(report, "sublocation_profitability")

    elif report_type == "Petty Cash Summary":
        report = query("""
            SELECT employee, location, sublocation, category,
                SUM(cash_out) AS total_cash_out,
                SUM(cash_in) AS total_cash_in,
                SUM(cash_in)-SUM(cash_out) AS net_balance
            FROM petty_cash
            GROUP BY employee, location, sublocation, category
        """)
        st.dataframe(report, use_container_width=True)
        render_export_buttons(report, "petty_cash_summary")

    elif report_type == "Employee Advances Summary":
        report = query("""
            SELECT employee_name, advance_type, location, sublocation,
                SUM(amount_given) AS total_given,
                SUM(amount_returned) AS total_returned,
                SUM(amount_given)-SUM(amount_returned) AS outstanding_balance
            FROM employee_advances
            GROUP BY employee_name, advance_type, location, sublocation
        """)
        st.dataframe(report, use_container_width=True)
        render_export_buttons(report, "employee_advances_summary")

    elif report_type == "Custom Query":
        st.warning("⚠️ Advanced: Write your own SQL query. Use with caution.")
        custom_sql = st.text_area("SQL Query", height=150, help="Only SELECT statements allowed")
        if st.button("Run Query", use_container_width=True):
            if not custom_sql.strip().upper().startswith("SELECT"):
                st.error("Only SELECT queries are allowed for security.")
            else:
                try:
                    result = query(custom_sql)
                    st.dataframe(result, use_container_width=True)
                    render_export_buttons(result, "custom_query")
                except Exception as e:
                    st.error(f"Query failed: {e}")


# =====================================================
# AUDIT LOG
# =====================================================

elif page == "Audit Log":
    st.title("📋 Audit Log")
    st.info("Track all data modifications across the system.")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        action_filter = st.multiselect("Action", ["CREATE", "UPDATE", "DELETE", "LOGIN_SUCCESS", "LOGIN_FAILED", "LOGOUT"], [])
    with col2:
        table_filter = st.multiselect("Table", list(ALLOWED_TABLES), [])
    with col3:
        user_filter = st.text_input("User")

    # Build query
    audit_query = "SELECT * FROM audit_log WHERE 1=1"
    params = []

    if action_filter:
        placeholders = ",".join(["%s"] * len(action_filter))
        audit_query += f" AND action IN ({placeholders})"
        params.extend(action_filter)
    if table_filter:
        placeholders = ",".join(["%s"] * len(table_filter))
        audit_query += f" AND table_name IN ({placeholders})"
        params.extend(table_filter)
    if user_filter:
        audit_query += " AND user_name ILIKE %s"
        params.append(f"%{user_filter}%")

    audit_query += " ORDER BY created_at DESC LIMIT 500"

    try:
        audit_df = query(audit_query, tuple(params))
        st.caption(f"Showing {len(audit_df)} records (max 500)")
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
        render_export_buttons(audit_df, "audit_log")
    except Exception as e:
        st.error(f"Failed to load audit log: {e}")