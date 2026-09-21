"""
CSV and Excel file adapter.

Handles:
- CSV files (auto-detecting delimiter and encoding)
- Excel files (.xlsx, .xls) via openpyxl
- Header row detection
- Basic data cleaning (strip whitespace, standardize column names)
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from src.data.adapters.base import DataAdapter, SourceAnalysis


class CSVExcelAdapter(DataAdapter):
    """Adapter for CSV and Excel file uploads."""

    # Common file extensions
    CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}
    EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}

    def extract_raw(self, source: str | bytes) -> pd.DataFrame:
        """
        Read a CSV or Excel file into a DataFrame.

        Args:
            source: File path (str) or raw file bytes.

        Returns:
            Raw DataFrame with cleaned column names.
        """
        if isinstance(source, bytes):
            return self._read_bytes(source)
        return self._read_file(source)

    def extract_and_analyze(self, source: str | bytes) -> SourceAnalysis:
        """Convenience: extract + structural analysis in one call."""
        df = self.extract_raw(source)
        return self.analyze_structure(df)

    def _read_file(self, filepath: str) -> pd.DataFrame:
        """Read from a file path, auto-detecting format."""
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext in self.EXCEL_EXTENSIONS:
            df = pd.read_excel(filepath, engine="openpyxl")
        elif ext in self.CSV_EXTENSIONS:
            df = self._read_csv_smart(filepath)
        else:
            # Try CSV as fallback
            df = self._read_csv_smart(filepath)

        return self._clean_columns(df)

    def _read_bytes(self, data: bytes) -> pd.DataFrame:
        """
        Read from raw bytes, trying Excel first then CSV.

        Used when receiving file uploads via the API where we have bytes
        but may not know the format.
        """
        # Try Excel first
        try:
            df = pd.read_excel(io.BytesIO(data), engine="openpyxl")
            return self._clean_columns(df)
        except Exception:
            pass

        # Fall back to CSV
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")

        df = self._read_csv_smart(io.StringIO(text))
        return self._clean_columns(df)

    @staticmethod
    def _read_csv_smart(source: str | io.StringIO) -> pd.DataFrame:
        """
        Read CSV with automatic delimiter detection.

        Tries comma first, then semicolon, then tab.
        """
        for sep in [",", ";", "\t"]:
            try:
                if isinstance(source, str):
                    df = pd.read_csv(source, sep=sep, on_bad_lines="warn")
                else:
                    source.seek(0)
                    df = pd.read_csv(source, sep=sep, on_bad_lines="warn")

                # If we got more than 1 column, this delimiter probably worked
                if len(df.columns) > 1:
                    return df
            except Exception:
                continue

        # Last resort: just read it
        if isinstance(source, str):
            return pd.read_csv(source, on_bad_lines="warn")
        source.seek(0)
        return pd.read_csv(source, on_bad_lines="warn")

    @staticmethod
    def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names: strip whitespace, lowercase."""
        df.columns = [
            str(col).strip().lower().replace(" ", "_")
            for col in df.columns
        ]
        return df
