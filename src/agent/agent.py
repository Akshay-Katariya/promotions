"""
Agent orchestrator integrating LangChain, Groq LLM, and SFCC Promotion Tools.
"""

from typing import List, Dict, Any, Generator, Tuple, Optional
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from src.config import settings, get_session_settings, Settings
from src.agent.tools import PROMOTION_TOOLS
from src.agent.prompts import SYSTEM_PROMPT


def get_agent_executor(custom_settings: Optional[Settings] = None):
    """Create and return the LangChain agent graph with Groq."""
    cfg = custom_settings or get_session_settings()
    if not cfg.is_groq_configured():
        raise ValueError(
            "GROQ_API_KEY is not configured. Please enter your Groq API key in the sidebar."
        )

    llm = ChatGroq(
        model=cfg.groq_model,
        api_key=cfg.groq_api_key,
        temperature=0.0,
    )

    return create_agent(
        model=llm,
        tools=PROMOTION_TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


def run_agent(messages: List[BaseMessage], custom_settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Run the agent graph synchronously on the message sequence."""
    agent = get_agent_executor(custom_settings)
    result = agent.invoke({"messages": messages})
    return result
