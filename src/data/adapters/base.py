"""
Abstract base class for data adapters.

Every data source (CSV, Excel, ERP, Sheets, etc.) implements this interface.
The adapter's job is to:
1. Extract raw data into a pandas DataFrame
2. Generate a source signature (hash) for schema-mapping cache lookups
3. Detect basic structural metadata (headers, types, null patterns)

Schema *interpretation* (semantic mapping to dimensions) is NOT the adapter's
job — that belongs to the Schema Inference Engine.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ColumnInfo:
    """Structural metadata for a single column."""

    name: str
    inferred_type: str  # "date", "numeric", "string", "enum-like", "boolean"
    null_count: int
    null_pct: float
    unique_count: int
    unique_pct: float
    sample_values: list[str] = field(default_factory=list)


@dataclass
class SourceAnalysis:
    """Result of structural analysis on a data source."""

    columns: list[ColumnInfo]
    row_count: int
    source_signature: str  # Hash for cache matching
    raw_dataframe: pd.DataFrame
    warnings: list[str] = field(default_factory=list)  # e.g., "50% null in column X"


class DataAdapter(ABC):
    """
    Abstract interface for pluggable data ingestion.

    Subclasses implement extract_raw() for their specific source type.
    The base class provides shared utilities for structural analysis.
    """

    @abstractmethod
    def extract_raw(self, source: str | bytes) -> pd.DataFrame:
        """
        Extract raw data from the source into a DataFrame.

        Args:
            source: File path, URL, connection config, or raw bytes
                    depending on the adapter type.

        Returns:
            Raw DataFrame with original column names and types.
        """
        ...

    def analyze_structure(self, df: pd.DataFrame) -> SourceAnalysis:
        """
        Run structural analysis on a raw DataFrame.

        Detects column types, null patterns, unique value ratios,
        and generates a source signature for cache matching.
        """
        columns: list[ColumnInfo] = []
        warnings: list[str] = []

        for col_name in df.columns:
            series = df[col_name]
            null_count = int(series.isna().sum())
            null_pct = null_count / len(df) if len(df) > 0 else 0.0
            unique_count = int(series.nunique())
            unique_pct = unique_count / len(df) if len(df) > 0 else 0.0

            # Infer column type
            inferred_type = self._infer_column_type(series)

            # Get sample non-null values
            non_null = series.dropna()
            samples = [str(v) for v in non_null.head(5).tolist()]

            col_info = ColumnInfo(
                name=str(col_name),
                inferred_type=inferred_type,
                null_count=null_count,
                null_pct=round(null_pct, 3),
                unique_count=unique_count,
                unique_pct=round(unique_pct, 3),
                sample_values=samples,
            )
            columns.append(col_info)

            # Flag high null density
            if null_pct > 0.3:
                warnings.append(
                    f"Column '{col_name}' is {null_pct:.0%} null — may be unreliable"
                )

        source_signature = self._compute_signature(columns)

        return SourceAnalysis(
            columns=columns,
            row_count=len(df),
            source_signature=source_signature,
            raw_dataframe=df,
            warnings=warnings,
        )

    @staticmethod
    def _infer_column_type(series: pd.Series) -> str:
        """Heuristic type inference for a pandas Series."""
        if pd.api.types.is_bool_dtype(series):
            return "boolean"

        if pd.api.types.is_numeric_dtype(series):
            return "numeric"

        if pd.api.types.is_datetime64_any_dtype(series):
            return "date"

        # Try parsing as dates
        non_null = series.dropna()
        if len(non_null) > 0:
            try:
                pd.to_datetime(non_null.head(20))
                return "date"
            except (ValueError, TypeError):
                pass

        # Check if it looks enum-like (few unique values relative to row count)
        if len(non_null) > 0:
            unique_ratio = non_null.nunique() / len(non_null)
            if unique_ratio < 0.05 and non_null.nunique() <= 20:
                return "enum-like"

        return "string"

    @staticmethod
    def _compute_signature(columns: list[ColumnInfo]) -> str:
        """
        Generate a deterministic hash from column names + types.

        Used to match against previously-approved schema mappings so
        repeat uploads of the same file structure skip re-inference.
        """
        fingerprint = "|".join(
            f"{c.name}:{c.inferred_type}" for c in columns
        )
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
