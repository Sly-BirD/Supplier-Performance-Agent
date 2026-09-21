"""
Schema Inference node — handles file upload and schema mapping proposal.

Triggered when intent = 'upload'. Runs the schema engine, produces a
proposal, and sets pending_approval so the graph interrupts for user review.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

from src.agent.state import AgentState
from src.data.adapters.csv_adapter import CSVExcelAdapter
from src.engines.schema_engine import SchemaEngine
from src.utils.llm import ModelRouter, TaskType


async def handle_upload(state: AgentState) -> dict:
    """
    Process a file upload: extract → analyze → propose schema mapping.

    Sets pending_approval with the schema proposal so the graph
    interrupts and waits for user confirmation.
    """
    file_bytes = state.get("uploaded_file_bytes")
    file_path = state.get("uploaded_file_path")

    if not file_bytes and not file_path:
        return {
            "messages": [AIMessage(content=(
                "I don't see an uploaded file. Please upload a CSV or Excel file "
                "and I'll analyze its structure."
            ))],
        }

    try:
        # Step 1: Extract raw data
        adapter = CSVExcelAdapter()
        source = file_bytes if file_bytes else file_path
        analysis = adapter.extract_and_analyze(source)

        # Step 2: Heuristic pre-classification
        schema_engine = SchemaEngine()
        hints = schema_engine.heuristic_pre_classify(analysis)

        # Step 3: LLM-assisted semantic mapping
        try:
            router = ModelRouter()
            model = router.get_model(TaskType.SCHEMA_INFERENCE)

            prompt = schema_engine.build_llm_prompt(analysis, hints)
            response = await model.ainvoke([
                {"role": "user", "content": prompt}
            ])

            proposal = schema_engine.parse_llm_response(
                response.content, analysis
            )
        except Exception:
            # Fallback to heuristic-only if LLM fails
            proposal = schema_engine._fallback_proposal(analysis)

        # Step 4: Format proposal for user review
        formatted = schema_engine.format_proposal_for_user(proposal)

        # Build the mapping payload for storage
        mapping_payload = {
            "mappings": [
                {
                    "column_name": m.column_name,
                    "dimension": m.dimension.value if m.dimension else None,
                    "metric_role": m.metric_role,
                    "confidence": m.confidence,
                }
                for m in proposal.mappings
            ],
            "supplier_id_column": proposal.supplier_id_column,
            "source_signature": analysis.source_signature,
            "row_count": analysis.row_count,
        }

        # Warnings
        warning_text = ""
        if analysis.warnings:
            warning_text = "\n\n**⚠️ Data Warnings:**\n" + "\n".join(
                f"  - {w}" for w in analysis.warnings
            )

        summary = (
            f"I analyzed your file ({analysis.row_count} rows, "
            f"{len(analysis.columns)} columns).\n\n"
            f"{formatted}{warning_text}"
        )

        return {
            "messages": [AIMessage(content=summary)],
            "pending_approval": {
                "approval_type": "schema_mapping",
                "proposal_id": "",  # Set after DB persistence
                "summary": summary,
                "payload": mapping_payload,
            },
        }

    except Exception as e:
        return {
            "messages": [AIMessage(content=(
                f"I encountered an error processing the file: {str(e)}\n\n"
                "Please make sure the file is a valid CSV or Excel file and try again."
            ))],
            "error": str(e),
        }
