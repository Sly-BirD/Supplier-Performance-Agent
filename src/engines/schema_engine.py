"""
Schema Inference Engine.

Two-stage process:
1. Structural Analysis (deterministic) — run by the DataAdapter
2. Semantic Mapping (LLM-assisted) — maps columns to the 5 dimensions

The LLM only suggests; nothing is applied until the user approves.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from src.data.adapters.base import ColumnInfo, SourceAnalysis
from src.data.models import Dimension


@dataclass
class ColumnMapping:
    """Proposed mapping for a single column."""

    column_name: str
    dimension: Dimension | None  # None = unmapped / identifier / irrelevant
    metric_role: str | None  # e.g., "defect_count", "received_count", "delivery_date"
    confidence: float  # 0.0 – 1.0
    reasoning: str  # Plain-language explanation for the user


@dataclass
class SchemaMappingProposal:
    """Complete proposed schema mapping for a data source."""

    mappings: list[ColumnMapping]
    supplier_id_column: str | None  # Which column identifies the supplier
    unmapped_columns: list[str] = field(default_factory=list)
    missing_dimensions: list[str] = field(default_factory=list)
    summary: str = ""  # Plain-language summary for the user


class SchemaEngine:
    """
    Combines structural analysis with LLM-assisted semantic mapping.

    The engine does NOT make any database changes — it only produces a
    SchemaMappingProposal that must be approved before use.
    """

    # Known patterns for heuristic pre-classification (before LLM)
    DELIVERY_DATE_HINTS = {
        "ship_date", "shipped_date", "delivery_date", "actual_date",
        "received_date", "arrival_date", "ship_dt", "actual_delivery",
    }
    PROMISED_DATE_HINTS = {
        "due_date", "due_by", "promised_date", "expected_date",
        "po_date", "order_date", "target_date", "due_dt",
    }
    QUALITY_HINTS = {
        "defect", "reject", "defective", "rejected", "inspection",
        "pass_rate", "fail_rate", "quality", "defect_rate", "reject_qty",
        "defective_qty", "received_qty", "recv_qty",
    }
    PRICING_HINTS = {
        "price", "cost", "unit_price", "total_price", "amount",
        "unit_cost", "invoice", "contract_price", "benchmark_price",
    }
    SUPPLIER_ID_HINTS = {
        "supplier", "vendor", "sup_id", "supplier_id", "vendor_id",
        "supplier_name", "vendor_name", "sup_name",
    }
    COMMUNICATION_HINTS = {
        "response_time", "reply_time", "resolution_time", "ticket",
        "issue", "complaint", "escalation", "sla",
    }

    def heuristic_pre_classify(
        self, analysis: SourceAnalysis
    ) -> dict[str, dict]:
        """
        Rule-based pre-classification before calling the LLM.

        Returns a dict of column_name → {hint_dimension, hint_role}
        for columns that match known patterns. The LLM uses these
        as input alongside the raw structural data.
        """
        hints: dict[str, dict] = {}

        for col in analysis.columns:
            name_lower = col.name.lower()
            tokens = set(name_lower.replace("_", " ").split())

            # Supplier identifier
            if tokens & self.SUPPLIER_ID_HINTS or "supplier" in name_lower or "vendor" in name_lower:
                hints[col.name] = {
                    "hint": "supplier_identifier",
                    "role": "supplier_id",
                }
                continue

            # Delivery dates
            if (tokens & self.DELIVERY_DATE_HINTS or any(h in name_lower for h in self.DELIVERY_DATE_HINTS)) and col.inferred_type == "date":
                hints[col.name] = {
                    "hint": "delivery",
                    "role": "actual_delivery_date",
                }
                continue

            if (tokens & self.PROMISED_DATE_HINTS or any(h in name_lower for h in self.PROMISED_DATE_HINTS)) and col.inferred_type == "date":
                hints[col.name] = {
                    "hint": "delivery",
                    "role": "promised_delivery_date",
                }
                continue

            # Quality metrics
            if (tokens & self.QUALITY_HINTS or any(h in name_lower for h in self.QUALITY_HINTS)) and col.inferred_type == "numeric":
                hints[col.name] = {
                    "hint": "quality",
                    "role": "defect_or_inspection_metric",
                }
                continue

            # Pricing
            if (tokens & self.PRICING_HINTS or any(h in name_lower for h in self.PRICING_HINTS)) and col.inferred_type == "numeric":
                hints[col.name] = {
                    "hint": "pricing",
                    "role": "price_or_cost",
                }
                continue

            # Communication
            if tokens & self.COMMUNICATION_HINTS or any(h in name_lower for h in self.COMMUNICATION_HINTS):
                hints[col.name] = {
                    "hint": "communication",
                    "role": "response_or_resolution_metric",
                }
                continue

        return hints

    def build_llm_prompt(
        self,
        analysis: SourceAnalysis,
        heuristic_hints: dict[str, dict],
    ) -> str:
        """
        Build the prompt sent to the Tier 1 LLM for semantic mapping.

        The LLM receives:
        - Column names, types, null patterns, sample values
        - Heuristic pre-classification hints
        - Instructions to map columns to the 5 dimensions

        Returns a structured JSON response.
        """
        column_descriptions = []
        for col in analysis.columns:
            hint = heuristic_hints.get(col.name, {})
            desc = (
                f"- Column '{col.name}': type={col.inferred_type}, "
                f"nulls={col.null_pct:.0%}, "
                f"unique_values={col.unique_count}, "
                f"samples={col.sample_values[:3]}"
            )
            if hint:
                desc += f", heuristic_hint={hint}"
            column_descriptions.append(desc)

        columns_text = "\n".join(column_descriptions)

        return f"""You are analyzing a supplier performance data file. Map each column to one of these categories:

