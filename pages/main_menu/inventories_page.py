from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page, Locator
from utils.constants import INVENTORIES_URL


class InventoriesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = INVENTORIES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search inventory...")

    @property
    def overview_title(self) -> Locator:
        return self.page.get_by_text("Inventory Overview")

    @property
    def filter_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"filter", re.IGNORECASE))

    @property
    def export_button(self) -> Locator:
        return self.page.get_by_role("button", name="Export")

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog")

    def is_inventories_visible(self) -> bool:
        try:
            self.overview_title.first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    # ── Search ────────────────────────────────────────────────────────────────

    def search_inventory(self, product_name: str) -> bool:
        try:
            self.search_input.wait_for(state="visible", timeout=10000)
            self.search_input.fill(product_name)
            self.search_input.press("Enter")
            self.page.wait_for_timeout(300)
            self.page.locator("table tbody tr").filter(
                has_text=product_name
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    # ── Read Stock Values ─────────────────────────────────────────────────────

    def get_stock_values(self, product_name: str) -> dict[str, str]:
        found = self.search_inventory(product_name)
        if not found:
            return {"status": "No Stock", "total_stock": "0", "available_stock": "0"}

        try:
            row = self.page.locator("table tbody tr").filter(
                has_text=product_name
            ).first
            row.wait_for(state="visible", timeout=3000)
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
            values["total_stock"] = cells[4].text_content().strip() if len(cells) > 4 else "0"
            values["available_stock"] = cells[5].text_content().strip() if len(cells) > 5 else "0"
        except Exception:
            values["total_stock"] = "0"
            values["available_stock"] = "0"

        return values


    def get_available_stock_number(self, product_name: str) -> Decimal:
        values = self.get_stock_values(product_name)
        stock_str = values.get("available_stock", "0")
        match = re.match(r"(\d+(?:\.\d+)?)", stock_str)
        return Decimal(match.group(1)) if match else Decimal("0")

    def get_total_stock_number(self, product_name: str) -> Decimal:
        values = self.get_stock_values(product_name)
        stock_str = values.get("total_stock", "0")
        match = re.match(r"(\d+(?:\.\d+)?)", stock_str)
        return Decimal(match.group(1)) if match else Decimal("0")

    # ── Filters ───────────────────────────────────────────────────────────────

    def expand_filters(self) -> None:
        try:
            if self.filter_button.is_visible():
                self.filter_button.click()
        except Exception:
            pass

    def filter_by_branch(self, branch_name: str) -> None:
        self.expand_filters()
        try:
            branch_select = self.page.locator("input[name='branch_id']").locator("xpath=..").locator(".react-select__control, .react-select__input-container").first
            branch_select.wait_for(state="visible", timeout=5000)
            branch_select.click()
            self.page.wait_for_timeout(300)
            self.page.keyboard.type(branch_name[:12], delay=30)
            self.page.wait_for_timeout(500)
            self.page.get_by_role("option", name=branch_name).first.click()
        except Exception:
            try:
                self.page.locator(".react-select__control").first.click()
                self.page.get_by_role("option", name=branch_name).first.click()
            except Exception:
                pass
        self.page.get_by_role("button", name="Filter", exact=True).click()
        self.page.wait_for_load_state("networkidle")

    def get_available_stock_for_branch(self, product_name: str, branch_name: str) -> Decimal:
        """Navigate, filter by branch, and read available stock for the product."""
        self.navigate()
        self.filter_by_branch(branch_name)
        return self.get_available_stock_number(product_name)

    def filter_by_category(self, category_name: str) -> None:
        self.expand_filters()
        cat_select = self.page.locator("input[name='category_id']").locator("xpath=..").locator(".react-select__input-container")
        cat_select.wait_for(state="visible", timeout=5000)
        cat_select.click()
        self.page.get_by_role("option", name=category_name).click()
        self.page.get_by_role("button", name="Filter", exact=True).click()

    def toggle_low_stock_filter(self) -> None:
        self.expand_filters()
        self.page.locator("input[name='low_stock_only']").check()
        self.page.get_by_role("button", name="Filter", exact=True).click()

    def clear_filters(self) -> None:
        self.expand_filters()
        try:
            low_stock_cb = self.page.locator("input[name='low_stock_only']")
            if low_stock_cb.count() > 0 and low_stock_cb.is_checked():
                low_stock_cb.uncheck()
            clear_btn = self.page.get_by_role("button", name=re.compile(r"Clear", re.I)).or_(self.page.get_by_text(re.compile(r"Clear Filter", re.I)))
            if clear_btn.count() > 0 and clear_btn.first.is_visible():
                clear_btn.first.click()
            else:
                filter_btn = self.page.get_by_role("button", name="Filter", exact=True)
                if filter_btn.is_visible():
                    filter_btn.click()
            self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            self.navigate()

    def is_table_empty(self) -> bool:
        try:
            self.page.get_by_text("No inventory found.").wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    def is_product_in_table(self, product_name: str) -> bool:
        try:
            self.page.locator("table tbody tr").filter(
                has_text=product_name
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    # ── Detail View (Drawer) ──────────────────────────────────────────────────

    def view_inventory_detail(self, product_name: str) -> bool:
        self.search_inventory(product_name)
        row = self.page.locator("table tbody tr").filter(
            has_text=product_name
        ).first
        row.wait_for(state="visible", timeout=5000)

        row.get_by_title("view").first.click()

        try:
            self.page.get_by_text("Batches").first.wait_for(
                state="visible", timeout=5000
            )
            self.page.get_by_text("Batch Number").first.wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    def close_detail_drawer(self) -> None:
        try:
            self.page.locator(".btn-close").first.click()
        except Exception:
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass

    # ── Export ────────────────────────────────────────────────────────────────

    def export_inventory_pdf(self, filter_type: str = "all") -> str | None:
        self.export_button.click()

        self.page.locator("div.modal-content, div[role='dialog']").get_by_text(
            "Export Inventory", exact=True
        ).first.wait_for(state="visible", timeout=5000)

        if filter_type != "all":
            stock_select = self.page.locator("input[name='stock']").locator("xpath=..").locator(".react-select__input-container")
            stock_select.click()
            label_map = {
                "all": "All",
                "low_stock": "Low Stock",
                "empty_stock": "No Stock",
            }
            self.page.get_by_role(
                "option", name=label_map.get(filter_type, "All")
            ).click()

        with self.page.expect_download(timeout=15000) as download_info:
            self.page.locator("div.modal-content, div[role='dialog']").get_by_role(
                "button", name="Filter"
            ).click()

        download = download_info.value
        return download.path()
