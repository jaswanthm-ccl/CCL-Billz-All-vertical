from __future__ import annotations

import re

from playwright.sync_api import Page, Response, expect

from pages.common.form_page import has_validation_feedback
from pages.common.base_page import BasePage
from utils.tenants import RETAIL, Tenant
from utils.constants import LIST_TIMEOUT, SETTLED_TIMEOUT, UI_TIMEOUT


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class SacHsnCodePage(BasePage):
    PATH = "/gst-codes"

    def __init__(self, page: Page, tenant: Tenant = RETAIL) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign sac_hsn_url directly.
    @property
    def sac_hsn_url(self) -> str:
        return self.url

    @sac_hsn_url.setter
    def sac_hsn_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add SAC/HSN Code")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def code_input(self):
        return self.dialog.locator('input[name="code"]')

    @property
    def sort_order_input(self):
        return self.dialog.locator('input[name="sort_order"]')

    @property
    def description_input(self):
        return self.dialog.locator('textarea[name="description"]')

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/gst-codes(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/gst-codes(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/gst-codes/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(r"/gst-codes/\d+(?:\?|$)", response.url) is not None
        )

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_sac_hsn_visible(self) -> bool:
        return self.add_button.is_visible()

    def _row(self, code: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(code, exact=True)
        ).first

    def _select_type(self, type_choice: str) -> None:
        self.dialog.locator(".react-select__input-container").first.click()
        self.page.get_by_role("option", name=type_choice, exact=True).click()

    def add_sac_hsn_code(
        self,
        type_choice: str,
        code: str,
        description: str | None = None,
        sort_order: int | str | None = None,
    ) -> Response:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self._select_type(type_choice)
        self.code_input.fill(code)

        if sort_order is not None:
            self.sort_order_input.fill(str(sort_order))
        if description:
            self.dialog.get_by_role("button", name="Add Description").click()
            self.description_input.fill(description)

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Create", exact=True).click()

        response = response_info.value
        expect(self.dialog).to_be_hidden(timeout=LIST_TIMEOUT)
        return response

    def search_sac_hsn_code(self, code: str) -> bool:
        self.search_box.fill(code)
        try:
            with self.page.expect_response(
                self._is_list_response, timeout=LIST_TIMEOUT
            ):
                self.search_box.press("Enter")
        except Exception:
            self.search_box.press("Enter")

        row = self._row(code)
        try:
            row.wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def view_sac_hsn_code(self, code: str) -> bool:
        assert self.search_sac_hsn_code(code)
        row = self._row(code)

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("view").first.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)

        visible = self.dialog.get_by_text(code, exact=True).is_visible()
        self.dialog.get_by_role("button", name="Back").click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return visible

    def edit_sac_hsn_code(
        self,
        old_code: str,
        new_code: str,
        description: str | None = None,
        sort_order: int | str | None = None,
    ) -> bool:
        assert self.search_sac_hsn_code(old_code)
        row = self._row(old_code)

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").first.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.code_input.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.code_input.fill(new_code)
        if sort_order is not None:
            self.sort_order_input.fill(str(sort_order))
        if description is not None:
            if self.description_input.count() == 0:
                self.dialog.get_by_role("button", name="Add Description").click()
            self.description_input.fill(description)

        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Update", exact=True).click()

        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 201}

    def get_edit_values(self, code: str) -> dict[str, str]:
        assert self.search_sac_hsn_code(code)
        row = self._row(code)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").first.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.code_input.wait_for(state="visible", timeout=UI_TIMEOUT)

        values = {
            "code": self.code_input.input_value(),
            "sort_order": self.sort_order_input.input_value(),
            "description": (
                self.description_input.input_value()
                if self.description_input.count()
                else ""
            ),
        }
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return values

    def delete_sac_hsn_code(self, code: str) -> bool:
        assert self.search_sac_hsn_code(code)
        row = self._row(code)
        delete_button = row.locator(DELETE_ICON_BUTTON).first
        delete_button.wait_for(state="visible", timeout=UI_TIMEOUT)
        delete_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.dialog.get_by_role("button", name="Delete Code").click()
        self.page.get_by_text("Deleted successfully.").first.wait_for(
            state="visible", timeout=LIST_TIMEOUT
        )
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def retrieve_sac_hsn_code(self, code: str) -> bool:
        assert self.search_sac_hsn_code(code)
        row = self._row(code)
        restore_button = row.locator(RETRIEVE_ICON_BUTTON).first
        restore_button.wait_for(state="visible", timeout=UI_TIMEOUT)
        restore_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.dialog.get_by_role("button", name="Retrieve Code").click()
        self.page.get_by_text("Retrieved successfully.").first.wait_for(
            state="visible", timeout=LIST_TIMEOUT
        )
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def validate_required_code(self) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        requests: list[str] = []

        def capture(request) -> None:
            if (
                request.method == "POST"
                and re.search(r"/gst-codes(?:\?|$)", request.url)
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
            required = self.dialog.get_by_text("Code is required", exact=True)
            required.wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            is_valid = required.is_visible() and not requests
        finally:
            self.page.remove_listener("request", capture)
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_valid

    def validate_invalid_code(self, code: str, type_choice: str = "SAC") -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self._select_type(type_choice)
        self.code_input.fill(code)
        requests: list[str] = []

        def capture(request) -> None:
            if (
                request.method == "POST"
                and re.search(r"/gst-codes(?:\?|$)", request.url)
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
            feedback = has_validation_feedback(
                self.page,
                r"code.*(?:invalid|valid|numeric|digits|length|characters|required)",
                r"invalid.*code",
                r"code.*(?:maximum|max)",
            )
            return feedback and not requests
        finally:
            self.page.remove_listener("request", capture)

    def validate_invalid_sort_order(self, value: str) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.code_input.fill("123456")
        self.sort_order_input.fill(value)
        requests: list[str] = []

        def capture(request) -> None:
            if (
                request.method == "POST"
                and re.search(r"/gst-codes(?:\?|$)", request.url)
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            self.dialog.get_by_role("button", name="Create", exact=True).click()
            feedback = has_validation_feedback(
                self.page,
                r"sort order.*(?:at least|minimum|min|integer|number)",
            )
            return feedback and not requests
        finally:
            self.page.remove_listener("request", capture)

    def validate_duplicate_sac_hsn_code(
        self, code: str, type_choice: str = "SAC"
    ) -> bool:
        self.add_button.click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self._select_type(type_choice)
        self.code_input.fill(code)

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Create", exact=True).click()

        rejected = response_info.value.status in {400, 409, 422}
        feedback = has_validation_feedback(
            self.page,
            r"already been taken",
            r"already exists",
            r"duplicate",
        )
        return rejected and feedback
