from __future__ import annotations

import re
from typing import Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response

from pages.common.base_page import BasePage
from utils.tenants import Tenant


class BatchesPage(BasePage):
    PATH = "/batches"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    @property
    def _rows(self):
        return self.page.locator("table tbody tr")

    @staticmethod
    def _is_list_response(response: Response, search: str | None = None) -> bool:
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/batches")
        ):
            return False
        return search is None or parse_qs(url.query).get("search", [""])[-1] == search

    def _reload_list(self, action: Callable[[], object], search: str | None = None) -> None:
        with self.page.expect_response(lambda r: self._is_list_response(r, search), timeout=15000):
            action()
        self._rows.first.wait_for(state="visible", timeout=10000)

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))

    def is_batches_visible(self) -> bool:
        return self.page.get_by_placeholder("Search...").is_visible()

    def search_batch(self, query: str) -> bool:
        search_box = self.page.get_by_placeholder("Search...")
        if search_box.input_value() != query:

            def search() -> None:
                search_box.fill(query)
                search_box.press("Enter")

            self._reload_list(search, search=query)
        try:
            self._rows.filter(has_text=query).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def verify_batch_row_details(self, product_name: str, expected_quantity_str: str) -> bool:
        """Verifies that the batch row for a given product has the expected quantity string (e.g. '10 / 10')"""
        self.search_batch(product_name)
        row = self._rows.filter(has_text=product_name).first
        row.wait_for(state="visible", timeout=5000)

        headers = [h.strip().upper() for h in self.page.locator("table thead th").all_inner_texts()]
        qty_text = row.locator("td").nth(headers.index("QUANTITY")).text_content().strip()

        parts = expected_quantity_str.split("/")
        available = parts[0].strip()
        total = parts[1].strip()
        assert available in qty_text and total in qty_text, (
            f"Expected available={available} and total={total} to be in {qty_text}"
        )
        return True

    def open_batch_trace(self, product_name: str) -> bool:
        """Clicks the batch number link to open the traceability particulars drawer"""
        self.search_batch(product_name)
        row = self._rows.filter(has_text=product_name).first

        batch_link = row.locator("button.btn-link").first
        batch_link.click()

        drawer = self.page.get_by_role("dialog")
        try:
            drawer.wait_for(state="visible", timeout=5000)
        except Exception:
            self.page.locator(".modal, .drawer").first.wait_for(state="visible", timeout=5000)

        assert drawer.is_visible() or self.page.locator(".drawer").first.is_visible()

        try:
            self.page.locator(".btn-close").click()
        except Exception:
            try:
                self.page.get_by_role("button", name="Close").click()
            except Exception:
                self.page.locator("button").filter(has_text=re.compile(r"^$")).first.click()

        try:
            drawer.wait_for(state="hidden", timeout=5000)
        except Exception:
            self.page.locator(".drawer").first.wait_for(state="hidden", timeout=5000)
        return True
