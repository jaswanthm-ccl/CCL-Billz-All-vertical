from __future__ import annotations

from playwright.sync_api import Page

from utils.constants import BASE_URL

LEDGERS_URL = f"{BASE_URL}/ledgers"


class LedgersPage:
    """Page object for the Ledgers module (/ledgers).

    Ledgers are auto-created when Customers, Suppliers, Bank Accounts are added.
    The list page shows all ledger accounts with edit capability.

    Table columns: NAME, TYPE, BRANCH, ACCOUNT GROUP, OPENING BALANCE, BALANCE, Actions
    Search: placeholder='Search ledgers...' (searches name, type, branch name)
    Filters: None
    Edit: opening_balance, opening_balance_type (Dr/Cr), account_group_id
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = LEDGERS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def is_ledgers_visible(self) -> bool:
        """Verify the ledgers page loaded."""
        try:
            self.page.get_by_text("ledger List").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    # ─── Table ─────────────────────────────────────────────────────────────────

    def get_row_count(self) -> int:
        """Return the number of visible rows."""
        try:
            self.page.locator("table tbody tr").first.wait_for(
                state="visible", timeout=5000
            )
            return self.page.locator("table tbody tr").count()
        except Exception:
            return 0

    def get_first_row_data(self) -> dict:
        """Read data from the first row.

        Returns dict with keys: name, type, branch, account_group, opening_balance, balance.
        """
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=5000)
        cells = row.locator("td").all()

        # Columns: NAME, TYPE, BRANCH, ACCOUNT GROUP, OPENING BALANCE, BALANCE, Actions
        return {
            "name": cells[0].text_content().strip() if len(cells) > 0 else "",
            "type": cells[1].text_content().strip() if len(cells) > 1 else "",
            "branch": cells[2].text_content().strip() if len(cells) > 2 else "",
            "account_group": cells[3].text_content().strip() if len(cells) > 3 else "",
            "opening_balance": cells[4].text_content().strip() if len(cells) > 4 else "",
            "balance": cells[5].text_content().strip() if len(cells) > 5 else "",
        }

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_ledger(self, query: str) -> bool:
        """Search ledgers by name, type, or branch name.

        SearchBar is live (onChange debounced) — no Enter key needed.
        We clear first, then type, then wait for the API to respond.
        """
        search_box = self.page.get_by_placeholder("Search ledgers...")
        search_box.fill("")
        self.page.wait_for_timeout(1000)
        search_box.fill(query)
        # Wait for debounce + API call + render
        self.page.wait_for_timeout(2000)
        self.page.wait_for_load_state("networkidle", timeout=10000)
        try:
            first_row = self.page.locator("table tbody tr").first
            first_row.wait_for(state="visible", timeout=5000)
            text = first_row.text_content()
            return "No ledgers found" not in text
        except Exception:
            return False

    def search_and_get_first_row(self, query: str) -> dict:
        """Search and return the first result row data."""
        self.search_ledger(query)
        return self.get_first_row_data()

    # ─── Edit ──────────────────────────────────────────────────────────────────

    def edit_ledger(self, name: str, opening_balance: str, balance_type: str = "dr") -> bool:
        """Search for a ledger by name, click edit, update opening balance.

        Args:
            name: Ledger name to search and edit.
            opening_balance: New opening balance value.
            balance_type: 'dr' (Debit) or 'cr' (Credit).

        Returns True if update succeeded.
        """
        # Search for the ledger
        if not self.search_ledger(name):
            return False

        # Click edit on the first matching row
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=5000)
        row.get_by_title("edit").first.click()

        # Wait for the edit modal
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Wait for form to load (has a Loader)
        try:
            modal.locator("form").wait_for(state="visible", timeout=10000)
        except Exception:
            pass

        # Fill opening balance
        balance_input = modal.locator("input[name='opening_balance']")
        balance_input.fill(opening_balance)

        # Select balance type (Dr/Cr) - it's a react-select
        type_select = modal.locator("input[name='opening_balance_type']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        type_select.click()
        self.page.wait_for_timeout(300)

        label = "DR" if balance_type == "dr" else "CR"
        self.page.get_by_role("option", name=label).click()
        self.page.wait_for_timeout(300)

        # Click Update
        modal.get_by_role("button", name="Update").click()

        # If opening balance changed, a confirm modal appears
        try:
            confirm = self.page.get_by_text("Confirm opening balance change")
            confirm.wait_for(state="visible", timeout=3000)
            # Click Update in confirm modal
            self.page.get_by_role("button", name="Update").nth(1).click()
        except Exception:
            # No confirm needed (balance didn't change or already same)
            pass

        # Wait for success toast
        try:
            self.page.get_by_text("Ledger updated successfully").first.wait_for(
                state="visible", timeout=10000
            )
            modal.wait_for(state="hidden", timeout=5000)
            return True
        except Exception:
            return False
