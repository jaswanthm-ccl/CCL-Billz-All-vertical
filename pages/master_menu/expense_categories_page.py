from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from pages.common.form_page import has_validation_feedback
from pages.common.base_page import BasePage
from utils.tenants import Tenant
from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class ExpenseCategoriesPage(BasePage):
    PATH = "/expense-categories"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign expense_categories_url directly.
    @property
    def expense_categories_url(self) -> str:
        return self.url

    @expense_categories_url.setter
    def expense_categories_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Expense Category")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def name_input(self):
        return self.dialog.locator('input[name="name"]')

    @property
    def sort_order_input(self):
        return self.dialog.locator('input[name="sort_order"]')

    @property
    def description_input(self):
        return self.dialog.locator('textarea[name="description"]')

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/expense-categories(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/expense-categories(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/expense-categories/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(r"/expense-categories/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/expense-categories/\d+(?:\?|$)", response.url)
            is not None
        )

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_expense_categories_visible(self) -> bool:
        return self.add_button.is_visible()

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def is_category_active(self, name: str) -> bool:
        if not self.search_expense_category(name):
            return False
        try:
            self._row(name).locator(DELETE_ICON_BUTTON).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False

    def add_expense_category(
        self,
        name: str,
        description: str | None = None,
        sort_order: int | str | None = None,
    ) -> Response:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
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

    def search_expense_category(self, name: str) -> bool:
        if self.search_box.input_value() != name:
            with self.page.expect_response(
                self._is_list_response, timeout=LIST_TIMEOUT
            ):
                self.search_box.fill(name)
        try:
            self._row(name).wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def has_view_action(self, name: str) -> bool:
        return (
            self.search_expense_category(name)
            and self._row(name).get_by_title("view").count() > 0
        )

    def edit_expense_category(
        self,
        old_name: str,
        new_name: str,
        description: str,
        sort_order: int | str,
    ) -> bool:
        if not self.search_expense_category(old_name):
            return False
        row = self._row(old_name)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(new_name)
        self.description_input.fill(description)
        self.sort_order_input.fill(str(sort_order))

        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Update", exact=True).click()

        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 201, 204}

    def get_edit_values(self, name: str) -> dict[str, str]:
        assert self.search_expense_category(name)
        row = self._row(name)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.wait_for(state="visible", timeout=UI_TIMEOUT)

        values = {
            "name": self.name_input.input_value(),
            "description": self.description_input.input_value(),
            "sort_order": self.sort_order_input.input_value(),
        }
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return values

    def delete_expense_category(self, name: str) -> bool:
        if not self.search_expense_category(name):
            return False
        self._row(name).locator(DELETE_ICON_BUTTON).click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Delete Category").click()
        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 204}

    def retrieve_expense_category(self, name: str) -> bool:
        if not self.search_expense_category(name):
            return False
        restore_button = self._row(name).locator(RETRIEVE_ICON_BUTTON)
        restore_button.wait_for(state="visible", timeout=UI_TIMEOUT)
        restore_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Retrieve Category").click()
        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 204}

    def validate_required_name(self) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        requests: list[str] = []

        def capture(request) -> None:
            if (
                request.method == "POST"
                and re.search(r"/expense-categories(?:\?|$)", request.url)
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
            feedback = has_validation_feedback(
                self.dialog, r"Category Name is required"
            )
            valid = feedback and not requests
        finally:
            self.page.remove_listener("request", capture)

        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return valid

    def validate_duplicate_category(self, name: str) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
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
