from __future__ import annotations

import re

from playwright.sync_api import Page, Response, expect

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


class RacksPage(BasePage):
    PATH = "/racks"

    def __init__(self, page: Page, tenant: Tenant = RETAIL) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign racks_url directly.
    @property
    def racks_url(self) -> str:
        return self.url

    @racks_url.setter
    def racks_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Rack")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/racks(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/racks(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/racks/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method == "PUT"
            and re.search(r"/racks/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/racks/\d+(?:\?|$)", response.url) is not None
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

    def is_racks_visible(self) -> bool:
        return self.add_button.is_visible()

    def add_rack(
        self,
        name: str,
        code: str,
        branch_name: str,
        description: str | None = None,
        sort_order: str | None = None,
    ) -> None:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        modal.locator('input[name="name"]').fill(name)
        modal.locator('input[name="code"]').fill(code)

        modal.locator(".react-select__input-container").click()
        self.page.get_by_role(
            "option", name=branch_name, exact=True
        ).click()

        if sort_order is not None:
            modal.locator('input[name="sort_order"]').fill(sort_order)

        if description:
            modal.get_by_role(
                "button", name="Add Description"
            ).click()
            modal.locator('textarea[name="description"]').fill(description)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_create_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role("button", name="Create").click()

        assert response_info.value.status in (200, 201), (
            f"Rack create API returned {response_info.value.status}"
        )
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)

    def validate_duplicate_rack(
        self, name: str, code: str, branch_name: str
    ) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        modal.locator('input[name="name"]').fill(name)
        modal.locator('input[name="code"]').fill(code)
        modal.locator(".react-select__input-container").click()
        self.page.get_by_role(
            "option", name=branch_name, exact=True
        ).click()

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Create").click()

        return response_info.value.status == 422 and has_validation_feedback(
            self.page,
            r"already been taken",
            r"already exists",
            r"duplicate",
        )

    def validate_required_fields(self) -> bool:
        submitted_requests = []

        def record_submission(request):
            if (
                request.method == "POST"
                and re.search(r"/racks(?:\?|$)", request.url)
            ):
                submitted_requests.append(request)

        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.page.on("request", record_submission)
        try:
            modal.get_by_role("button", name="Create").click()
            for message in (
                "Rack Name is required",
                "Rack Code is required",
                "Branch is required",
            ):
                modal.get_by_text(message, exact=True).wait_for(
                    state="visible", timeout=UI_TIMEOUT
                )
        finally:
            self.page.remove_listener("request", record_submission)

        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return not submitted_requests

    def search_rack(self, name: str) -> bool:
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

    def view_rack(
        self,
        name: str,
        *,
        expected_code: str | None = None,
        expected_branch: str | None = None,
        expected_sort_order: str | None = None,
        expected_description: str | None = None,
    ) -> bool:
        if not self.search_rack(name):
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
                expected_code,
                expected_branch,
                expected_sort_order,
                expected_description,
            ):
                if expected_value is not None:
                    modal.get_by_text(
                        expected_value, exact=True
                    ).first.wait_for(
                        state="visible", timeout=UI_TIMEOUT
                    )
            text_visible = True
        except Exception:
            text_visible = False

        modal.get_by_role("button", name="Back to List").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return text_visible

    def edit_rack(
        self,
        old_name: str,
        new_name: str,
        *,
        new_code: str | None = None,
        new_description: str | None = None,
        new_sort_order: str | None = None,
    ) -> bool:
        if not self.search_rack(old_name):
            return False

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(old_name).get_by_title("edit").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        name_input = modal.locator('input[name="name"]')
        expect(name_input).to_have_value(old_name, timeout=LIST_TIMEOUT)
        name_input.fill(new_name)
        if new_code is not None:
            modal.locator('input[name="code"]').fill(new_code)
        if new_sort_order is not None:
            modal.locator('input[name="sort_order"]').fill(new_sort_order)
        if new_description is not None:
            description = modal.locator('textarea[name="description"]')
            if not description.is_visible():
                modal.get_by_role(
                    "button", name="Add Description"
                ).click()
            description.fill(new_description)

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

    def delete_rack(self, name: str) -> bool:
        if not self.search_rack(name):
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
                modal.get_by_role("button", name="Delete Rack").click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def retrieve_rack(self, name: str) -> bool:
        if not self.search_rack(name):
            return False

        self._row(name).locator(RETRIEVE_ICON_BUTTON).click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role("button", name="Retrieve Rack").click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def is_rack_active(self, name: str) -> bool:
        if not self.search_rack(name):
            return False
        try:
            self._row(name).locator(DELETE_ICON_BUTTON).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False
