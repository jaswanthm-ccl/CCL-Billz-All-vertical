from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from pages.common.base_page import BasePage
from utils.tenants import RETAIL, Tenant
from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)
from pages.common.form_page import has_validation_feedback


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class CategoriesPage(BasePage):
    PATH = "/categories"

    def __init__(self, page: Page, tenant: Tenant = RETAIL) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign categories_url directly.
    @property
    def categories_url(self) -> str:
        return self.url

    @categories_url.setter
    def categories_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Category")

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
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/categories(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/categories(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/categories/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(r"/categories/\d+", response.url) is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/categories/\d+", response.url) is not None
        )

    def navigate(self) -> None:
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            self.page.goto(self.url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_categories_visible(self) -> bool:
        return self.add_button.is_visible()

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def is_category_active(self, name: str) -> bool:
        if not self.search_category(name):
            return False
        row = self._row(name)
        delete_btn = row.locator(DELETE_ICON_BUTTON)
        try:
            delete_btn.wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def add_category(
        self,
        name: str,
        sort_order: int | str | None = None,
        description: str | None = None,
    ) -> None:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(name)
        if sort_order is not None:
            self.sort_order_input.fill(str(sort_order))
        if description:
            self.description_input.fill(description)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_create_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role("button", name="Create").click()

        assert response_info.value.status in (200, 201)
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)

    def search_category(self, category_name: str) -> bool:
        if self.search_box.input_value() != category_name:
            with self.page.expect_response(
                self._is_list_response, timeout=LIST_TIMEOUT
            ):
                self.search_box.fill(category_name)
        try:
            self._row(category_name).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False

    def view_category(
        self,
        category_name: str,
        expected_description: str | None = None,
        expected_sort_order: str | int | None = None,
    ) -> bool:
        if not self.search_category(category_name):
            return False

        row = self._row(category_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("view").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        try:
            modal.get_by_text(category_name, exact=True).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            if expected_description:
                modal.get_by_text(expected_description, exact=False).first.wait_for(
                    state="visible", timeout=UI_TIMEOUT
                )
            if expected_sort_order is not None:
                modal.get_by_text(str(expected_sort_order), exact=False).first.wait_for(
                    state="visible", timeout=UI_TIMEOUT
                )
            is_visible = True
        except Exception:
            is_visible = False

        modal.get_by_role("button", name="Back to List").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_visible

    def edit_category(
        self,
        old_name: str,
        new_name: str,
        new_sort_order: int | str | None = None,
        new_description: str | None = None,
    ) -> bool:
        if not self.search_category(old_name):
            return False

        row = self._row(old_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(new_name)
        if new_sort_order is not None:
            self.sort_order_input.fill(str(new_sort_order))
        if new_description:
            self.description_input.fill(new_description)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_update_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role("button", name="Update").click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def delete_category(self, category_name: str) -> bool:
        if not self.search_category(category_name):
            return False

        row = self._row(category_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        row.locator(DELETE_ICON_BUTTON).click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Delete Category"
                ).click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def retrieve_category(self, category_name: str) -> bool:
        if not self.search_category(category_name):
            return False

        row = self._row(category_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        retrieve_btn = row.locator(RETRIEVE_ICON_BUTTON)
        retrieve_btn.wait_for(state="visible", timeout=UI_TIMEOUT)
        retrieve_btn.click()

        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Retrieve Category"
                ).click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def validate_required_fields(self) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        requests: list[str] = []
        listener = lambda request: requests.append(request.url)
        self.page.on("request", listener)
        try:
            modal.get_by_role("button", name="Create").click()
            has_error = has_validation_feedback(
                self.page,
                r"Category Name is required",
                r"field is required",
                r"required",
            )
            api_calls = [
                url for url in requests if re.search(r"/categories(?:\?|$)", url)
            ]
            is_valid = has_error and len(api_calls) == 0
        finally:
            self.page.remove_listener("request", listener)

        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_valid

    def validate_duplicate_category(self, name: str) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(name)

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Create").click()

        rejected = response_info.value.status in (400, 409, 422)
        has_error = has_validation_feedback(
            self.page,
            r"already been taken",
            r"already exists",
            r"duplicate",
        )
        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return rejected and has_error
