from __future__ import annotations

from typing import Any

from pages.report.gstr_1_base_page import Gstr1ReportPage
from utils.constants import GSTR1_B2B_URL


class Gstr1B2bPage(Gstr1ReportPage):
    """GSTR-1 B2B report interactions and strict API-backed assertions."""

    REPORT_NAME = "GSTR-1 B2B"
    API_PATH_SUFFIX = "/reports/gstr1/b2b"
    REPORT_URL = GSTR1_B2B_URL
    EXPECTED_HEADERS = [
        "INVOICE NUMBER",
        "INVOICE DATE",
        "CUSTOMER NAME",
        "CUSTOMER GSTIN",
        "CUSTOMER STATE",
        "INVOICE VALUE",
        "TAXABLE VALUE",
        "CGST",
        "SGST",
        "IGST",
        "TOTAL GST",
        "TOTAL INVOICE AMOUNT",
        "BRANCH",
        "HSN/SAC",
        "GST %",
    ]

    @staticmethod
    def find_invoice(
        data: dict[str, Any], invoice_no: str
    ) -> dict[str, Any] | None:
        rows = data.get("rows", [])
        if not isinstance(rows, list):
            return None
        return next(
            (
                row
                for row in rows
                if row.get("invoice_number") == invoice_no
                or row.get("invoice_no") == invoice_no
            ),
            None,
        )
