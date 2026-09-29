"""Restaurant Financial Report Page Object.

Route: RESTAURANT_BASE_URL/reports/financial-report
"""
from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page, Locator
from pages.common.base_page import BasePage
from utils.tenants import RESTAURANT, Tenant


class FinancialReportPage(BasePage):
    PATH = "/reports/financial-report"

    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)

    def navigate(self) -> None:
        self.page.goto(self.url, wait_until="domcontentloaded")
        try:
            self.today_button.wait_for(state="visible", timeout=10000)
        except Exception:
            pass

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def today_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Today", re.I)).first

    @property
    def filter_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"^Filter$", re.I)).first

    @property
    def clear_filters_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Clear Filters", re.I)).first

    @property
    def branch_select_control(self) -> Locator:
        return self.page.locator(".react-select__control").first

    # ── Actions ─────────────────────────────────────────────────────────────

    def apply_today_filter(self) -> None:
        if self.today_button.is_visible():
            self.today_button.click()
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(400)
        elif self.filter_button.is_visible():
            self.filter_button.click()
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(400)

    def get_metric_value(self, card_name: str) -> Decimal:
        """Extract monetary decimal value from a named card/section."""
        container = self.page.locator("div, .card, section").filter(
            has_text=re.compile(rf"{card_name}", re.I)
        ).last
        text = container.inner_text()
        # Find ₹1090.00 or ₹15000.00 or -₹500.00
        match = re.search(r"₹\s*(-?[0-9,]+(?:\.[0-9]+)?)", text)
        if match:
            clean = match.group(1).replace(",", "")
            return Decimal(clean)
        return Decimal("0")

    def get_cash_expense(self) -> Decimal:
        return self.get_metric_value("Cash Expense")

    def get_upi_expense(self) -> Decimal:
        return self.get_metric_value("UPI Expense")

    def get_credit_expense(self) -> Decimal:
        return self.get_metric_value("Credit Expense")

    def get_cash_income(self) -> Decimal:
        return self.get_metric_value("Cash Income")

    def get_upi_income(self) -> Decimal:
        return self.get_metric_value("UPI Income")

    def get_credit_income(self) -> Decimal:
        return self.get_metric_value("Credit Income")
