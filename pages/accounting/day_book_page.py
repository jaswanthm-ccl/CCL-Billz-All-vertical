from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Page, expect

from utils.constants import ACCOUNTING_DAY_BOOK_URL


class DayBookPage:
    """Accounting Day Book voucher audit report."""

    EMPTY_MESSAGES = ("Run report to load vouchers.", "No data found")

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = ACCOUNTING_DAY_BOOK_URL
        self.last_report: dict = {}
        self.last_response_status: int | None = None

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.get_by_role("heading", name="Day book").wait_for()
        self.page.get_by_role("button", name="Run report").wait_for()

    @property
    def from_date(self):
        return self.page.locator("label", has_text="From").first.locator("xpath=..").locator("input")

    @property
    def to_date(self):
        return self.page.locator("label", has_text="To").first.locator("xpath=..").locator("input")

    def is_page_visible(self) -> bool:
        return (
            self.page.get_by_role("heading", name="Day book").is_visible()
            and self.page.get_by_role("button", name="Run report").is_visible()
        )

    def run_report(self, from_date: str, to_date: str) -> dict:
        self.from_date.fill(from_date)
        self.to_date.fill(to_date)
        with self.page.expect_response(
            lambda response: "accounting/day-book" in response.url
            and response.request.method == "GET",
            timeout=15_000,
        ) as response_info:
            self.page.get_by_role("button", name="Run report").click()

        response = response_info.value
        self.last_response_status = response.status
        body = response.json()
        self.last_report = body.get("data") or {}
        expect(self.page.get_by_role("button", name="Run report")).to_be_enabled(timeout=10_000)
        return self.last_report

    def headers(self) -> list[str]:
        return [
            header.inner_text().strip()
            for header in self.page.locator("thead th").all()
        ]

    def get_row_count(self) -> int:
        rows = self.page.locator("table tbody tr")
        if rows.count() == 0:
            return 0
        first_text = rows.first.inner_text().strip()
        if any(message in first_text for message in self.EMPTY_MESSAGES):
            return 0
        return rows.count()

    @staticmethod
    def parse_amount(text: str) -> Decimal:
        normalized = re.sub(r"[^\d.-]", "", text)
        return Decimal(normalized or "0")

    def get_all_rows_data(self) -> list[dict[str, str | Decimal]]:
        if self.get_row_count() == 0:
            return []

        data: list[dict[str, str | Decimal]] = []
        for row in self.page.locator("table tbody tr").all():
            cells = row.locator("td").all()
            if len(cells) < 6:
                continue
            data.append(
                {
                    "date": cells[0].inner_text().strip(),
                    "voucher_no": cells[1].inner_text().strip(),
                    "type": cells[2].inner_text().strip(),
                    "narration": cells[3].inner_text().strip(),
                    "debit": self.parse_amount(cells[4].inner_text()),
                    "credit": self.parse_amount(cells[5].inner_text()),
                }
            )
        return data

    def row_by_voucher(self, voucher_no: str) -> dict[str, str | Decimal] | None:
        return next(
            (row for row in self.get_all_rows_data() if row["voucher_no"] == voucher_no),
            None,
        )

    def validation_error_is_visible(self) -> bool:
        error = self.page.get_by_text(
            re.compile(r"validation failed|to_date.*after|failed to load", re.IGNORECASE)
        ).first
        try:
            error.wait_for(state="visible", timeout=5_000)
            return True
        except Exception:
            return False
