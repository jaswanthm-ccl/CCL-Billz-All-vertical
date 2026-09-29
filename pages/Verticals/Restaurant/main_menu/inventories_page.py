"""Restaurant Inventories Page Object.

Route: RES_INVENTORIES_URL (/inventories)
Handles:
- Restaurant 10-column inventory table structure
- Branch and Product filtering
- Reading Opening Stock, Today Received, Today Allocated, and Final Available Stock
- Viewing details drawer and batch records
"""
from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_INVENTORIES_URL


class InventoriesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_INVENTORIES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search inventory...").or_(
            self.page.locator("input[placeholder*='Search']")
        ).first

    @property
    def expand_filters_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Expand filters", re.I)).first

    @property
    def collapse_filters_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Collapse filters", re.I)).first

    @property
    def submit_filter_button(self) -> Locator:
        return self.page.get_by_role("button", name="Filter", exact=True).first

    @property
    def export_button(self) -> Locator:
        return self.page.get_by_role("button", name="Export").first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".modal-dialog, div[role='dialog']")).first

    # ── Search & Filter ───────────────────────────────────────────────────────

    def search_inventory(self, product_name: str) -> bool:
        try:
            self.search_input.wait_for(state="visible", timeout=5000)
            self.search_input.fill(product_name)
            self.search_input.press("Enter")
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(300)
            self.page.locator("table tbody tr").filter(
                has_text=product_name
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def expand_filters(self) -> None:
        try:
            if self.collapse_filters_button.is_visible():
                return
            if self.expand_filters_button.is_visible():
                self.expand_filters_button.click()
                self.page.wait_for_timeout(300)
        except Exception:
            pass

    def collapse_filters(self) -> None:
        try:
            if self.collapse_filters_button.is_visible():
                self.collapse_filters_button.click()
                self.page.wait_for_timeout(300)
        except Exception:
            pass

    def filter_by_product_and_branch(self, product_name: str | None = None, branch_name: str | None = None) -> None:
        self.expand_filters()
        self.page.wait_for_timeout(300)

        filter_box = self.page.locator("div.border, div.card-body, form").filter(
            has_text=re.compile(r"Select Product|Select Branch", re.I)
        ).first

        if product_name:
            prod_control = filter_box.locator("label:has-text('Product'), div:has-text('Select Product')").last.locator(".react-select__control, .react-select__input-container").first
            if not prod_control.is_visible():
                prod_control = filter_box.locator(".react-select__control").nth(0)
            prod_control.click()
            self.page.wait_for_timeout(200)
            self.page.keyboard.type(product_name[:12])
            self.page.wait_for_timeout(300)
            opt = self.page.locator(".react-select__option").filter(has_text=product_name).first
            if opt.is_visible():
                opt.click()
            else:
                self.page.keyboard.press("Enter")

        if branch_name:
            branch_control = filter_box.locator("label:has-text('Branch'), div:has-text('Select Branch')").last.locator(".react-select__control, .react-select__input-container").first
            if not branch_control.is_visible():
                branch_control = filter_box.locator(".react-select__control").nth(1)
            branch_control.click()
            self.page.wait_for_timeout(200)
            self.page.keyboard.type(branch_name[:12])
            self.page.wait_for_timeout(300)
            opt = self.page.locator(".react-select__option").filter(has_text=branch_name).first
            if opt.is_visible():
                opt.click()
            else:
                self.page.keyboard.press("Enter")

        if self.submit_filter_button.is_visible():
            self.submit_filter_button.click()
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(600)

    # ── Read Stock Values (Restaurant 10-column table) ─────────────────────────

    def get_stock_values(self, product_name: str, branch_name: str | None = None) -> dict[str, str]:
        row = self.page.locator("table tbody tr").filter(has_text=product_name)
        if branch_name:
            row = row.filter(has_text=branch_name)
        row = row.first

        try:
            row.wait_for(state="visible", timeout=5000)
        except Exception:
            return {"status": "No Stock", "total_stock": "0", "available_stock": "0"}

        cells = row.locator("td").all()
        values: dict[str, str] = {}

        try:
            badge = row.locator(".badge").first
            values["status"] = badge.text_content().strip() if badge.count() > 0 else ""
        except Exception:
            values["status"] = ""

        try:
            values["opening_stock"] = cells[3].text_content().strip()
            values["today_received"] = cells[4].text_content().strip()
            values["today_allocated"] = cells[5].text_content().strip()
            values["total_stock"] = cells[6].text_content().strip()
            values["available_stock"] = cells[6].text_content().strip()
        except Exception:
            values["total_stock"] = "0"
            values["available_stock"] = "0"

        return values

    def get_available_stock_number(self, product_name: str, branch_name: str | None = None) -> Decimal:
        values = self.get_stock_values(product_name, branch_name=branch_name)
        stock_str = values.get("available_stock", "0")
        match = re.match(r"(\d+(?:\.\d+)?)", stock_str)
        return Decimal(match.group(1)) if match else Decimal("0")

    def get_total_stock_number(self, product_name: str, branch_name: str | None = None) -> Decimal:
        values = self.get_stock_values(product_name, branch_name=branch_name)
        stock_str = values.get("total_stock", "0")
        match = re.match(r"(\d+(?:\.\d+)?)", stock_str)
        return Decimal(match.group(1)) if match else Decimal("0")

    def is_product_in_table(self, product_name: str) -> bool:
        try:
            self.page.locator("table tbody tr").filter(
                has_text=product_name
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    # ── Detail View ───────────────────────────────────────────────────────────

    def view_inventory_detail(self, product_name: str) -> bool:
        row = self.page.locator("table tbody tr").filter(has_text=product_name).first
        row.wait_for(state="visible", timeout=5000)
        row.locator("button[title='view'], a[title='view'], i.bi-eye").first.click()

        try:
            self.page.get_by_text("Batches").or_(self.page.locator(".offcanvas, .drawer, div[role='dialog']")).first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def close_detail_drawer(self) -> None:
        try:
            self.page.locator(".btn-close, button[aria-label='Close']").first.click()
        except Exception:
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass
