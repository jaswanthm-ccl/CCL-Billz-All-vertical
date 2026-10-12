from __future__ import annotations

from typing import Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response, TimeoutError as PlaywrightTimeoutError

from pages.common.base_page import BasePage
from utils.tenants import Tenant


class ExpensesPage(BasePage):
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

    PATH = "/expenses"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)
        self.last_save_response: Response | None = None

    @property
    def _rows(self):
        return self.page.locator("table tbody tr")

    @staticmethod
    def _is_list_response(response: Response, search: str | None = None) -> bool:
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/expenses")
        ):
            return False
        return search is None or parse_qs(url.query).get("search", [""])[-1] == search

    def _reload_list(self, action: Callable[[], object], search: str | None = None) -> None:
        with self.page.expect_response(lambda r: self._is_list_response(r, search), timeout=15000):
            action()
        self._rows.first.wait_for(state="visible", timeout=10000)

    @staticmethod
    def _is_save_response(response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        if response.request.method == "GET":
            return False
        return path.endswith("/expenses") or "/expenses/" in path + "/"

    def _save(self, action: Callable[[], object]) -> bool:
        """Run submit and wait for POST/PUT under /expenses. False if no request (validation blocked)."""
        self.last_save_response = None
        try:
            with self.page.expect_response(self._is_save_response, timeout=15000) as info:
                action()
        except PlaywrightTimeoutError:
            return False
        self.last_save_response = info.value
        return info.value.ok

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))

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

        if date:
            modal.locator("input[name='date']").fill(date)

        modal.locator("input[name='amount']").fill(amount)

        modal.locator("input[name='expense_category_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=category).click()

        modal.locator("input[name='branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=branch).click()

        modal.locator("input[name='payment_type']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=payment_type).click()

        if payment_type == "Bank Account" and bank_account:
            bank_control = modal.locator("input[name='bank_account_id']").locator(
                "xpath=.."
            ).locator(".react-select__input-container")
            bank_control.wait_for(state="visible", timeout=5000)
            bank_control.click()
            self.page.get_by_role("option", name=bank_account).click()

        if description:
            modal.locator("textarea[name='description']").fill(description)

        if not self._save(modal.get_by_role("button", name="Create").click):
            reply = self.last_save_response.text()[:300] if self.last_save_response else "no request sent"
            toast = self.page.locator(".Toastify__toast").first
            toast_msg = toast.text_content().strip() if toast.is_visible() else ""
            raise AssertionError(f"Expense creation failed: {toast_msg or reply}")
        modal.wait_for(state="hidden", timeout=15000)

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_expense(self, query: str) -> bool:
        """Search expenses by text (searches across category, description, etc)."""
        search_box = self.page.get_by_placeholder("Search...")
        if search_box.input_value() != query:

            def search() -> None:
                search_box.fill(query)
                search_box.press("Enter")

            self._reload_list(search, search=query)
        try:
            self._rows.first.wait_for(state="visible", timeout=5000)
            first_text = self._rows.first.text_content() or ""
            return "No Data Found" not in first_text and "No Expenses found" not in first_text
        except Exception:
            return False

    def get_first_row_data(self) -> dict:
        """Read data from the first row in the expenses table.

        Returns dict with keys: date, category, amount, branch, paid_from, description, status.
        """
        row = self._rows.first
        row.wait_for(state="visible", timeout=5000)
        cells = row.locator("td").all()

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
        toggle = self.page.locator("button.filters-toggle-btn")
        if toggle.count() and toggle.is_visible():
            if toggle.get_attribute("aria-expanded") == "false":
                toggle.click()
                self.page.locator(".filters-section-modern").wait_for(
                    state="visible", timeout=5000
                )
            return
        expand = self.page.get_by_label("Expand filters")
        if expand.count() and expand.is_visible():
            expand.click()
            self.page.locator(".filters-section-modern").wait_for(
                state="visible", timeout=5000
            )

    def filter_by_branch(self, branch_name: str) -> None:
        """Apply branch filter."""
        self._expand_filters()
        branch_input = self.page.locator("input[name='branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        branch_input.click()
        self.page.get_by_role("option", name=branch_name).click()
        self._reload_list(
            lambda: self.page.locator(".filters-section-modern button[type='submit']").click()
        )

    def filter_by_category(self, category_name: str) -> None:
        """Apply category filter."""
        self._expand_filters()
        cat_input = self.page.locator("input[name='expense_category_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        cat_input.click()
        self.page.get_by_role("option", name=category_name).click()
        self._reload_list(
            lambda: self.page.locator(".filters-section-modern button[type='submit']").click()
        )

    def clear_search(self) -> None:
        """Clear the search box."""
        search_box = self.page.get_by_placeholder("Search...")

        def clear() -> None:
            search_box.fill("")
            search_box.press("Enter")

        self._reload_list(clear, search="")
