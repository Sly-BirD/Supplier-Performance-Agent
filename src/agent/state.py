"""
Agent state definition for the LangGraph state machine.

This TypedDict defines everything the graph tracks across nodes:
conversation messages, current intent, pending approvals, etc.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ApprovalRequest(TypedDict, total=False):
    """A pending item waiting for user approval."""

    approval_type: str  # "schema_mapping" | "scoring_config" | "alert_config"
    proposal_id: str  # DB record ID of the proposed config/mapping
    summary: str  # Plain-language description of what's being proposed
    payload: dict  # The actual proposed values


class AgentState(TypedDict, total=False):
    """
    State tracked across the LangGraph state machine.

    Uses LangGraph's message annotation for automatic message merging.
    """

    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]

    # Routing
    current_intent: str | None  # upload | scorecard | alert | compare | qa | config
    supplier_context: str | None  # Resolved supplier_id (if applicable)

    # Approval workflow
    pending_approval: ApprovalRequest | None
    approved_defaults: bool | None
    approved_config_id: str | None
    approved_config_type: str | None
    approved_payload: dict | None

    # Data context
    data_source_id: str | None  # Current file/source being processed
    uploaded_file_path: str | None  # Path to uploaded file (for processing)
    uploaded_file_bytes: bytes | None  # Raw uploaded file content
    system_context: dict | None  # Live DB snapshot: suppliers, alerts, scores, configs

    # Config snapshot
    active_scoring_config: dict | None
    active_alert_config: dict | None

    # Error handling
    error: str | None
