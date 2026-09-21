"""
Chat route — conversational interface to the agent.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage, AIMessage

from src.api.deps import get_db, get_user_id

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """Single message in conversation history."""
    role: str = Field(default="user", description="user | agent | assistant")
    content: str = Field(description="Message content")


class ChatRequest(BaseModel):
    """Incoming chat message with conversation history."""
    message: str = Field(description="User's message text")
    conversation_id: str | None = Field(default=None, description="Conversation thread ID")
    history: list[ChatMessage] = Field(default_factory=list, description="Recent conversation history")


class ChatResponse(BaseModel):
    """Agent's response."""
    reply: str
    pending_approval: dict | None = None
    conversation_id: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db=Depends(get_db),
    user_id: str = Depends(get_user_id),
):
    """
    Send a message to the agent and get a response.
    All context is scoped to the authenticated user's data.

    If the agent needs approval for a setting, the response will
    include a pending_approval object and persist it to the database.
    """
    from sqlalchemy import select, func
    from src.data.models import Supplier, Alert, ScoreSnapshot
    from src.config.store import ConfigStore
    from src.agent.graph import agent_graph

    # Fetch live database context (scoped to user)
    try:
        sup_res = await db.execute(
            select(Supplier.id, Supplier.name, Supplier.category, Supplier.region)
            .where(Supplier.user_id == user_id)
            .order_by(Supplier.name)
            .limit(50)
        )
        suppliers_rows = sup_res.all()

        total_suppliers = (await db.execute(
            select(func.count(Supplier.id)).where(Supplier.user_id == user_id)
        )).scalar() or 0

        user_supplier_ids = [s.id for s in suppliers_rows]

        # Alerts scoped to user's suppliers
        if user_supplier_ids:
            alert_res = await db.execute(
                select(Alert.id, Alert.supplier_id, Alert.severity, Alert.title, Alert.description)
                .where(Alert.supplier_id.in_(user_supplier_ids))
                .order_by(Alert.fired_at.desc())
                .limit(20)
            )
            alert_rows = alert_res.all()
            total_alerts = (await db.execute(
                select(func.count(Alert.id)).where(Alert.supplier_id.in_(user_supplier_ids))
            )).scalar() or 0
        else:
            alert_rows = []
            total_alerts = 0

        # Scores scoped to user's suppliers — include composite and dimensional breakdowns
        if user_supplier_ids:
            snap_res = await db.execute(
                select(ScoreSnapshot.supplier_id, ScoreSnapshot.score, ScoreSnapshot.tier, ScoreSnapshot.trend, ScoreSnapshot.dimension)
                .where(ScoreSnapshot.supplier_id.in_(user_supplier_ids))
                .order_by(ScoreSnapshot.computed_at.desc())
                .limit(100)
            )
            snap_rows = snap_res.all()

            scores_by_sup: dict[str, dict] = {}
            for sc in snap_rows:
                sid = sc.supplier_id
                if sid not in scores_by_sup:
                    scores_by_sup[sid] = {
                        "supplier_id": sid,
                        "composite_score": None,
                        "tier": "Unclassified",
                        "trend": "stable",
                        "dimensions": {},
                    }
                if sc.dimension is None:
                    if scores_by_sup[sid]["composite_score"] is None:
                        scores_by_sup[sid]["composite_score"] = sc.score
                        scores_by_sup[sid]["tier"] = sc.tier or "Unclassified"
                        scores_by_sup[sid]["trend"] = sc.trend.value if hasattr(sc.trend, "value") else str(sc.trend or "stable")
                else:
                    dim_key = sc.dimension.value if hasattr(sc.dimension, "value") else str(sc.dimension)
                    if dim_key not in scores_by_sup[sid]["dimensions"]:
                        scores_by_sup[sid]["dimensions"][dim_key] = sc.score

            scores_list = list(scores_by_sup.values())
        else:
            scores_list = []

        store = ConfigStore(db, user_id=user_id)
        active_weights = await store.get_active("scoring_weights")
        active_alerts_cfg = await store.get_active("alert_rules")

        pending_alert = await store.get_pending("alert_rules") or await store.get_pending("alert_config")
        pending_scoring = await store.get_pending("scoring_weights") or await store.get_pending("scoring_config")
        pending_rec = pending_alert or pending_scoring

        pending_approval_state = None
        if pending_rec:
            pending_approval_state = {
                "approval_type": pending_rec.config_type,
                "proposal_id": pending_rec.id,
                "payload": pending_rec.payload,
                "version": pending_rec.version,
            }

        system_context = {
            "total_suppliers": total_suppliers,
            "suppliers": [{"id": s.id, "name": s.name, "category": s.category, "region": s.region} for s in suppliers_rows],
            "total_alerts": total_alerts,
            "alerts": [
                {
                    "id": a.id,
                    "supplier_id": a.supplier_id,
                    "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                    "title": a.title,
                    "description": a.description,
                }
                for a in alert_rows
            ],
            "scores": scores_list,
            "has_scoring_config": active_weights is not None,
            "has_alert_config": active_alerts_cfg is not None,
        }
    except Exception as e:
        logger.error(f"Failed to fetch live database context for chat: {e}", exc_info=True)
        system_context = {
            "total_suppliers": 0,
            "suppliers": [],
            "total_alerts": 0,
            "alerts": [],
            "scores": [],
            "has_scoring_config": False,
            "has_alert_config": False,
        }
        active_weights = None
        active_alerts_cfg = None
        pending_approval_state = None

    # Reconstruct multi-turn message history
    message_objs = []
    for h in request.history[-6:]:
        if h.role in ("agent", "assistant"):
            message_objs.append(AIMessage(content=h.content))
        else:
            message_objs.append(HumanMessage(content=h.content))
    message_objs.append(HumanMessage(content=request.message))

    # Build input state with live database grounding and pending approvals
    input_state = {
        "messages": message_objs,
        "system_context": system_context,
        "active_scoring_config": active_weights.payload if active_weights else None,
        "active_alert_config": active_alerts_cfg.payload if active_alerts_cfg else None,
        "pending_approval": pending_approval_state,
    }

    # Run the graph
    try:
        result = await agent_graph.ainvoke(input_state)

        # Handle approval persistence
        if result.get("approved_config_id"):
            try:
                await store.approve(result["approved_config_id"], approved_by="user")
                await db.commit()
            except Exception as app_err:
                logger.warning(f"Error persisting approved config: {app_err}")
        elif result.get("approved_defaults"):
            try:
                from src.config.defaults import DEFAULT_ALERT_CONFIG
                rec = await store.propose("alert_rules", DEFAULT_ALERT_CONFIG.model_dump())
                await store.approve(rec.id, approved_by="user")
                await db.commit()
            except Exception as def_err:
                logger.warning(f"Error saving approved default alerts: {def_err}")

        # If graph created a new pending proposal, persist it to database
        new_pending = result.get("pending_approval")
        if new_pending and isinstance(new_pending, dict) and not new_pending.get("proposal_id"):
            try:
                cfg_type = new_pending.get("approval_type", "alert_rules")
                payload = new_pending.get("payload", {})
                if payload:
                    rec = await store.propose(cfg_type, payload)
                    new_pending["proposal_id"] = rec.id
                    await db.commit()
            except Exception as prop_err:
                logger.warning(f"Error storing proposed config: {prop_err}")

        # Extract the last AI message
        messages = result.get("messages", [])
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        reply = ai_messages[-1].content if ai_messages else "I couldn't process that request."

        return ChatResponse(
            reply=reply,
            pending_approval=new_pending,
            conversation_id=request.conversation_id,
        )

    except Exception as e:
        logger.error(f"Chat execution error: {e}", exc_info=True)
        return ChatResponse(
            reply=f"An error occurred: {str(e)}",
            conversation_id=request.conversation_id,
        )

