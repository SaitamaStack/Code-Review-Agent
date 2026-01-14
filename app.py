"""
Local Code Review & Fix Agent - Streamlit Application

A privacy-first Python web app that reviews, explains, and iteratively
fixes Python code using a self-healing agent loop. Fully offline.

Run with: streamlit run app.py
"""

import streamlit as st

from config import get_config, update_config
from agents.graph import run_agent, run_agent_stream
from models.schemas import AgentState
from ui.components import (
    display_code,
    display_review,
    display_execution_result,
    display_diff,
    display_fixed_code,
    display_status_badge,
    code_input_area,
)
from utils.helpers import format_code, get_timestamp


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Code Review Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Code block styling */
    .stCodeBlock {
        border-radius: 8px;
    }
    
    /* Chat message styling */
    .stChatMessage {
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Success/Error message styling */
    .stSuccess, .stError, .stInfo, .stWarning {
        border-radius: 8px;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        padding-top: 2rem;
    }
    
    /* Header styling */
    h1 {
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = None
    
    if "original_code" not in st.session_state:
        st.session_state.original_code = ""
    
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False
    
    if "history" not in st.session_state:
        st.session_state.history = []


init_session_state()


# =============================================================================
# SIDEBAR - Settings & Configuration
# =============================================================================

with st.sidebar:
    st.title("⚙️ Settings")
    
    config = get_config()
    
    # Model settings
    st.subheader("🤖 LLM Settings")
    
    model_name = st.text_input(
        "Ollama Model",
        value=config.model_name,
        help="The Ollama model to use (e.g., qwen3:8b, codellama:7b)",
    )
    
    ollama_url = st.text_input(
        "Ollama Base URL",
        value=config.ollama_base_url,
        help="URL where Ollama is running",
    )
    
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=config.temperature,
        step=0.1,
        help="Lower = more deterministic, Higher = more creative",
    )
    
    # Execution settings
    st.subheader("🔒 Execution Settings")
    
    max_retries = st.number_input(
        "Max Retry Attempts",
        min_value=1,
        max_value=10,
        value=config.max_retries,
        help="Maximum attempts to fix failing code",
    )
    
    timeout = st.number_input(
        "Execution Timeout (s)",
        min_value=1,
        max_value=60,
        value=config.execution_timeout,
        help="Maximum seconds to wait for code execution",
    )
    
    # Apply settings
    if st.button("Apply Settings", type="primary"):
        update_config(
            model_name=model_name,
            ollama_base_url=ollama_url,
            temperature=temperature,
            max_retries=max_retries,
            execution_timeout=timeout,
        )
        st.success("Settings updated!")
    
    st.divider()
    
    # Session actions
    st.subheader("📁 Session")
    
    if st.button("Clear History", type="secondary"):
        st.session_state.messages = []
        st.session_state.agent_state = None
        st.session_state.original_code = ""
        st.session_state.history = []
        st.rerun()
    
    st.divider()
    
    # Info section
    st.subheader("ℹ️ About")
    st.markdown("""
    **Local Code Review Agent**
    
    A privacy-first tool that:
    - 🔍 Reviews your Python code
    - 🔧 Suggests and applies fixes
    - 🚀 Tests execution in a sandbox
    - 🔄 Retries until it works
    
    All processing happens locally with Ollama.
    No data leaves your machine.
    """)


# =============================================================================
# MAIN CONTENT AREA
# =============================================================================

st.title("🔍 Local Code Review & Fix Agent")
st.markdown("*Privacy-first Python code review, powered by local LLMs*")

# Display chat history
for message in st.session_state.messages:
    role = message.get("role", "assistant")
    content = message.get("content", "")
    
    with st.chat_message(role, avatar="👤" if role == "user" else "🤖"):
        st.markdown(content)

# Main interaction area
st.divider()

# Tabs for different input methods
tab1, tab2 = st.tabs(["📝 Code Input", "📂 File Upload"])

with tab1:
    # Code input text area
    user_code = st.text_area(
        "Enter your Python code",
        height=300,
        placeholder="""# Enter your Python code here
# Example:
def greet(name):
    print(f"Hello, {name}!")

greet("World")
""",
        key="code_input_main",
    )

with tab2:
    # File upload
    uploaded_file = st.file_uploader(
        "Upload a Python file",
        type=["py"],
        help="Upload a .py file to review",
    )
    
    if uploaded_file is not None:
        user_code = uploaded_file.read().decode("utf-8")
        st.code(user_code, language="python")

# Action buttons
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    review_button = st.button(
        "🔍 Review & Fix",
        type="primary",
        disabled=st.session_state.is_processing,
        use_container_width=True,
    )

with col2:
    execute_only = st.button(
        "🚀 Execute Only",
        type="secondary",
        disabled=st.session_state.is_processing,
        use_container_width=True,
    )


# =============================================================================
# AGENT EXECUTION
# =============================================================================

def run_review_agent(code: str):
    """Run the code review agent and update the UI."""
    st.session_state.is_processing = True
    st.session_state.original_code = code
    
    # Add user message to chat
    st.session_state.messages.append({
        "role": "user",
        "content": f"Please review and fix this code:\n```python\n{code[:500]}{'...' if len(code) > 500 else ''}\n```",
    })
    
    try:
        # Run the agent
        with st.spinner("🔄 Agent is working..."):
            final_state = run_agent(code)
        
        st.session_state.agent_state = final_state
        
        # Add to history
        st.session_state.history.append({
            "timestamp": get_timestamp(),
            "original_code": code,
            "final_state": final_state,
        })
        
        # Build response message
        status = final_state.get("status", "unknown")
        
        if status == "success":
            response = "✅ **Code review and fix complete!**\n\n"
        else:
            response = "⚠️ **Review complete, but some issues remain.**\n\n"
        
        # Add review summary
        review = final_state.get("review")
        if review:
            response += f"**Review Summary:** {review.summary}\n\n"
            if review.issues:
                response += "**Issues Found:**\n"
                for issue in review.issues[:5]:
                    response += f"- {issue}\n"
                response += "\n"
        
        # Add execution result
        exec_result = final_state.get("execution_result")
        if exec_result:
            if exec_result.success:
                response += f"**Execution:** ✅ Success\n"
                if exec_result.output:
                    response += f"**Output:** `{exec_result.output[:200]}`\n"
            else:
                response += f"**Execution:** ❌ Failed\n"
                response += f"**Error:** `{exec_result.error[:200] if exec_result.error else 'Unknown'}`\n"
        
        st.session_state.messages.append({
            "role": "assistant", 
            "content": response,
        })
        
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"❌ An error occurred: {str(e)}\n\nMake sure Ollama is running and the model is available.",
        })
    
    finally:
        st.session_state.is_processing = False


