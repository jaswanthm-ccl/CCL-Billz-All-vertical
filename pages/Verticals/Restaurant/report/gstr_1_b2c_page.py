"""Restaurant GSTR-1 B2C Page Object.

Route: RESTAURANT_BASE_URL/reports/gstr1-b2c
Inherits from shared Gstr1B2cPage and adapts URL and timeouts for the restaurant tenant.
"""
from __future__ import annotations

import re
from typing import Any, Callable
from urllib.parse import urlparse

from playwright.sync_api import Page, Response

from pages.report.gstr_1_b2c_page import Gstr1B2cPage as SharedGstr1B2cPage
from utils.res_constants import RES_GSTR1_B2C_URL


class Gstr1B2cPage(SharedGstr1B2cPage):
    """Restaurant adapter for the GSTR-1 B2C report page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = RES_GSTR1_B2C_URL
        self.REPORT_URL = RES_GSTR1_B2C_URL

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
        if not response.ok:
            try:
                detail = response.text()
            except Exception:
                detail = "<response body unavailable>"
            raise AssertionError(
                f"{self.REPORT_NAME} API failed with HTTP {response.status}: {detail}"
            )

        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise AssertionError(
                f"{self.REPORT_NAME} API returned an invalid payload: {payload!r}"
            )

        self.last_data = data
        overlay = self.page.locator(".loading-state-modern--overlay")
        if overlay.count():
            try:
                overlay.wait_for(state="hidden", timeout=10_000)
            except Exception:
                pass
        return data

    def expand_filters(self) -> None:
        """Expand the modern filter panel so filter controls become visible."""
        test_input = self.page.locator("input[name='start_date']").first
        if test_input.count() > 0 and test_input.is_visible():
            return

        toggles = [
            self.page.locator(".filters-header-modern").first,
            self.page.locator(".filters-toggle-btn").first,
            self.page.locator("button[aria-label='Expand filters']").first,
            self.page.get_by_role("button", name="Expand filters").first,
            self.page.locator("button:has(i.bi-chevron-down), button:has(i.bi-funnel)").first,
            self.page.get_by_role("button", name=re.compile(r"Filter", re.I)).first,
        ]

        for toggle in toggles:
            try:
                if toggle.count() > 0 and toggle.is_visible():
                    toggle.click()
                    self.page.wait_for_timeout(500)
                    if test_input.is_visible():
                        return
            except Exception:
                continue

        # Fallback: force visibility via JS
        try:
            self.page.evaluate("""
                document.querySelectorAll('.filters-body-modern, .filters-content, .collapse')
                    .forEach(el => {
                        el.style.display = 'block';
                        el.classList.add('show');
                    });
            """)
            self.page.wait_for_timeout(300)
        except Exception:
            pass
