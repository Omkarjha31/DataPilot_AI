import os
import sys
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# 1. Load environment variables (.env locally, st.secrets on Streamlit Cloud)
load_dotenv()

# Synchronize st.secrets into os.environ if running on Streamlit Cloud
try:
    if hasattr(st, "secrets"):
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "host", "port", "user", "password", "database"]:
            if key in st.secrets and key not in os.environ:
                os.environ[key] = str(st.secrets[key])
except Exception:
    pass

# Ensure default port exists
if "port" not in os.environ:
    os.environ["port"] = "5432"

from langchain_core.messages import HumanMessage
from agents.data_agent import data_agent
from agents.sql_analyst import sql_analyst
from agents.etl_analyst import etl_analyst
from utils.database import DatabaseUtil

# Page configuration
st.set_page_config(
    page_title="DataPilot AI - Intelligent Data Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #2563eb, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-title {
        color: #64748b;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .badge-sql {
        display: inline-block;
        background-color: #dbeafe;
        color: #1e40af;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .badge-etl {
        display: inline-block;
        background-color: #fef3c7;
        color: #92400e;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .badge-safe {
        display: inline-block;
        background-color: #dcfce7;
        color: #166534;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-unsafe {
        display: inline-block;
        background-color: #fee2e2;
        color: #991b1b;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("DataPilot AI")
    st.caption("Multi-Agent Architecture powered by LangGraph")
    
    st.markdown("---")
    st.subheader("⚙️ System Status")
    
    # Check API keys
    openai_ok = bool(os.environ.get("OPENAI_API_KEY"))
    anthropic_ok = bool(os.environ.get("ANTHROPIC_API_KEY"))
    
    col1, col2 = st.columns(2)
    with col1:
        if openai_ok:
            st.success("OpenAI: Connected", icon="✅")
        else:
            st.error("OpenAI: Missing", icon="❌")
    with col2:
        if anthropic_ok:
            st.success("Anthropic: Connected", icon="✅")
        else:
            st.error("Anthropic: Missing", icon="❌")
            
    # Check Database Connection
    db_conn = None
    try:
        conn_details = {
            "host": os.environ.get("host", "localhost"),
            "port": int(os.environ.get("port", 5432)),
            "user": os.environ.get("user", "postgres"),
            "password": os.environ.get("password", "postgres"),
            "dbname": os.environ.get("database", "postgres")
        }
        test_db = DatabaseUtil(conn_details)
        if test_db.connection:
            st.success("PostgreSQL: Connected", icon="🐘")
            test_db.connection.close()
        else:
            st.warning("PostgreSQL: Disconnected", icon="⚠️")
    except Exception:
        st.warning("PostgreSQL: Disconnected", icon="⚠️")

    st.markdown("---")
    st.subheader("🎯 Execution Mode")
    mode = st.radio(
        "Select Agent Route:",
        ["🤖 Auto-Detect (Router)", "🗄️ SQL Analyst Agent", "🔄 ETL Analyst Agent"],
        index=0,
        help="Auto-Detect routes your query dynamically to SQL or ETL based on intent."
    )

    st.markdown("---")
    st.subheader("💡 Example Queries")
    
    example_queries = [
        ("🗄️ Distinct Payment Methods", "What are the different types of Payment Methods we have in our database?"),
        ("🗄️ Top 5 Rated Drivers", "Show me the top 5 drivers with the highest average ratings."),
        ("🔄 Extract Pokemon API", "Extract data from 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in csv format"),
        ("🔄 Transform Extracted CSV", "Transform the data in data/extract/extracted_data.csv by filtering for bulbasaur only and save to data/transform in csv format")
    ]
    
    for label, query_text in example_queries:
        if st.button(label, use_container_width=True):
            st.session_state["pending_input"] = query_text

    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# ----------------- MAIN CONTENT -----------------
st.markdown('<div class="main-title">DataPilot AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Intelligent Multi-Agent System for Database Analytics & Automated ETL Pipelines</div>', unsafe_allow_html=True)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display previous conversation
for msg in st.session_state["messages"]:
    role = msg["role"]
    with st.chat_message(role):
        st.write(msg["content"])
        
        # Display agent execution details if present
        details = msg.get("details")
        if details:
            route = details.get("route")
            if route == "sql":
                st.markdown(f'<span class="badge-sql">SQL Analyst</span>', unsafe_allow_html=True)
                if details.get("is_safe") == "Yes":
                    st.markdown('<span class="badge-safe">Safety Judge: Safe ✓</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge-unsafe">Safety Judge: Unsafe ✕</span>', unsafe_allow_html=True)
                
                with st.expander("🔍 View SQL Query & Database Details"):
                    st.markdown("**Curated Question:**")
                    st.info(details.get("curated_ques", "N/A"))
                    
                    st.markdown("**Generated SQL:**")
                    st.code(details.get("generated_sql", "-- No query generated"), language="sql")
                    
                    st.markdown("**Safety Comments:**")
                    st.write(details.get("comments", "N/A"))
                    
                    st.markdown("**Raw Database Output:**")
                    st.code(details.get("raw_result", "No output returned"), language="text")
                    
            elif route == "etl":
                st.markdown(f'<span class="badge-etl">ETL Analyst</span>', unsafe_allow_html=True)
                with st.expander("🔍 View ETL Pipeline Logs"):
                    st.markdown("**Tool Execution History:**")
                    for tool_step in details.get("tools_used", []):
                        st.info(tool_step)

# User input handling
user_input = st.chat_input("Enter your analytical question or ETL request...")

# Check if a pending example query was clicked
if st.session_state.get("pending_input"):
    user_input = st.session_state.pop("pending_input")

if user_input:
    # Append user message
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Process query
    with st.chat_message("assistant"):
        with st.spinner("Processing request with Multi-Agent graph..."):
            try:
                final_answer = ""
                details = {}

                # 1. SQL Analyst Direct Mode
                if mode == "🗄️ SQL Analyst Agent":
                    input_schema = {
                        "messages": [],
                        "user_question": user_input,
                        "curated_ques": "",
                        "prompt_query_context": "",
                        "generated_sql_query": "",
                        "is_safe": "No",
                        "comments": "",
                        "sql_query_execution_result": "",
                        "final_answer": ""
                    }
                    res = sql_analyst.invoke(input_schema)
                    final_answer = res.get("final_answer", "")
                    details = {
                        "route": "sql",
                        "curated_ques": res.get("curated_ques", ""),
                        "generated_sql": res.get("generated_sql_query", ""),
                        "is_safe": res.get("is_safe", "No"),
                        "comments": res.get("comments", ""),
                        "raw_result": res.get("sql_query_execution_result", "")
                    }

                # 2. ETL Analyst Direct Mode
                elif mode == "🔄 ETL Analyst Agent":
                    res = etl_analyst.invoke(
                        {"messages": [HumanMessage(content=user_input)]}
                    )
                    messages_list = res.get("messages", [])
                    final_answer = messages_list[-1].content if messages_list else "ETL Task finished."
                    
                    tool_logs = []
                    for m in messages_list:
                        if hasattr(m, "tool_call_id") or m.__class__.__name__ == "ToolMessage":
                            tool_logs.append(m.content)

                    details = {
                        "route": "etl",
                        "tools_used": tool_logs
                    }

                # 3. Auto-Detect Router Mode (Default)
                else:
                    res = data_agent.invoke(
                        {"messages": [HumanMessage(content=user_input)], "route_response": ""}
                    )
                    route = res.get("route_response", "unknown")
                    last_msg = res.get("messages", [])[-1]

                    if isinstance(last_msg, dict) and "final_answer" in last_msg:
                        # Routed to SQL
                        final_answer = last_msg.get("final_answer", "")
                        details = {
                            "route": "sql",
                            "curated_ques": last_msg.get("curated_ques", ""),
                            "generated_sql": last_msg.get("generated_sql_query", ""),
                            "is_safe": last_msg.get("is_safe", "No"),
                            "comments": last_msg.get("comments", ""),
                            "raw_result": last_msg.get("sql_query_execution_result", "")
                        }
                    elif isinstance(last_msg, dict) and "messages" in last_msg:
                        # Routed to ETL
                        etl_msgs = last_msg.get("messages", [])
                        final_answer = etl_msgs[-1].content if etl_msgs else "ETL task completed."
                        tool_logs = [m.content for m in etl_msgs if hasattr(m, "tool_call_id") or m.__class__.__name__ == "ToolMessage"]
                        details = {
                            "route": "etl",
                            "tools_used": tool_logs
                        }
                    else:
                        final_answer = str(last_msg)
                        details = {"route": route}

                # Display the Assistant's Response
                st.write(final_answer)

                # Display execution breakdown
                if details.get("route") == "sql":
                    st.markdown(f'<span class="badge-sql">SQL Analyst</span>', unsafe_allow_html=True)
                    if details.get("is_safe") == "Yes":
                        st.markdown('<span class="badge-safe">Safety Judge: Safe ✓</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-unsafe">Safety Judge: Unsafe ✕</span>', unsafe_allow_html=True)
                    
                    with st.expander("🔍 View SQL Query & Database Details"):
                        st.markdown("**Curated Question:**")
                        st.info(details.get("curated_ques", "N/A"))
                        st.markdown("**Generated SQL:**")
                        st.code(details.get("generated_sql", "-- No query generated"), language="sql")
                        st.markdown("**Safety Comments:**")
                        st.write(details.get("comments", "N/A"))
                        st.markdown("**Raw Database Output:**")
                        st.code(details.get("raw_result", "No output returned"), language="text")

                elif details.get("route") == "etl":
                    st.markdown(f'<span class="badge-etl">ETL Analyst</span>', unsafe_allow_html=True)
                    with st.expander("🔍 View ETL Pipeline Logs"):
                        st.markdown("**Tool Execution History:**")
                        for tool_step in details.get("tools_used", []):
                            st.info(tool_step)

                # Save assistant response to session state
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": final_answer,
                    "details": details
                })

            except Exception as e:
                err_msg = f"❌ An error occurred during execution: {str(e)}"
                st.error(err_msg)
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": err_msg,
                    "details": None
                })
