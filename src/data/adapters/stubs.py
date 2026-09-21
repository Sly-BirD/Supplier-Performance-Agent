"""
Stub adapters for Phase 3 data connectors.

These define the interface contract but raise NotImplementedError.
Implemented when the corresponding connector phase is built.
"""

from __future__ import annotations

import pandas as pd

from src.data.adapters.base import DataAdapter


class ERPAdapter(DataAdapter):
    """Stub: ERP connector (SAP, NetSuite, Oracle) — Phase 3."""

    def extract_raw(self, source: str | bytes) -> pd.DataFrame:
        raise NotImplementedError(
            "ERP adapter is not yet implemented. "
            "This connector is planned for Phase 3. "
            "Please upload data as CSV/Excel for now."
        )


class GoogleSheetsAdapter(DataAdapter):
    """Stub: Google Sheets connector — Phase 3."""

    def extract_raw(self, source: str | bytes) -> pd.DataFrame:
        raise NotImplementedError(
            "Google Sheets adapter is not yet implemented. "
            "This connector is planned for Phase 3. "
            "Please export your Sheet as CSV and upload it."
        )


class EmailTicketingAdapter(DataAdapter):
    """Stub: Email/Ticketing connector (Gmail, Outlook, Zendesk, Jira) — Phase 3."""

    def extract_raw(self, source: str | bytes) -> pd.DataFrame:
        raise NotImplementedError(
            "Email/Ticketing adapter is not yet implemented. "
            "This connector is planned for Phase 3. "
            "Please export communication data as CSV and upload it."
        )
