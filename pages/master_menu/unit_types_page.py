from __future__ import annotations

import re

from playwright.sync_api import Page, Response, expect

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


class UnitTypesPage(BasePage):
    PATH = "/unit-types"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign unit_types_url directly.
    @property
    def unit_types_url(self) -> str:
        return self.url

    @unit_types_url.setter
    def unit_types_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Unit Type")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def name_input(self):
        return self.dialog.get_by_role(
            "textbox", name="Enter unit type name"
        )

    @property
    def symbol_input(self):
        return self.dialog.get_by_role(
            "textbox", name=re.compile(r"Enter unit symbol")
        )

    @property
    def description_input(self):
        return self.dialog.get_by_role(
            "textbox", name="Enter unit type description"
        )

    @property
    def sort_order_input(self):
        return self.dialog.locator('input[name="sort_order"]')

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/unit-types(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/unit-types(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/unit-types/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method == "PUT"
            and re.search(r"/unit-types/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/unit-types/\d+(?:\?|$)", response.url)
            is not None
        )

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def navigate(self) -> None:
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            self.page.goto(self.url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_unit_types_visible(self) -> bool:
        return self.add_button.is_visible()

    def add_unit_type(
        self,
        name: str,
        unit: str,
        description: str,
        sort_order: str | int | None = None,
    ) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(name)
        self.symbol_input.fill(unit)
        self.description_input.fill(description)
        if sort_order is not None:
            self.sort_order_input.fill(str(sort_order))

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_create_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Create Unit Type"
                ).click()

        if response_info.value.status not in (200, 201):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def search_unit_type(self, name: str) -> bool:
        if self.search_box.input_value() != name:
            with self.page.expect_response(
                self._is_list_response, timeout=LIST_TIMEOUT
            ):
                self.search_box.fill(name)
        try:
            self._row(name).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False

    def view_unit_type(
        self,
        name: str,
        *,
        expected_symbol: str | None = None,
        expected_description: str | None = None,
        expected_sort_order: str | int | None = None,
    ) -> bool:
        if not self.search_unit_type(name):
            return False

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(name).get_by_title("view").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        try:
            for expected_value in (
                name,
                expected_symbol,
                expected_description,
                expected_sort_order,
            ):
                if expected_value is not None:
                    modal.get_by_text(
                        str(expected_value), exact=True
                    ).first.wait_for(
                        state="visible", timeout=UI_TIMEOUT
                    )
            values_persisted = True
        except Exception:
            values_persisted = False

        modal.get_by_role("button", name="Close").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return values_persisted

    def edit_unit_type(
        self,
        old_name: str,
        new_name: str,
        new_unit: str,
        new_description: str,
        new_sort_order: str | int,
    ) -> bool:
        if not self.search_unit_type(old_name):
            return False

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(old_name).get_by_title("edit").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        expect(self.name_input).to_have_value(
            old_name, timeout=LIST_TIMEOUT
        )

        self.name_input.fill(new_name)
        self.symbol_input.fill(new_unit)
        self.description_input.fill(new_description)
        self.sort_order_input.fill(str(new_sort_order))

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_update_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Update Unit Type"
                ).click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def delete_unit_type(self, name: str) -> bool:
        if not self.search_unit_type(name):
            return False

        self._row(name).locator(DELETE_ICON_BUTTON).click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Delete Unit Type"
                ).click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def retrieve_unit_type(self, name: str) -> bool:
        if not self.search_unit_type(name):
            return False

        retrieve_button = self._row(name).locator(RETRIEVE_ICON_BUTTON)
        retrieve_button.wait_for(state="visible", timeout=UI_TIMEOUT)
        retrieve_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Retrieve Unit Type"
                ).click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def is_unit_type_active(self, name: str) -> bool:
        if not self.search_unit_type(name):
            return False
        try:
            self._row(name).locator(DELETE_ICON_BUTTON).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False

    def validate_required_fields(self) -> bool:
        submitted_requests = []

        def record_submission(request):
            if (
                request.method == "POST"
                and re.search(r"/unit-types(?:\?|$)", request.url)
            ):
                submitted_requests.append(request)

        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.page.on("request", record_submission)
        try:
            modal.get_by_role(
                "button", name="Create Unit Type"
            ).click()
            for message in (
                "Name is required",
                "Symbol is required",
                "Description is required",
            ):
                modal.get_by_text(message, exact=True).wait_for(
                    state="visible", timeout=UI_TIMEOUT
                )
        finally:
            self.page.remove_listener("request", record_submission)

        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return not submitted_requests

    def validate_invalid_sort_order(
        self, value: str, expected_message: str
    ) -> bool:
        submitted_requests = []

        def record_submission(request):
            if (
                request.method == "POST"
                and re.search(r"/unit-types(?:\?|$)", request.url)
            ):
                submitted_requests.append(request)

        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill("Validation Unit")
        self.symbol_input.fill("VU")
        self.description_input.fill("Sort order validation")
        self.sort_order_input.fill(value)

        self.page.on("request", record_submission)
        try:
            modal.get_by_role(
                "button", name="Create Unit Type"
            ).click()
            modal.get_by_text(
                expected_message, exact=True
            ).wait_for(state="visible", timeout=UI_TIMEOUT)
        finally:
            self.page.remove_listener("request", record_submission)

        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return not submitted_requests

    def validate_duplicate_unit(
        self, name: str, unit: str, description: str
    ) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(name)
        self.symbol_input.fill(unit)
        self.description_input.fill(description)

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role(
                "button", name="Create Unit Type"
            ).click()

        return response_info.value.status == 422 and has_validation_feedback(
            self.page,
            r"already been taken",
            r"already exists",
            r"duplicate",
        )
