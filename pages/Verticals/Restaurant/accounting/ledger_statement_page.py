"""Restaurant Ledger Statement Page Object.

Route: RESTAURANT_BASE_URL/reports/ledger-statement
"""
from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page, Locator

from pages.accounting.ledger_statement_page import LedgerStatementPage as SharedLedgerStatementPage
from utils.res_constants import RESTAURANT_BASE_URL


class LedgerStatementPage(SharedLedgerStatementPage):
    """Restaurant adapter for the Ledger Statement report page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = f"{RESTAURANT_BASE_URL}/reports/ledger-statement"

    @property
    def ledger_select(self) -> Locator:
        return self.page.locator(".react-select__control").first

    @property
    def branch_select(self) -> Locator:
        return self.page.locator(".react-select__control").nth(1)

    def select_ledger(self, ledger_name: str, auto_filter: bool = True) -> None:
        """Select the requested Restaurant ledger using the shared strict contract."""
        super().select_ledger(ledger_name, auto_filter=auto_filter)
