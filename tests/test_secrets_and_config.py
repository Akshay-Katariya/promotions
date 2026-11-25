"""
Unit tests for Streamlit Secret Manager loading and BYOK configuration fallback.
"""

import unittest
from unittest.mock import patch, MagicMock
from src.config import (
    Settings,
    get_streamlit_secret,
    is_secret_in_manager,
    get_secret_or_env,
    get_default_settings,
    get_session_settings,
)


class TestStreamlitSecretsLoading(unittest.TestCase):
    def test_no_secrets_fallback(self):
        """When no secrets are in st.secrets or env, settings use default empty strings."""
        with patch("streamlit.secrets", {}, create=True):
            with patch.dict("os.environ", {}, clear=True):
                s = get_default_settings()
                self.assertEqual(s.groq_api_key, "")
                self.assertEqual(s.sfcc_basic_auth, "")
                self.assertEqual(s.sfcc_short_code, "")
                self.assertFalse(s.is_groq_configured())
                self.assertFalse(s.is_sfcc_configured())
                self.assertEqual(
                    set(s.get_missing_sfcc_fields()),
                    {"Basic Auth Token", "Short Code", "Organization ID", "Site ID"},
                )

    def test_flat_secrets_loading(self):
        """When some flat keys are defined in st.secrets, they are loaded."""
        mock_secrets = {
            "GROQ_API_KEY": "gsk_secret_123",
            "SFCC_SHORT_CODE": "short_code_xyz",
            "SFCC_SITE_ID": "RefArch",
        }
        with patch("streamlit.secrets", mock_secrets, create=True):
            with patch.dict("os.environ", {}, clear=True):
                self.assertTrue(is_secret_in_manager("GROQ_API_KEY", "groq", ["api_key"]))
                self.assertTrue(is_secret_in_manager("SFCC_SHORT_CODE", "sfcc", ["short_code"]))
                self.assertFalse(is_secret_in_manager("SFCC_BASIC_AUTH", "sfcc", ["basic_auth"]))

                s = get_default_settings()
                self.assertEqual(s.groq_api_key, "gsk_secret_123")
                self.assertEqual(s.sfcc_short_code, "short_code_xyz")
                self.assertEqual(s.sfcc_site_id, "RefArch")
                self.assertEqual(s.sfcc_basic_auth, "")
                self.assertEqual(s.sfcc_org_id, "")

                # Groq is ready
                self.assertTrue(s.is_groq_configured())
                # SFCC is incomplete because basic_auth and org_id are missing
                self.assertFalse(s.is_sfcc_configured())
                self.assertEqual(
                    set(s.get_missing_sfcc_fields()),
                    {"Basic Auth Token", "Organization ID"},
                )

    def test_nested_toml_secrets_loading(self):
        """When secrets use nested TOML sections, they are resolved correctly."""
        mock_secrets = {
            "groq": {
                "api_key": "gsk_nested_key",
                "model": "deepseek-r1-distill-llama-70b",
            },
            "sfcc": {
                "basic_auth": "Basic bXlfdG9rZW4=",
                "short_code": "tenant_123",
                "org_id": "f_ecom_tenant_123",
                "site_id": "SiteGenesis",
            },
        }
        with patch("streamlit.secrets", mock_secrets, create=True):
            with patch.dict("os.environ", {}, clear=True):
                s = get_default_settings()
                self.assertEqual(s.groq_api_key, "gsk_nested_key")
                self.assertEqual(s.groq_model, "deepseek-r1-distill-llama-70b")
                self.assertEqual(s.sfcc_basic_auth, "Basic bXlfdG9rZW4=")
                self.assertEqual(s.sfcc_short_code, "tenant_123")
                self.assertEqual(s.sfcc_org_id, "f_ecom_tenant_123")
                self.assertEqual(s.sfcc_site_id, "SiteGenesis")

                self.assertTrue(s.is_groq_configured())
                self.assertTrue(s.is_sfcc_configured())
                self.assertEqual(s.get_missing_sfcc_fields(), [])

    def test_placeholder_filtering(self):
        """Placeholder values like 'your_groq_api_key_here' are treated as empty."""
        mock_secrets = {
            "GROQ_API_KEY": "your_groq_api_key_here",
            "SFCC_BASIC_AUTH": "xxx",
            "SFCC_SHORT_CODE": "real_short_code",
        }
        with patch("streamlit.secrets", mock_secrets, create=True):
            with patch.dict("os.environ", {}, clear=True):
                s = get_default_settings()
                self.assertEqual(s.groq_api_key, "")
                self.assertEqual(s.sfcc_basic_auth, "")
                self.assertEqual(s.sfcc_short_code, "real_short_code")
                self.assertFalse(s.is_groq_configured())
                self.assertIn("Basic Auth Token", s.get_missing_sfcc_fields())

    def test_session_state_overrides_secrets(self):
        """User session state takes precedence over secrets manager for BYOK."""
        mock_secrets = {
            "GROQ_API_KEY": "gsk_from_secrets",
            "SFCC_SHORT_CODE": "short_from_secrets",
        }
        mock_session_state = {
            "groq_api_key": "gsk_user_custom_key",
            "sfcc_short_code": "short_from_secrets",
            "sfcc_basic_auth": "Basic dXNlcjpwYXNz",
            "sfcc_org_id": "f_ecom_org",
            "sfcc_site_id": "RefArch",
        }
        with patch("streamlit.secrets", mock_secrets, create=True):
            with patch("streamlit.session_state", mock_session_state, create=True):
                session_cfg = get_session_settings()
                self.assertEqual(session_cfg.groq_api_key, "gsk_user_custom_key")
                self.assertEqual(session_cfg.sfcc_short_code, "short_from_secrets")
                self.assertEqual(session_cfg.sfcc_basic_auth, "Basic dXNlcjpwYXNz")
                self.assertTrue(session_cfg.is_groq_configured())
                self.assertTrue(session_cfg.is_sfcc_configured())


if __name__ == "__main__":
    unittest.main()
