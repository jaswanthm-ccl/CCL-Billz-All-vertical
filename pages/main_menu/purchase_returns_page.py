from __future__ import annotations

import re
from playwright.sync_api import Page
from utils.constants import PURCHASE_RETURNS_URL

class PurchaseReturnsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = PURCHASE_RETURNS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)

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
        
        self.page.get_by_role("button", name="Return").click()
        
        # Wait for success toast
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
            self.page.get_by_text(re.compile(r"Purchase return", re.IGNORECASE)).first.wait_for(state="visible", timeout=5000)

    def filter_returns(self, branch_name: str, supplier_name: str) -> None:
        self.navigate()
        self.page.wait_for_load_state("networkidle")

        # Click Expand filters if it's there
        try:
            expand_btn = self.page.get_by_role("button", name="Expand filters")
            if expand_btn.is_visible():
                expand_btn.click()
        except Exception:
            pass

        # Select Branch in filters
        # Use a combination of class and text selectors to click the branch react-select container
        try:
            self.page.locator("div").filter(has_text=re.compile(r"^All Branches$")).nth(2).click(timeout=3000)
        except Exception:
            try:
                self.page.locator("input[name='branch_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
            except Exception:
                # Fallback: find the first react-select container in the filter section
                self.page.locator(".react-select__input-container").first.click()
        self.page.get_by_role("option", name=branch_name).click()

        # Select Supplier in filters
        try:
            self.page.locator("input[name='supplier_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
        except Exception:
            # Click the second react-select container
            self.page.locator(".react-select__input-container").nth(1).click()
        self.page.get_by_role("option", name=supplier_name).click()

        # Click Filter button
        self.page.get_by_role("button", name="Filter", exact=True).click()
        self.page.wait_for_load_state("networkidle")

    def verify_return_details(self, product_name: str, quantity: str, rate: str, total_amount: str) -> bool:
        # Locate the return row (e.g. "T-Shirt Orange MT-ShirtQ: 1 | R: 300 | A: 300")
        pattern = f"{product_name}.*Q: {quantity}.*R: {rate}.*A: {total_amount}"
        row = self.page.locator("div").filter(has_text=re.compile(pattern)).first
        row.click()

        # Click View button
        self.page.get_by_title("view").first.click()
        
        # Verify dialog contains the product name
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=5000)
        
        # Verify product cell in the dialog
        product_cell = self.page.get_by_role("cell", name=product_name, exact=True)
        product_cell.wait_for(state="visible", timeout=5000)
        
        # Close dialog
        dialog.get_by_role("button").filter(has_text=re.compile(r"^$")).click()
        dialog.wait_for(state="hidden", timeout=5000)
        return True
