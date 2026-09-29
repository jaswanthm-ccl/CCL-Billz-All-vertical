from __future__ import annotations

from typing import Any

from pages.report.gstr_1_base_page import Gstr1ReportPage
from utils.constants import GSTR1_B2C_URL


class Gstr1B2cPage(Gstr1ReportPage):
    """GSTR-1 B2C report interactions and strict API-backed assertions."""

    REPORT_NAME = "GSTR-1 B2C"
    API_PATH_SUFFIX = "/reports/gstr1/b2c"
    REPORT_URL = GSTR1_B2C_URL
    EXPECTED_HEADERS = [
        "INVOICE NUMBER",
        "INVOICE DATE",
        "CUSTOMER NAME",
        "CUSTOMER STATE",
        "INVOICE VALUE",
        "TAXABLE VALUE",
        "CGST",
        "SGST",
        "IGST",
        "TOTAL GST",
        "TOTAL INVOICE AMOUNT",
        "CUSTOMER TYPE",
        "BRANCH",
        "HSN/SAC",
        "GST %",
    ]

    @staticmethod
    def find_rate_group(
        data: dict[str, Any], state_name: str, tax_rate: str | float
    ) -> dict[str, Any] | None:
        rows = data.get("rows", [])
        if not isinstance(rows, list):
            return None
        return next(
            (
                row
                for row in rows
                if row.get("state") == state_name
                and str(row.get("tax_rate", row.get("rate"))) == str(tax_rate)
            ),
            None,
        )
