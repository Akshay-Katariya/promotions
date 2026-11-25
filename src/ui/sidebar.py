"""
Sidebar component for Streamlit: handles BYOK (Bring Your Own Key) configuration,
automatic loading from Streamlit Secret Manager, session-isolated credentials,
and connection testing.
"""

import streamlit as st
from src.config import (
    get_default_settings,
    get_session_settings,
    is_secret_in_manager,
)
from src.sfcc.auth import SFCCAuth
from src.sfcc.client import SFCCPromotionsClient


def render_sidebar():
    """Render the configuration sidebar with Secret Manager and BYOK support."""
    with st.sidebar:
        st.title("⚡ Settings & SFCC")

        default_cfg = get_default_settings()

        # Initialize session state keys from Streamlit Secret Manager / Environment on first load
        if "_byok_initialized" not in st.session_state:
            st.session_state["groq_api_key"] = default_cfg.groq_api_key
            st.session_state["groq_model"] = default_cfg.groq_model
            st.session_state["sfcc_basic_auth"] = default_cfg.sfcc_basic_auth
            st.session_state["sfcc_short_code"] = default_cfg.sfcc_short_code
            st.session_state["sfcc_org_id"] = default_cfg.sfcc_org_id
            st.session_state["sfcc_site_id"] = default_cfg.sfcc_site_id
            st.session_state["_byok_initialized"] = True

        # Ensure all expected session keys exist
        if "groq_api_key" not in st.session_state:
            st.session_state["groq_api_key"] = default_cfg.groq_api_key
        if "groq_model" not in st.session_state:
            st.session_state["groq_model"] = default_cfg.groq_model
        if "sfcc_basic_auth" not in st.session_state:
            st.session_state["sfcc_basic_auth"] = default_cfg.sfcc_basic_auth
        if "sfcc_short_code" not in st.session_state:
            st.session_state["sfcc_short_code"] = default_cfg.sfcc_short_code
        if "sfcc_org_id" not in st.session_state:
            st.session_state["sfcc_org_id"] = default_cfg.sfcc_org_id
        if "sfcc_site_id" not in st.session_state:
            st.session_state["sfcc_site_id"] = default_cfg.sfcc_site_id

        # Track which credentials originated in Streamlit Secret Manager
        has_groq_secret = is_secret_in_manager("groq_api_key", "groq", ["api_key"])
        has_sfcc_auth_secret = is_secret_in_manager("sfcc_basic_auth", "sfcc", ["basic_auth", "auth"])
        has_sfcc_short_secret = is_secret_in_manager("sfcc_short_code", "sfcc", ["short_code"])
        has_sfcc_org_secret = is_secret_in_manager("sfcc_org_id", "sfcc", ["org_id"])
        has_sfcc_site_secret = is_secret_in_manager("sfcc_site_id", "sfcc", ["site_id"])

        any_secrets = any([
            has_groq_secret,
            has_sfcc_auth_secret,
            has_sfcc_short_secret,
            has_sfcc_org_secret,
            has_sfcc_site_secret,
        ])

        if any_secrets:
            st.info("🔐 Secrets detected in Streamlit Secret Manager. Values are pre-filled; please complete any empty fields.")

        cfg = get_session_settings()

        # Groq Expander (auto-expanded if not configured)
        with st.expander("🔑 Groq LLM Settings", expanded=not cfg.is_groq_configured()):
            groq_help = (
                "Loaded from Streamlit Secret Manager (override anytime)"
                if has_groq_secret
                else "Obtain your free API key from https://console.groq.com/keys"
            )
            st.text_input(
                "Groq API Key",
                type="password",
                key="groq_api_key",
                help=groq_help,
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
                badge = " (from secrets)" if has_groq_secret and st.session_state.get("groq_api_key") == default_cfg.groq_api_key else ""
                st.success(f"Groq: Ready (`{cfg.groq_model}`){badge}")
            else:
                st.warning("Please provide your Groq API Key.")

        # SFCC Configuration Expander (auto-expanded if not configured)
        with st.expander("🛍️ SFCC Configuration", expanded=not cfg.is_sfcc_configured()):
            auth_help = (
                "Loaded from Streamlit Secret Manager (override anytime)"
                if has_sfcc_auth_secret
                else "Account Manager credentials as Basic <base64> or raw base64 string"
            )
            st.text_input(
                "Basic Auth Token",
                type="password",
                key="sfcc_basic_auth",
                help=auth_help,
                placeholder="Basic ...",
            )
            st.text_input(
                "Short Code",
                key="sfcc_short_code",
                help="Loaded from Secret Manager" if has_sfcc_short_secret else None,
                placeholder="e.g. your_short_code",
            )
            st.text_input(
                "Organization ID",
                key="sfcc_org_id",
                help="Loaded from Secret Manager" if has_sfcc_org_secret else None,
                placeholder="e.g. f_ecom_your_org_id",
            )
            st.text_input(
                "Site ID",
                key="sfcc_site_id",
                help="Loaded from Secret Manager" if has_sfcc_site_secret else None,
                placeholder="e.g. RefArch",
            )

            cfg = get_session_settings()
            if cfg.is_sfcc_configured():
                st.success("SFCC credentials set")
            else:
                missing = cfg.get_missing_sfcc_fields()
                if missing:
                    st.warning(f"Please fill in missing SFCC fields: {', '.join(missing)}")
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

        # Connection and Reset Controls
        st.markdown("---")
        if any_secrets:
            if st.button("🔄 Reload Secret Manager Defaults", use_container_width=True, help="Reset fields to values defined in Streamlit Secret Manager"):
                st.session_state["groq_api_key"] = default_cfg.groq_api_key
                st.session_state["groq_model"] = default_cfg.groq_model
                st.session_state["sfcc_basic_auth"] = default_cfg.sfcc_basic_auth
                st.session_state["sfcc_short_code"] = default_cfg.sfcc_short_code
                st.session_state["sfcc_org_id"] = default_cfg.sfcc_org_id
                st.session_state["sfcc_site_id"] = default_cfg.sfcc_site_id
                st.rerun()

        if st.button("🔌 Test SFCC Connection", use_container_width=True):
            if not cfg.is_sfcc_configured():
                missing = cfg.get_missing_sfcc_fields()
                missing_str = f" ({', '.join(missing)})" if missing else ""
                st.error(f"Please fill in all SFCC details first{missing_str}.")
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
        st.caption("SFCC AI Promotion Manager v1.0 (BYOK & Secrets Mode)")
        st.caption("🔐 Credentials are session-isolated and never persisted to disk.")


