from __future__ import annotations

from playwright.sync_api import Locator, Page

from utils.constants import BASE_URL, LIST_TIMEOUT, UI_TIMEOUT

PAYMENTS_URL = f"{BASE_URL}/payments"


class PaymentsPage:
    """Page object for the Payments module (/payments).

    Payments is a READ-ONLY list. Payments are auto-generated when Sales
    or Purchases are created with paid_amount > 0. No create/edit/delete.

    Table columns: #, TYPE, REFERENCE, STATUS, AMOUNT (₹)
    Search: placeholder='Search Payments...'
    Filters: None (disabled in the component)
    View: clicking REFERENCE opens a modal with Sale/Purchase details.
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = PAYMENTS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")
        loading_overlay = self.page.locator(".loading-state-modern--overlay").first
        if loading_overlay.count() > 0:
            try:
                loading_overlay.wait_for(state="hidden", timeout=LIST_TIMEOUT)
            except Exception:
                pass

    def is_payments_visible(self) -> bool:
        """Verify the payments page loaded (title visible)."""
        try:
            self.page.get_by_text("Payments").first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            return True
        except Exception:
            return False

    # ─── Table ─────────────────────────────────────────────────────────────────

    def get_row_count(self) -> int:
        """Return the number of rows in the payments table."""
        try:
            self.page.locator("table tbody tr").first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            return self.page.locator("table tbody tr").count()
        except Exception:
            return 0

    def get_first_row_data(self) -> dict:
        """Read data from the first row in the payments table.

        Returns dict with keys: id, type, reference, status, amount.
        """
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=UI_TIMEOUT)
        cells = row.locator("td").all()

        # Table columns: #, TYPE, REFERENCE, STATUS, AMOUNT (₹)
        return {
            "id": cells[0].text_content().strip() if len(cells) > 0 else "",
            "type": cells[1].text_content().strip() if len(cells) > 1 else "",
            "reference": cells[2].text_content().strip() if len(cells) > 2 else "",
            "status": cells[3].text_content().strip() if len(cells) > 3 else "",
            "amount": cells[4].text_content().strip() if len(cells) > 4 else "",
        }

    def is_table_empty(self) -> bool:
        """Check if the table shows empty state."""
        try:
            first_row = self.page.locator("table tbody tr").first
            first_row.wait_for(state="visible", timeout=3000)
            return "No" in first_row.text_content() and "found" in first_row.text_content()
        except Exception:
            return True

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search Payments...").or_(
            self.page.get_by_placeholder("Search...")
        ).or_(
            self.page.locator("input[placeholder*='Search']")
        ).first

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_payment(self, query: str) -> bool:
        """Search payments by text."""
        loading_overlay = self.page.locator(".loading-state-modern--overlay").first
        if loading_overlay.count() > 0:
            try:
                loading_overlay.wait_for(state="hidden", timeout=LIST_TIMEOUT)
            except Exception:
                pass

        self.search_input.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.search_input.fill(query)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle", timeout=LIST_TIMEOUT)
        self.page.wait_for_timeout(1000)
        try:
            first_row = self.page.locator("table tbody tr").first
            first_row.wait_for(state="visible", timeout=UI_TIMEOUT)
            text = first_row.text_content()
            return "No" not in text or "found" not in text
        except Exception:
            return False

    # ─── View Reference ────────────────────────────────────────────────────────

    def view_payment_reference(self) -> bool:
        """Click the REFERENCE link on the first row to open the view modal.

        Returns True if the modal opened successfully.
        """
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=5000)

        # The reference is a clickable span with class text-primary
        ref_link = row.locator(".text-primary, a").first
        ref_link.click()

        # Wait for the modal to appear
        modal = self.page.get_by_role("dialog")
        try:
            modal.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def close_modal(self) -> None:
        """Close the currently open modal."""
        try:
            self.page.locator(".btn-close").first.click()
            self.page.get_by_role("dialog").wait_for(state="hidden", timeout=5000)
        except Exception:
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass
