from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable

from playwright.sync_api import Page

from utils.constants import CASH_FLOW_URL


class CashFlowPage:
    """Page object for the Cash Flow Statement report."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = CASH_FLOW_URL
        self.report: dict = {}
        self.last_status: int | None = None

    @staticmethod
    def _is_report_response(response) -> bool:
        return (
            "accounting/cash-flow" in response.url
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
        return self.page.get_by_role("heading", name="Cash Flow Statement", exact=True)

    @property
    def from_date(self):
        return self.page.locator('input[name="from_date"]')

    @property
    def to_date(self):
        return self.page.locator('input[name="to_date"]')

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
            and self.page.get_by_text("Operating Activities", exact=True).is_visible()
            and self.page.get_by_text("Investing Activities", exact=True).is_visible()
            and self.page.get_by_text("Financing Activities", exact=True).is_visible()
        )

    def apply_filters(
        self,
        from_date: str,
        to_date: str,
        branch: str | None = None,
    ) -> dict:
        self.from_date.fill(from_date)
        self.to_date.fill(to_date)
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

    def submit_without_dates(self) -> None:
        self.from_date.fill("")
        self.to_date.fill("")
        self.page.get_by_role("button", name="Filter", exact=True).click()

    def submit_invalid_range(self, from_date: str, to_date: str) -> None:
        self.from_date.fill(from_date)
        self.to_date.fill(to_date)
        self.page.get_by_role("button", name="Filter", exact=True).click()

    @staticmethod
    def parse_amount(value: str) -> Decimal:
        normalized = re.sub(r"[^\d.-]", "", value)
        if normalized in {"", "-", ".", "-."}:
            return Decimal("0")
        return Decimal(normalized)

    def activity_amount(self, activity: str, metric: str) -> Decimal:
        card = self.page.locator(".card", has=self.page.get_by_text(activity, exact=True))
        column = card.locator(".col", has=self.page.get_by_text(metric, exact=True))
        return self.parse_amount(column.locator(".fw-bold").inner_text())

    def summary_amount(self, label: str) -> Decimal:
        card = self.page.locator(".card", has=self.page.get_by_text(label, exact=True))
        return self.parse_amount(card.locator("h5").inner_text())
