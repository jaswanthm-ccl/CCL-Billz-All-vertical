from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response

from utils.constants import OUTSTANDING_BILLS_URL


class OutstandingBillsPage:
    """Read-only page object for the standalone Outstanding Bills report."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = OUTSTANDING_BILLS_URL
        self.last_data: dict[str, Any] = {}

    @staticmethod
    def _query(response: Response) -> dict[str, list[str]]:
        return parse_qs(urlparse(response.url).query)

    @classmethod
    def _is_outstanding_response(cls, response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        return (
            response.request.method == "GET"
            and path.endswith("/outstanding")
            and not path.endswith("/vouchers/outstanding")
        )

    @classmethod
    def _matches_params(cls, response: Response, **params: object) -> bool:
        if not cls._is_outstanding_response(response):
            return False
        query = cls._query(response)
        for key, value in params.items():
            if value is None or value == "":
                continue
            val_in_query = query.get(key, [None])[-1]
            if val_in_query is not None:
                if str(value).lower().rstrip("s") != str(val_in_query).lower().rstrip("s"):
                    return False
        return True

    def _capture(
        self,
        action: Callable[[], None],
        predicate: Callable[[Response], bool] | None = None,
        timeout: float = 30000,
    ) -> dict[str, Any]:
        matcher = predicate or self._is_outstanding_response
        with self.page.expect_response(matcher, timeout=timeout) as response_info:
            action()
        response = response_info.value
        assert response.ok, f"Outstanding API returned HTTP {response.status}: {response.url}"
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
            self.page.locator(".spinner-border, .loading-state-modern--overlay").wait_for(state="hidden", timeout=5000)
        except Exception:
            pass
        return self.last_data

    def navigate(self, bill_type: str = "sales") -> dict[str, Any]:
        target = self.url if bill_type == "sales" else f"{self.url}?type=purchases"
        return self._capture(
            lambda: self.page.goto(target, wait_until="domcontentloaded"),
            lambda response: self._matches_params(response, type=bill_type, page=1, limit=20),
        )

    def expand_filters(self) -> None:
        type_sel = self.page.locator("#outstanding-bill-type, select[name='type']").first
        if type_sel.count() > 0 and type_sel.is_visible():
            return
        toggles = [
            self.page.locator(".filters-header-modern").first,
            self.page.locator(".filters-toggle-btn").first,
            self.page.locator("button[aria-label='Expand filters']").first,
            self.page.locator("button:has(i.bi-chevron-down), button:has(i.bi-funnel)").first,
        ]
        for toggle in toggles:
            try:
                if toggle.count() > 0 and toggle.is_visible():
                    toggle.click()
                    self.page.wait_for_timeout(400)
                    if type_sel.is_visible():
                        return
            except Exception:
                continue

        try:
            self.page.evaluate("""
                document.querySelectorAll('.filter-select-modern, #outstanding-bill-type, #outstanding-bill-status')
                    .forEach(el => {
                        let parent = el.closest('.filters-body-modern, .filters-content, .collapse');
                        if (parent) {
                            parent.style.display = 'block';
                            parent.classList.add('show');
                        }
                    });
            """)
            self.page.wait_for_timeout(200)
        except Exception:
            pass

    def set_type(self, bill_type: str) -> dict[str, Any]:
        self.expand_filters()
        type_sel = self.page.locator("#outstanding-bill-type, select[name='type']").first
        type_sel.wait_for(state="visible", timeout=5000)
        return self._capture(
            lambda: type_sel.select_option(bill_type),
            lambda response: self._matches_params(response, type=bill_type, page=1),
        )

    def set_bill_type(self, bill_type: str) -> dict[str, Any]:
        return self.set_type(bill_type)

    def set_status(self, status: str, bill_type: str = "sales") -> dict[str, Any]:
        self.expand_filters()
        status_sel = self.page.locator("#outstanding-bill-status, select[name='status']").first
        status_sel.wait_for(state="visible", timeout=5000)
        return self._capture(
            lambda: status_sel.select_option(status),
            lambda response: self._matches_params(
                response, status=status, page=1
            ),
        )

    def clear_filters(self, bill_type: str = "sales") -> dict[str, Any]:
        self.expand_filters()
        return self._capture(
            lambda: self.page.locator("button:has-text('Clear'), button:has-text('Reset')").first.click(),
            lambda response: self._matches_params(response, page=1),
        )

    def search(self, query: str, bill_type: str = "sales") -> dict[str, Any]:
        return self._capture(
            lambda: self.page.get_by_placeholder("Search invoice...").fill(query),
            lambda response: self._matches_params(
                response, type=bill_type, search=query, page=1
            ),
        )

    def set_page_size(self, size: int, bill_type: str = "sales") -> dict[str, Any]:
        control = self.page.locator(".react-select__control, div[class*='react-select']").first

        def select_size() -> None:
            control.click()
            self.page.wait_for_timeout(200)
            opt = self.page.locator(".react-select__option, div[class*='-option']").filter(
                has_text=re.compile(rf"{size}\s*rows", re.I)
            ).first
            if opt.count() > 0:
                opt.click()
            else:
                self.page.get_by_role("option", name=re.compile(rf"{size}\s*rows", re.I)).first.click()

        return self._capture(
            select_size,
            lambda response: self._matches_params(
                response, type=bill_type, page=1, limit=size
            ),
        )

    def go_to_page(self, page_number: int, bill_type: str = "sales") -> dict[str, Any]:
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

            # 2. Modern app-pagination Next button
            if page_number > 1:
                next_nav = self.page.locator(
                    "button[aria-label='Next page'], .app-pagination__nav:has(i.bi-chevron-right)"
                ).first
                if next_nav.count() > 0 and next_nav.is_enabled():
                    next_nav.scroll_into_view_if_needed()
                    next_nav.click()
                    return

            # 3. Standard Bootstrap pagination
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
            lambda response: self._matches_params(
                response, type=bill_type, page=page_number
            ),
        )

    def load_all(self, bill_type: str = "sales") -> dict[str, Any]:
        data = self.navigate(bill_type)
        total = data.get("pagination", {}).get("total", 0) or len(data.get("items", []))
        if total > 20:
            try:
                data = self.set_page_size(100, bill_type)
            except Exception:
                pass
        return data

    @staticmethod
    def find_bill(
        data: dict[str, Any], *, party_name: str, bill_id: object | None = None
    ) -> dict[str, Any] | None:
        items = data.get("items", []) or data.get("data", []) or (data if isinstance(data, list) else [])
        for item in items:
            p_val = (
                item.get("party_name")
                or item.get("customer_name")
                or item.get("supplier_name")
                or item.get("party")
                or item.get("customer")
                or item.get("supplier")
                or item.get("ledger_name")
                or item.get("client_name")
                or ""
            )
            if isinstance(p_val, dict):
                p_name = p_val.get("name") or p_val.get("party_name") or ""
            else:
                p_name = str(p_val).strip()

            if not p_name:
                continue

            if (party_name.lower() in p_name.lower() or p_name.lower() in party_name.lower()) and (
                bill_id is None or item.get("id") == bill_id or item.get("bill_id") == bill_id
            ):
                return item
        return None

    def selected_type(self) -> str:
        self.expand_filters()
        sel = self.page.locator("#outstanding-bill-type, select[name='type']").first
        return sel.input_value()

    def selected_status(self) -> str:
        self.expand_filters()
        sel = self.page.locator("#outstanding-bill-status, select[name='status']").first
        return sel.input_value()

    def heading_visible(self) -> bool:
        return self.page.get_by_text("Outstanding bills", exact=True).first.is_visible()

    def heading_visible(self) -> bool:
        return self.page.get_by_text("Outstanding bills", exact=True).first.is_visible()

    def headers(self) -> list[str]:
        return [
            value.strip()
            for value in self.page.locator("table thead th").all_text_contents()
        ]

    def rows(self) -> list[list[str]]:
        result: list[list[str]] = []
        for row in self.page.locator("table tbody tr").all():
            cells = [value.strip() for value in row.locator("td").all_text_contents()]
            if len(cells) == 6:
                result.append(cells)
        return result

    def selected_type(self) -> str:
        self.expand_filters()
        return self.page.locator("#outstanding-bill-type").input_value()

    def selected_status(self) -> str:
        self.expand_filters()
        return self.page.locator("#outstanding-bill-status").input_value()

    @staticmethod
    def amount(value: object) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))
