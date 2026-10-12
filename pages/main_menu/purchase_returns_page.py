from __future__ import annotations

import re
from typing import Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response

from pages.common.base_page import BasePage
from pages.common.components import ReactSelect
from utils.constants import LIST_TIMEOUT, UI_TIMEOUT
from utils.tenants import Tenant


class PurchaseReturnsPage(BasePage):
    PATH = "/purchase-returns"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    @property
    def _rows(self):
        return self.page.locator("table tbody tr")

    @staticmethod
    def _is_list_response(response: Response, search: str | None = None) -> bool:
        url = urlparse(response.url)
        path = url.path.rstrip("/")
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not (path.endswith("/purchase-returns") or path.endswith("/purchase-return"))
        ):
            return False
        return search is None or parse_qs(url.query).get("search", [""])[-1] == search

    def _reload_list(self, action: Callable[[], object], search: str | None = None) -> None:
        with self.page.expect_response(lambda r: self._is_list_response(r, search), timeout=15000):
            action()
        # List may render a table or card rows
        self.page.locator("table tbody tr, [class*='list'], [class*='card']").first.wait_for(
            state="visible", timeout=10000
        )

    def return_serials(self, serials: list[str], line_index: int = 0) -> Response:
        """In the open Purchase Return dialog, return the given tracked serials on one line; returns the API response."""
        return_dialog = self.page.get_by_role("dialog").filter(has_text="Purchase Return").last
        return_dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        return_dialog.locator(f"input[name='items.{line_index}.included']").check()
        return_dialog.get_by_role("button", name=re.compile(r"^Select ")).nth(line_index).click()

        picker = self.page.get_by_role("dialog").filter(has_text="Choose returnable").last
        picker.wait_for(state="visible", timeout=UI_TIMEOUT)
        serial_select = ReactSelect(self.page, picker.locator(".react-select__control").first)
        for serial in serials:
            serial_select.select(serial)
        picker.get_by_role("button", name="Done").click()
        picker.wait_for(state="hidden", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            lambda r: r.request.method == "POST" and urlparse(r.url).path.rstrip("/").endswith("/purchase-return"),
            timeout=LIST_TIMEOUT,
        ) as response_info:
            return_dialog.get_by_role("button", name="Return").click()
        return response_info.value

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))

    def is_purchase_returns_visible(self) -> bool:
        try:
            self.page.get_by_placeholder(re.compile(r"Search", re.IGNORECASE)).wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def perform_return(self, quantity: str) -> None:
        quantity_field = self.page.get_by_placeholder("Quantity")
        quantity_field.click()
        quantity_field.fill(str(quantity))

        with self.page.expect_response(
            lambda r: r.request.method == "POST"
            and urlparse(r.url).path.rstrip("/").endswith("/purchase-return"),
            timeout=LIST_TIMEOUT,
        ) as response_info:
            self.page.get_by_role("button", name="Return").click()
        response = response_info.value
        assert response.ok, f"Purchase return rejected ({response.status}): {response.text()[:500]}"

        try:
            toast = self.page.locator(".Toastify__toast-body, .toast-body, [role='alert'], .ant-message").filter(
                has_text=re.compile(r"Purchase.*return", re.IGNORECASE)
            ).first
            toast.wait_for(state="visible", timeout=10000)
            try:
                toast.wait_for(state="hidden", timeout=5000)
            except Exception:
                pass
        except Exception:
            self.page.get_by_text(re.compile(r"Purchase return", re.IGNORECASE)).first.wait_for(
                state="visible", timeout=5000
            )

    def filter_returns(self, branch_name: str, supplier_name: str) -> None:
        self.navigate()

        expand_btn = self.page.get_by_label("Expand filters")
        if expand_btn.count() and expand_btn.is_visible():
            expand_btn.click()
            self.page.get_by_role("button", name="Filter", exact=True).wait_for(
                state="visible", timeout=5000
            )

        branch_control = self.page.locator("input[name='branch_id']").locator("xpath=..").locator(
            ".react-select__control"
        ).first
        try:
            branch_control.click(timeout=3000)
        except Exception:
            self.page.locator("div").filter(has_text=re.compile(r"^All Branches$")).nth(2).click(timeout=3000)
        option = self.page.get_by_role("option", name=branch_name)
        option.wait_for(state="visible", timeout=5000)
        option.click()

        supplier_control = self.page.locator("input[name='supplier_id']").locator("xpath=..").locator(
            ".react-select__control"
        ).first
        try:
            supplier_control.click(timeout=3000)
        except Exception:
            self.page.locator(".react-select__control").nth(1).click()
        option = self.page.get_by_role("option", name=supplier_name)
        option.wait_for(state="visible", timeout=5000)
        option.click()

        self._reload_list(
            lambda: self.page.get_by_role("button", name="Filter", exact=True).click()
        )

    def verify_return_details(self, product_name: str, quantity: str, rate: str, total_amount: str) -> bool:
        pattern = f"{product_name}.*Q: {quantity}.*R: {rate}.*A: {total_amount}"
        row = self.page.locator("div").filter(has_text=re.compile(pattern)).first
        row.click()

        self.page.get_by_title("view").first.click()

        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=5000)

        product_cell = self.page.get_by_role("cell", name=product_name, exact=True)
        product_cell.wait_for(state="visible", timeout=5000)

        dialog.get_by_role("button").filter(has_text=re.compile(r"^$")).click()
        dialog.wait_for(state="hidden", timeout=5000)
        return True
