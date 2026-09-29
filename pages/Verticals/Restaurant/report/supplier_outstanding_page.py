"""Restaurant Supplier Outstanding Page Object.

Route: RESTAURANT_BASE_URL/reports/supplier-outstanding
Inherits from Restaurant CustomerOutstandingPage and overrides supplier-specific attributes.
"""
from __future__ import annotations

from playwright.sync_api import Page

from pages.Verticals.Restaurant.report.customer_outstanding_page import CustomerOutstandingPage
from utils.res_constants import RES_SUPPLIER_OUTSTANDING_URL


class SupplierOutstandingPage(CustomerOutstandingPage):
    """Restaurant adapter for the Supplier Outstanding report page."""

    REPORT_NAME = "Supplier Outstanding"
    API_PATH_SUFFIX = "/accounting/supplier-outstanding"
    SEARCH_PLACEHOLDER = "Search supplier…"
    REPORT_URL = RES_SUPPLIER_OUTSTANDING_URL
    EXPECTED_HEADERS = [
        "SUPPLIER",
        "LEDGER",
        "OUTSTANDING",
        "BALANCE TYPE",
        "BRANCH",
        "LAST TXN",
        "ACTIONS",
    ]

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = RES_SUPPLIER_OUTSTANDING_URL
        self.REPORT_URL = RES_SUPPLIER_OUTSTANDING_URL
