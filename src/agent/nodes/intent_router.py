"""
Intent Router node — classifies user messages and resolves context.

Uses Tier 1 LLM (Gemini Flash) for fast, cheap intent classification.
Also resolves ambiguous supplier references ("that supplier" → supplier_id).
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import AgentState
from src.agent.prompts import INTENT_CLASSIFICATION_PROMPT
from src.utils.llm import ModelRouter, TaskType


async def classify_intent(state: AgentState) -> dict:
    """
    Classify the user's intent from their latest message.

    Updates state with:
    - current_intent: the classified intent category
    - supplier_context: resolved supplier_id (if mentioned)
    """
    messages = state.get("messages", [])
    if not messages:
        return {"current_intent": "help"}

    last_message = messages[-1]

    # Check if this is an approval response
    if state.get("pending_approval"):
        content_lower = last_message.content.lower() if hasattr(last_message, "content") else ""
        approval_keywords = {"yes", "approve", "confirm", "ok", "looks good", "correct", "accept"}
        rejection_keywords = {"no", "reject", "change", "edit", "wrong", "incorrect"}

        if any(kw in content_lower for kw in approval_keywords):
            return {"current_intent": "approve"}
        if any(kw in content_lower for kw in rejection_keywords):
            return {"current_intent": "approve"}  # Route to approval gate for rejection too

    # Check for file upload intent
    if state.get("uploaded_file_bytes") or state.get("uploaded_file_path"):
        return {"current_intent": "upload"}

    # Fast-path for common greetings and short salutations
    user_raw = last_message.content if hasattr(last_message, "content") else str(last_message)
    user_clean = user_raw.strip().lower()
    common_greetings = {"hey", "hi", "hello", "hey signal", "hello signal", "good morning", "good evening", "greetings", "yo", "sup"}
    if user_clean in common_greetings:
        return {"current_intent": "qa"}

    # Use LLM for intent classification
    try:
        router = ModelRouter()
        model = router.get_model(TaskType.INTENT_CLASSIFICATION)

        user_text = last_message.content if hasattr(last_message, "content") else str(last_message)
        prompt = INTENT_CLASSIFICATION_PROMPT.format(message=user_text)

        response = await model.ainvoke([HumanMessage(content=prompt)])
        intent = response.content.strip().lower()

        # Validate against known intents
        valid_intents = {
            "upload", "scorecard", "alert", "compare", "qa", "config", "approve", "help"
        }
        if intent not in valid_intents:
            intent = "qa"  # Default to Q&A for unrecognized intents

        return {"current_intent": intent}

    except Exception as e:
        # Fallback: default to Q&A
        return {
            "current_intent": "qa",
            "error": f"Intent classification failed: {str(e)}",
        }


async def route_intent(state: AgentState) -> str:
    """Return the current intent for conditional routing."""
    return state.get("current_intent", "qa")
