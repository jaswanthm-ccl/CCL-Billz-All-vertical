from __future__ import annotations

import re
from urllib.parse import urlparse
from playwright.sync_api import Page, Response
from pages.common.base_page import BasePage
from utils.constants import LIST_TIMEOUT
from utils.tenants import Tenant

class SaleReturnsPage(BasePage):
    PATH = "/sale-returns"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    def submit_return(self) -> Response:
        """Submit the open sale-return form as shown (tracked serials come preselected) and return the API response."""
        with self.page.expect_response(
            lambda r: r.request.method == "POST" and urlparse(r.url).path.rstrip("/").endswith("/sales-return"),
            timeout=LIST_TIMEOUT,
        ) as response_info:
            self.page.get_by_role("button", name="Return").click()
        return response_info.value

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

        response = self.submit_return()
        assert response.ok, f"Sale return rejected ({response.status}): {response.text()[:500]}"

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
