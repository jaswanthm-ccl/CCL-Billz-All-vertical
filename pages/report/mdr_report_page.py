from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response

from utils.constants import MDR_REPORT_URL


class MdrReportPage:
    """MDR Report interactions with API-backed report assertions."""

    SUMMARY_HEADERS = [
        "Bank",
        "Vouchers",
        "Net settlement",
        "MDR charge",
        "Gross",
        "Weighted MDR %",
    ]
    DETAIL_HEADERS = [
        "Date",
        "Voucher",
        "Bank",
        "Net",
        "MDR",
        "Gross",
        "MDR %",
        "Narration",
    ]

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = MDR_REPORT_URL
        self.last_data: dict[str, Any] = {}

    @staticmethod
    def month_start() -> str:
        today = date.today()
        return today.replace(day=1).isoformat()

    @staticmethod
    def today() -> str:
        return date.today().isoformat()

    @staticmethod
    def _query(response: Response) -> dict[str, list[str]]:
        return parse_qs(urlparse(response.url).query)

    @staticmethod
    def _is_report_response(response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        return (
            response.request.method == "GET"
            and path.endswith("/accounting/mdr-report")
        )

    @classmethod
    def _matches_params(cls, response: Response, **params: object) -> bool:
        if not cls._is_report_response(response):
            return False
        query = cls._query(response)
        return all(query.get(key, [None])[-1] == str(value) for key, value in params.items())

    def _capture(
        self,
        action: Callable[[], None],
        predicate: Callable[[Response], bool] | None = None,
    ) -> dict[str, Any]:
        matcher = predicate or self._is_report_response
        with self.page.expect_response(matcher, timeout=15_000) as response_info:
            action()
        response = response_info.value
        assert response.ok, f"MDR Report API returned HTTP {response.status}: {response.url}"
        payload = response.json()
        self.last_data = payload.get("data", payload)
        self.page.locator(".loading-state-modern--overlay").wait_for(
            state="hidden", timeout=10_000
        )
        return self.last_data

    def navigate(self) -> dict[str, Any]:
        return self._capture(
            lambda: self.page.goto(self.url, wait_until="domcontentloaded"),
            lambda response: self._matches_params(
                response,
                from_date=self.month_start(),
                to_date=self.today(),
            ),
        )

    def apply_filters(
        self,
        *,
        from_date: str,
        to_date: str,
        bank_name: str | None = None,
    ) -> dict[str, Any]:
        self.page.locator("input[name='from_date']").fill(from_date)
        self.page.locator("input[name='to_date']").fill(to_date)

        if bank_name:
            bank = self.page.locator(".filters-content-modern .react-select__control")
            bank.click()
            self.page.get_by_role("option", name=bank_name, exact=True).click()

        return self._capture(
            lambda: self.page.get_by_role("button", name="Filter", exact=True).click(),
            lambda response: self._matches_params(
                response, from_date=from_date, to_date=to_date
            ),
        )

    def clear_filters(self) -> dict[str, Any]:
        return self._capture(
            lambda: self.page.get_by_role("button", name="Clear Filters").click(),
            lambda response: self._matches_params(
                response,
                from_date=self.month_start(),
                to_date=self.today(),
            ),
        )

    def heading_visible(self) -> bool:
        return self.page.get_by_role(
            "heading", name="MDR Report", exact=True
        ).is_visible()

    def summary_headers(self) -> list[str]:
        table = self.page.locator("table").filter(
            has=self.page.get_by_role("columnheader", name="Vouchers", exact=True)
        )
        return [value.strip() for value in table.locator("thead th").all_text_contents()]

    def detail_headers(self) -> list[str]:
        table = self.page.locator("table").filter(
            has=self.page.get_by_role("columnheader", name="Voucher", exact=True)
        )
        return [value.strip() for value in table.locator("thead th").all_text_contents()]

    def summary_row_count(self) -> int:
        table = self.page.locator("table").filter(
            has=self.page.get_by_role("columnheader", name="Vouchers", exact=True)
        )
        return table.locator("tbody tr").count()

    def detail_row_count(self) -> int:
        table = self.page.locator("table").filter(
            has=self.page.get_by_role("columnheader", name="Voucher", exact=True)
        )
        return table.locator("tbody tr").count()

    def voucher_link(self, voucher_id: object):
        return self.page.locator(f"a[href='/vouchers/{voucher_id}']")

    def no_settlements_visible(self) -> bool:
        return self.page.get_by_text(
            "No MDR settlements for the selected period.", exact=True
        ).is_visible()

    @staticmethod
    def find_entry(
        data: dict[str, Any], *, narration: str
    ) -> dict[str, Any] | None:
        return next(
            (
                entry
                for entry in data.get("entries", [])
                if entry.get("narration") == narration
            ),
            None,
        )

    @staticmethod
    def find_bank_summary(
        data: dict[str, Any], *, bank_name: str
    ) -> dict[str, Any] | None:
        return next(
            (
                summary
                for summary in data.get("summary_by_bank", [])
                if summary.get("bank_name") == bank_name
            ),
            None,
        )

    @staticmethod
    def amount(value: object) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))
