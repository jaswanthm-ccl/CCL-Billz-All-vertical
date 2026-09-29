from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from pages.common.form_page import has_validation_feedback
from utils.constants import (
    ENQUIRY_TYPES_URL,
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class EnquiryTypesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.enquiry_types_url = ENQUIRY_TYPES_URL

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Enquiry Type")

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
    def notes_input(self):
        return self.dialog.locator('textarea[name="notes"]')

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"xhr", "fetch"}
            and re.search(r"/enquiry-types(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/enquiry-types(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/enquiry-types/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(r"/enquiry-types/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/enquiry-types/\d+(?:\?|$)", response.url)
            is not None
        )

    def navigate(self) -> None:
        self.page.goto(self.enquiry_types_url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_enquiry_types_visible(self) -> bool:
        return self.add_button.is_visible()

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def is_enquiry_type_active(self, name: str) -> bool:
        if not self.search_enquiry_type(name):
            return False
        try:
            self._row(name).locator(DELETE_ICON_BUTTON).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False

    def add_enquiry_type(
        self,
        name: str,
        notes: str | None = None,
        sort_order: int | str | None = None,
    ) -> Response:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(name)
        if notes is not None:
            self.notes_input.fill(notes)
        if sort_order is not None:
            self.sort_order_input.fill(str(sort_order))
        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value

    def search_enquiry_type(self, name: str) -> bool:
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

    def view_enquiry_type(
        self, name: str, notes: str, sort_order: int | str
    ) -> bool:
        assert self.search_enquiry_type(name)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(name).get_by_title("view").click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        visible = all(
            self.dialog.get_by_text(value, exact=True).count() > 0
            for value in (name, notes, str(sort_order))
        )
        self.dialog.get_by_role("button", name="Back to List").click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return visible

    def edit_enquiry_type(
        self,
        old_name: str,
        new_name: str,
        notes: str,
        sort_order: int | str,
    ) -> bool:
        assert self.search_enquiry_type(old_name)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(old_name).get_by_title("edit").click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(new_name)
        self.notes_input.fill(notes)
        self.sort_order_input.fill(str(sort_order))
        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Update", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 201, 204}

    def get_edit_values(self, name: str) -> dict[str, str]:
        assert self.search_enquiry_type(name)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(name).get_by_title("edit").click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.wait_for(state="visible", timeout=UI_TIMEOUT)
        values = {
            "name": self.name_input.input_value(),
            "notes": self.notes_input.input_value(),
            "sort_order": self.sort_order_input.input_value(),
        }
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return values

    def delete_enquiry_type(self, name: str) -> bool:
        assert self.search_enquiry_type(name)
        self._row(name).locator(DELETE_ICON_BUTTON).click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Delete Enquiry").click()
        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 204}

    def retrieve_enquiry_type(self, name: str) -> bool:
        assert self.search_enquiry_type(name)
        button = self._row(name).locator(RETRIEVE_ICON_BUTTON)
        button.wait_for(state="visible", timeout=UI_TIMEOUT)
        button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Retrieve Enquiry").click()
        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 204}

    def _validate_client_side(
        self, *, name: str = "", notes: str = "", sort_order: str = ""
    ) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(name)
        self.notes_input.fill(notes)
        self.sort_order_input.fill(sort_order)
        requests: list[str] = []

        def capture(request) -> None:
            if request.method == "POST" and re.search(
                r"/enquiry-types(?:\?|$)", request.url
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
            feedback = has_validation_feedback(
                self.dialog,
                r"Enquiry Name is required",
                r"Notes cannot exceed 1000 characters",
                r"Sort order must be at least 1",
            )
            valid = feedback and not requests
        finally:
            self.page.remove_listener("request", capture)
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return valid

    def validate_required_name(self) -> bool:
        return self._validate_client_side()

    def validate_sort_order_minimum(self) -> bool:
        return self._validate_client_side(name="Valid enquiry type", sort_order="0")

    def validate_notes_max_length(self) -> bool:
        return self._validate_client_side(name="Valid enquiry type", notes="N" * 1001)

    def validate_duplicate_name(self, name: str) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(name)
        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
        rejected = response_info.value.status in {400, 409, 422}
        feedback = has_validation_feedback(
            self.dialog, r"already been taken", r"already exists", r"duplicate"
        )
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return rejected and feedback
