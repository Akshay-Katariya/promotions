"""
Authentication handler for Salesforce Commerce Cloud (DWSSO OAuth2).
Handles token acquisition and in-memory caching.
"""

import time
import httpx
from typing import Optional, Dict, Any


class SFCCAuth:
    """Handles DWSSO OAuth 2.0 token acquisition and caching."""

    def __init__(
        self,
        basic_auth: str,
        token_url: str = "https://account.demandware.com/dwsso/oauth2/access_token",
        scope: Optional[str] = None,
    ):
        self.basic_auth = basic_auth.strip()
        # Ensure Basic prefix is present
        if not self.basic_auth.startswith("Basic "):
            self.basic_auth = f"Basic {self.basic_auth}"
        self.token_url = token_url
        self.scope = scope
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0

    def is_token_valid(self) -> bool:
        """Check if current cached token is still valid (with a 60-second buffer)."""
        return bool(self._access_token and time.time() < (self._expires_at - 60))

    def fetch_token(self) -> str:
        """Fetch a fresh access token from DWSSO endpoint."""
        headers = {
            "Authorization": self.basic_auth,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}
        if self.scope:
            data["scope"] = self.scope

        with httpx.Client(timeout=15.0) as client:
            response = client.post(self.token_url, headers=headers, data=data)

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to obtain SFCC access token ({response.status_code}): {response.text}"
            )

        payload: Dict[str, Any] = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError(f"No access_token returned in response: {payload}")

        expires_in = payload.get("expires_in", 3600)
        self._access_token = token
        self._expires_at = time.time() + float(expires_in)
        return token

    def get_valid_token(self, force_refresh: bool = False) -> str:
        """Get a valid access token, fetching or refreshing if necessary."""
        if force_refresh or not self.is_token_valid():
            return self.fetch_token()
        return self._access_token or self.fetch_token()
