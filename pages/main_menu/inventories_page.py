from __future__ import annotations

import re
import time
from decimal import Decimal
from typing import Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Locator, Response, expect
from pages.common.base_page import BasePage
from utils.tenants import Tenant


class InventoriesPage(BasePage):
    PATH = "/inventories"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))

    # ── List loading ──────────────────────────────────────────────────────────

    @staticmethod
    def _list_params(response: Response) -> dict[str, str] | None:
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/inventories")
        ):
            return None
        return {key: values[-1] for key, values in parse_qs(url.query).items()}

    def _reload_list(self, action: Callable[[], object], **expected: str) -> None:
        """Run `action`, wait for the inventory list it triggers (matching `expected` query params) and its render."""

        def matches(response: Response) -> bool:
            params = self._list_params(response)
            return params is not None and all(params.get(key) == value for key, value in expected.items())

        with self.page.expect_response(matches, timeout=15000) as info:
            action()
        data = info.value.json().get("data")
        items = data.get("data", data.get("items")) if isinstance(data, dict) else data
        rows = self.page.locator("table tbody tr")
        if isinstance(items, list) and items:
            expect(rows).to_have_count(len(items), timeout=10000)
        else:
            rows.first.wait_for(state="visible", timeout=10000)

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
        """Search the inventory list; True when a row containing `product_name` is shown."""
        self.search_input.wait_for(state="visible", timeout=10000)
        if self.search_input.input_value() != product_name:

            def search() -> None:
                self.search_input.fill(product_name)
                self.search_input.press("Enter")

            self._reload_list(search, search=product_name)
        return self.is_product_in_table(product_name)

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

    def get_available_units(
        self, product_name: str, attribute_name: str, branch: str | None = None, search: str | None = None
    ) -> list[str]:
        """Tracked unit values (e.g. serial numbers) listed in the AVAILABLE UNITS column for the product,
        optionally in one branch's row (a product has one row per branch that holds it).
        For a variant ("Phone 8GB") pass the base product name as `search`: the search box doesn't match variant names."""
        if not self.search_inventory(search or product_name):
            return []
        headers = [h.strip().upper() for h in self.page.locator("thead th").all_inner_texts()]
        if "AVAILABLE UNITS" not in headers:
            return []
        rows = self.page.locator("table tbody tr").filter(has_text=product_name)
        if branch:
            rows = rows.filter(has_text=branch)
            if rows.count() == 0:
                return []
        row = rows.first
        cell_text = row.locator("td").nth(headers.index("AVAILABLE UNITS")).inner_text()
        return re.findall(rf"{re.escape(attribute_name)}:\s*(\S+)", cell_text)

    def wait_for_available_units(
        self,
        product_name: str,
        attribute_name: str,
        expected: list[str],
        branch: str | None = None,
        search: str | None = None,
        timeout_s: float = 20,
    ) -> list[str]:
        """Re-read AVAILABLE UNITS until it equals `expected` (stock updates land a moment after the
        transaction under load). Returns the last value read so the caller can assert on it."""
        deadline = time.monotonic() + timeout_s
        while True:
            self.navigate()
            units = self.get_available_units(product_name, attribute_name, branch=branch, search=search)
            if sorted(units) == sorted(expected) or time.monotonic() > deadline:
                return units

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
        """Filter the list to one branch; fails if the branch can't be picked (never shows all branches instead)."""
        self.expand_filters()
        branch_select = self.page.locator("input[name='branch_id']").locator("xpath=..").locator(
            ".react-select__control, .react-select__input-container"
        ).first
        branch_select.click()
        self.page.keyboard.type(branch_name[:12], delay=30)
        self.page.get_by_role("option", name=branch_name).first.click()
        self._reload_list(self.page.get_by_role("button", name="Filter", exact=True).click)

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
        self._reload_list(self.page.get_by_role("button", name="Filter", exact=True).click)

    def toggle_low_stock_filter(self) -> None:
        self.expand_filters()
        self.page.locator("input[name='low_stock_only']").check()
        self._reload_list(self.page.get_by_role("button", name="Filter", exact=True).click, low_stock_only="true")

    def clear_filters(self) -> None:
        """Reset the filters and wait for the unfiltered list."""
        self.expand_filters()
        low_stock_cb = self.page.locator("input[name='low_stock_only']")
        if low_stock_cb.count() > 0 and low_stock_cb.is_checked():
            low_stock_cb.uncheck()
        clear_btn = self.page.get_by_role("button", name=re.compile(r"Clear", re.I)).or_(
            self.page.get_by_text(re.compile(r"Clear Filter", re.I))
        )
        if clear_btn.count() > 0 and clear_btn.first.is_visible():
            self._reload_list(clear_btn.first.click)
        else:
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
            expect(self.page.locator("table tbody tr").filter(has_text=product_name).first).to_be_visible(timeout=5000)
            return True
        except AssertionError:
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
                "button", name=re.compile(r"^(?:Export PDF|Filter)$")
            ).first.click()

        download = download_info.value
        return download.path()
