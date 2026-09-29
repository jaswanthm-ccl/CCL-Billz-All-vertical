"""Shared API-backed page object for Restaurant incentive reports."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response

from utils.res_constants import RESTAURANT_BASE_URL


class RestaurantIncentiveReportPage:
    def __init__(self, page: Page, *, route: str, endpoint: str) -> None:
        self.page = page
        self.url = f"{RESTAURANT_BASE_URL}{route}"
        self.endpoint = endpoint
        self.last_data: dict[str, Any] = {}

    @staticmethod
    def today() -> str:
        return date.today().isoformat()

    def _is_report_response(self, response: Response) -> bool:
        return (
            response.request.method == "GET"
            and urlparse(response.url).path.rstrip("/").endswith(self.endpoint)
        )

    @staticmethod
    def _query(response: Response) -> dict[str, list[str]]:
        return parse_qs(urlparse(response.url).query)

    def _capture(self, action, expected: dict[str, str]) -> dict[str, Any]:
        def matches(response: Response) -> bool:
            if not self._is_report_response(response):
                return False
            query = self._query(response)
            return all(
                query.get(key, [None])[-1] == value
                for key, value in expected.items()
            )

        with self.page.expect_response(matches, timeout=15000) as response_info:
            action()
        response = response_info.value
        payload = response.json()
        assert response.ok, (
            f"Incentive Report API returned HTTP {response.status}: {payload}"
        )
        self.last_data = payload.get("data") or {}
        assert {"rows", "totals", "meta"} <= self.last_data.keys(), self.last_data
        return self.last_data

    def navigate(self) -> dict[str, Any]:
        today = self.today()
        return self._capture(
            lambda: self.page.goto(self.url, wait_until="domcontentloaded"),
            {"from_date": today, "to_date": today},
        )

    def _select_labeled_option(self, label: str, option_name: str) -> None:
        field = self.page.locator(".filter-item-modern").filter(
            has=self.page.get_by_text(label, exact=True)
        )
        control = field.locator(".react-select__control")
        control.wait_for(state="visible", timeout=5000)
        control.click()
        option = self.page.get_by_role("option", name=option_name, exact=True)
        option.wait_for(state="visible", timeout=5000)
        option.click()
        assert (
            control.locator(".react-select__single-value").inner_text().strip()
            == option_name
        )

    def filter_report(
        self,
        *,
        from_date: str,
        to_date: str,
        staff_name: str | None = None,
        branch_name: str | None = None,
    ) -> dict[str, Any]:
        self.page.locator("input[name='start_date']").fill(from_date)
        self.page.locator("input[name='end_date']").fill(to_date)
        if branch_name:
            self._select_labeled_option("Branch", branch_name)
        if staff_name:
            self._select_labeled_option("Waiter", staff_name)

        return self._capture(
            lambda: self.page.get_by_role(
                "button", name="Search", exact=True
            ).click(),
            {"from_date": from_date, "to_date": to_date},
        )

    def get_table_rows(self) -> list[list[str]]:
        return [
            [cell.inner_text().strip() for cell in row.locator("td").all()]
            for row in self.page.locator("table tbody tr").all()
        ]

    @staticmethod
    def amount(value: object) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))
