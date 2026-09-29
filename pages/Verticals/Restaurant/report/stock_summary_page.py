"""Restaurant Stock Summary Page Object.

Route: RESTAURANT_BASE_URL/reports/stock-summary
Inherits from shared StockSummaryPage and adapts URL and timeouts for the restaurant tenant.
"""
from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlparse

from playwright.sync_api import Page, Response

from pages.report.stock_summary_page import StockSummaryPage as SharedStockSummaryPage
from utils.res_constants import RES_STOCK_SUMMARY_URL


class StockSummaryPage(SharedStockSummaryPage):
    """Restaurant adapter for the Stock Summary report page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = RES_STOCK_SUMMARY_URL

    def _capture(
        self,
        action: Callable[[], None],
        predicate: Callable[[Response], bool] | None = None,
        timeout: float = 30_000,
    ) -> dict[str, Any]:
        matcher = predicate or self._is_report_response
        with self.page.expect_response(matcher, timeout=timeout) as response_info:
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

        overlay = self.page.locator(".loading-state-modern--overlay")
        if overlay.count():
            try:
                overlay.wait_for(state="hidden", timeout=10_000)
            except Exception:
                pass
        return self.last_data

    def navigate(self) -> None:
        self.page.goto(self.url, wait_until="domcontentloaded")
        try:
            self.page.get_by_text(
                "Click Run report to view current stock summary.", exact=False
            ).wait_for(state="visible", timeout=6_000)
        except Exception:
            pass

    def run_report(self) -> dict[str, Any]:
        run_btn = self.page.get_by_role(
            "button", name="Run report", exact=True
        ).or_(self.page.locator("button:has-text('Run report')")).first
        return self._capture(lambda: run_btn.click())

    def run_search(self, query: str) -> dict[str, Any]:
        self.page.locator("input[name='search']").fill(query)
        run_btn = self.page.get_by_role(
            "button", name="Run report", exact=True
        ).or_(self.page.locator("button:has-text('Run report')")).first
        return self._capture(lambda: run_btn.click())
