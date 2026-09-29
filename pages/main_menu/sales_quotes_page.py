from __future__ import annotations

import re
from playwright.sync_api import Page
from utils.constants import SALES_QUOTES_URL

class SalesQuotesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = SALES_QUOTES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)

    def is_sales_quotes_visible(self) -> bool:
        try:
            self.page.get_by_placeholder("Search...").wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def add_sales_quote(self, customer: str, branch: str, product: str, quantity: str | int) -> None:
        self.page.goto(f"{self.url}/add")
        self.page.wait_for_load_state("networkidle")

        # 1. Select Customer
        try:
            self.page.locator("input[name='customer_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
        except Exception:
            self.page.locator(".react-select__input-container").first.click()
        self.page.get_by_role("option", name=customer).click()
        self.page.wait_for_timeout(500)

        # 2. Select Branch
        try:
            self.page.locator("input[name='branch_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
        except Exception:
            self.page.locator(".react-select__input-container").nth(1).click()
        self.page.get_by_role("option", name=branch).click()
        self.page.wait_for_timeout(500)

        # 3. Select Product
        try:
            self.page.locator(".mb-3.mt-3 .react-select__input-container").first.click(timeout=3000)
        except Exception:
            try:
                self.page.locator("input[name*='product']").locator("xpath=..").locator(".react-select__input-container").first.click(timeout=3000)
            except Exception:
                self.page.locator(".react-select__input-container").last.click()
        self.page.get_by_role("option", name=product).click()
        self.page.wait_for_timeout(500)

        # 4. Fill Quantity
        qty_input = self.page.get_by_placeholder("Quantity")
        qty_input.click()
        qty_input.fill(str(quantity))

        # 5. Click Create
        self.page.get_by_role("button", name="Create").click()

        # A confirmation dialog/modal sometimes follows the first Create click (similar to Sales)
        try:
            confirm_btn = self.page.locator("div.modal-footer button, div[role='dialog'] button").filter(has_text=re.compile(r"^Create$", re.IGNORECASE))
            if confirm_btn.count() > 0:
                confirm_btn.first.click()
        except Exception:
            pass

        # Wait for toast
        toast = self.page.get_by_text("Sales Quote created")
        toast.wait_for(state="visible", timeout=10000)
        self.navigate()
        self.page.wait_for_load_state("networkidle")

    def search_sales_quote(self, query: str) -> bool:
        search_box = self.page.get_by_placeholder("Search...")
        search_box.fill(query)
        search_box.press("Enter")
        self.page.wait_for_load_state("networkidle", timeout=5000)
        try:
            self.page.locator("table tbody tr").filter(has_text=query).first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def view_sales_quote(self, query: str, customer_name: str, branch_name: str) -> bool:
        self.search_sales_quote(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("view").click()

        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=5000)

        # Verify details
        dialog.get_by_text(customer_name).first.wait_for(state="visible", timeout=5000)
        dialog.get_by_text(branch_name).first.wait_for(state="visible", timeout=5000)

        # Close dialog
        try:
            self.page.locator(".btn-close").click()
        except Exception:
            dialog.get_by_role("button").filter(has_text=re.compile(r"^$")).first.click()
        dialog.wait_for(state="hidden", timeout=5000)
        return True

    def edit_sales_quote(self, query: str, new_quantity: str | int) -> None:
        self.search_sales_quote(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("edit").click()

        # Update Quantity
        qty_input = self.page.get_by_placeholder("Quantity")
        qty_input.click()
        qty_input.fill(str(new_quantity))

        # Click Update
        self.page.get_by_role("button", name="Update").click()
        self.page.wait_for_load_state("networkidle")
        self.navigate()
        self.page.wait_for_load_state("networkidle")

    def delete_sales_quote(self, query: str) -> None:
        self.search_sales_quote(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("delete").first.click()

        # Confirm delete
        self.page.get_by_role("button", name="Delete").click()
        toast = self.page.get_by_text("Deleted successfully.")
        toast.wait_for(state="visible", timeout=10000)
        self.navigate()
        self.page.wait_for_load_state("networkidle")

    def retrieve_sales_quote(self, query: str) -> None:
        self.search_sales_quote(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("delete").first.click()

        # Confirm retrieve
        self.page.get_by_role("button", name="Retrieve").click()
        toast = self.page.get_by_text("Retrieved successfully.")
        toast.wait_for(state="visible", timeout=10000)
        self.navigate()
        self.page.wait_for_load_state("networkidle")

    def download_sales_quote(self, query: str) -> str | None:
        self.search_sales_quote(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first

        with self.page.expect_download() as download_info:
            row.get_by_title("download").first.click()
        download = download_info.value

        # Optional toast wait
        try:
            self.page.get_by_text("File downloaded successfully").wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        return download.path()
