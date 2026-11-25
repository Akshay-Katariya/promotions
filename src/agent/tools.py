"""
LangChain tools for the SFCC Promotion Management Agent.
"""

from typing import Any, Dict, Optional
import json
from langchain_core.tools import tool
from src.sfcc.client import SFCCPromotionsClient
from src.agent.action_registry import action_registry

# Lazy client instance
_client: Optional[SFCCPromotionsClient] = None


def get_client() -> SFCCPromotionsClient:
    try:
        import streamlit as st
        if hasattr(st, "session_state") and "sfcc_client" in st.session_state:
            return st.session_state["sfcc_client"]
    except Exception:
        pass
    global _client
    if _client is None:
        _client = SFCCPromotionsClient()
    return _client


def set_client(client: Optional[SFCCPromotionsClient]) -> None:
    global _client
    _client = client


@tool
def list_promotions(limit: int = 15, offset: int = 0) -> str:
    """
    List promotions from Salesforce Commerce Cloud (SFCC).
    Returns a compact summary list of promotions. Use get_promotion for full JSON details of a specific promotion.
    Args:
        limit: Maximum number of promotions to return (default 15).
        offset: Offset for pagination (default 0).
    """
    try:
        client = get_client()
        result = client.list_promotions(limit=limit, offset=offset)
        hits = result.get("hits", result.get("data", []))
        total = result.get("total", len(hits))

        summaries = []
        for h in hits:
            name_val = h.get("name", "")
            if isinstance(name_val, dict):
                disp_name = name_val.get("default") or next(iter(name_val.values()), "")
            else:
                disp_name = str(name_val)

            summaries.append({
                "id": h.get("id"),
                "name": disp_name,
                "class": h.get("promotionClass"),
                "enabled": h.get("enabled", False),
                "archived": h.get("archived", False),
            })

        output = {
            "total_promotions_in_site": total,
            "returned_count": len(summaries),
            "offset": offset,
            "promotions": summaries,
        }
        return json.dumps(output, indent=2)
    except Exception as e:
        return f"Error listing promotions: {str(e)}"


@tool
def get_promotion(promotion_id: str) -> str:
    """
    Get detailed information about a specific promotion by its ID.
    Args:
        promotion_id: The ID of the promotion to retrieve (e.g. 'postman_promo_01').
    """
    try:
        client = get_client()
        result = client.get_promotion(promotion_id=promotion_id)
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error retrieving promotion '{promotion_id}': {str(e)}"


@tool
def create_promotion(
    promotion_id: str,
    name: str,
    promotion_class: str = "product",
    enabled: bool = True,
    currency: Optional[str] = None,
    archived: bool = False,
    extra_payload_json: Optional[str] = None,
) -> str:
    """
    Create a new promotion or replace an existing one in SFCC.
    Args:
        promotion_id: Unique promotion identifier (e.g. 'summer_sale_2026').
        name: Promotion display name (e.g. 'Summer Sale 20% Off').
        promotion_class: One of 'product', 'order', or 'shipping'. Default is 'product'.
        enabled: Whether the promotion is active. Default is True.
        currency: Optional ISO-4217 currency code (e.g. 'USD').
        archived: Whether promotion is archived. Default is False.
        extra_payload_json: Optional JSON string with additional SFCC fields.
    """
    try:
        client = get_client()
        payload: Dict[str, Any] = {
            "name": {"default": name},
            "enabled": enabled,
            "promotionClass": promotion_class,
            "archived": archived,
        }
        if currency:
            payload["currency"] = currency

        if extra_payload_json:
            try:
                extra = json.loads(extra_payload_json)
                if isinstance(extra, dict):
                    payload.update(extra)
            except Exception:
                pass

        result = client.create_or_replace_promotion(promotion_id=promotion_id, payload=payload)
        return (
            f"Successfully created promotion '{promotion_id}'!\n\n"
            f"Response:\n```json\n{json.dumps(result, indent=2)}\n```"
        )
    except Exception as e:
        return f"Error creating promotion '{promotion_id}': {str(e)}"


@tool
def propose_modify_promotion(
    promotion_id: str,
    updates_json: str,
    description: str,
) -> str:
    """
    Propose modifying an existing promotion.
    SAFETY REQUIREMENT: Does NOT execute the modification immediately.
    Registers a pending action and returns an Action ID awaiting user confirmation.
    Args:
        promotion_id: The ID of the promotion to modify.
        updates_json: JSON string representing fields to update (e.g. '{"enabled": false}' or '{"name": {"default": "New Name"}}').
        description: Brief summary explaining what is being modified.
    """
    try:
        updates = json.loads(updates_json)
        action = action_registry.register_action(
            action_type="modify_promotion",
            promotion_id=promotion_id,
            description=description,
            payload=updates,
        )
        return (
            f"MODIFICATION PROPOSAL REGISTERED:\n"
            f"- Action ID: {action.action_id}\n"
            f"- Promotion ID: {promotion_id}\n"
            f"- Description: {description}\n"
            f"- Planned Updates: {json.dumps(updates, indent=2)}\n\n"
            f"Status: Awaiting user confirmation. Please ask the user to confirm via the UI button or by saying 'Confirm {action.action_id}'."
        )
    except Exception as e:
        return f"Error registering modification proposal: {str(e)}"


@tool
def propose_delete_promotion(
    promotion_id: str,
    reason: str,
) -> str:
    """
    Propose deleting an existing promotion from SFCC.
    SAFETY REQUIREMENT: Does NOT delete immediately.
    Registers a pending deletion action and returns an Action ID awaiting user confirmation.
    Args:
        promotion_id: The ID of the promotion to delete.
        reason: The reason or context for deleting this promotion.
    """
    try:
        description = f"Delete promotion '{promotion_id}'. Reason: {reason}"
        action = action_registry.register_action(
            action_type="delete_promotion",
            promotion_id=promotion_id,
            description=description,
            payload={},
        )
        return (
            f"DELETION PROPOSAL REGISTERED:\n"
            f"- Action ID: {action.action_id}\n"
            f"- Promotion ID: {promotion_id}\n"
            f"- Reason: {reason}\n\n"
            f"Status: Awaiting user confirmation. Please ask the user to confirm via the UI button or by saying 'Confirm {action.action_id}'."
        )
    except Exception as e:
        return f"Error registering deletion proposal: {str(e)}"


@tool
def execute_confirmed_action(action_id: str) -> str:
    """
    Execute a previously proposed action that has received user confirmation.
    Args:
        action_id: The Action ID (e.g. 'ACT-A1B2C3') to execute.
    """
    try:
        client = get_client()
        result = action_registry.execute_action(action_id, client)
        if result.get("success"):
            return f"Action {action_id} was successfully executed!\nResult: {json.dumps(result.get('result', {}), indent=2)}"
        return f"Execution of {action_id} failed: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error executing action {action_id}: {str(e)}"


@tool
def cancel_action(action_id: str) -> str:
    """
    Cancel a pending action by its Action ID.
    Args:
        action_id: The Action ID (e.g. 'ACT-A1B2C3') to cancel.
    """
    action = action_registry.cancel_action(action_id)
    if action:
        return f"Action {action_id} has been cancelled."
    return f"Action {action_id} was not found."


PROMOTION_TOOLS = [
    list_promotions,
    get_promotion,
    create_promotion,
    propose_modify_promotion,
    propose_delete_promotion,
    execute_confirmed_action,
    cancel_action,
]
