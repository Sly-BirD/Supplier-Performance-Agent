"""
Approval Gate node — handles user approval/rejection of proposed settings.

This is the mechanism from About.md §7: the agent proposes, the user
approves/edits/rejects, and the agent persists + labels the result.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from src.agent.state import AgentState


async def handle_approval(state: AgentState) -> dict:
    """
    Process user approval or rejection of a pending proposal.

    On approval: persists the config and clears pending_approval.
    On rejection: acknowledges and clears pending_approval so the
    user can re-request with changes.
    """
    pending = state.get("pending_approval")
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    user_text = ""
    if last_message and hasattr(last_message, "content"):
        user_text = last_message.content.lower().strip()

    approval_words = {"yes", "approve", "confirm", "ok", "looks good", "correct", "accept", "sure", "yep", "yeah"}
    rejection_words = {"no", "reject", "change", "edit", "wrong", "incorrect", "modify", "cancel"}

    is_approval = any(word in user_text for word in approval_words)
    is_rejection = any(word in user_text for word in rejection_words)

    # If no explicit pending object, but user said "yes" to an approval question in conversation
    if not pending:
        if is_approval and not is_rejection:
            return {
                "messages": [AIMessage(content=(
                    "✅ **Confirmed! Baseline threshold and scoring configurations are active.**\n\n"
                    "Your suppliers are actively monitored under the standard rules:\n"
                    "- **Delivery**: Late deliveries ≥ 3.0 (High severity)\n"
                    "- **Price**: Price variance > 8.0% (Medium severity)\n"
                    "- **Quality**: Defect rate > 5.0% (High severity)\n"
                    "- **Composite**: Critical score / tier downgrade (Critical severity)\n\n"
                    "Would you like me to show which suppliers currently need attention?"
                ))],
                "approved_defaults": True,
            }

        return {
            "messages": [AIMessage(content=(
                "All current settings and thresholds are active! "
                "You can ask me to evaluate supplier risks, view scorecards, or type \"change alert thresholds\" to modify settings."
            ))],
        }

    approval_type = pending.get("approval_type", "")
    type_labels = {
        "schema_mapping": "schema mapping",
        "scoring_config": "scoring configuration",
        "alert_config": "alert thresholds",
        "alert_rules": "alert thresholds",
    }
    label = type_labels.get(approval_type, approval_type)

    if is_approval and not is_rejection:
        response_text = (
            f"✅ **{label.title()} approved!**\n\n"
            f"Your settings are now active and will be used for all future "
            f"scoring and evaluation. You can view or change them at any time "
            f"by asking \"show my current settings\"."
        )

        updates: dict = {
            "messages": [AIMessage(content=response_text)],
            "pending_approval": None,
            "approved_config_id": pending.get("proposal_id"),
            "approved_config_type": approval_type,
            "approved_payload": pending.get("payload"),
        }

        if approval_type in ("scoring_config", "scoring_weights"):
            updates["active_scoring_config"] = pending.get("payload")
        elif approval_type in ("alert_config", "alert_rules"):
            updates["active_alert_config"] = pending.get("payload")

        return updates

    elif is_rejection:
        return {
            "messages": [AIMessage(content=(
                f"No problem! The proposed {label} has been discarded.\n\n"
                f"You can tell me what you'd like to change, and I'll "
                f"prepare an updated proposal. For example:\n"
                f"- \"Set quality weight to 30%\"\n"
                f"- \"Change the grace window to 3 days\"\n"
                f"- \"Use contract terms for pricing benchmark\""
            ))],
            "pending_approval": None,
        }

    else:
        return {
            "messages": [AIMessage(content=(
                f"I have a pending {label} proposal waiting for your review.\n\n"
                f"Please respond with **approve** to accept, or let me know "
                f"what changes you'd like to make."
            ))],
        }
