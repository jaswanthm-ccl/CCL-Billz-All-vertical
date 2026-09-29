"""Restaurant Trial Balance Page Object.

Route: RESTAURANT_BASE_URL/reports/trial-balance
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable

from playwright.sync_api import Page, Locator

from pages.accounting.trial_balance_page import TrialBalancePage as SharedTrialBalancePage
from utils.res_constants import RESTAURANT_BASE_URL


class TrialBalancePage(SharedTrialBalancePage):
    """Restaurant adapter for the Trial Balance report page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = f"{RESTAURANT_BASE_URL}/reports/trial-balance"

    @property
    def branch_input(self) -> Locator:
        """Branch selector input inside react-select."""
        branch_control = self.page.locator(".react-select__control").filter(
            has_text=re.compile(r"Branch|All Branches", re.I)
        ).or_(self.page.locator(".react-select__control").first)
        return branch_control
