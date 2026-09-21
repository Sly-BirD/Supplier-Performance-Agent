"""
Test fixtures — synthetic supplier data for testing.

Creates messy, realistic CSVs to validate schema inference,
scoring, and alert engines against edge cases.
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_delivery_csv() -> str:
    """
    Synthetic delivery data with some messy patterns:
    - Mixed date formats
    - A few null values
    - Late and on-time deliveries
    """
    data = [
        ["SupplierID", "SupplierName", "PO_Number", "DueDate", "ShipDate", "Qty_Ordered", "Qty_Received"],
        ["SUP001", "Acme Packaging", "PO-1001", "2024-01-15", "2024-01-14", "500", "500"],
        ["SUP001", "Acme Packaging", "PO-1002", "2024-02-10", "2024-02-12", "300", "300"],
        ["SUP001", "Acme Packaging", "PO-1003", "2024-03-01", "2024-03-08", "200", "190"],
        ["SUP002", "Beta Corp", "PO-2001", "2024-01-20", "2024-01-19", "1000", "1000"],
        ["SUP002", "Beta Corp", "PO-2002", "2024-02-15", "2024-02-15", "800", "800"],
        ["SUP002", "Beta Corp", "PO-2003", "2024-03-10", "2024-03-10", "600", "598"],
        ["SUP003", "Gamma Ltd", "PO-3001", "2024-01-25", "2024-02-01", "400", "380"],
        ["SUP003", "Gamma Ltd", "PO-3002", "2024-02-20", "2024-02-28", "250", "240"],
        ["SUP003", "Gamma Ltd", "PO-3003", "2024-03-15", "2024-03-22", "150", ""],
    ]
    return _to_csv_string(data)


@pytest.fixture
def sample_quality_csv() -> str:
    """Quality/inspection data with defect rates."""
    data = [
        ["vendor_id", "vendor_name", "batch_id", "inspection_date", "received_qty", "reject_qty", "pass_rate"],
        ["SUP001", "Acme Packaging", "B-101", "2024-01-20", "500", "6", "0.988"],
        ["SUP001", "Acme Packaging", "B-102", "2024-02-15", "300", "4", "0.987"],
        ["SUP001", "Acme Packaging", "B-103", "2024-03-10", "200", "10", "0.950"],
        ["SUP002", "Beta Corp", "B-201", "2024-01-25", "1000", "5", "0.995"],
        ["SUP002", "Beta Corp", "B-202", "2024-02-20", "800", "3", "0.996"],
        ["SUP002", "Beta Corp", "B-203", "2024-03-15", "600", "2", "0.997"],
    ]
    return _to_csv_string(data)


@pytest.fixture
def sample_pricing_csv() -> str:
    """Pricing data with variances."""
    data = [
        ["Supplier", "Item", "ContractPrice", "ActualPrice", "InvoiceDate", "Quantity"],
        ["Acme Packaging", "Widget A", "10.00", "10.50", "2024-01-15", "500"],
        ["Acme Packaging", "Widget A", "10.00", "10.80", "2024-02-15", "300"],
        ["Acme Packaging", "Widget B", "25.00", "25.00", "2024-03-01", "200"],
        ["Beta Corp", "Part X", "50.00", "49.50", "2024-01-20", "1000"],
        ["Beta Corp", "Part X", "50.00", "50.00", "2024-02-20", "800"],
        ["Beta Corp", "Part Y", "75.00", "78.00", "2024-03-10", "600"],
    ]
    return _to_csv_string(data)


@pytest.fixture
def messy_csv() -> str:
    """
    Intentionally messy CSV for testing schema inference edge cases:
    - Inconsistent column names
    - Mixed types in same column
    - High null density
    - Negative quantities
    """
    data = [
        ["sup ID", "  Supplier Name  ", "order_dt", "recv dt", "Qty", "rejects", "Notes"],
        ["001", "Acme", "01/15/2024", "01/14/2024", "500", "6", "OK"],
        ["001", "Acme", "02/10/2024", "02/12/2024", "300", "", "Late by 2 days"],
        ["002", "Beta", "2024-01-20", "2024-01-19", "1000", "5", ""],
        ["002", "Beta", "2024-02-15", "2024-02-15", "-50", "3", "Partial return"],
        ["003", "Gamma", "March 1 2024", "", "", "", "Missing data"],
        ["", "", "2024-03-15", "2024-03-20", "150", "0", "Unknown supplier"],
    ]
    return _to_csv_string(data)


@pytest.fixture
def sample_delivery_csv_bytes(sample_delivery_csv: str) -> bytes:
    """Return delivery CSV as bytes (simulating file upload)."""
    return sample_delivery_csv.encode("utf-8")


def _to_csv_string(rows: list[list[str]]) -> str:
    """Convert a list of rows to a CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue()


def save_fixtures():
    """Save fixture CSVs to disk for manual testing."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    fixtures = {
        "delivery_data.csv": [
            ["SupplierID", "SupplierName", "PO_Number", "DueDate", "ShipDate", "Qty_Ordered", "Qty_Received"],
            ["SUP001", "Acme Packaging", "PO-1001", "2024-01-15", "2024-01-14", "500", "500"],
            ["SUP001", "Acme Packaging", "PO-1002", "2024-02-10", "2024-02-12", "300", "300"],
            ["SUP002", "Beta Corp", "PO-2001", "2024-01-20", "2024-01-19", "1000", "1000"],
        ],
        "quality_data.csv": [
            ["vendor_id", "vendor_name", "batch_id", "inspection_date", "received_qty", "reject_qty"],
            ["SUP001", "Acme Packaging", "B-101", "2024-01-20", "500", "6"],
            ["SUP002", "Beta Corp", "B-201", "2024-01-25", "1000", "5"],
        ],
    }

    for filename, rows in fixtures.items():
        filepath = FIXTURES_DIR / filename
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)


if __name__ == "__main__":
    save_fixtures()
    print(f"Fixtures saved to {FIXTURES_DIR}")
