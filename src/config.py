"""
Configuration management for the SFCC Promotion Management Agent.
Loads settings with priority:
1. User-supplied session values in Streamlit (BYOK)
2. Streamlit Secret Manager (st.secrets)
3. Environment variables and .env file
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _clean_val(val: Any) -> Optional[str]:
    """Strip whitespace and filter out placeholder values."""
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return ""
    lower = val_str.lower()
    if lower == "xxx" or "your_" in lower or lower.endswith("_here"):
        return ""
    return val_str


def _is_placeholder(val: Optional[str]) -> bool:
    if not val:
        return True
    s = val.strip().lower()
    return s == "xxx" or "your_" in s or s.endswith("_here")


def get_streamlit_secret(
    key: str,
    section: Optional[str] = None,
    subkeys: Optional[List[str]] = None,
) -> Optional[str]:
    """Retrieve secret from Streamlit Secret Manager (st.secrets) if present."""
    try:
        import streamlit as st
        # 1. Direct flat key lookup (exact, lower, upper)
        for k in (key, key.lower(), key.upper()):
            try:
                if k in st.secrets:
                    val = _clean_val(st.secrets[k])
                    if val is not None and val != "":
                        return val
            except Exception:
                pass

        # 2. Section lookup (e.g. st.secrets["sfcc"]["short_code"])
        if section:
            for s in (section, section.lower(), section.upper()):
                try:
                    if s in st.secrets:
                        sec_dict = st.secrets[s]
                        candidate_keys = list(subkeys or []) + [key, key.lower(), key.upper()]
                        for sk in candidate_keys:
                            try:
                                if sk in sec_dict:
                                    val = _clean_val(sec_dict[sk])
                                    if val is not None and val != "":
                                        return val
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass
    return None


def is_secret_in_manager(
    key: str,
    section: Optional[str] = None,
    subkeys: Optional[List[str]] = None,
) -> bool:
    """Return True if key is present in Streamlit Secret Manager with a non-placeholder value."""
    return get_streamlit_secret(key, section=section, subkeys=subkeys) is not None


def get_secret_or_env(
    key: str,
    default: Any = "",
    section: Optional[str] = None,
    subkeys: Optional[List[str]] = None,
) -> Any:
    """
    Retrieve setting with priority:
    1. Streamlit Secret Manager (st.secrets)
    2. Environment variables / .env (os.environ)
    3. Default value
    """
    sec_val = get_streamlit_secret(key, section=section, subkeys=subkeys)
    if sec_val is not None and sec_val != "":
        return sec_val

    for k in (key, key.upper(), key.lower()):
        env_val = os.getenv(k)
        if env_val is not None:
            cleaned = _clean_val(env_val)
            if cleaned is not None and cleaned != "":
                return cleaned

    return default


@dataclass
class Settings:
    # Groq LLM Configuration
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # Salesforce Commerce Cloud (SFCC) Configuration
    sfcc_basic_auth: str = ""
    sfcc_short_code: str = ""
    sfcc_org_id: str = ""
    sfcc_site_id: str = ""
    sfcc_tenant_id: Optional[str] = None
    sfcc_scope: Optional[str] = None
    sfcc_token_url: str = "https://account.demandware.com/dwsso/oauth2/access_token"
    sfcc_base_url: Optional[str] = None

    @property
    def tenant_id(self) -> str:
        """Derive tenant ID (e.g. org_001) from org_id (e.g. f_ecom_org_001) if not explicitly set."""
        if self.sfcc_tenant_id:
            return self.sfcc_tenant_id
        org = self.sfcc_org_id or ""
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
        """Check if Groq API key is set and valid."""
        return bool(self.groq_api_key and not _is_placeholder(self.groq_api_key))

    def is_sfcc_configured(self) -> bool:
        """Check if basic auth and tenant settings are configured and not placeholders."""
        return bool(
            self.sfcc_basic_auth
            and not _is_placeholder(self.sfcc_basic_auth)
            and self.sfcc_short_code
            and not _is_placeholder(self.sfcc_short_code)
            and self.sfcc_org_id
            and not _is_placeholder(self.sfcc_org_id)
            and self.sfcc_site_id
            and not _is_placeholder(self.sfcc_site_id)
        )

    def get_missing_sfcc_fields(self) -> List[str]:
        """Return human-readable names of missing SFCC fields."""
        missing = []
        if not self.sfcc_basic_auth or _is_placeholder(self.sfcc_basic_auth):
            missing.append("Basic Auth Token")
        if not self.sfcc_short_code or _is_placeholder(self.sfcc_short_code):
            missing.append("Short Code")
        if not self.sfcc_org_id or _is_placeholder(self.sfcc_org_id):
            missing.append("Organization ID")
        if not self.sfcc_site_id or _is_placeholder(self.sfcc_site_id):
            missing.append("Site ID")
        return missing


def get_default_settings() -> Settings:
    """Load default settings checking Streamlit secrets first, then environment variables."""
    return Settings(
        groq_api_key=get_secret_or_env("GROQ_API_KEY", "", section="groq", subkeys=["api_key", "key"]),
        groq_model=get_secret_or_env("GROQ_MODEL", "openai/gpt-oss-120b", section="groq", subkeys=["model"]),
        sfcc_basic_auth=get_secret_or_env("SFCC_BASIC_AUTH", "", section="sfcc", subkeys=["basic_auth", "auth", "token"]),
        sfcc_short_code=get_secret_or_env("SFCC_SHORT_CODE", "", section="sfcc", subkeys=["short_code"]),
        sfcc_org_id=get_secret_or_env("SFCC_ORG_ID", "", section="sfcc", subkeys=["org_id", "organization_id"]),
        sfcc_site_id=get_secret_or_env("SFCC_SITE_ID", "", section="sfcc", subkeys=["site_id"]),
        sfcc_tenant_id=get_secret_or_env("SFCC_TENANT_ID", None, section="sfcc", subkeys=["tenant_id"]),
        sfcc_scope=get_secret_or_env("SFCC_SCOPE", None, section="sfcc", subkeys=["scope"]),
        sfcc_token_url=get_secret_or_env(
            "SFCC_TOKEN_URL",
            "https://account.demandware.com/dwsso/oauth2/access_token",
            section="sfcc",
            subkeys=["token_url"],
        ),
        sfcc_base_url=get_secret_or_env("SFCC_BASE_URL", None, section="sfcc", subkeys=["base_url"]),
    )


# Singleton settings instance (for CLI/testing)
settings = get_default_settings()


def get_session_settings() -> Settings:
    """
    Return Settings instance for the current session.
    In Streamlit, retrieves user-provided BYOK credentials from st.session_state.
    If a key is not present in session state, falls back to default settings
    (Streamlit Secret Manager -> Environment -> defaults).
    """
    defaults = get_default_settings()
    try:
        import streamlit as st
        if hasattr(st, "session_state"):
            return Settings(
                groq_api_key=st.session_state.get("groq_api_key", defaults.groq_api_key),
                groq_model=st.session_state.get("groq_model", defaults.groq_model),
                sfcc_basic_auth=st.session_state.get("sfcc_basic_auth", defaults.sfcc_basic_auth),
                sfcc_short_code=st.session_state.get("sfcc_short_code", defaults.sfcc_short_code),
                sfcc_org_id=st.session_state.get("sfcc_org_id", defaults.sfcc_org_id),
                sfcc_site_id=st.session_state.get("sfcc_site_id", defaults.sfcc_site_id),
                sfcc_tenant_id=st.session_state.get("sfcc_tenant_id", defaults.sfcc_tenant_id),
                sfcc_scope=st.session_state.get("sfcc_scope", defaults.sfcc_scope),
                sfcc_token_url=st.session_state.get("sfcc_token_url", defaults.sfcc_token_url),
                sfcc_base_url=st.session_state.get("sfcc_base_url", defaults.sfcc_base_url),
            )
    except Exception:
        pass
    return defaults


