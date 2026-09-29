from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable

from playwright.sync_api import Page

from utils.constants import TRIAL_BALANCE_URL


class TrialBalancePage:
    """Page object for the Trial Balance report."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = TRIAL_BALANCE_URL
        self.report: dict = {}
        self.last_status: int | None = None

    @staticmethod
    def _is_report_response(response) -> bool:
        return (
            "accounting/trial-balance" in response.url
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
        return self.page.get_by_role("heading", name="Trial Balance Report")

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
            and self.page.get_by_text("Trial Balance Details", exact=True).is_visible()
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
        return Decimal(normalized or "0")

    def table_headers(self) -> list[str]:
        return [
            text.strip()
            for text in self.page.locator("table thead th").all_inner_texts()
        ]

    def rows(self) -> list[dict[str, str | Decimal]]:
        raw_rows = self.page.locator("table tbody tr").evaluate_all(
            "rows => rows.map(row => Array.from(row.cells).map(cell => cell.innerText.trim()))"
        )
        return [
            {
                "ledger": cells[0],
                "type": cells[1],
                "branch": cells[2],
                "debit": self.parse_amount(cells[3]),
                "credit": self.parse_amount(cells[4]),
            }
            for cells in raw_rows
            if len(cells) == 5
        ]

    def summary_amount(self, label: str) -> Decimal:
        card_index = {"Total Debit": 0, "Total Credit": 1}[label]
        card = self.page.locator(".row.mb-4 .card").nth(card_index)
        return self.parse_amount(card.locator("h4").inner_text())

    def footer_amount(self, column: str) -> Decimal:
        cell_index = {"debit": 1, "credit": 2}[column]
        return self.parse_amount(
            self.page.locator("table tfoot td").nth(cell_index).inner_text()
        )

    def open_first_ledger(self) -> None:
        first_row = self.page.locator("table tbody tr").first
        first_row.wait_for(state="visible")
        first_row.click()
        self.page.wait_for_url("**/reports/ledger-statement")
