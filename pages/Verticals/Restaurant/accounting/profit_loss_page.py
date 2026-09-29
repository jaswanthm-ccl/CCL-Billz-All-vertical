"""Restaurant Profit & Loss Page Object.

Route: RES_PROFIT_LOSS_URL (/reports/profit-loss)
Extends the base ProfitLossPage, overriding only the URL so that all
filter helpers, row parsers, and summary-card readers are reused.
"""

from __future__ import annotations

from playwright.sync_api import Page

from pages.accounting.profit_loss_page import ProfitLossPage as BaseProfitLossPage
from utils.res_constants import RES_PROFIT_LOSS_URL


class ProfitLossPage(BaseProfitLossPage):
    """Page object for the Restaurant-vertical Profit / Loss report."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # Override the URL to point at the Restaurant app
        self.url = RES_PROFIT_LOSS_URL
