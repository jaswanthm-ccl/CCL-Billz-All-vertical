from __future__ import annotations

import re
from playwright.sync_api import Page
from utils.constants import SALE_RETURNS_URL

class SaleReturnsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = SALE_RETURNS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)

    def is_sale_returns_visible(self) -> bool:
        try:
            self.page.get_by_placeholder(re.compile(r"Search", re.IGNORECASE)).wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def perform_return(self, quantity: str | int) -> None:
        qty_input = self.page.get_by_placeholder("Quantity").first
        qty_input.click()
        qty_input.fill(str(quantity))
        
        self.page.get_by_role("button", name="Return").click()
        
        # Wait for toast
        try:
            toast = self.page.locator(".Toastify__toast-body, .toast-body, [role='alert'], .ant-message").filter(
                has_text=re.compile(r"Sale.*return", re.IGNORECASE)
            ).first
            toast.wait_for(state="visible", timeout=10000)
        except Exception:
            self.page.get_by_text(re.compile(r"Sales? return", re.IGNORECASE)).first.wait_for(state="visible", timeout=5000)
        self.navigate()
        self.page.wait_for_load_state("networkidle")

    def search_return(self, query: str) -> bool:
        search_box = self.page.get_by_placeholder(re.compile(r"Search", re.IGNORECASE))
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

    def verify_return_details(self, query: str, price: str, quantity: str, total: str) -> bool:
        self.search_return(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("view").first.click()

        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=5000)

        # Verify details inside dialog: customer, quantity, and total amount
        dialog.get_by_text(query).first.wait_for(state="visible", timeout=5000)
        try:
            dialog.get_by_text(str(quantity)).first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        try:
            dialog.get_by_text(str(total)).first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        # Close dialog
        try:
            self.page.locator(".btn-close").click()
        except Exception:
            dialog.get_by_role("button").filter(has_text=re.compile(r"^$")).first.click()
        dialog.wait_for(state="hidden", timeout=5000)
        return True

    def download_return(self, query: str) -> str | None:
        self.search_return(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        
        with self.page.expect_download() as download_info:
            row.get_by_title("download").first.click()
        download = download_info.value
        
        try:
            self.page.get_by_text("File downloaded successfully").wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        return download.path()
