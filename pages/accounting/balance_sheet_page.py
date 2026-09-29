from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable

from playwright.sync_api import Page

from utils.constants import BALANCE_SHEET_URL


class BalanceSheetPage:
    """Page object for the Balance Sheet report."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = BALANCE_SHEET_URL
        self.report: dict = {}
        self.last_status: int | None = None

    @staticmethod
    def _is_report_response(response) -> bool:
        return (
            "accounting/balance-sheet" in response.url
            and response.request.method == "GET"
        )

    def _capture(self, action: Callable[[], object]) -> dict:
        with self.page.expect_response(self._is_report_response, timeout=15_000) as info:
            action()
        response = info.value
        self.last_status = response.status
        self.report = response.json().get("data") or {}
        self.heading.wait_for(state="visible")
        return self.report

    @property
    def heading(self):
        return self.page.get_by_role("heading", name="Balance Sheet", exact=True)

    @property
    def as_of_date(self):
        return self.page.locator('input[name="as_of_date"]')

    @property
    def branch_input(self):
        return (
            self.page.locator("label", has_text="Branch")
            .first.locator("xpath=..")
            .locator('input[role="combobox"]')
        )

    def navigate(self) -> dict:
        return self._capture(lambda: self.page.goto(self.url))

    def is_page_visible(self) -> bool:
        return (
            self.heading.is_visible()
            and self.page.get_by_role("button", name="Filter", exact=True).is_visible()
            and self.page.get_by_text("Assets", exact=True).first.is_visible()
            and self.page.get_by_text("Liabilities & Equity", exact=True).is_visible()
        )

    def apply_filters(self, as_of_date: str, branch: str | None = None) -> dict:
        self.as_of_date.fill(as_of_date)
        if branch:
            self.branch_input.click()
            self.branch_input.fill(branch)
            self.page.get_by_role("option", name=branch, exact=True).click()
        return self._capture(
            lambda: self.page.get_by_role("button", name="Filter", exact=True).click()
        )

    def clear_filters(self) -> dict:
        return self._capture(
            lambda: self.page.locator("button.clear-filters-btn").click()
        )

    def submit_without_date(self) -> None:
        self.as_of_date.fill("")
        self.page.get_by_role("button", name="Filter", exact=True).click()

    def date_validation_error(self):
        return self.page.get_by_text("Date is required", exact=True)

    @staticmethod
    def parse_amount(value: str) -> Decimal:
        normalized = re.sub(r"[^\d.-]", "", value)
        if normalized in {"", "-", ".", "-."}:
            return Decimal("0")
        return Decimal(normalized)

    def summary_amount(self, label: str) -> Decimal:
        card_index = {"Total Assets": 0, "Liabilities": 1, "Equity": 2}[label]
        card = self.page.locator(".row.mb-4 .card").nth(card_index)
        return self.parse_amount(card.locator("h4").inner_text())

    def footer_amount(self, section: str) -> Decimal:
        table_index = {"assets": 0, "liabilities_and_equity": 1}[section]
        return self.parse_amount(
            self.page.locator("table").nth(table_index).locator("tfoot td").last.inner_text()
        )

    def liabilities_subtotal(self) -> Decimal:
        row = self.page.locator("table").nth(1).locator(
            "tbody tr", has_text="Total Liabilities"
        )
        return self.parse_amount(row.locator("td").last.inner_text())

    def balance_message(self) -> str:
        return self.page.locator(".alert.mt-4").inner_text().strip()

    def displayed_ledger_count(self) -> int:
        return self.page.locator("tr.table-row-clickable").count()

    def collapse_first_group(self) -> None:
        self.page.get_by_role("button", name="Collapse group").first.click()

    def expand_first_group(self) -> None:
        self.page.get_by_role("button", name="Expand group").first.click()

    def open_first_ledger(self) -> None:
        row = self.page.locator("tr.table-row-clickable").first
        row.wait_for(state="visible")
        row.click()
        self.page.wait_for_url("**/reports/ledger-statement")
