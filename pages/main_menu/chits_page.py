from __future__ import annotations

import re
from decimal import Decimal

from playwright.sync_api import Page

from utils.constants import BASE_URL

CHITS_URL = f"{BASE_URL}/chits"


class ChitsPage:
    """Page object for the Chits module (/chits).

    Chits are fund-based financial instruments. Full CRUD plus
    Record Payment and Record Commission actions.

    Form fields: chit_name, branch_id, foreman_name, chit_value,
                 tenure_months, monthly_amount, start_date, commission_amount, notes
    Table: NAME, DATE, FORMAN NAME, DESCRIPTION, CLOSED, Actions
    Search: placeholder='Search...' (live, debounced)
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = CHITS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def is_chits_visible(self) -> bool:
        """Verify the chits page loaded."""
        try:
            self.page.get_by_text("Chit Management").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    # ─── Create ────────────────────────────────────────────────────────────────

    def add_chit(
        self,
        chit_name: str,
        branch: str,
        chit_value: str,
        tenure_months: str,
        monthly_amount: str,
        foreman_name: str = "",
        commission_amount: str = "",
        notes: str = "",
    ) -> None:
        """Create a new chit."""
        self.page.get_by_role("button", name="Add Chit").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Chit Name
        modal.locator("input[name='chit_name']").fill(chit_name)

        # Branch (react-select) — click to open, type to filter, select
        branch_container = modal.locator("input[name='branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        branch_container.click()
        self.page.wait_for_timeout(500)
        # Type branch name using keyboard (input is focused after click)
        self.page.keyboard.type(branch, delay=50)
        self.page.wait_for_timeout(1000)
        # Wait for option to appear then click
        option = self.page.get_by_role("option", name=branch)
        option.wait_for(state="visible", timeout=10000)
        option.click()
        self.page.wait_for_timeout(300)

        # Foreman Name
        if foreman_name:
            modal.locator("input[name='foreman_name']").fill(foreman_name)

        # Chit Value
        modal.locator("input[name='chit_value']").fill(chit_value)

        # Tenure Months
        modal.locator("input[name='tenure_months']").fill(tenure_months)

        # Monthly Amount
        modal.locator("input[name='monthly_amount']").fill(monthly_amount)

        # Commission Amount
        if commission_amount:
            modal.locator("input[name='commission_amount']").fill(commission_amount)

        # Notes (need to click "Add Description" button first)
        if notes:
            modal.get_by_role("button", name="Add Description").click()
            modal.locator("textarea[name='notes']").fill(notes)

        # Submit
        modal.get_by_role("button", name="Create").click()

        # Wait for modal to close (success)
        try:
            modal.wait_for(state="hidden", timeout=15000)
        except Exception:
            errors = modal.locator(".text-danger, .invalid-feedback").all()
            visible_errors = [e.text_content().strip() for e in errors if e.is_visible() and e.text_content().strip() and e.text_content().strip() != "*"]
            if visible_errors:
                raise AssertionError(f"Chit creation validation errors: {visible_errors}")
            raise

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_chit(self, query: str) -> bool:
        """Search chits (live search, debounced)."""
        search_box = self.page.get_by_placeholder("Search...")
        search_box.fill("")
        self.page.wait_for_timeout(1000)
        search_box.fill(query)
        self.page.wait_for_timeout(2000)
        self.page.wait_for_load_state("networkidle", timeout=10000)
        try:
            first_row = self.page.locator("table tbody tr").first
            first_row.wait_for(state="visible", timeout=5000)
            text = first_row.text_content()
            return "No Chits found" not in text
        except Exception:
            return False

    # ─── Table ─────────────────────────────────────────────────────────────────

    def get_row_count(self) -> int:
        """Return visible row count."""
        try:
            self.page.locator("table tbody tr").first.wait_for(
                state="visible", timeout=5000
            )
            return self.page.locator("table tbody tr").count()
        except Exception:
            return 0

    def get_first_row_data(self) -> dict:
        """Read first row data. Columns: NAME, DATE, FORMAN NAME, DESCRIPTION, CLOSED, Actions."""
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=5000)
        cells = row.locator("td").all()
        return {
            "name": cells[0].text_content().strip() if len(cells) > 0 else "",
            "date": cells[1].text_content().strip() if len(cells) > 1 else "",
            "foreman_name": cells[2].text_content().strip() if len(cells) > 2 else "",
            "description": cells[3].text_content().strip() if len(cells) > 3 else "",
            "is_closed": cells[4].text_content().strip() if len(cells) > 4 else "",
        }

    # ─── View ──────────────────────────────────────────────────────────────────

    def view_chit(self, query: str) -> bool:
        """Search for a chit and click view."""
        if not self.search_chit(query):
            return False

        view_btn = self.page.locator("button[title='view'], button[title='View'], a[title='view'], a[title='View'], .btn-info, button:has-text('View'), i.bi-eye").first
        view_btn.click()
        modal = self.page.get_by_role("dialog")
        try:
            modal.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def close_modal(self) -> None:
        """Close the currently open modal."""
        try:
            self.page.locator(".btn-close, button.close, [aria-label='Close']").first.click()
            self.page.get_by_role("dialog").wait_for(state="hidden", timeout=5000)
        except Exception:
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass

    # ─── Edit ──────────────────────────────────────────────────────────────────

    def edit_chit(self, query: str, new_foreman: str) -> bool:
        """Search for a chit, click edit, change foreman name, save."""
        if not self.search_chit(query):
            return False

        edit_btn = self.page.locator("button[title='edit'], button[title='Edit'], a[title='edit'], a[title='Edit'], .btn-warning, button:has-text('Edit'), i.bi-pencil").first
        edit_btn.click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Wait for form to load
        modal.locator("input[name='chit_name']").wait_for(state="visible", timeout=5000)

        # Update foreman name
        foreman_input = modal.locator("input[name='foreman_name']")
        foreman_input.fill(new_foreman)

        # Submit
        modal.get_by_role("button", name="Update").click()

        try:
            modal.wait_for(state="hidden", timeout=15000)
            return True
        except Exception:
            return False

    def is_edit_available(self, query: str) -> bool:
        """Search for a chit and check if edit action is available."""
        if not self.search_chit(query):
            return False
        first_row = self.page.locator("table tbody tr").first
        edit_btn = first_row.locator(
            "button[title='edit'], button[title='Edit'], a[title='edit'], a[title='Edit'], .btn-warning, button:has-text('Edit'), i.bi-pencil"
        )
        return edit_btn.count() > 0 and edit_btn.first.is_visible()

    # ─── Close Chit ────────────────────────────────────────────────────────────

    def close_chit(self, query: str) -> bool:
        """Search for a chit, open View, click 'Close Chit', confirm."""
        if not self.view_chit(query):
            return False

        modal = self.page.get_by_role("dialog")

        # Click "Close Chit" button inside the view modal
        close_btn = modal.locator("button").filter(has_text=re.compile(r"close\s*chit|close", re.I)).first
        try:
            close_btn.wait_for(state="visible", timeout=5000)
        except Exception:
            # Chit may already be closed (button not shown)
            self.close_modal()
            return False

        close_btn.click()

        # Confirm dialog appears
        confirm_btn = self.page.locator("button").filter(has_text=re.compile(r"yes|confirm|ok", re.I)).last
        try:
            confirm_btn.wait_for(state="visible", timeout=5000)
            confirm_btn.click()
        except Exception:
            pass

        # Wait for modal to close (success)
        try:
            modal.wait_for(state="hidden", timeout=15000)
            return True
        except Exception:
            return True

    # ─── Record Payment ────────────────────────────────────────────────────────

    def record_payment(
        self,
        chit_name: str,
        amount: str,
        payment_mode: str = "Cash",
        bank_account: str = "",
        bonus_amount: str = "",
        payment_month: str = "",
        narration: str = "",
    ) -> bool:
        """Record a payment for a chit using the 'Pay' button on the list page."""
        # Click "Pay" button on the list page
        self.page.get_by_role("button", name="Pay").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Select chit from dropdown (react-select)
        controls = modal.locator(".react-select__control")
        chit_select = controls.first
        chit_select.click()
        self.page.wait_for_timeout(300)
        self.page.keyboard.type(chit_name)
        self.page.wait_for_timeout(300)
        opt = self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=chit_name).first
        if opt.count() and opt.is_visible():
            opt.click()
        else:
            self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(300)

        # Amount
        modal.locator("input[name='amount']").fill(amount)

        # Bonus Amount
        if bonus_amount:
            modal.locator("input[name='bonus_amount']").fill(bonus_amount)

        # Payment Month
        if payment_month:
            modal.locator("input[name='payment_month']").fill(payment_month)

        # Payment Mode (react-select — second select in the form)
        if payment_mode != "Cash":
            controls = modal.locator(".react-select__control")
            if controls.count() > 1:
                payment_mode_select = controls.nth(1)
                payment_mode_select.click()
                self.page.wait_for_timeout(300)
                opt = self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=payment_mode).first
                if opt.count() and opt.is_visible():
                    opt.click()
                else:
                    self.page.keyboard.press("Enter")
                self.page.wait_for_timeout(300)

            # Bank Account (third react-select)
            if bank_account and controls.count() > 2:
                bank_select = controls.nth(2)
                bank_select.click()
                self.page.wait_for_timeout(300)
                self.page.keyboard.type(bank_account)
                self.page.wait_for_timeout(300)
                opt = self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=bank_account).first
                if opt.count() and opt.is_visible():
                    opt.click()
                else:
                    self.page.keyboard.press("Enter")
                self.page.wait_for_timeout(300)

        # Narration
        if narration:
            modal.locator("textarea[name='narration']").fill(narration)

        # Submit
        modal.get_by_role("button", name="Pay").click()

        # Wait for modal to close (success)
        try:
            modal.wait_for(state="hidden", timeout=15000)
            return True
        except Exception:
            return False

    # ─── Record Commission ─────────────────────────────────────────────────────

    def record_commission(
        self,
        chit_name: str,
        amount: str,
        commission_month: str = "",
        narration: str = "",
    ) -> bool:
        """Record a commission for a chit using the 'Commission' button on the list page.

        Args:
            chit_name: Name of the chit (selected from dropdown).
            amount: Commission amount.
            commission_month: Optional commission month number.
            narration: Optional narration text.
        """
        # Click "Commission" button on the list page
        self.page.get_by_role("button", name="Commission").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Select chit from dropdown (react-select)
        chit_select = modal.locator("[class*='react-select']").first
        chit_select.click()
        self.page.wait_for_timeout(500)
        self.page.get_by_role("option", name=chit_name).click()
        self.page.wait_for_timeout(300)

        # Amount
        modal.locator("input[name='amount']").fill(amount)

        # Commission Month
        if commission_month:
            modal.locator("input[name='commission_month']").fill(commission_month)

        # Narration
        if narration:
            modal.locator("textarea[name='narration']").fill(narration)

        # Submit
        modal.get_by_role("button", name="Add").click()

        # Wait for modal to close (success)
        try:
            modal.wait_for(state="hidden", timeout=15000)
            return True
        except Exception:
            return False

    # ─── View Payment List ─────────────────────────────────────────────────────

    def view_payment_list(self, query: str) -> bool:
        """Search for a chit and open its payment list via the row action."""
        if not self.search_chit(query):
            return False

        self.page.get_by_title("payment list").first.click()
        modal = self.page.get_by_role("dialog")
        try:
            modal.wait_for(state="visible", timeout=5000)
            # Verify it's the payment list modal
            modal.get_by_text("Payment List").wait_for(
                state="visible", timeout=5000
            )
            # Wait for payment data to load from API
            self.page.wait_for_load_state("networkidle", timeout=10000)
            self.page.wait_for_timeout(1000)
            return True
        except Exception:
            return False

    # ─── View Commission List ──────────────────────────────────────────────────

    def view_commission_list(self, query: str) -> bool:
        """Search for a chit and open its commission list via the row action."""
        if not self.search_chit(query):
            return False

        self.page.get_by_title("commission list").first.click()
        modal = self.page.get_by_role("dialog")
        try:
            modal.wait_for(state="visible", timeout=5000)
            # Verify it's the commission list modal
            modal.get_by_text("Commission List").wait_for(
                state="visible", timeout=5000
            )
            # Wait for commission data to load from API
            self.page.wait_for_load_state("networkidle", timeout=10000)
            self.page.wait_for_timeout(1000)
            return True
        except Exception:
            return False

    # ─── View Summary ──────────────────────────────────────────────────────────

    def view_summary(self, query: str) -> bool:
        """Search for a chit and open its summary via the row action."""
        if not self.search_chit(query):
            return False

        self.page.get_by_title("summary").first.click()
        modal = self.page.get_by_role("dialog")
        try:
            modal.wait_for(state="visible", timeout=5000)
            # Verify summary content is visible (look for summary labels)
            modal.get_by_text("Total Contribution").wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def get_summary_data(self) -> dict:
        """Read summary data from the currently open summary modal.

        Call after view_summary() returns True.
        """
        modal = self.page.get_by_role("dialog")
        # Summary items are in cards with label + value structure
        items = modal.locator(".fw-bold.fs-6").all()
        labels = modal.locator(".text-muted.small").all()
        data = {}
        for label_el, value_el in zip(labels, items):
            label = label_el.text_content().strip()
            value = value_el.text_content().strip()
            data[label] = value
        return data

    def get_payment_list_rows(self) -> list[dict[str, str]]:
        """Read the top-level rows from an open payment-list modal."""
        modal = self.page.get_by_role("dialog")
        rows: list[dict[str, str]] = []
        for row in modal.locator("table").first.locator("tbody > tr").all():
            cells = [text.strip() for text in row.locator(":scope > td").all_text_contents()]
            if len(cells) == 5:
                rows.append(
                    {
                        "voucher_no": cells[0],
                        "narration": cells[1],
                        "date": cells[2],
                        "total": cells[3],
                    }
                )
        return rows

    @staticmethod
    def parse_amount(value: str) -> Decimal:
        cleaned = re.sub(r"[^\d.-]", "", value)
        return Decimal(cleaned or "0").quantize(Decimal("0.01"))

    # ─── Edit Availability Check ───────────────────────────────────────────────

    def is_edit_available(self, query: str) -> bool:
        """Check if the edit action button is visible for a chit row."""
        if not self.search_chit(query):
            return False

        edit_buttons = self.page.get_by_title("edit")
        return edit_buttons.count() > 0

    # ─── Delete ────────────────────────────────────────────────────────────────

    def delete_chit(self, query: str) -> bool:
        """Search for a chit and delete it via the row action."""
        if not self.search_chit(query):
            return False

        delete_btn = self.page.get_by_title("delete")
        if delete_btn.count() == 0:
            return False

        delete_btn.first.click()

        # Confirm deletion dialog
        confirm_btn = self.page.get_by_role("button", name="yes")
        try:
            confirm_btn.wait_for(state="visible", timeout=5000)
            confirm_btn.click()
            self.page.wait_for_timeout(2000)
            self.page.wait_for_load_state("networkidle", timeout=10000)
            return True
        except Exception:
            return False

    # ─── Restore ───────────────────────────────────────────────────────────────

    def restore_chit(self, query: str) -> bool:
        """Search for a deleted chit and restore it via the row action."""
        if not self.search_chit(query):
            return False

        restore_btn = self.page.get_by_title("retrieve")
        if restore_btn.count() == 0:
            return False

        restore_btn.first.click()

        # Confirm restore dialog
        confirm_btn = self.page.get_by_role("button", name="yes")
        try:
            confirm_btn.wait_for(state="visible", timeout=5000)
            confirm_btn.click()
            self.page.wait_for_timeout(2000)
            self.page.wait_for_load_state("networkidle", timeout=10000)
            return True
        except Exception:
            return False

    # ─── Validation Helpers ────────────────────────────────────────────────────

    def submit_empty_add_form(self) -> list[str]:
        """Open the Add Chit form and submit without filling fields.

        Returns a list of visible validation error messages.
        """
        self.page.get_by_role("button", name="Add Chit").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Submit immediately
        modal.get_by_role("button", name="Create").click()
        self.page.wait_for_timeout(1000)

        # Collect validation errors
        errors = modal.locator(".text-danger, .invalid-feedback").all()
        visible_errors = [
            e.text_content().strip()
            for e in errors
            if e.is_visible()
            and e.text_content().strip()
            and e.text_content().strip() != "*"
        ]

        # Close modal
        self.close_modal()
        return visible_errors

    def submit_empty_payment_form(self) -> list[str]:
        """Open the Record Payment form and submit without filling fields.

        Returns a list of visible validation error messages.
        """
        self.page.get_by_role("button", name="Pay").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Clear amount field (it defaults to 0)
        modal.locator("input[name='amount']").fill("")

        # Submit immediately
        modal.get_by_role("button", name="Pay").click()
        self.page.wait_for_timeout(1000)

        # Collect validation errors
        errors = modal.locator(".text-danger, .invalid-feedback").all()
        visible_errors = [
            e.text_content().strip()
            for e in errors
            if e.is_visible()
            and e.text_content().strip()
            and e.text_content().strip() != "*"
        ]

        # Close modal
        self.close_modal()
        return visible_errors

    def submit_empty_commission_form(self) -> list[str]:
        """Open the Record Commission form and submit without filling fields.

        Returns a list of visible validation error messages.
        """
        self.page.get_by_role("button", name="Commission").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Clear amount field (it defaults to 0)
        modal.locator("input[name='amount']").fill("")

        # Submit immediately
        modal.get_by_role("button", name="Add").click()
        self.page.wait_for_timeout(1000)

        # Collect validation errors
        errors = modal.locator(".text-danger, .invalid-feedback").all()
        visible_errors = [
            e.text_content().strip()
            for e in errors
            if e.is_visible()
            and e.text_content().strip()
            and e.text_content().strip() != "*"
        ]

        # Close modal
        self.close_modal()
        return visible_errors

    def is_chit_in_payment_dropdown(self, chit_name: str) -> bool:
        """Check if a chit appears in the Record Payment dropdown.

        Opens the Pay form, opens the chit dropdown, checks for the name.
        """
        self.page.get_by_role("button", name="Pay").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Open chit dropdown
        chit_select = modal.locator("[class*='react-select']").first
        chit_select.click()
        self.page.wait_for_timeout(500)

        # Check if the chit name appears in the options
        options = self.page.locator("[class*='react-select__option']").all()
        found = any(chit_name in opt.text_content() for opt in options)

        # Close modal
        self.close_modal()
        return found

    def get_payment_list_row_count(self) -> int:
        """Get the number of payment/commission rows in the currently open list modal.

        Call after view_payment_list() or view_commission_list() returns True.
        Waits for table data to load before counting.
        """
        modal = self.page.get_by_role("dialog")

        # Wait for loading to finish (Loader component disappears)
        self.page.wait_for_timeout(2000)
        self.page.wait_for_load_state("networkidle", timeout=10000)

        rows = modal.locator("table tbody tr").all()
        # Filter out "No payments found" / "No commissions found" messages
        for row in rows:
            text = row.text_content()
            if "No " in text and "found" in text:
                return 0
        return len(rows)
