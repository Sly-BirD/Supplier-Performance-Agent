"""
Alerting node — handles alert queries and alert evaluation.

Triggered when intent = 'alert'. Can either:
1. Show recent alerts for a supplier
2. Trigger alert evaluation for all suppliers
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from src.agent.state import AgentState


async def handle_alerts(state: AgentState) -> dict:
    """
    Handle alert-related queries.

    If the question is about which suppliers to worry about or risk evaluation,
    delegates to QA synthesis with full scorecard grounding.
    If the user asks to see alerts, returns the active alert feed.
    Only proposes thresholds when the user explicitly asks to configure or change them.
    """
    sys_ctx = state.get("system_context") or {}
    total_suppliers = sys_ctx.get("total_suppliers", 0)
    if total_suppliers == 0:
        return {
            "messages": [AIMessage(content=(
                "There are currently 0 suppliers in your workspace. "
                "Before I can identify at-risk vendors or trigger alerts, please upload a supplier dataset (CSV or Excel) containing order records, delivery timestamps, or quality inspection data.\n\n"
                "Once uploaded, I will automatically evaluate all suppliers against thresholds for delivery delays, defect anomalies, and SLA contract breaches."
            ))],
        }

    messages = state.get("messages", [])
    last_msg = messages[-1].content.lower() if messages and hasattr(messages[-1], "content") else ""

    # If the user is asking which suppliers to worry about, performance, or risk:
    # Delegate to handle_qa to provide a rich, synthesized executive answer!
    risk_query_keywords = ["worry", "risk", "who", "which", "how", "failing", "bad", "worst", "attention", "problem"]
    if any(kw in last_msg for kw in risk_query_keywords):
        from src.agent.nodes.qa import handle_qa
        return await handle_qa(state)

    # Check if the user specifically asked to configure or adjust alert settings
    wants_config = any(w in last_msg for kw in ["config", "threshold", "rule", "change alert", "set alert", "adjust", "propose"] for w in [kw])

    if wants_config:
        from src.config.defaults import DEFAULT_ALERT_CONFIG
        config_payload = DEFAULT_ALERT_CONFIG.model_dump()

        rules_text = []
        for rule in DEFAULT_ALERT_CONFIG.rules:
            rules_text.append(
                f"- **{rule.rule_type.title()}**: {rule.description} "
                f"(threshold: `{rule.threshold_value}`, severity: `{rule.severity.value}`)"
            )

        summary = (
            "Here are the proposed alert thresholds:\n\n"
            + "\n".join(rules_text) + "\n\n"
            "**Delivery channels:** In-app feed + Automated Email\n\n"
            "Would you like to approve these thresholds, or adjust any values?"
        )

        return {
            "messages": [AIMessage(content=summary)],
            "pending_approval": {
                "approval_type": "alert_rules",
                "proposal_id": "",
                "summary": summary,
                "payload": config_payload,
            },
        }

    # Otherwise, display active alerts from the database
    alerts = sys_ctx.get("alerts", [])
    if alerts:
        alert_lines = []
        for a in alerts[:8]:
            sev = a.get("severity", "medium").upper()
            icon = "🔴" if sev == "CRITICAL" else ("🟠" if sev == "HIGH" else "🟡")
            alert_lines.append(f"{icon} **[{sev}] {a.get('title')}**\n   {a.get('description')}")

        reply = (
            f"### 🔔 Active Threshold Alerts ({len(alerts)})\n\n"
            + "\n\n".join(alert_lines) +
            "\n\n*Would you like to drill into any specific supplier, or acknowledge these alerts?*"
        )
        return {"messages": [AIMessage(content=reply)]}

    return {
        "messages": [AIMessage(content=(
            f"✅ **All {total_suppliers} monitored suppliers are currently operating within nominal thresholds.**\n\n"
            "There are zero active alerts fired in your workspace. You can ask \"Which suppliers should I worry about?\" to see overall risk ranking, or \"Configure alert thresholds\" to adjust sensitivity."
        ))],
    }
