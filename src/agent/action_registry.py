"""
Action Registry for managing pending operations that require user confirmation.
Enforces the safety requirement: all modify and delete actions must be confirmed before execution.
"""

import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import datetime


@dataclass
class PendingAction:
    action_id: str
    action_type: str  # "delete_promotion", "modify_promotion", "create_promotion"
    promotion_id: str
    description: str
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    status: str = "pending"  # "pending", "confirmed", "executed", "cancelled"
    result: Optional[Dict[str, Any]] = None


class ActionRegistry:
    """Stores and executes actions requiring user confirmation."""

    def __init__(self):
        self._actions: Dict[str, PendingAction] = {}

    def register_action(
        self,
        action_type: str,
        promotion_id: str,
        description: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> PendingAction:
        """Register a new action requiring confirmation."""
        # Short friendly ID e.g. ACT-1234
        action_id = f"ACT-{uuid.uuid4().hex[:6].upper()}"
        action = PendingAction(
            action_id=action_id,
            action_type=action_type,
            promotion_id=promotion_id,
            description=description,
            payload=payload or {},
            status="pending",
        )
        self._actions[action_id] = action
        return action

    def get_action(self, action_id: str) -> Optional[PendingAction]:
        return self._actions.get(action_id)

    def get_pending_actions(self) -> Dict[str, PendingAction]:
        return {aid: a for aid, a in self._actions.items() if a.status == "pending"}

    def cancel_action(self, action_id: str) -> Optional[PendingAction]:
        action = self.get_action(action_id)
        if action and action.status == "pending":
            action.status = "cancelled"
            action.result = {"cancelled": True, "message": "Action was cancelled by the user."}
            return action
        return action

    def execute_action(self, action_id: str, client: Any) -> Dict[str, Any]:
        """Execute a confirmed action against the SFCC client."""
        action = self.get_action(action_id)
        if not action:
            return {"error": "Not Found", "message": f"Action {action_id} not found."}

        if action.status not in ("pending", "confirmed"):
            return {
                "error": "Invalid State",
                "message": f"Action {action_id} has already been {action.status}.",
            }

        try:
            if action.action_type == "delete_promotion":
                res = client.delete_promotion(action.promotion_id)
            elif action.action_type == "modify_promotion":
                res = client.modify_promotion(action.promotion_id, action.payload)
            elif action.action_type == "create_promotion":
                res = client.create_or_replace_promotion(action.promotion_id, action.payload)
            else:
                return {"error": "Unsupported Action", "message": action.action_type}

            action.status = "executed"
            action.result = res
            return {"success": True, "action_id": action_id, "result": res}
        except Exception as e:
            action.result = {"error": str(e)}
            return {"success": False, "error": str(e)}


# Global registry instance
action_registry = ActionRegistry()
