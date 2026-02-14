import streamlit as st
import sqlite3
import pandas as pd
from services.nlp_engine import generate_sql_from_nl
from database.audit_schema import create_audit_table
from services.audit_logger import log_action
from database.db_config import DB_PATH
create_audit_table()

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="LegalBrain AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Audit Database (Creates audit.db automatically)

# -------------------- MOCK EMPLOYEE DATABASE --------------------
EMPLOYEES = {
    "E001": {"name": "Aarav Sharma", "role": "Admin"},
    "E002": {"name": "Meera Nair", "role": "Manager"},
    "E003": {"name": "Rahul Verma", "role": "Staff"},
}

# -------------------- SESSION STATE --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = {}

if "db_path" not in st.session_state:
    st.session_state.db_path = None

# -------------------- ENTERPRISE DARK CSS --------------------
st.markdown("""
<style>
html, body, [class*="css"]  {
    background-color: #0f172a;
    color: #e2e8f0;
}
.block-container {
    padding-top: 2rem;
}
.stButton>button {
    border-radius: 10px;
    background-color: #1e293b;
    color: white;
    border: 1px solid #334155;
}
.stButton>button:hover {
    background-color: #334155;
}
.dataset-card {
    padding: 15px;
    border-radius: 12px;
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #f1f5f9 !important;
    font-weight: 600;
}
.success-box {
    background-color: #064e3b;
    padding: 10px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# -------------------- SIDEBAR ------------------------
# =====================================================
with st.sidebar:

    st.title("⚖️ LegalBrain AI")

    # ---------------- LOGIN SYSTEM ----------------
    if not st.session_state.logged_in:
        emp_id = st.text_input("Enter Employee ID")

        if st.button("Login"):
            if emp_id in EMPLOYEES:
                st.session_state.logged_in = True
                st.session_state.user = EMPLOYEES[emp_id]
                st.success("Login Successful")
                st.rerun()
            else:
                st.error("Invalid Employee ID")

    else:
        st.markdown("### 👤 User Profile")
        st.write(f"**Name:** {st.session_state.user['name']}")
        st.write(f"**Role:** {st.session_state.user['role']}")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = {}
            st.session_state.db_path = None
            st.rerun()

    st.markdown("---")

    # ---------------- SQLITE UPLOAD ----------------
    if st.session_state.logged_in:
        uploaded_file = st.file_uploader(
            "Upload .sqlite Database",
            type=["sqlite", "db", "sqlite3"]
        )

        if uploaded_file:
            db_path = f"temp_{uploaded_file.name}"
            with open(db_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.session_state.db_path = db_path
            st.success("Database Loaded Successfully")

# =====================================================
# -------------------- MAIN DASHBOARD -----------------
# =====================================================
if st.session_state.logged_in:

    # --------- DATASET GALLERY ----------
    st.subheader("📂 Available Dataset")

    if st.session_state.db_path:
        st.markdown(f"""
        <div class="dataset-card">
        🗄️ {st.session_state.db_path}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No Database Selected")

    st.markdown("---")

    # --------- TABS ----------
    tabs = ["Query Console"]
    if st.session_state.user["role"] in ["Manager", "Admin"]:
        tabs.append("History Logs")

    selected_tab = st.tabs(tabs)

    # =====================================================
    # ---------------- QUERY CONSOLE ----------------------
    # =====================================================
    with selected_tab[0]:

        st.subheader("💬 Natural Language Query")
        user_query = st.chat_input("Write your database instruction...")

        if user_query and st.session_state.db_path:

            generated_sql = generate_sql_from_nl(user_query)
            st.subheader("🧠 Generated SQL")
            st.code(generated_sql, language="sql")

            role = st.session_state.user["role"]

            # ---------- ROLE PERMISSION CHECK ----------
            if "delete" in generated_sql.lower() and role == "Staff":
                st.error("❌ Permission Denied: Staff cannot perform DELETE operations.")

                # LOG PERMISSION DENIED (VERY PROFESSIONAL)
                log_action(
                    user_id=st.session_state.user["name"],
                    user_role=role,
                    action_type="DELETE_BLOCKED",
                    dataset_name=st.session_state.db_path,
                    natural_language_query=user_query,
                    generated_sql=generated_sql,
                    outcome_status="DENIED",
                    affected_rows=0
                )
                st.stop()

            # ---------- SAFETY CONFIRMATION ----------
            dangerous = any(k in generated_sql.lower() for k in ["delete", "update"])
            execute = True

            if dangerous:
                st.warning("⚠️ This operation will modify the database.")
                execute = st.checkbox("Confirm Execution")

            if execute:
                conn = sqlite3.connect(st.session_state.db_path)
                cursor = conn.cursor()

                try:
                    cursor.execute(generated_sql)

                    if generated_sql.lower().startswith("select"):
                        df = pd.read_sql_query(generated_sql, conn)
                        affected_rows = len(df)
                    else:
                        conn.commit()
                        affected_rows = cursor.rowcount
                        df = None

                    # -------- REAL AUDIT LOGGING (CORRECT PLACE) --------
                    action_type = "SELECT"
                    sql_lower = generated_sql.lower()

                    if "update" in sql_lower:
                        action_type = "UPDATE"
                    elif "delete" in sql_lower:
                        action_type = "DELETE"
                    elif "insert" in sql_lower:
                        action_type = "INSERT"

                    log_action(
                        user_id=st.session_state.user["name"],
                        user_role=role,
                        action_type=action_type,
                        dataset_name=st.session_state.db_path,
                        natural_language_query=user_query,
                        generated_sql=generated_sql,
                        outcome_status="SUCCESS",
                        affected_rows=affected_rows
                    )

                    st.markdown(f"""
                    <div class="success-box">
                    ✅ {affected_rows} rows affected in {st.session_state.db_path}
                    </div>
                    """, unsafe_allow_html=True)

                    if df is not None:
                        st.subheader("📊 Affected Dataset")
                        st.dataframe(df, width="stretch")

                except Exception as e:
                    st.error(f"Execution Error: {e}")

                    # -------- FAILURE AUDIT LOGGING --------
                    log_action(
                        user_id=st.session_state.user["name"],
                        user_role=role,
                        action_type="FAILED",
                        dataset_name=st.session_state.db_path,
                        natural_language_query=user_query,
                        generated_sql=generated_sql,
                        outcome_status="FAILED",
                        affected_rows=0
                    )

                finally:
                    conn.close()

    # =====================================================
    # ---------------- HISTORY (ADMIN/MANAGER) ------------
    # =====================================================
    if len(selected_tab) > 1:
        with selected_tab[1]:
            st.subheader("📜 Audit History")

            conn = sqlite3.connect(DB_PATH) 
            query = """
            SELECT 
               user_id AS User,
               user_role AS Role,
               action_type AS Action,
               dataset_name AS Dataset,
               natural_language_query AS Query,
               generated_sql AS SQL,
               affected_rows AS Rows,
               outcome_status AS Status,
               executed_at AS Time
            FROM audit_log
            ORDER BY executed_at DESC
            """
            history_df = pd.read_sql_query(query, conn)
            conn.close()

            if not history_df.empty:
                st.dataframe(history_df, width="stretch")
            else:
                st.info("No logs yet.")

else:
    st.info("Please login to access LegalBrain AI.")