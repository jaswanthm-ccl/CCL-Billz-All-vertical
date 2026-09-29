from __future__ import annotations

import re
from playwright.sync_api import Page
from utils.constants import BATCHES_URL

class BatchesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = BATCHES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)

    def is_batches_visible(self) -> bool:
        # We check visibility directly using Playwright's locator visibility state
        return self.page.get_by_placeholder("Search...").is_visible()

    def search_batch(self, query: str) -> bool:
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

    def verify_batch_row_details(self, product_name: str, expected_quantity_str: str) -> bool:
        """Verifies that the batch row for a given product has the expected quantity string (e.g. '10 / 10')"""
        self.search_batch(product_name)
        row = self.page.locator("table tbody tr").filter(has_text=product_name).first
        row.wait_for(state="visible", timeout=5000)
        
        # Quantity is in the 3rd column (index 2)
        qty_cell = row.locator("td").nth(2)
        qty_text = qty_cell.text_content().strip()
        
        # Split expected string (e.g. "10 / 10") and verify both numbers exist in cell text
        parts = expected_quantity_str.split("/")
        available = parts[0].strip()
        total = parts[1].strip()
        assert available in qty_text and total in qty_text, f"Expected available={available} and total={total} to be in {qty_text}"
        return True

    def open_batch_trace(self, product_name: str) -> bool:
        """Clicks the batch number link to open the traceability particulars drawer"""
        self.search_batch(product_name)
        row = self.page.locator("table tbody tr").filter(has_text=product_name).first
        
        # Click the link (the button inside the first cell)
        batch_link = row.locator("button.btn-link").first
        batch_link.click()
        
        # Wait for drawer/dialog to open
        drawer = self.page.get_by_role("dialog")
        try:
            drawer.wait_for(state="visible", timeout=5000)
        except Exception:
            self.page.locator(".modal, .drawer").first.wait_for(state="visible", timeout=5000)
            
        # Assert it opened
        assert drawer.is_visible() or self.page.locator(".drawer").first.is_visible()
        
        # Close drawer
        try:
            self.page.locator(".btn-close").click()
        except Exception:
            try:
                self.page.get_by_role("button", name="Close").click()
            except Exception:
                self.page.locator("button").filter(has_text=re.compile(r"^$")).first.click()
        
        # Wait for drawer to close
        self.page.wait_for_timeout(1000)
        return True
