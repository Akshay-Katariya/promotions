"""
Unit tests for SFCC Auth, SFCC Promotions Client, Action Registry, and Tools.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
from src.sfcc.auth import SFCCAuth
from src.sfcc.client import SFCCPromotionsClient
from src.agent.action_registry import ActionRegistry, PendingAction
from src.agent.tools import (
    propose_modify_promotion,
    propose_delete_promotion,
    create_promotion,
    execute_confirmed_action,
    cancel_action,
)


class TestSFCCAuth(unittest.TestCase):
    def test_basic_auth_formatting(self):
        auth1 = SFCCAuth(basic_auth="dXNlcjpwYXNz")
        self.assertEqual(auth1.basic_auth, "Basic dXNlcjpwYXNz")

        auth2 = SFCCAuth(basic_auth="Basic dXNlcjpwYXNz")
        self.assertEqual(auth2.basic_auth, "Basic dXNlcjpwYXNz")

    @patch("httpx.Client")
    def test_fetch_token_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock_jwt_token_123",
            "expires_in": 3600,
        }
        mock_client.post.return_value = mock_resp

        auth = SFCCAuth(basic_auth="test_token")
        token = auth.get_valid_token()
        self.assertEqual(token, "mock_jwt_token_123")
        self.assertTrue(auth.is_token_valid())


class TestSFCCPromotionsClient(unittest.TestCase):
    def setUp(self):
        self.mock_auth = MagicMock()
        self.mock_auth.get_valid_token.return_value = "mock_jwt_token_123"
        self.client = SFCCPromotionsClient(
            auth=self.mock_auth,
            base_url="https://test.api.commercecloud.salesforce.com/pricing/promotions/v1/organizations/test_org",
            default_site_id="RefArch",
        )

    @patch("httpx.Client")
    def test_list_promotions(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"total": 1, "hits": [{"id": "promo_1"}]}
        mock_client.post.return_value = mock_resp

        res = self.client.list_promotions(limit=10)
        self.assertEqual(res["total"], 1)
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        self.assertEqual(kwargs["params"]["siteId"], "RefArch")
        self.assertEqual(kwargs["json"]["limit"], 10)

    @patch("httpx.Client")
    def test_create_or_replace_promotion(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": "test_promo",
            "name": {"default": "Test Promo"},
            "enabled": True,
            "promotionClass": "product",
        }
        mock_client.put.return_value = mock_resp

        payload = {
            "name": {"default": "Test Promo"},
            "enabled": True,
            "promotionClass": "product",
        }
        res = self.client.create_or_replace_promotion("test_promo", payload)
        self.assertEqual(res["id"], "test_promo")
        mock_client.put.assert_called_once()


class TestActionRegistry(unittest.TestCase):
    def test_registry_lifecycle(self):
        registry = ActionRegistry()
        action = registry.register_action(
            action_type="delete_promotion",
            promotion_id="promo_to_delete",
            description="Testing deletion",
        )
        self.assertTrue(action.action_id.startswith("ACT-"))
        self.assertEqual(action.status, "pending")

        # Verify in pending list
        pending = registry.get_pending_actions()
        self.assertIn(action.action_id, pending)

        # Cancel action
        cancelled = registry.cancel_action(action.action_id)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertNotIn(action.action_id, registry.get_pending_actions())

    def test_execute_action_flow(self):
        registry = ActionRegistry()
        action = registry.register_action(
            action_type="delete_promotion",
            promotion_id="promo_to_delete",
            description="Testing deletion",
        )
        mock_client = MagicMock()
        mock_client.delete_promotion.return_value = {"success": True}

        res = registry.execute_action(action.action_id, mock_client)
        self.assertTrue(res["success"])
        self.assertEqual(action.status, "executed")
        mock_client.delete_promotion.assert_called_once_with("promo_to_delete")


class TestToolsConfirmation(unittest.TestCase):
    def test_propose_modify_creates_pending_action(self):
        res = propose_modify_promotion.invoke({
            "promotion_id": "test_p1",
            "updates_json": json.dumps({"enabled": False}),
            "description": "Disable promotion",
        })
        self.assertIn("MODIFICATION PROPOSAL REGISTERED", res)
        self.assertIn("Awaiting user confirmation", res)

    def test_propose_delete_creates_pending_action(self):
        res = propose_delete_promotion.invoke({
            "promotion_id": "test_p1",
            "reason": "Expired promotion",
        })
        self.assertIn("DELETION PROPOSAL REGISTERED", res)
        self.assertIn("Awaiting user confirmation", res)


if __name__ == "__main__":
    unittest.main()
