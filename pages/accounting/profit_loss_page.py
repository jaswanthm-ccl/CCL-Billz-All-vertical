from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from utils.constants import PROFIT_LOSS_URL


class ProfitLossPage:
    """Page object for the non-restaurant Profit / Loss report."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = PROFIT_LOSS_URL
        self.report: dict = {}
        self.last_status: int | None = None

    @staticmethod
    def _is_report_response(response) -> bool:
        return (
            "accounting/profit-loss" in response.url
            and response.request.method == "GET"
            and "/export" not in response.url
        )

    def _capture(self, action) -> dict:
        with self.page.expect_response(self._is_report_response, timeout=15_000) as response_info:
            action()
        response = response_info.value
        self.last_status = response.status
        self.report = response.json().get("data") or {}
        self.page.get_by_role("heading", name="Profit & Loss Reports").wait_for()
        return self.report

    def navigate(self) -> dict:
        return self._capture(lambda: self.page.goto(self.url))

    @property
    def from_date(self):
        return self.page.locator('input[name="from_date"]')

    @property
    def to_date(self):
        return self.page.locator('input[name="to_date"]')

    def is_page_visible(self) -> bool:
        return (
            self.page.get_by_role("heading", name="Profit & Loss Reports").is_visible()
            and self.page.get_by_role("button", name="Filter", exact=True).is_visible()
        )

    def apply_filters(
        self, from_date: str, to_date: str, branch: str | None = None
    ) -> dict:
        self.from_date.fill(from_date)
        self.to_date.fill(to_date)
        if branch:
            branch_input = (
                self.page.locator("label", has_text="Branch")
                .first.locator("xpath=..")
                .locator('input[role="combobox"]')
            )
            branch_input.click()
            self.page.get_by_role("option", name=branch, exact=True).click()
        return self._capture(
            lambda: self.page.get_by_role("button", name="Filter", exact=True).click()
        )

    def submit_invalid_range(self, from_date: str, to_date: str) -> None:
        self.from_date.fill(from_date)
        self.to_date.fill(to_date)
        self.page.get_by_role("button", name="Filter", exact=True).click()

    def date_validation_error(self):
        return self.page.get_by_text("End date must be on or after start date")

    @staticmethod
    def parse_amount(text: str) -> Decimal:
        normalized = re.sub(r"[^\d.-]", "", text)
        return Decimal(normalized or "0")

    def table_headers(self) -> list[list[str]]:
        return [
            [header.inner_text().strip() for header in table.locator("thead th").all()]
            for table in self.page.locator("table").all()
        ]

    def section_rows(self, section: str) -> list[dict[str, str | Decimal]]:
        table_index = {"Income": 0, "Expense": 1}[section]
        table = self.page.locator("table").nth(table_index)
        rows: list[dict[str, str | Decimal]] = []
        raw_rows = table.locator("tbody tr").evaluate_all(
            "rows => rows.map(row => Array.from(row.cells).map(cell => cell.innerText.trim()))"
        )
        for cells in raw_rows:
            if len(cells) != 3 or "No income data found" in " ".join(cells):
                continue
            rows.append(
                {
                    "ledger": cells[0],
                    "branch": cells[1],
                    "amount": self.parse_amount(cells[2]),
                }
            )
        return rows

    def summary_amount(self, label: str) -> Decimal:
        card_index = {"Total Income": 0, "Total Expense": 1, "Net Profit": 2, "Net Loss": 2}[label]
        card = self.page.locator(".row.mb-4 .card").nth(card_index)
        return self.parse_amount(card.locator("h5").inner_text())

    def net_label(self) -> str:
        profit = self.page.get_by_text("Net Profit", exact=True)
        return "Net Profit" if profit.count() and profit.first.is_visible() else "Net Loss"
