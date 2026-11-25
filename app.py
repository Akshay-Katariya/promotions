"""
Streamlit Web Application for SFCC Promotion Management Agent.
"""

import sys
from pathlib import Path

# Ensure repository root is on sys.path so modules under src/ resolve properly
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import List, Dict, Any
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from src.config import settings, get_session_settings
from src.agent.agent import run_agent
from src.agent.action_registry import action_registry
from src.sfcc.client import SFCCPromotionsClient
from src.ui.sidebar import render_sidebar
from src.ui.promotions_view import render_promotions_explorer

# Configure Streamlit page
st.set_page_config(
    page_title="SFCC Promotion AI Agent",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .confirmation-card {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 8px;
        padding: 1.2rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .stButton>button {
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Render Sidebar
render_sidebar()

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I am your **Salesforce Commerce Cloud Promotion AI Agent**.\n\n"
                "I can help you:\n"
                "- 📋 **List and search** promotions in your site\n"
                "- 🔍 **Inspect** details of any promotion\n"
                "- ✨ **Create** new promotions with standard or custom rules\n"
                "- ✏️ **Modify** existing promotions (with safety confirmation)\n"
                "- 🗑️ **Delete** promotions (with safety confirmation)\n\n"
                "How would you like to get started?"
            ),
        }
    ]

# Header
cfg = get_session_settings()
st.markdown('<div class="main-header">🛍️ SFCC Promotion AI Agent</div>', unsafe_allow_html=True)
if cfg.is_sfcc_configured():
    sub_text = f"Managing promotions on <b>{cfg.sfcc_site_id}</b> ({cfg.sfcc_org_id}) via <b>{cfg.groq_model}</b>"
else:
    sub_text = f"Bring Your Own Key (BYOK) — Configure Groq & SFCC in the sidebar (👈) to start."
st.markdown(
    f'<div class="sub-header">{sub_text}</div>',
    unsafe_allow_html=True,
)

# Main Navigation Tabs
tab_chat, tab_explorer = st.tabs(["💬 AI Assistant", "📋 Promotions Explorer"])

with tab_chat:
    # Quick Action Chips & Controls
    c_chip1, c_chip2, c_chip3, c_spacer, c_clear = st.columns([1.3, 1.3, 1.3, 2.5, 1.0])
    with c_chip1:
        if st.button("📋 Active Promos", use_container_width=True, help="Show all active promotions"):
            st.session_state["user_input_prompt"] = "Show all active promotions on the site."
            st.rerun()
    with c_chip2:
        if st.button("🔴 Inactive / Drafts", use_container_width=True, help="List disabled or inactive promotions"):
            st.session_state["user_input_prompt"] = "List all disabled or inactive promotions on the site."
            st.rerun()
    with c_chip3:
        if st.button("📊 Site Audit", use_container_width=True, help="Summary breakdown of promotion classes and status"):
            st.session_state["user_input_prompt"] = "Provide a summary breakdown of promotion classes (product, order, shipping) and status on this site."
            st.rerun()
    with c_clear:
        if st.button("🧹 Clear Chat", use_container_width=True, help="Reset conversation history"):
            st.session_state["messages"] = [
                {"role": "assistant", "content": "Chat history cleared. How can I help you today?"}
            ]
            st.rerun()

    st.markdown("---")

    # Display Conversation Messages (Full Width)
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Check and Render Pending Confirmation Cards
    pending_actions = action_registry.get_pending_actions()
    if pending_actions:
        for action_id, action in list(pending_actions.items()):
            with st.container():
                st.warning(
                    f"⚠️ **CONFIRMATION REQUIRED**: `{action.action_id}` — {action.action_type.replace('_', ' ').upper()}"
                )
                st.markdown(f"**Target Promotion ID**: `{action.promotion_id}`")
                st.markdown(f"**Summary**: {action.description}")
                if action.payload:
                    st.markdown("**Proposed Payload / Updates:**")
                    st.json(action.payload)

                col_conf, col_canc = st.columns([1, 1])
                with col_conf:
                    if st.button(
                        f"✅ Confirm & Execute ({action.action_id})",
                        key=f"btn_confirm_{action_id}",
                        type="primary",
                    ):
                        with st.spinner(f"Executing {action.action_id} on SFCC..."):
                            client = SFCCPromotionsClient()
                            res = action_registry.execute_action(action_id, client)
                            if res.get("success"):
                                st.session_state["messages"].append(
                                    {
                                        "role": "assistant",
                                        "content": (
                                            f"✅ **Action `{action_id}` Executed Successfully!**\n\n"
                                            f"Operation: `{action.action_type}` on promotion `{action.promotion_id}`.\n"
                                            f"```json\n{res.get('result')}\n```"
                                        ),
                                    }
                                )
                                # Invalidate cached promotions so explorer updates
                                st.session_state.pop("cached_promotions", None)
                            else:
                                st.session_state["messages"].append(
                                    {
                                        "role": "assistant",
                                        "content": f"❌ **Action `{action_id}` Failed**: {res.get('error')}",
                                    }
                                )
                            st.rerun()

                with col_canc:
                    if st.button(f"❌ Cancel ({action.action_id})", key=f"btn_cancel_{action_id}"):
                        action_registry.cancel_action(action_id)
                        st.session_state["messages"].append(
                            {
                                "role": "assistant",
                                "content": f"🚫 **Action `{action_id}` was cancelled** by user.",
                            }
                        )
                        st.rerun()

    # Handle User Input (Direct input box or preset chips)
    user_prompt = st.chat_input("Ask to create, modify, list, or delete promotions...")
    if "user_input_prompt" in st.session_state:
        user_prompt = st.session_state.pop("user_input_prompt")

    if user_prompt:
        cfg = get_session_settings()
        if not cfg.is_groq_configured():
            st.error("⚠️ **Groq API Key Required**: Please open the sidebar (👈) and enter your Groq API Key.")
            st.stop()
        if not cfg.is_sfcc_configured():
            st.error("⚠️ **SFCC Configuration Required**: Please open the sidebar (👈) and enter your SFCC Basic Auth and Tenant details.")
            st.stop()

        # Append user message
        st.session_state["messages"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Build LangChain messages history
        lc_messages: List[BaseMessage] = []
        for m in st.session_state["messages"][:-1]:
            if m["role"] == "user":
                lc_messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                lc_messages.append(AIMessage(content=m["content"]))
        lc_messages.append(HumanMessage(content=user_prompt))

        # Run Agent
        with st.chat_message("assistant"):
            with st.spinner("AI Agent thinking and coordinating with SFCC..."):
                try:
                    agent_result = run_agent(lc_messages)
                    messages_out = agent_result.get("messages", [])
                    last_message = messages_out[-1] if messages_out else None
                    response_content = (
                        last_message.content if last_message else "Task completed."
                    )

                    st.markdown(response_content)
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": response_content}
                    )

                    # Invalidate cached promotions if any change may have occurred
                    st.session_state.pop("cached_promotions", None)
                    st.rerun()
                except Exception as e:
                    err_msg = f"❌ **Error running agent**: {str(e)}"
                    st.error(err_msg)
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": err_msg}
                    )

with tab_explorer:
    render_promotions_explorer()
