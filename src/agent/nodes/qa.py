"""
Q&A node — handles general supplier performance questions.

Uses Tier 2 LLM (Gemini Pro) for complex narrative synthesis,
always grounding answers in computed metrics from the Scoring Engine.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agent.state import AgentState
from src.agent.prompts import SYSTEM_PROMPT
from src.utils.llm import ModelRouter, TaskType


async def handle_qa(state: AgentState) -> dict:
    """
    Answer natural-language questions about supplier performance.

    Grounds answers in computed metrics. Never guesses a score.
    Offers drill-down suggestions.
    """
    messages = state.get("messages", [])

    if not messages:
        return {
            "messages": [AIMessage(content=(
                "Hello! I'm your Supplier Performance Agent. I can help you:\n\n"
                "📊 **View scorecards** — \"How is Acme Corp doing?\"\n"
                "🔔 **Check alerts** — \"Are there any suppliers at risk?\"\n"
                "📁 **Upload data** — Upload a CSV or Excel file\n"
                "⚖️ **Compare suppliers** — \"Compare Acme vs. Beta Corp\"\n"
                "⚙️ **Manage settings** — \"Show my current scoring weights\"\n\n"
                "What would you like to do?"
            ))],
        }

    try:
        router = ModelRouter()
        model = router.get_model(TaskType.QA_SYNTHESIS)

        # Build dynamic context-aware system prompt
        sys_ctx = state.get("system_context") or {}
        total_suppliers = sys_ctx.get("total_suppliers", 0)
        suppliers = sys_ctx.get("suppliers", [])
        total_alerts = sys_ctx.get("total_alerts", 0)
        alerts = sys_ctx.get("alerts", [])

        if total_suppliers == 0:
            state_description = (
                "CURRENT WORKSPACE DATA STATE:\n"
                "- Suppliers in database: 0 (No supplier datasets have been ingested yet)\n"
                "- Alerts active: 0\n"
                "- Ingestion status: WAITING FOR USER DATASET (CSV / Excel)\n\n"
                "BEHAVIOR RULES FOR CURRENT STATE:\n"
                "1. If greeted (e.g. 'Hey', 'Hello', 'Hi'): Greet the user warmly and introduce yourself as Signal, their autonomous Supplier Intelligence & Performance Agent. Inform them that the system is ready, but no supplier data has been uploaded yet. Explain that they can drop a CSV or Excel file right into the interface (or click the Upload button) with order, delivery, or quality metrics. Once ingested, you will compute 5-dimensional scorecards (Quality, Pricing, Delivery, Communication, Reliability) and monitor anomalies.\n"
                "2. If asked about supplier risks, scorecards, or alerts: Be transparent that 0 suppliers are currently in the database, so there are no scorecards or alerts to display yet. Invite them to upload a dataset to begin.\n"
                "3. ZERO-HALLUCINATION POLICY: NEVER invent or hallucinate fake supplier names (like 'Acme Corp') or fake scores as if they exist in the database. Always report the actual 0-supplier state accurately."
            )
        else:
            scores_data = sys_ctx.get("scores", [])
            scores_by_id = {s["supplier_id"]: s for s in scores_data}

            supplier_lines = []
            at_risk_list = []
            healthy_list = []

            for s in suppliers:
                sid = s.get("id")
                sc = scores_by_id.get(sid, {})
                c_score = sc.get("composite_score")
                tier = sc.get("tier", "Unclassified")
                trend = sc.get("trend", "flat")
                dims = sc.get("dimensions", {})
                dim_summary = ", ".join([f"{k.capitalize()}: {v:.1f}" for k, v in dims.items()])

                score_str = f"Score: {c_score:.1f} | Tier: {tier} | Trend: {trend}" if c_score is not None else "Pending calculation"
                if dim_summary:
                    score_str += f" [{dim_summary}]"

                entry = f"• {s.get('name')} ({s.get('category', 'General')}, {s.get('region', 'Global')}): {score_str}"
                supplier_lines.append(entry)

                if (c_score is not None and c_score < 75) or tier in ["Critical", "At-Risk"]:
                    at_risk_list.append(s.get("name"))
                else:
                    healthy_list.append(s.get("name"))

            suppliers_text = "\n".join(supplier_lines)

            alerts_preview = "\n".join([
                f"- [{a.get('severity', 'ALERT').upper()}] {a.get('title')}: {a.get('description', '')}"
                for a in alerts[:10]
            ]) or "No active alerts."

            state_description = (
                f"CURRENT WORKSPACE DATA STATE:\n"
                f"- Total Suppliers Monitored: {total_suppliers}\n"
                f"- High-Risk / Critical Suppliers ({len(at_risk_list)}): {', '.join(at_risk_list) if at_risk_list else 'None'}\n"
                f"- Healthy Suppliers ({len(healthy_list)}): {', '.join(healthy_list) if healthy_list else 'None'}\n"
                f"- Active Alerts Fired: {total_alerts}\n\n"
                f"LIVE SUPPLIER DIRECTORY & METRICS:\n{suppliers_text}\n\n"
                f"ACTIVE THRESHOLD ALERTS:\n{alerts_preview}\n\n"
                f"EXECUTIVE RESPONSE GUIDELINES:\n"
                f"1. When asked 'which suppliers should I worry about' or about risk: Start with a direct executive summary naming the at-risk suppliers ({', '.join(at_risk_list) if at_risk_list else 'none'}). For each at-risk supplier, cite their exact overall score, tier, and specific failing dimension scores (e.g. AeroFlow Hydraulics at 62.3 due to Cost: 58.0 and Reliability: 60.0). Provide concrete recommendations (e.g., vendor audits, PO holds, contract review).\n"
                f"2. Use structured, beautiful formatting with Markdown headers, bold highlights, and clean bulleted lists.\n"
                f"3. Note that alert triggers are actively evaluating on standard thresholds.\n"
                f"4. Ground all answers strictly in the real numbers provided above. Never invent fake names or placeholder figures."
            )

        full_prompt = f"{SYSTEM_PROMPT}\n\n---\n{state_description}"

        conversation = [SystemMessage(content=full_prompt)]

        # Add relevant conversation history (last 10 messages)
        for msg in messages[-10:]:
            conversation.append(msg)

        response = await model.ainvoke(conversation)

        return {
            "messages": [AIMessage(content=response.content)],
        }

    except Exception as e:
        return {
            "messages": [AIMessage(content=(
                f"I encountered an error processing your question: {str(e)}\n\n"
                "Could you rephrase your question? Or try one of these:\n"
                "- \"Show me the scorecard for [supplier name]\"\n"
                "- \"What are the current alerts?\"\n"
                "- \"Upload a file\" (attach a CSV/Excel)"
            ))],
            "error": str(e),
        }
