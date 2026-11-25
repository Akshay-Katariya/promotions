"""
Salesforce Commerce Cloud (SFCC) SCAPI Pricing Promotions Client.
Supports List, Get, Create/Replace (PUT), Modify (PATCH), and Delete (DELETE).
"""

from typing import Any, Dict, Optional, List
import httpx
from src.config import settings, Settings, get_session_settings
from src.sfcc.auth import SFCCAuth


class SFCCPromotionsClient:
    """REST Client for SFCC SCAPI Promotions API."""

    def __init__(
        self,
        auth: Optional[SFCCAuth] = None,
        base_url: Optional[str] = None,
        default_site_id: Optional[str] = None,
        config: Optional[Settings] = None,
    ):
        from src.config import get_session_settings
        cfg = config or get_session_settings()
        self.auth = auth or SFCCAuth(
            basic_auth=cfg.sfcc_basic_auth,
            token_url=cfg.sfcc_token_url,
            scope=cfg.default_scope,
        )
        self.base_url = (base_url or cfg.api_base_url).rstrip("/")
        self.default_site_id = default_site_id or cfg.sfcc_site_id

    def _get_headers(self) -> Dict[str, str]:
        token = self.auth.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def list_promotions(
        self,
        site_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List/Search promotions for a specific site.
        Endpoint: POST /promotions?siteId={siteId}
        Payload: SearchRequest with matchAllQuery, limit, and offset
        """
        target_site = site_id or self.default_site_id
        url = f"{self.base_url}/promotions"
        params: Dict[str, Any] = {
            "siteId": target_site,
        }

        search_payload: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "query": {
                "matchAllQuery": {}
            },
        }
        if sort:
            search_payload["sort"] = sort

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, headers=self._get_headers(), params=params, json=search_payload)

        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(f"Failed to list promotions ({resp.status_code}): {resp.text}")

    def get_promotion(
        self,
        promotion_id: str,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get details of a specific promotion.
        Endpoint: GET /promotions/{id}?siteId={siteId}
        """
        target_site = site_id or self.default_site_id
        url = f"{self.base_url}/promotions/{promotion_id}"
        params = {"siteId": target_site}

        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=self._get_headers(), params=params)

        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return {"error": "Not Found", "message": f"Promotion '{promotion_id}' does not exist."}
        raise RuntimeError(f"Failed to get promotion '{promotion_id}' ({resp.status_code}): {resp.text}")

    def create_or_replace_promotion(
        self,
        promotion_id: str,
        payload: Dict[str, Any],
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or replace a promotion via PUT.
        Endpoint: PUT /promotions/{id}?siteId={siteId}
        """
        target_site = site_id or self.default_site_id
        url = f"{self.base_url}/promotions/{promotion_id}"
        params = {"siteId": target_site}

        with httpx.Client(timeout=20.0) as client:
            resp = client.put(url, headers=self._get_headers(), params=params, json=payload)

        if resp.status_code in (200, 201):
            return resp.json()
        raise RuntimeError(
            f"Failed to create/replace promotion '{promotion_id}' ({resp.status_code}): {resp.text}"
        )

    def modify_promotion(
        self,
        promotion_id: str,
        payload: Dict[str, Any],
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Modify specific fields of a promotion via PATCH.
        Endpoint: PATCH /promotions/{id}?siteId={siteId}
        """
        target_site = site_id or self.default_site_id
        url = f"{self.base_url}/promotions/{promotion_id}"
        params = {"siteId": target_site}

        with httpx.Client(timeout=20.0) as client:
            resp = client.patch(url, headers=self._get_headers(), params=params, json=payload)

        if resp.status_code in (200, 204):
            return resp.json() if resp.content else {"success": True, "promotion_id": promotion_id}
        raise RuntimeError(
            f"Failed to modify promotion '{promotion_id}' ({resp.status_code}): {resp.text}"
        )

    def delete_promotion(
        self,
        promotion_id: str,
        site_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete a promotion via DELETE.
        Endpoint: DELETE /promotions/{id}?siteId={siteId}
        """
        target_site = site_id or self.default_site_id
        url = f"{self.base_url}/promotions/{promotion_id}"
        params = {"siteId": target_site}

        with httpx.Client(timeout=20.0) as client:
            resp = client.delete(url, headers=self._get_headers(), params=params)

        if resp.status_code in (200, 204):
            return {"success": True, "message": f"Promotion '{promotion_id}' was successfully deleted."}
        raise RuntimeError(
            f"Failed to delete promotion '{promotion_id}' ({resp.status_code}): {resp.text}"
        )
