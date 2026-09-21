"""
Scoring node — generates supplier scorecards.

Triggered when intent = 'scorecard'. Fetches supplier data, runs the
scoring engine, and formats the result.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from src.agent.state import AgentState
from src.utils.formatters import format_scorecard_text


async def handle_scorecard(state: AgentState) -> dict:
    """
    Generate a scorecard for the requested supplier.

    If no suppliers exist, guides user to upload data.
    If no scoring config is approved yet, sets pending_approval
    with proposed defaults so the user can review them first.
    """
    sys_ctx = state.get("system_context") or {}
    total_suppliers = sys_ctx.get("total_suppliers", 0)
    if total_suppliers == 0:
        return {
            "messages": [AIMessage(content=(
                "There are currently 0 suppliers in your workspace. "
                "To generate supplier scorecards and multi-dimensional analysis, please upload a supplier dataset (CSV or Excel).\n\n"
                "Once uploaded, I'll calculate dimensional scorecards across Quality, Delivery, Pricing, Communication, and Reliability."
            ))],
        }

    messages = state.get("messages", [])
    supplier_id = state.get("supplier_context")

    # Check if scoring config exists
    scoring_config = state.get("active_scoring_config")

    if not scoring_config:
        # Need to propose scoring config first
        from src.config.defaults import DEFAULT_SCORING_CONFIG, RATIONALE

        config_payload = DEFAULT_SCORING_CONFIG.model_dump()

        summary = (
            "Before I can generate scorecards, I need you to approve the scoring settings.\n\n"
            "**Proposed Dimension Weights:**\n"
            f"  - Quality: {DEFAULT_SCORING_CONFIG.weights.quality}%\n"
            f"  - Pricing: {DEFAULT_SCORING_CONFIG.weights.pricing}%\n"
            f"  - Delivery: {DEFAULT_SCORING_CONFIG.weights.delivery}%\n"
            f"  - Communication: {DEFAULT_SCORING_CONFIG.weights.communication}%\n"
            f"  - Reliability: {DEFAULT_SCORING_CONFIG.weights.reliability}%\n\n"
            f"💡 *{RATIONALE['weights']}*\n\n"
            f"**On-time definition:** ±{DEFAULT_SCORING_CONFIG.on_time.grace_days} days grace window\n"
            f"💡 *{RATIONALE['on_time_grace']}*\n\n"
            f"**Scoring window:** {DEFAULT_SCORING_CONFIG.current_window_days} days (current), "
            f"{DEFAULT_SCORING_CONFIG.trend_window_days} days (trend)\n"
            f"💡 *{RATIONALE['current_window']}*\n\n"
            f"**Pricing benchmark:** {DEFAULT_SCORING_CONFIG.pricing_benchmark.value}\n"
            f"💡 *{RATIONALE['pricing_benchmark']}*\n\n"
            "Would you like to approve these settings, or would you like to adjust any values?"
        )

        return {
            "messages": [AIMessage(content=summary)],
            "pending_approval": {
                "approval_type": "scoring_config",
                "proposal_id": "",
                "summary": summary,
                "payload": config_payload,
            },
        }

    if not supplier_id:
        return {
            "messages": [AIMessage(content=(
                "Which supplier would you like to see the scorecard for? "
                "You can provide a supplier name or ID."
            ))],
        }

    # Generate scorecard
    # NOTE: In a full implementation, this would call the ScoringEngine
    # with actual DB data. For now, return a placeholder indicating
    # the scoring pipeline is ready.
    return {
        "messages": [AIMessage(content=(
            f"I'll generate the scorecard for supplier `{supplier_id}` "
            f"using your approved settings. "
            "The scoring engine will compute scores across all available dimensions."
        ))],
    }