def execute_code_only(code: str):
    """Execute code without review."""
    from tools.executor import execute_code_safely
    
    st.session_state.messages.append({
        "role": "user",
        "content": f"Execute this code:\n```python\n{code[:300]}...\n```",
    })
    
    result = execute_code_safely(code)
    
    if result.success:
        response = f"✅ **Code executed successfully!**\n\n**Output:**\n```\n{result.output or '(no output)'}\n```"
    else:
        response = f"❌ **Execution failed!**\n\n**Error:**\n```\n{result.error}\n```"
    
    response += f"\n\n⏱️ Execution time: {result.execution_time:.3f}s"
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
    })


# Handle button clicks
if review_button and user_code.strip():
    run_review_agent(format_code(user_code))
    st.rerun()

if execute_only and user_code.strip():
    execute_code_only(format_code(user_code))
    st.rerun()


# =============================================================================
# RESULTS DISPLAY
# =============================================================================

if st.session_state.agent_state:
    st.divider()
    st.subheader("📊 Detailed Results")
    
    state = st.session_state.agent_state
    
    # Results in tabs
    results_tabs = st.tabs([
        "📋 Review",
        "🔧 Fixed Code", 
        "🚀 Execution",
        "🔄 Diff View",
    ])
    
    with results_tabs[0]:
        display_review(state.get("review"))
    
    with results_tabs[1]:
        display_fixed_code(state.get("fixed_code"))
        
        # Show current code
        if state.get("current_code"):
            st.subheader("Current Code")
            st.code(state["current_code"], language="python")
    
    with results_tabs[2]:
        display_execution_result(state.get("execution_result"))
        
        # Show attempt info
        attempt = state.get("attempt", 0)
        config = get_config()
        if attempt > 0:
            st.info(f"🔄 Completed after {attempt} attempt(s) (max: {config.max_retries})")
        
        # Show error history
        error_history = state.get("error_history", [])
        if error_history:
            with st.expander("📜 Error History"):
                for i, error in enumerate(error_history, 1):
                    st.markdown(f"**Attempt {i}:** `{error[:200]}`")
    
    with results_tabs[3]:
        original = st.session_state.original_code
        current = state.get("current_code", "")
        display_diff(original, current)


# =============================================================================
# FOLLOW-UP INPUT (Multi-turn conversation)
# =============================================================================

if st.session_state.agent_state:
    st.divider()
    
    # Follow-up chat input
    follow_up = st.chat_input(
        "Ask for refinements (e.g., 'Make it more efficient', 'Add error handling')",
        disabled=st.session_state.is_processing,
    )
    
    if follow_up:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": follow_up,
        })
        
        # For now, just acknowledge (full implementation would use refinement prompt)
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"I understand you want to: *{follow_up}*\n\nTo apply this refinement, please modify the code in the input area and click 'Review & Fix' again. Multi-turn refinement will be fully implemented in a future update.",
        })
        
        st.rerun()


# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption(
    "🔒 All processing happens locally. Your code never leaves your machine. "
    "Powered by Ollama and LangGraph."
)
