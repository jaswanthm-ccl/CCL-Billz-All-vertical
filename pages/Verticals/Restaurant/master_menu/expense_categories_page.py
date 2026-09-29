"""Restaurant Expense Categories page object."""

import re

from playwright.sync_api import Page, Response

from pages.common.form_page import has_validation_feedback
from pages.master_menu.expense_categories_page import (
    ExpenseCategoriesPage as SharedExpenseCategoriesPage,
)
from utils.constants import LIST_TIMEOUT, UI_TIMEOUT
from utils.tenants import RESTAURANT, Tenant


class ExpenseCategoriesPage(SharedExpenseCategoriesPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
        self.selected_expense_group = ""

    @property
    def expense_group_control(self):
        return self.dialog.locator(".react-select__control").first

    def _select_expense_group(self, preferred: str | None = None) -> str:
        self.expense_group_control.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.expense_group_control.click()
        options = self.page.locator(".react-select__option")
        options.first.wait_for(state="visible", timeout=UI_TIMEOUT)

        option_texts = [text.strip() for text in options.all_inner_texts()]
        selectable = [text for text in option_texts if text.lower() != "bank"]
        if not selectable:
            raise AssertionError("No non-Bank Expense Group is available")

        selected = preferred if preferred in selectable else selectable[0]
        options.filter(has_text=re.compile(f"^{re.escape(selected)}$", re.I)).first.click()
        self.selected_expense_group = selected
        return selected

    def add_expense_category(
        self,
        name: str,
        description: str | None = None,
        sort_order: int | str | None = None,
        expense_group: str | None = None,
    ) -> Response:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self._select_expense_group(expense_group)
        self.name_input.fill(name)
        if description is not None:
            self.description_input.fill(description)
        if sort_order is not None:
            self.sort_order_input.fill(str(sort_order))

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Create", exact=True).click()

        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value

    def row_has_expense_group(self, name: str, expense_group: str) -> bool:
        return self.search_expense_category(name) and self._row(name).get_by_text(
            expense_group, exact=True
        ).is_visible()

    def validate_required_fields(self) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        requests: list[str] = []

        def capture(request) -> None:
            if request.method == "POST" and re.search(
                r"/expense-categories(?:\?|$)", request.url
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
            name_error = has_validation_feedback(
                self.dialog, r"Category Name is required"
            )
            group_error = has_validation_feedback(
                self.dialog, r"Expense Group is required"
            )
        finally:
            self.page.remove_listener("request", capture)

        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return name_error and group_error and not requests

    def validate_bank_group_excluded(self) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.expense_group_control.click()
        options = self.page.locator(".react-select__option")
        options.first.wait_for(state="visible", timeout=UI_TIMEOUT)
        option_texts = [text.strip().lower() for text in options.all_inner_texts()]
        bank_is_absent = "bank" not in option_texts
        self.page.keyboard.press("Escape")
        self.dialog.get_by_role(
            "button", name="Cancel", exact=True
        ).click(force=True)
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return bank_is_absent

    def validate_duplicate_category(self, name: str) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self._select_expense_group()
        self.name_input.fill(name)

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Create", exact=True).click()

        rejected = response_info.value.status in {400, 409, 422}
        feedback = has_validation_feedback(
            self.dialog,
            r"already been taken",
            r"already exists",
            r"duplicate",
        )
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return rejected and feedback
