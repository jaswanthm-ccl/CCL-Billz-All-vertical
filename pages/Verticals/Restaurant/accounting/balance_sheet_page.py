"""Restaurant Balance Sheet Page Object.

Route: RESTAURANT_BASE_URL/reports/balance-sheet
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable

from playwright.sync_api import Page, Locator

from pages.accounting.balance_sheet_page import BalanceSheetPage as SharedBalanceSheetPage
from utils.res_constants import RESTAURANT_BASE_URL


class BalanceSheetPage(SharedBalanceSheetPage):
    """Restaurant adapter for the Balance Sheet report page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = f"{RESTAURANT_BASE_URL}/reports/balance-sheet"

    def _capture(self, action: Callable[[], object], timeout: int = 30_000) -> dict:
        with self.page.expect_response(self._is_report_response, timeout=timeout) as info:
            action()
        response = info.value
        self.last_status = response.status
        self.report = response.json().get("data") or {}
        self.heading.wait_for(state="visible", timeout=timeout)
        return self.report

    def navigate(self) -> dict:
        return self._capture(lambda: self.page.goto(self.url, wait_until="domcontentloaded"))

    @property
    def branch_input(self) -> Locator:
        """Branch selector input inside react-select."""
        branch_control = self.page.locator(".react-select__control").filter(
            has_text=re.compile(r"Branch|All Branches", re.I)
        ).or_(self.page.locator(".react-select__control").first)
        return branch_control

    def apply_filters(self, as_of_date: str, branch: str | None = None) -> dict:
        self.as_of_date.fill(as_of_date)
        if branch and branch != "All Branches":
            try:
                self.branch_input.click()
                self.page.wait_for_timeout(200)
                opt = self.page.get_by_role("option", name=branch, exact=False).first
                if opt.count() > 0 and opt.is_visible():
                    opt.click()
                else:
                    self.page.keyboard.type(branch[:6])
                    self.page.wait_for_timeout(300)
                    matched = self.page.locator(".react-select__option").filter(
                        has_text=re.compile(branch, re.I)
                    ).first
                    if matched.count() > 0 and matched.is_visible():
                        matched.click()
                    else:
                        self.page.locator(".react-select__option").first.click()
            except Exception:
                pass
        return self._capture(
            lambda: self.page.get_by_role("button", name="Filter", exact=True).click()
        )

    def clear_filters(self) -> dict:
        clear_btn = self.page.locator("button.clear-filters-btn").or_(
            self.page.get_by_role("button", name=re.compile(r"Clear", re.I))
        ).first
        return self._capture(lambda: clear_btn.click())