DIMENSIONS (pick the most appropriate):
- quality: Defect counts, inspection results, pass/fail rates
- pricing: Prices, costs, invoice amounts, contract terms
- delivery: Delivery dates, promised dates, shipment tracking
- communication: Response times, ticket counts, resolution times
- reliability: Fulfillment quantities, order completion rates

SPECIAL ROLES:
- supplier_id: The column that identifies which supplier each row belongs to
- record_date: The date column that should be used as the record timestamp
- unmapped: Columns that don't fit any dimension (e.g., internal IDs, notes)

DATA SOURCE ({analysis.row_count} rows, {len(analysis.columns)} columns):
{columns_text}

Respond with a JSON array. For each column, provide:
{{
    "column_name": "the column name",
    "dimension": "quality|pricing|delivery|communication|reliability|null",
    "metric_role": "specific role like 'defect_count', 'actual_delivery_date', 'unit_price', etc.",
    "confidence": 0.0-1.0,
    "reasoning": "one sentence explaining why"
}}

Also include a "supplier_id_column" field (the best candidate) and a "summary" field with a plain-language description of what you found.

Respond ONLY with valid JSON, no markdown fencing."""

    def parse_llm_response(
        self,
        llm_response: str,
        analysis: SourceAnalysis,
    ) -> SchemaMappingProposal:
        """
        Parse the LLM's JSON response into a SchemaMappingProposal.

        Handles malformed responses gracefully — if parsing fails,
        falls back to heuristic-only mapping.
        """
        try:
            data = json.loads(llm_response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown fencing
            import re
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", llm_response)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Complete fallback — return heuristic-only proposal
                return self._fallback_proposal(analysis)

        # Handle both dict and list responses
        if isinstance(data, dict):
            mappings_raw = data.get("mappings", data.get("columns", []))
            supplier_id_col = data.get("supplier_id_column")
            summary = data.get("summary", "")
        elif isinstance(data, list):
            mappings_raw = data
            supplier_id_col = None
            summary = ""
        else:
            return self._fallback_proposal(analysis)

        mappings: list[ColumnMapping] = []
        unmapped: list[str] = []
        mapped_dimensions: set[str] = set()

        for item in mappings_raw:
            dim_str = item.get("dimension")
            dimension = None
            if dim_str and dim_str != "null":
                try:
                    dimension = Dimension(dim_str)
                    mapped_dimensions.add(dim_str)
                except ValueError:
                    pass

            role = item.get("metric_role", "")
            if role == "supplier_id" and not supplier_id_col:
                supplier_id_col = item.get("column_name")

            mapping = ColumnMapping(
                column_name=item.get("column_name", ""),
                dimension=dimension,
                metric_role=item.get("metric_role"),
                confidence=float(item.get("confidence", 0.5)),
                reasoning=item.get("reasoning", ""),
            )
            mappings.append(mapping)

            if dimension is None and role != "supplier_id" and role != "record_date":
                unmapped.append(item.get("column_name", ""))

        # Identify missing dimensions
        all_dims = {"quality", "pricing", "delivery", "communication", "reliability"}
        missing = list(all_dims - mapped_dimensions)

        return SchemaMappingProposal(
            mappings=mappings,
            supplier_id_column=supplier_id_col,
            unmapped_columns=unmapped,
            missing_dimensions=missing,
            summary=summary,
        )

    def _fallback_proposal(self, analysis: SourceAnalysis) -> SchemaMappingProposal:
        """Generate a heuristic-only proposal when the LLM fails."""
        hints = self.heuristic_pre_classify(analysis)
        mappings: list[ColumnMapping] = []
        supplier_col = None

        for col in analysis.columns:
            hint = hints.get(col.name, {})
            if hint.get("role") == "supplier_id":
                supplier_col = col.name

            dim = None
            hint_dim = hint.get("hint")
            if hint_dim and hint_dim != "supplier_identifier":
                try:
                    dim = Dimension(hint_dim)
                except ValueError:
                    pass

            mappings.append(ColumnMapping(
                column_name=col.name,
                dimension=dim,
                metric_role=hint.get("role"),
                confidence=0.6 if hint else 0.2,
                reasoning=f"Heuristic match based on column name pattern"
                if hint else "No heuristic match — needs manual classification",
            ))

        return SchemaMappingProposal(
            mappings=mappings,
            supplier_id_column=supplier_col,
            summary="⚠️ This mapping was generated using heuristics only (LLM unavailable). "
                    "Please review carefully.",
        )

    def format_proposal_for_user(self, proposal: SchemaMappingProposal) -> str:
        """
        Format a SchemaMappingProposal as plain-language text for user review.

        This is what the agent shows when it says 'I found 6 columns...'
        """
        lines = [proposal.summary, ""]

        if proposal.supplier_id_column:
            lines.append(
                f"📋 **Supplier identifier column**: `{proposal.supplier_id_column}`"
            )
            lines.append("")

        lines.append("**Column Mappings:**")
        for m in proposal.mappings:
            dim_label = m.dimension.value if m.dimension else "unmapped"
            confidence_bar = "🟢" if m.confidence >= 0.8 else "🟡" if m.confidence >= 0.5 else "🔴"
            lines.append(
                f"  {confidence_bar} `{m.column_name}` → **{dim_label}** "
                f"({m.metric_role or 'unknown role'}) — {m.reasoning}"
            )

        if proposal.missing_dimensions:
            lines.append("")
            lines.append(
                f"⚠️ **No data found for**: {', '.join(proposal.missing_dimensions)}. "
                f"These dimensions will be omitted from scoring."
            )

        lines.append("")
        lines.append("Does this mapping look correct? You can approve it as-is or correct any mappings.")

        return "\n".join(lines)
