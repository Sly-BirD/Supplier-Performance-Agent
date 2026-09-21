"""
Tests for the Schema Inference Engine.

Validates:
- Heuristic pre-classification accuracy
- Column type detection
- Source signature generation
- Proposal formatting
"""

from __future__ import annotations

import io
import pytest
import pandas as pd

from src.data.adapters.csv_adapter import CSVExcelAdapter
from src.engines.schema_engine import SchemaEngine


class TestCSVAdapter:
    """Test the CSV/Excel adapter."""

    def test_extract_delivery_csv(self, sample_delivery_csv: str):
        adapter = CSVExcelAdapter()
        df = adapter.extract_raw(sample_delivery_csv.encode("utf-8"))
        assert len(df) == 9
        assert "supplierid" in df.columns
        assert "duedate" in df.columns

    def test_extract_quality_csv(self, sample_quality_csv: str):
        adapter = CSVExcelAdapter()
        df = adapter.extract_raw(sample_quality_csv.encode("utf-8"))
        assert len(df) == 6
        assert "vendor_id" in df.columns
        assert "reject_qty" in df.columns

    def test_column_cleaning(self):
        adapter = CSVExcelAdapter()
        csv_data = b"  Name  , Age , City \nAlice,30,NYC\n"
        df = adapter.extract_raw(csv_data)
        assert list(df.columns) == ["name", "age", "city"]

    def test_analyze_structure(self, sample_delivery_csv: str):
        adapter = CSVExcelAdapter()
        analysis = adapter.extract_and_analyze(sample_delivery_csv.encode("utf-8"))
        assert analysis.row_count == 9
        assert len(analysis.columns) == 7
        assert analysis.source_signature  # Non-empty hash

    def test_source_signature_deterministic(self, sample_delivery_csv: str):
        adapter = CSVExcelAdapter()
        a1 = adapter.extract_and_analyze(sample_delivery_csv.encode("utf-8"))
        a2 = adapter.extract_and_analyze(sample_delivery_csv.encode("utf-8"))
        assert a1.source_signature == a2.source_signature


class TestSchemaEngine:
    """Test heuristic pre-classification."""

    def test_heuristic_delivery_columns(self, sample_delivery_csv: str):
        adapter = CSVExcelAdapter()
        analysis = adapter.extract_and_analyze(sample_delivery_csv.encode("utf-8"))

        engine = SchemaEngine()
        hints = engine.heuristic_pre_classify(analysis)

        # Should detect supplier ID
        supplier_hints = {k: v for k, v in hints.items() if v.get("role") == "supplier_id"}
        assert len(supplier_hints) > 0, "Should detect at least one supplier ID column"

    def test_heuristic_quality_columns(self, sample_quality_csv: str):
        adapter = CSVExcelAdapter()
        analysis = adapter.extract_and_analyze(sample_quality_csv.encode("utf-8"))

        engine = SchemaEngine()
        hints = engine.heuristic_pre_classify(analysis)

        # Should detect vendor as supplier
        vendor_hints = {k: v for k, v in hints.items() if "vendor" in k}
        assert len(vendor_hints) > 0, "Should detect vendor columns"

    def test_heuristic_pricing_columns(self, sample_pricing_csv: str):
        adapter = CSVExcelAdapter()
        analysis = adapter.extract_and_analyze(sample_pricing_csv.encode("utf-8"))

        engine = SchemaEngine()
        hints = engine.heuristic_pre_classify(analysis)

        # Should detect price columns
        price_hints = {k: v for k, v in hints.items() if v.get("hint") == "pricing"}
        assert len(price_hints) > 0, "Should detect pricing columns"

    def test_fallback_proposal(self, sample_delivery_csv: str):
        adapter = CSVExcelAdapter()
        analysis = adapter.extract_and_analyze(sample_delivery_csv.encode("utf-8"))

        engine = SchemaEngine()
        proposal = engine._fallback_proposal(analysis)

        assert len(proposal.mappings) == 7
        assert "heuristic" in proposal.summary.lower() or "⚠" in proposal.summary

    def test_format_proposal(self, sample_delivery_csv: str):
        adapter = CSVExcelAdapter()
        analysis = adapter.extract_and_analyze(sample_delivery_csv.encode("utf-8"))

        engine = SchemaEngine()
        proposal = engine._fallback_proposal(analysis)
        formatted = engine.format_proposal_for_user(proposal)

        assert "Column Mappings" in formatted
        assert "approve" in formatted.lower() or "correct" in formatted.lower()

    def test_messy_csv_handling(self, messy_csv: str):
        adapter = CSVExcelAdapter()
        analysis = adapter.extract_and_analyze(messy_csv.encode("utf-8"))

        # Should detect warnings for high null columns
        assert len(analysis.warnings) > 0, "Should flag high null density columns"

        engine = SchemaEngine()
        hints = engine.heuristic_pre_classify(analysis)
        # Should still extract some hints despite messiness
        assert isinstance(hints, dict)
