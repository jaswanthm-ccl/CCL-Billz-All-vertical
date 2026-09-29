from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse
import re

from playwright.sync_api import Download, Page, Response

from utils.constants import STOCK_SUMMARY_URL


class StockSummaryPage:
    """Stock Summary report interactions and API-backed assertions."""

    EXPECTED_HEADERS = [
        "Product",
        "Variant",
        "Available Qty",
        "Average Cost",
        "Available Units",
        "Cost Value",
        "Selling Value",
    ]
    EXPORT_HEADERS = [
        "Branch",
        "Product",
        "Variant",
        "SKU",
        "HSN/SAC",
        "Unit Value",
        "Unit Status",
        "Available Qty",
        "Average Cost",
        "Cost Value",
        "Selling Value",
    ]

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = STOCK_SUMMARY_URL
        self.last_data: dict[str, Any] = {}

    @staticmethod
    def _query(response: Response) -> dict[str, list[str]]:
        return parse_qs(urlparse(response.url).query)

    @staticmethod
    def _is_report_response(response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        return (
            response.request.method == "GET"
            and path.endswith("/reports/stock-summary")
            and not path.endswith("/export")
            and not path.endswith("/unit-values")
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
        assert response.ok, f"Stock Summary API returned HTTP {response.status}: {response.url}"
        payload = response.json()
        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], dict):
                self.last_data = payload["data"]
            elif "data" in payload and isinstance(payload["data"], list):
                self.last_data = {
                    "rows": payload["data"],
                    "items": payload["data"],
                    "meta": payload.get("meta", payload.get("pagination", {"per_page": 20, "last_page": 1})),
                    "pagination": payload.get("pagination", payload.get("meta", {"page": 1, "last_page": 1})),
                    "summary": payload.get("summary", {}),
                }
            else:
                self.last_data = payload
        else:
            self.last_data = payload

        self.page.locator(".loading-state-modern--overlay").wait_for(
            state="hidden", timeout=10_000
        )
        return self.last_data

    def navigate(self) -> None:
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.page.get_by_text(
            "Click Run report to view current stock summary.", exact=False
        ).wait_for(state="visible", timeout=10_000)

    def run_report(self) -> dict[str, Any]:
        return self._capture(
            lambda: self.page.get_by_role(
                "button", name="Run report", exact=True
            ).click(),
            lambda response: self._matches_params(
                response,
                page=1,
                per_page=25,
                low_stock_only=0,
                include_non_available_imeis=0,
            ),
        )

    def run_search(self, query: str) -> dict[str, Any]:
        self.page.locator("input[name='search']").fill(query)
        return self._capture(
            lambda: self.page.get_by_role(
                "button", name="Run report", exact=True
            ).click(),
            lambda response: self._matches_params(response, search=query, page=1),
        )

    def run_branch_filter(self, branch_name: str) -> tuple[str, dict[str, Any]]:
        branch = self.page.locator(
            ".filters-content-modern .react-select__control"
        ).nth(0)
        branch.click()
        option = self.page.get_by_role("option", name=branch_name, exact=True)
        option.click()
        hidden = self.page.locator("input[name='branch_id']")
        value = hidden.get_attribute("value") if hidden.count() else None

        data = self._capture(
            lambda: self.page.get_by_role(
                "button", name="Run report", exact=True
            ).click()
        )
        selected_id = value or (
            str(data["rows"][0]["branch_id"]) if data["rows"] else ""
        )
        return selected_id, data

    def run_cost_range(self, cost_from: str, cost_to: str) -> dict[str, Any]:
        self.page.locator("input[name='cost_from']").fill(cost_from)
        self.page.locator("input[name='cost_to']").fill(cost_to)
        return self._capture(
            lambda: self.page.get_by_role(
                "button", name="Run report", exact=True
            ).click(),
            lambda response: self._matches_params(
                response, cost_from=cost_from, cost_to=cost_to, page=1
            ),
        )

    def clear_filters(self) -> None:
        self.page.get_by_role("button", name="Expand filters").click()
        self.page.locator(".clear-filters-btn").click()
        self.page.get_by_text(
            "Click Run report to view current stock summary.", exact=False
        ).wait_for(state="visible", timeout=10_000)

    def set_page_size(self, size: int) -> dict[str, Any]:
        control = self.page.locator(
            ".react-select__control:visible, div[class*='react-select']:visible"
        ).last

        def select_size() -> None:
            control.click()
            self.page.wait_for_timeout(200)
            opt = self.page.locator(".react-select__option, div[class*='-option']").filter(
                has_text=re.compile(rf"{size}\s*rows", re.I)
            ).first
            if opt.count() and opt.is_visible():
                opt.click()
            else:
                self.page.get_by_role("option", name=f"{size} rows", exact=True).click()

        return self._capture(
            select_size,
            lambda response: self._matches_params(response, per_page=size, page=1),
        )

    def go_to_page(self, page_number: int, per_page: int = 5) -> dict[str, Any]:
        def click_page() -> None:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(300)
            btn = self.page.locator(".pagination .page-item, .pagination a, .pagination button, button.page-link, a.page-link, .page-link").filter(
                has_text=re.compile(rf"^\s*{page_number}\s*$")
            ).first
            if btn.count() > 0:
                btn.scroll_into_view_if_needed()
                btn.click()
                return

            next_btn = self.page.locator(".pagination .page-item, .pagination a, .pagination button, button, a").filter(
                has_text=re.compile(r"Next|›|»", re.I)
            ).first
            if next_btn.count() > 0 and next_btn.is_enabled():
                next_btn.scroll_into_view_if_needed()
                next_btn.click()
                return

            self.page.get_by_text(str(page_number), exact=True).click()

        return self._capture(
            click_page,
            lambda response: self._matches_params(
                response, page=page_number, per_page=per_page
            ),
        )

    def export(self, file_format: str) -> Download:
        label = "Export CSV" if file_format == "csv" else "Export XLSX"
        with self.page.expect_download(timeout=20_000) as download_info:
            self.page.get_by_role("button", name=label, exact=True).click()
        return download_info.value

    def heading_visible(self) -> bool:
        return self.page.get_by_role(
            "heading", name="Stock Summary", exact=True
        ).is_visible()

    def prompt_visible(self) -> bool:
        return self.page.get_by_text(
            "Click Run report to view current stock summary.", exact=False
        ).is_visible()

    def headers(self) -> list[str]:
        return [
            value.strip()
            for value in self.page.locator("table thead th").all_text_contents()
        ]

    def row_count(self) -> int:
        return self.page.locator("table tbody tr").count()

    @staticmethod
    def find_product(
        data: dict[str, Any], *, product_name: str, branch_name: str | None = None
    ) -> dict[str, Any] | None:
        return next(
            (
                row
                for row in data.get("rows", [])
                if row.get("product_name") == product_name
                and (
                    branch_name is None
                    or row.get("branch_name") == branch_name
                )
            ),
            None,
        )

    @staticmethod
    def amount(value: object) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))

    @staticmethod
    def downloaded_path(download: Download) -> Path:
        path = download.path()
        assert path, "Stock Summary download has no local path"
        return Path(path)
