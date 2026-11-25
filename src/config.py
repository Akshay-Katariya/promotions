"""
Configuration management for the SFCC Promotion Management Agent.
Loads settings from environment variables and .env file.
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()


@dataclass
class Settings:
    # Groq LLM Configuration
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # Salesforce Commerce Cloud (SFCC) Configuration
    sfcc_basic_auth: str = os.getenv("SFCC_BASIC_AUTH", "")
    sfcc_short_code: str = os.getenv("SFCC_SHORT_CODE", "")
    sfcc_org_id: str = os.getenv("SFCC_ORG_ID", "")
    sfcc_site_id: str = os.getenv("SFCC_SITE_ID", "")
    sfcc_tenant_id: Optional[str] = os.getenv("SFCC_TENANT_ID", None)
    sfcc_scope: Optional[str] = os.getenv("SFCC_SCOPE", None)
    sfcc_token_url: str = os.getenv(
        "SFCC_TOKEN_URL",
        "https://account.demandware.com/dwsso/oauth2/access_token",
    )
    sfcc_base_url: Optional[str] = os.getenv("SFCC_BASE_URL", None)

    @property
    def tenant_id(self) -> str:
        """Derive tenant ID (e.g. org_001) from org_id (e.g. f_ecom_org_001) if not explicitly set."""
        if self.sfcc_tenant_id:
            return self.sfcc_tenant_id
        org = self.sfcc_org_id
        for prefix in ("f_ecom_", "ecom_"):
            if org.startswith(prefix):
                return org[len(prefix):]
        return org

    @property
    def default_scope(self) -> str:
        """Construct the required SCAPI scope including tenant filter."""
        if self.sfcc_scope:
            return self.sfcc_scope
        return f"SALESFORCE_COMMERCE_API:{self.tenant_id} sfcc.promotions.rw"

    @property
    def api_base_url(self) -> str:
        """Construct the SCAPI pricing promotions base URL if not explicitly overridden."""
        if self.sfcc_base_url:
            return self.sfcc_base_url.rstrip("/")
        return f"https://{self.sfcc_short_code}.api.commercecloud.salesforce.com/pricing/promotions/v1/organizations/{self.sfcc_org_id}"

    def is_groq_configured(self) -> bool:
        """Check if Groq API key is set."""
        return bool(self.groq_api_key and self.groq_api_key.strip() and self.groq_api_key != "xxx")

    def is_sfcc_configured(self) -> bool:
        """Check if basic auth and tenant settings are configured."""
        return bool(
            self.sfcc_basic_auth
            and self.sfcc_basic_auth.strip()
            and self.sfcc_basic_auth != "xxx"
            and self.sfcc_short_code
            and self.sfcc_org_id
            and self.sfcc_site_id
        )


# Singleton settings instance (for CLI/testing)
settings = Settings()


def get_session_settings() -> Settings:
    """
    Return Settings instance for the current session.
    In Streamlit, retrieves user-provided BYOK credentials from st.session_state.
    Falls back to environment settings for CLI/testing.
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx is not None:
            import streamlit as st
            if "groq_api_key" in st.session_state:
                return Settings(
                    groq_api_key=st.session_state.get("groq_api_key", ""),
                    groq_model=st.session_state.get("groq_model", "openai/gpt-oss-120b"),
                    sfcc_basic_auth=st.session_state.get("sfcc_basic_auth", ""),
                    sfcc_short_code=st.session_state.get("sfcc_short_code", ""),
                    sfcc_org_id=st.session_state.get("sfcc_org_id", ""),
                    sfcc_site_id=st.session_state.get("sfcc_site_id", ""),
                    sfcc_token_url=st.session_state.get(
                        "sfcc_token_url",
                        "https://account.demandware.com/dwsso/oauth2/access_token",
                    ),
                    sfcc_base_url=st.session_state.get("sfcc_base_url", None),
                )
    except Exception:
        pass
    return settings

