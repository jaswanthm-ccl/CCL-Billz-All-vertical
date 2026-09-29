"""Restaurant Suppliers Page Object.

Route: RES_SUPPLIERS_URL (/suppliers)
"""
from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_SUPPLIERS_URL


class SuppliersPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_SUPPLIERS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def add_supplier_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Supplier", re.I)).first

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
        return self.modal_dialog.locator('input[name="address"], textarea[name="address"], input[placeholder*="Address"]').first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first

    @property
    def submit_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Create Supplier|Create|Save", re.I)).first

    # ── Actions ─────────────────────────────────────────────────────────────

    def add_supplier(
        self,
        name: str,
        phone: str = "9876543210",
        mobile: str | None = None,
        address: str = "123 Supplier Road",
    ) -> bool:
        phone_val = mobile or phone
        self.add_supplier_button.wait_for(state="visible", timeout=5000)
        self.add_supplier_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        # Allow async country/state fetch to resolve in form
        self.page.wait_for_timeout(800)

        self.name_input.fill(name)
        if self.phone_input.is_visible():
            self.phone_input.fill(phone_val)

        if self.address_input.is_visible():
            self.address_input.fill(address)

        with self.page.expect_response(
            lambda r: "/suppliers" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            self.submit_button.click()

        assert resp_info.value.status in (200, 201), f"Create supplier returned HTTP {resp_info.value.status}"
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)
        return True

    def search_supplier(self, name: str) -> bool:
        self.search_input.wait_for(state="visible", timeout=5000)
        self.search_input.fill(name)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")
        try:
            self.page.locator("table tbody tr").filter(has_text=name).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def delete_supplier(self, name: str) -> bool:
        if not self.search_supplier(name):
            return False
        row = self.page.locator("table tbody tr").filter(has_text=name).first
        row.locator("button[title='delete'], button:has(i.bi-trash)").first.click()

        confirm_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"Delete|Confirm", re.I)).first
        if confirm_btn.is_visible():
            confirm_btn.click()

        self.page.wait_for_load_state("networkidle")
        return True
