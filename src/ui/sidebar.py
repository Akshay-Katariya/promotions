"""
Sidebar component for Streamlit: handles BYOK (Bring Your Own Key) configuration,
session-isolated credentials, and connection testing.
"""

import streamlit as st
from src.config import get_session_settings
from src.sfcc.auth import SFCCAuth
from src.sfcc.client import SFCCPromotionsClient


def render_sidebar():
    """Render the configuration sidebar in BYOK mode."""
    with st.sidebar:
        st.title("⚡ Settings & SFCC")

        # Initialize session state keys for BYOK (defaulting to empty strings)
        if "groq_api_key" not in st.session_state:
            st.session_state["groq_api_key"] = ""
        if "groq_model" not in st.session_state:
            st.session_state["groq_model"] = "openai/gpt-oss-120b"
        if "sfcc_basic_auth" not in st.session_state:
            st.session_state["sfcc_basic_auth"] = ""
        if "sfcc_short_code" not in st.session_state:
            st.session_state["sfcc_short_code"] = ""
        if "sfcc_org_id" not in st.session_state:
            st.session_state["sfcc_org_id"] = ""
        if "sfcc_site_id" not in st.session_state:
            st.session_state["sfcc_site_id"] = ""

        cfg = get_session_settings()

        with st.expander("🔑 Groq LLM Settings", expanded=not cfg.is_groq_configured()):
            st.text_input(
                "Groq API Key",
                type="password",
                key="groq_api_key",
                help="Obtain your free API key from https://console.groq.com/keys",
                placeholder="gsk_...",
            )
            st.text_input(
                "Groq Model",
                key="groq_model",
                help="Default: openai/gpt-oss-120b",
            )

            # Re-read session settings after input update
            cfg = get_session_settings()
            if cfg.is_groq_configured():
                st.success(f"Groq: Ready (`{cfg.groq_model}`)")
            else:
                st.warning("Please provide your Groq API Key.")

        with st.expander("🛍️ SFCC Configuration", expanded=not cfg.is_sfcc_configured()):
            st.text_input(
                "Basic Auth Token",
                type="password",
                key="sfcc_basic_auth",
                help="Account Manager credentials as Basic <base64> or raw base64 string",
                placeholder="Basic ...",
            )
            st.text_input("Short Code", key="sfcc_short_code", placeholder="e.g. your_short_code")
            st.text_input("Organization ID", key="sfcc_org_id", placeholder="e.g. f_ecom_your_org_id")
            st.text_input("Site ID", key="sfcc_site_id", placeholder="e.g. RefArch")

            cfg = get_session_settings()
            if cfg.is_sfcc_configured():
                st.success("SFCC credentials set")
            else:
                st.warning("SFCC credentials incomplete")

        # Keep session client in sync
        if cfg.is_sfcc_configured():
            try:
                auth = SFCCAuth(
                    basic_auth=cfg.sfcc_basic_auth,
                    token_url=cfg.sfcc_token_url,
                    scope=cfg.default_scope,
                )
                st.session_state["sfcc_client"] = SFCCPromotionsClient(auth=auth, config=cfg)
            except Exception:
                pass
        else:
            st.session_state.pop("sfcc_client", None)

        # Test Connection Button
        st.markdown("---")
        if st.button("🔌 Test SFCC Connection", use_container_width=True):
            if not cfg.is_sfcc_configured():
                st.error("Please enter SFCC Basic Auth and Tenant details first.")
            else:
                with st.spinner("Connecting to SFCC DWSSO OAuth & Promotions API..."):
                    try:
                        auth = SFCCAuth(
                            basic_auth=cfg.sfcc_basic_auth,
                            token_url=cfg.sfcc_token_url,
                            scope=cfg.default_scope,
                        )
                        token = auth.get_valid_token(force_refresh=True)
                        client = SFCCPromotionsClient(auth=auth, config=cfg)
                        res = client.list_promotions(limit=1)
                        total = res.get("total", len(res.get("hits", res.get("data", []))))
                        st.success(f"Connection Successful! Found {total} promotions on site '{cfg.sfcc_site_id}'.")
                    except Exception as e:
                        st.error(f"Connection Failed: {str(e)}")

        st.markdown("---")
        st.caption("SFCC AI Promotion Manager v1.0 (BYOK Mode)")
        st.caption("🔐 Keys are kept strictly in your local browser session.")

