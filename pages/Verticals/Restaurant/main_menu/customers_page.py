"""Restaurant Customers Page Object.

Route: RES_CUSTOMERS_URL (/customers)
"""
from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_CUSTOMERS_URL
from utils.random_data import generate_random_phone


class CustomersPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_CUSTOMERS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    @property
    def add_customer_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Customer", re.I)).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".modal-dialog, div[role='dialog']")).first

    @property
    def name_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="name"], input[placeholder*="Name"]').first

    @property
    def phone_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="phone"], input[placeholder*="phone"], input[placeholder*="Phone"]').first

    @property
    def address_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="addresses.0.address_line1"], input[placeholder*="Address"]').first

    @property
    def postal_code_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="addresses.0.postal_code"], input[placeholder*="Postal"], input[placeholder*="pincode"]').first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first

    @property
    def submit_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Create Customer|Create|Save", re.I)).first

    def add_customer(
        self,
        name: str,
        phone: str |  None = None,
        mobile: str | None = None,
        address: str = "123 Main Road",
        postal_code: str = "600001",
    ) -> bool:
        phone_val = mobile or phone or generate_random_phone()
        self.add_customer_button.wait_for(state="visible", timeout=5000)
        self.add_customer_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        # Allow async country/state fetch to resolve in form
        self.page.wait_for_timeout(800)

        self.name_input.fill(name)
        if self.phone_input.is_visible():
            self.phone_input.fill(phone_val)

        if self.address_input.is_visible():
            self.address_input.fill(address)

        if self.postal_code_input.is_visible():
            self.postal_code_input.fill(postal_code)

        with self.page.expect_response(
            lambda r: "/customers" in r.url and r.request.method == "POST", timeout=30000
        ) as resp_info:
            self.submit_button.click()

        assert resp_info.value.status in (200, 201), f"Create customer returned HTTP {resp_info.value.status}"
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)
        return True

    def search_customer(self, name: str) -> bool:
        self.search_input.wait_for(state="visible", timeout=5000)
        self.search_input.fill(name)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")
        try:
            self.page.locator("table tbody tr").filter(has_text=name).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def delete_customer(self, name: str) -> bool:
        if not self.search_customer(name):
            return False
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        try:
            row.first.wait_for(state="visible", timeout=5000)
            active_delete_btn = row.first.locator("button[title='delete']:has(i.bi-trash)")
            if active_delete_btn.count() == 0:
                return False
            active_delete_btn.first.click()

            modal = self.modal_dialog
            modal.wait_for(state="visible", timeout=5000)

            delete_btn = modal.get_by_role("button", name="Delete Customer")
            delete_btn.wait_for(state="visible", timeout=3000)
            with self.page.expect_response(
                lambda r: "/customers" in r.url and r.request.method == "DELETE",
                timeout=10000
            ) as resp_info:
                delete_btn.click()
            assert resp_info.value.status in (200, 204), f"Delete customer failed with HTTP {resp_info.value.status}"
            modal.wait_for(state="hidden", timeout=5000)
            return True
        except Exception:
            return False

