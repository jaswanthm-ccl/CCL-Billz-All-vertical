"""Restaurant Supplier Outstanding Page Object.

Route: RESTAURANT_BASE_URL/reports/supplier-outstanding
Inherits from Restaurant CustomerOutstandingPage and overrides supplier-specific attributes.
"""
from __future__ import annotations

from playwright.sync_api import Page

from pages.Verticals.Restaurant.report.customer_outstanding_page import CustomerOutstandingPage


class SupplierOutstandingPage(CustomerOutstandingPage):
    """Restaurant adapter for the Supplier Outstanding report page."""

    REPORT_NAME = "Supplier Outstanding"
    API_PATH_SUFFIX = "/accounting/supplier-outstanding"
    SEARCH_PLACEHOLDER = "Search supplier…"
    PATH = "/reports/supplier-outstanding"
    EXPECTED_HEADERS = [
        "SUPPLIER",
        "LEDGER",
        "OUTSTANDING",
        "BALANCE TYPE",
        "BRANCH",
        "LAST TXN",
        "ACTIONS",
    ]