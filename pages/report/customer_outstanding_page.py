from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Download, Page, Response

from pages.common.base_page import BasePage
from utils.tenants import Tenant


class CustomerOutstandingPage(BasePage):
    """Customer Outstanding report interactions and API-backed assertions."""

    REPORT_NAME = "Customer Outstanding"
    API_PATH_SUFFIX = "/accounting/customer-outstanding"
    SEARCH_PLACEHOLDER = "Search customer…"
    PATH = "/reports/customer-outstanding"
    EXPECTED_HEADERS = [
        "CUSTOMER",
        "LEDGER",
        "OUTSTANDING",
        "BALANCE TYPE",
        "BRANCH",
        "LAST TXN",
        "ACTIONS",
    ]

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)
        self.last_data: dict[str, Any] = {}

    @staticmethod
    def _query(response: Response) -> dict[str, list[str]]:
        return parse_qs(urlparse(response.url).query)

    @classmethod
    def _is_report_response(cls, response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        return (
            response.request.method == "GET"
            and path.endswith(cls.API_PATH_SUFFIX)
            and not path.endswith("/export")
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
        timeout: float = 30_000,
    ) -> dict[str, Any]:
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

        self.page.locator(".loading-state-modern--overlay").wait_for(
            state="hidden", timeout=10_000
        )
        return self.last_data

    def navigate(self) -> dict[str, Any]:
        return self._capture(
            lambda: self.page.goto(self.url, wait_until="domcontentloaded"),
            lambda response: self._matches_params(
                response,
                page=1,
                limit=20,
                sort_by="name",
                sort_dir="asc",
            ),
        )

    def expand_filters(self) -> None:
        test_el = self.page.locator(
            ".filters-content-modern select, .filters-content-modern input, .filters-body-modern"
        ).first
        if test_el.count() > 0 and test_el.is_visible():
            return
        button = self.page.locator(".filters-toggle-btn:has(i.bi-chevron-down), button[aria-label='Expand filters'], .filters-toggle-btn").first
        if button.count() and button.is_visible():
            button.click()
            self.page.wait_for_timeout(300)

    def search(self, query: str) -> dict[str, Any]:
        return self._capture(
            lambda: self.page.get_by_placeholder(self.SEARCH_PLACEHOLDER).fill(query),
            lambda response: self._matches_params(response, search=query, page=1),
        )

    def select_branch(self, branch_name: str) -> tuple[str, dict[str, Any]]:
        self.expand_filters()
        branch = self.page.locator(".filters-content-modern select").nth(0)
        option = branch.locator("option").filter(has_text=branch_name)
        value = option.get_attribute("value")
        assert value, f"Branch option not found: {branch_name}"
        data = self._capture(
            lambda: branch.select_option(value),
            lambda response: self._matches_params(response, branch_id=value, page=1),
        )
        return value, data

    def set_min_outstanding(self, amount: str) -> dict[str, Any]:
        self.expand_filters()
        control = self.page.locator(".filters-content-modern input[type='number']").nth(0)
        return self._capture(
            lambda: control.fill(amount),
            lambda response: self._matches_params(
                response, min_outstanding=amount, page=1
            ),
        )

    def set_max_outstanding(self, amount: str) -> dict[str, Any]:
        self.expand_filters()
        control = self.page.locator(".filters-content-modern input[type='number']").nth(1)
        return self._capture(
            lambda: control.fill(amount),
            lambda response: self._matches_params(
                response, max_outstanding=amount, page=1
            ),
        )

    def set_sort(self, sort_by: str, sort_dir: str = "asc") -> dict[str, Any]:
        self.expand_filters()
        controls = self.page.locator(".filters-content-modern select")
        sort_by_control = controls.nth(1)
        sort_dir_control = controls.nth(2)

        if sort_by_control.input_value() != sort_by:
            self._capture(
                lambda: sort_by_control.select_option(sort_by),
                lambda response: self._matches_params(
                    response, sort_by=sort_by, page=1
                ),
            )

        if sort_dir_control.input_value() == sort_dir:
            return self.last_data

        return self._capture(
            lambda: sort_dir_control.select_option(sort_dir),
            lambda response: self._matches_params(
                response, sort_by=sort_by, sort_dir=sort_dir, page=1
            ),
        )

    def reset_filters(self) -> dict[str, Any]:
        self.expand_filters()
        return self._capture(
            lambda: self.page.get_by_role("button", name="Reset filters").click(),
            lambda response: self._matches_params(
                response,
                page=1,
                limit=20,
                sort_by="name",
                sort_dir="asc",
            ),
        )

    def set_page_size(self, size: int) -> dict[str, Any]:
        control = self.page.locator(".react-select__control:visible, div[class*='react-select']:visible").last

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
            lambda response: self._matches_params(response, limit=size, page=1),
        )

    def go_to_page(self, page_number: int) -> dict[str, Any]:
        def click_page() -> None:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(300)

            # 1. Modern app-pagination input
            page_input = self.page.locator("input.app-pagination__input, .app-pagination input").first
            if page_input.count() > 0 and page_input.is_visible():
                page_input.scroll_into_view_if_needed()
                page_input.fill(str(page_number))
                page_input.press("Enter")
                return

            # 2. Modern app-pagination Next button (if navigating to page 2 or next)
            if page_number > 1:
                next_nav = self.page.locator(
                    "button[aria-label='Next page'], .app-pagination__nav:has(i.bi-chevron-right)"
                ).first
                if next_nav.count() > 0 and next_nav.is_enabled():
                    next_nav.scroll_into_view_if_needed()
                    next_nav.click()
                    return

            # 3. Standard Bootstrap pagination numbers
            btn = self.page.locator(
                ".pagination .page-item, .pagination a, .pagination button, button.page-link, a.page-link, .page-link"
            ).filter(has_text=re.compile(rf"^\s*{page_number}\s*$")).first
            if btn.count() > 0 and btn.is_visible():
                btn.scroll_into_view_if_needed()
                btn.click()
                return

            # 4. Standard Next button
            next_btn = self.page.locator(
                ".pagination .page-item, .pagination a, .pagination button, button, a"
            ).filter(has_text=re.compile(r"Next|›|»", re.I)).first
            if next_btn.count() > 0 and next_btn.is_enabled():
                next_btn.scroll_into_view_if_needed()
                next_btn.click()
                return

            self.page.get_by_text(str(page_number), exact=True).click()

        return self._capture(
            click_page,
            lambda response: self._matches_params(response, page=page_number),
        )

    def open_ledger(self, party_name: str) -> dict[str, Any]:
        row = self.row_for(party_name)
        assert row.count(), f"Customer Outstanding row not found: {party_name}"

        def is_ledger_response(response: Response) -> bool:
            path = urlparse(response.url).path.rstrip("/")
            return (
                response.request.method == "GET"
                and path.endswith("/accounting/ledger-statement/entries")
            )

        with self.page.expect_response(is_ledger_response, timeout=30_000) as response_info:
            row.get_by_role("button", name="View Ledger").click()
        response = response_info.value
        assert response.ok, f"Ledger drawer API returned HTTP {response.status}"
        payload = response.json()
        self.page.locator(".ledger-drawer-loading").wait_for(
            state="hidden", timeout=10_000
        )
        return payload.get("data", payload)

    def export_csv(self) -> Download:
        with self.page.expect_download(timeout=15_000) as download_info:
            self.page.get_by_role("button", name="Export CSV").click()
        return download_info.value

    def heading_visible(self) -> bool:
        return self.page.get_by_role(
            "heading", name=self.REPORT_NAME, exact=True
        ).is_visible()

    def headers(self) -> list[str]:
        return [
            value.strip()
            for value in self.page.locator("table thead th").all_text_contents()
        ]

    def rows(self) -> list[list[str]]:
        result: list[list[str]] = []
        for row in self.page.locator("table tbody tr").all():
            cells = [value.strip() for value in row.locator("td").all_text_contents()]
            if len(cells) == 7:
                result.append(cells)
        return result

    def row_for(self, party_name: str):
        return self.page.locator("table tbody tr").filter(
            has=self.page.get_by_text(party_name, exact=True)
        ).first

    @staticmethod
    def find_party(
        data: dict[str, Any], party_name: str
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in data.get("items", [])
                if item.get("party_name") == party_name
            ),
            None,
        )

    @staticmethod
    def amount(value: object) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))

    @staticmethod
    def downloaded_path(download: Download) -> Path:
        path = download.path()
        assert path, "Customer Outstanding CSV download has no local path"
        return Path(path)

    def get_summary_metrics(self) -> dict[str, str]:
        """Extract summary metrics cards from top of report."""
        cards = self.page.locator(".card-body:has(.text-muted)")
        metrics = {}
        for card in cards.all():
            label = card.locator(".text-muted").inner_text().strip()
            val = card.locator(".fs-5").inner_text().strip()
            metrics[label] = val
        return metrics

    def get_party_outstanding_amount(self, party_name: str) -> Decimal:
        """Search party and return outstanding amount from table."""
        self.search(party_name)
        self.page.wait_for_timeout(500)
        row = self.row_for(party_name)
        if row.count() == 0 or not row.is_visible():
            return Decimal("0.00")
        cells = [c.strip() for c in row.locator("td").all_text_contents()]
        if len(cells) >= 3:
            raw = cells[2].replace("₹", "").replace(",", "").strip()
            try:
                return Decimal(raw).quantize(Decimal("0.01"))
            except Exception:
                return Decimal("0.00")
        return Decimal("0.00")
