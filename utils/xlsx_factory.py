"""Temporary XLSX builders used by browser import tests."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from openpyxl import Workbook


RESTAURANT_PRODUCT_HEADERS = (
    "s.no",
    "Product Name",
    "Category Name",
    "Selling Price",
    "Incentive %",
    "GST Percentage",
    "Product Type",
    "Menu Product Type",
    "Item Code",
    "Department",
    "Unit Type",
    "Cost Price",
    "Expiry (in days)",
    "HSN/SAC Code",
    "Description",
    "Low Stock",
)


def create_restaurant_product_import_xlsx(
    output_path: Path,
    rows: Sequence[Mapping[str, object]],
) -> Path:
    """Create one Restaurant product-import workbook from structured rows."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Restaurant Products"
    sheet.append(RESTAURANT_PRODUCT_HEADERS)

    for index, row in enumerate(rows, start=1):
        values = {"s.no": index, **row}
        sheet.append([values.get(header, "") for header in RESTAURANT_PRODUCT_HEADERS])

    workbook.save(output_path)
    return output_path
