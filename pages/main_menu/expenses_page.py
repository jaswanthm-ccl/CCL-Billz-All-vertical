from __future__ import annotations

import re
from playwright.sync_api import Page

from utils.constants import BASE_URL

EXPENSES_URL = f"{BASE_URL}/expenses"


class ExpensesPage:
    """Page object for the Expenses module (/expenses).

    Form fields (Add Expense modal):
      - date: input[type=date]
      - amount: input[type=number]
      - expense_category_id: React-Select (Category)
      - branch_id: React-Select (Branch)
      - payment_type: React-Select (Cash / Bank Account)
      - bank_account_id: React-Select (only visible when Bank Account selected)
      - description: textarea

    List table columns: DATE, CATEGORY, AMOUNT, BRANCH, PAID FROM, DESCRIPTION, STATUS, Actions
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = EXPENSES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def is_expenses_visible(self) -> bool:
        """Verify the expenses page loaded (Add Expense button present)."""
        try:
            self.page.get_by_role("button", name="Add Expense").wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    # ─── Create ────────────────────────────────────────────────────────────────

    def add_expense(
        self,
        category: str,
        branch: str,
        amount: str,
        payment_type: str = "Cash",
        bank_account: str | None = None,
        description: str = "",
        date: str | None = None,
    ) -> None:
        """Create an expense.

        Args:
            category: Expense category name (react-select option text)
            branch: Branch name (react-select option text)
            amount: Amount as string
            payment_type: 'Cash' or 'Bank Account'
            bank_account: Bank account name (required when payment_type='Bank Account')
            description: Optional description text
            date: Optional date string (YYYY-MM-DD). Defaults to today.
        """
        self.page.get_by_role("button", name="Add Expense").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Date (defaults to today if not provided)
        if date:
            modal.locator("input[name='date']").fill(date)

        # Amount
        modal.locator("input[name='amount']").fill(amount)

        # Category (react-select)
        modal.locator("input[name='expense_category_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=category).click()
        self.page.wait_for_timeout(300)

        # Branch (react-select)
        modal.locator("input[name='branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=branch).click()
        self.page.wait_for_timeout(300)

        # Payment type (react-select)
        modal.locator("input[name='payment_type']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=payment_type).click()
        self.page.wait_for_timeout(500)

        # Bank Account (only appears when payment_type == 'Bank Account')
        if payment_type == "Bank Account" and bank_account:
            modal.locator("input[name='bank_account_id']").locator(
                "xpath=.."
            ).locator(".react-select__input-container").click()
            self.page.get_by_role("option", name=bank_account).click()
            self.page.wait_for_timeout(300)

        # Description
        if description:
            modal.locator("textarea[name='description']").fill(description)

        # Submit
        modal.get_by_role("button", name="Create").click()

        # Wait for success — modal should close on success
        try:
            modal.wait_for(state="hidden", timeout=15000)
        except Exception:
            # Check if there's an error toast
            toast = self.page.locator(".Toastify__toast").first
            if toast.is_visible():
                msg = toast.text_content().strip()
                raise AssertionError(f"Expense creation failed: {msg}")
            raise

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_expense(self, query: str) -> bool:
        """Search expenses by text (searches across category, description, etc)."""
        search_box = self.page.get_by_placeholder("Search...")
        search_box.fill(query)
        search_box.press("Enter")
        self.page.wait_for_load_state("networkidle", timeout=5000)
        try:
            self.page.locator("table tbody tr").first.wait_for(
                state="visible", timeout=5000
            )
            # Verify result doesn't say "No Data Found"
            first_text = self.page.locator("table tbody tr").first.text_content()
            return "No Data Found" not in first_text
        except Exception:
            return False

    def get_first_row_data(self) -> dict:
        """Read data from the first row in the expenses table.

        Returns dict with keys: date, category, amount, branch, paid_from, description, status.
        """
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=5000)
        cells = row.locator("td").all()

        # Table columns: DATE, CATEGORY, AMOUNT, BRANCH, PAID FROM, DESCRIPTION, STATUS, Actions
        return {
            "date": cells[0].text_content().strip() if len(cells) > 0 else "",
            "category": cells[1].text_content().strip() if len(cells) > 1 else "",
            "amount": cells[2].text_content().strip() if len(cells) > 2 else "",
            "branch": cells[3].text_content().strip() if len(cells) > 3 else "",
            "paid_from": cells[4].text_content().strip() if len(cells) > 4 else "",
            "description": cells[5].text_content().strip() if len(cells) > 5 else "",
            "status": cells[6].text_content().strip() if len(cells) > 6 else "",
        }

    def is_table_empty(self) -> bool:
        """Check if the table shows empty/no-data state."""
        try:
            self.page.get_by_text("No Expenses found").wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    # ─── Filters ───────────────────────────────────────────────────────────────

    def _expand_filters(self) -> None:
        """Expand the filters panel by clicking the toggle button."""
        try:
            toggle = self.page.locator("button.filters-toggle-btn")
            if toggle.is_visible():
                # Check if already expanded
                expanded = toggle.get_attribute("aria-expanded")
                if expanded == "false":
                    toggle.click()
                    self.page.wait_for_timeout(500)
        except Exception:
            # Fallback: try aria-label
            try:
                self.page.get_by_label("Expand filters").click()
                self.page.wait_for_timeout(500)
            except Exception:
                pass

    def filter_by_branch(self, branch_name: str) -> None:
        """Apply branch filter."""
        self._expand_filters()
        # The branch filter react-select has a hidden input[name='branch_id']
        branch_input = self.page.locator("input[name='branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        branch_input.click()
        self.page.get_by_role("option", name=branch_name).click()
        self.page.wait_for_timeout(300)
        self.page.locator(".filters-section-modern button[type='submit']").click()
        self.page.wait_for_load_state("networkidle", timeout=5000)

    def filter_by_category(self, category_name: str) -> None:
        """Apply category filter."""
        self._expand_filters()
        # The category filter react-select has a hidden input[name='expense_category_id']
        cat_input = self.page.locator("input[name='expense_category_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        cat_input.click()
        self.page.get_by_role("option", name=category_name).click()
        self.page.wait_for_timeout(300)
        self.page.locator(".filters-section-modern button[type='submit']").click()
        self.page.wait_for_load_state("networkidle", timeout=5000)

    def clear_search(self) -> None:
        """Clear the search box."""
        search_box = self.page.get_by_placeholder("Search...")
        search_box.fill("")
        search_box.press("Enter")
        self.page.wait_for_load_state("networkidle", timeout=5000)
