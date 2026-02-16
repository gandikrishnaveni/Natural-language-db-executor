import streamlit as st
import sqlite3
import pandas as pd
import os
import io
import time

# Core project imports
from nlp_engine import NLPEngine  
from database.audit_schema import create_audit_table
from services.audit_logger import log_action
from database.db_config import DB_PATH

# Initialize Audit Database on startup
create_audit_table()

# -------------------- OPTIMIZATION: ENGINE CACHING --------------------
@st.cache_resource
def load_engine(db_path):
    """Initializes the engine only once per database to save resources."""
    return NLPEngine(db_path)

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="LegalBrain AI", page_icon="⚖️", layout="wide")

# -------------------- MOCK EMPLOYEE DATABASE --------------------
EMPLOYEES = {
    "E001": {"name": "Aarav Sharma", "role": "Admin"},
    "E002": {"name": "Meera Nair", "role": "Manager"},
    "E003": {"name": "Rahul Verma", "role": "Employee"},
}

# -------------------- SESSION STATE --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = {}
if "db_path" not in st.session_state:
    st.session_state.db_path = "data/college_2.sqlite"
if "last_query" not in st.session_state:
    st.session_state.last_query = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "pending_dml" not in st.session_state:
    st.session_state.pending_dml = None

# -------------------- ENTERPRISE CSS --------------------
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0f172a; color: #e2e8f0; }
    .stButton>button { border-radius: 10px; background-color: #1e293b; color: white; border: 1px solid #334155; }
    .dataset-card { padding: 15px; border-radius: 12px; background-color: #1e293b; border: 1px solid #38bdf8; color: #38bdf8 !important; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .query-box { background-color: #1e293b; padding: 20px; border-radius: 15px; border-left: 5px solid #38bdf8; margin-bottom: 20px; }
    .success-box { background-color: #064e3b; padding: 15px; border-radius: 8px; border-left: 5px solid #10b981; margin-top: 10px; margin-bottom: 10px; }
    .warning-box { background-color: #451a03; padding: 15px; border-radius: 8px; border-left: 5px solid #f59e0b; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# -------------------- SIDEBAR ------------------------
with st.sidebar:
    st.title("⚖️ LegalBrain AI")
    if not st.session_state.logged_in:
        emp_id = st.text_input("Employee ID", placeholder="E001")
        if st.button("Login", use_container_width=True):
            if emp_id in EMPLOYEES:
                st.session_state.logged_in = True
                st.session_state.user = EMPLOYEES[emp_id]
                st.rerun()
            else:
                st.error("Invalid ID")
    else:
        st.write(f"👤 **{st.session_state.user['name']}**")
        st.caption(f"Role: {st.session_state.user['role']}")
        
        st.divider()
        st.subheader("📤 Upload New Database")
        uploaded_file = st.file_uploader("Choose a .sqlite file", type=["sqlite", "db", "sqlite3"])
        
        if uploaded_file is not None:
            if not os.path.exists("data"): os.makedirs("data")
            target_path = os.path.join("data", uploaded_file.name)
            with open(target_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved {uploaded_file.name}")
            st.session_state.db_path = target_path
            st.rerun()

        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# -------------------- MAIN DASHBOARD -----------------
if st.session_state.logged_in:
    
    # --------- DATABASE GALLERY ----------
    st.subheader("📂 Select Available Database")
    data_folder = "data"
    if not os.path.exists(data_folder): os.makedirs(data_folder)
    db_files = [f for f in os.listdir(data_folder) if f.endswith(('.sqlite', '.db', '.sqlite3'))]
    
    if db_files:
        cols = st.columns(4)
        for idx, db_name in enumerate(db_files):
            with cols[idx % 4]:
                current_p = os.path.join(data_folder, db_name)
                btn_label = f"✅ {db_name}" if st.session_state.db_path == current_p else f"📁 {db_name}"
                if st.button(btn_label, use_container_width=True):
                    st.session_state.db_path = current_p
                    st.rerun()
    
    st.markdown(f'<div class="dataset-card">ACTIVE CONTEXT: {os.path.basename(st.session_state.db_path)}</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Query Console", "Audit Logs"] if st.session_state.user["role"] != "Employee" else ["Query Console"])

    with tabs[0]:
        user_input = st.chat_input("Enter your natural language query...")

        if user_input:
            st.session_state.last_result = None
            st.session_state.pending_dml = None
            st.session_state.last_query = user_input
            
            with st.status("⚖️ Intelligence Pipeline Active...", expanded=True) as status:
                step_placeholder = st.empty()
                
                # Function to show ALL steps and highlight the current one
                def update_ui_steps(current_step):
                    all_steps = [
                        "📂 Step 1: Indexing Database Schema",
                        "🛡️ Step 2: Running Ambiguity Guard",
                        "🧠 Step 3: LLM SQL Generation (Qwen 2.5)",
                        "🧼 Step 4: Syntax Sanitization",
                        "🔍 Step 5: Dry-Run Trace Analysis",
                        "⚙️ Step 6: Finalizing Execution & Audit"
                    ]
                    html = ""
                    for i, text in enumerate(all_steps):
                        if i < current_step:
                            html += f"<div style='color: #10b981; font-weight: bold;'>{text} ✅</div>"
                        elif i == current_step:
                            html += f"<div style='color: #38bdf8; font-weight: bold;'>{text} ⚡ (Processing...)</div>"
                        else:
                            html += f"<div style='color: #475569;'>{text}</div>"
                    step_placeholder.markdown(html, unsafe_allow_html=True)

                try:
                    update_ui_steps(0)
                    engine = load_engine(st.session_state.db_path)
                    
                    update_ui_steps(1)
                    clarification = engine.get_clarification(user_input)
                    
                    if "AMBIGUOUS" in clarification:
                        st.session_state.last_result = {"type": "warning", "content": clarification}
                        status.update(label="⚠️ Ambiguity Detected", state="error", expanded=False)
                    else:
                        update_ui_steps(2)
                        generated_sql = engine.generate_sql(user_input)
                        
                        update_ui_steps(3)
                        # Sanitizer logic here
                        
                        update_ui_steps(4)
                        # Dry run logic here
                        
                        dml_keywords = ["UPDATE", "DELETE", "INSERT", "DROP", "ALTER"]
                        if any(k in generated_sql.upper() for k in dml_keywords):
                            st.session_state.pending_dml = generated_sql
                            status.update(label="✅ Authorization Required", state="complete", expanded=False)
                        else:
                            update_ui_steps(5)
                            result = engine.execute_query(generated_sql, user_command=user_input)
                            
                            # Log Audit for SELECT
                            log_action(st.session_state.user["name"], st.session_state.user["role"], "SELECT", os.path.basename(st.session_state.db_path), user_input, generated_sql, "SUCCESS", len(result) if isinstance(result, pd.DataFrame) else 0)
                            
                            st.session_state.last_result = {"type": "data", "sql": generated_sql, "data": result}
                            update_ui_steps(6) # Finalize all steps
                            status.update(label="✅ Pipeline Complete", state="complete", expanded=False)

                except Exception as e:
                    st.error(f"Error: {e}")
                    status.update(label="❌ Pipeline Error", state="error")

        # --- DML AUTHORIZATION GATE ---
        if st.session_state.pending_dml:
            st.markdown('<div class="warning-box">⚠️ <b>Action Required:</b> Data Manipulation Request</div>', unsafe_allow_html=True)
            st.code(st.session_state.pending_dml, language="sql")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Authorize & Commit", use_container_width=True):
                    engine = load_engine(st.session_state.db_path)
                    res = engine.execute_query(st.session_state.pending_dml, user_command=st.session_state.last_query)
                    log_action(st.session_state.user["name"], st.session_state.user["role"], "DML_COMMIT", os.path.basename(st.session_state.db_path), st.session_state.last_query, st.session_state.pending_dml, "SUCCESS", 0)
                    st.session_state.last_result = {"type": "data", "sql": st.session_state.pending_dml, "data": res}
                    st.session_state.pending_dml = None
                    st.rerun()
            with c2:
                if st.button("❌ Reject Request", use_container_width=True):
                    st.session_state.pending_dml = None
                    st.rerun()

        # --- RESULTS DISPLAY ---
        if st.session_state.last_result and not st.session_state.pending_dml:
            res = st.session_state.last_result
            st.markdown(f'<div class="query-box"><b>Inquiry:</b> {st.session_state.last_query}</div>', unsafe_allow_html=True)
            
            if res["type"] == "warning":
                st.warning(res["content"])
            else:
                st.markdown("### 📄 Validated SQL")
                st.code(res["sql"], language="sql")
                
                if isinstance(res["data"], pd.DataFrame):
                    st.markdown(f'<div class="success-box">✅ Found {len(res["data"])} records</div>', unsafe_allow_html=True)
                    st.dataframe(res["data"], use_container_width=True, hide_index=True)
                    csv = res["data"].to_csv(index=False).encode('utf-8')
                    st.download_button(label="📥 Download Results as CSV", data=csv, file_name="export.csv", mime="text/csv")
                else:
                    st.success(res["data"])

    # --- AUDIT TABS ---
    if len(tabs) > 1:
        with tabs[1]:
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    df_logs = pd.read_sql_query("SELECT * FROM audit_log ORDER BY executed_at DESC", conn)
                    st.dataframe(df_logs, use_container_width=True, hide_index=True)
            except:
                st.info("Audit logs are initializing...")
else:
    st.markdown("<h2 style='text-align: center;'>LegalBrain AI</h2>", unsafe_allow_html=True)