"""Restaurant Customer Outstanding Page Object.

Route: RESTAURANT_BASE_URL/reports/customer-outstanding
Inherits from shared CustomerOutstandingPage and overrides the URL.
"""
from __future__ import annotations

import re

from playwright.sync_api import Page

from pages.report.customer_outstanding_page import CustomerOutstandingPage as SharedCustomerOutstandingPage
from utils.res_constants import RES_CUSTOMER_OUTSTANDING_URL


class CustomerOutstandingPage(SharedCustomerOutstandingPage):
    """Restaurant adapter for the Customer Outstanding report page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = RES_CUSTOMER_OUTSTANDING_URL
        self.REPORT_URL = RES_CUSTOMER_OUTSTANDING_URL

    def _capture(self, action, predicate=None, timeout=30_000):
        """Override with higher timeout for restaurant server."""
        matcher = predicate or self._is_report_response
        with self.page.expect_response(matcher, timeout=timeout) as response_info:
            action()
        response = response_info.value
        assert response.ok, (
            f"{self.REPORT_NAME} API returned HTTP {response.status}: {response.url}"
        )
        payload = response.json()
        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], dict):
                self.last_data = payload["data"]
            elif "data" in payload and isinstance(payload["data"], list):
                self.last_data = {
                    "items": payload["data"],
                    "rows": payload["data"],
                    "pagination": payload.get("pagination", {"page": 1, "last_page": 1}),
                    "summary": payload.get("summary", {}),
                }
            else:
                self.last_data = payload
        else:
            self.last_data = payload

        try:
            self.page.locator(".loading-state-modern--overlay").wait_for(
                state="hidden", timeout=10_000
            )
        except Exception:
            pass
        return self.last_data

    def expand_filters(self) -> None:
        """Expand the modern filter panel so filter controls become visible."""
        test_el = self.page.locator(
            ".filters-content-modern select, .filters-content-modern input"
        ).first
        if test_el.count() > 0 and test_el.is_visible():
            return

        toggles = [
            self.page.locator(".filters-header-modern").first,
            self.page.locator(".filters-toggle-btn").first,
            self.page.locator("button[aria-label='Expand filters']").first,
            self.page.locator("button:has(i.bi-chevron-down), button:has(i.bi-funnel)").first,
            self.page.get_by_role("button", name=re.compile(r"Filter", re.I)).first,
        ]

        for toggle in toggles:
            try:
                if toggle.count() > 0 and toggle.is_visible():
                    toggle.click()
                    self.page.wait_for_timeout(500)
                    if test_el.is_visible():
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
