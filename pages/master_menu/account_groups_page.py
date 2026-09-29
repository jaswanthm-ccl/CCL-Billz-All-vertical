from __future__ import annotations

import re

from playwright.sync_api import Page, Response, expect

from pages.common.base_page import BasePage
from utils.tenants import Tenant
from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class AccountGroupsPage(BasePage):
    PATH = "/account-groups"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign account_groups_url directly.
    @property
    def account_groups_url(self) -> str:
        return self.url

    @account_groups_url.setter
    def account_groups_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Account Group")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/account-groups(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/account-groups(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/account-groups/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method == "PUT"
            and re.search(r"/account-groups/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/account-groups/\d+(?:\?|$)", response.url)
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

        table_button = self.page.get_by_role(
            "button", name="Table", exact=True
        )
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            table_button.click()

    def is_account_group_visible(self) -> bool:
        return self.add_button.is_visible()

    def add_account_group(
        self,
        name: str,
        parent_group: str = "— Root —",
        nature: str | None = None,
    ) -> None:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        modal.get_by_role("textbox", name="Enter Account group name").fill(name)

        if parent_group != "— Root —":
            parent_ctrl = modal.locator("input[name='parent_id']").locator("..").locator(".react-select__input-container")
            if parent_ctrl.count() > 0:
                parent_ctrl.click()
            else:
                modal.locator(".react-select__control").first.click()
            option = self.page.get_by_role("option", name=parent_group, exact=False).first
            option.wait_for(state="visible", timeout=UI_TIMEOUT)
            option.click()
        elif modal.locator(".react-select__control").count() > 0:
            modal.locator(".react-select__control").first.click()
            option = self.page.get_by_role("option", name="— Root —", exact=True)
            if option.count() > 0:
                option.click()

        if nature:
            nature_ctrl = modal.locator("input[name='nature']").locator("..").locator(".react-select__input-container")
            if nature_ctrl.count() > 0:
                nature_ctrl.click()
                self.page.get_by_role("option", name=nature, exact=False).first.click()

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_create_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Create Account Group"
                ).click()

        assert response_info.value.status in (200, 201), (
            f"Account Group create API returned "
            f"{response_info.value.status}"
        )
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)

    def search_account_group(self, name: str) -> bool:
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

    def view_account_group(self, name: str, expected_parent: str | None = None) -> bool:
        if not self.search_account_group(name):
            return False

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(name).get_by_title("view").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        try:
            modal.get_by_text(name, exact=True).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            is_valid = True
            if expected_parent:
                modal.get_by_text(
                    expected_parent, exact=True
                ).first.wait_for(state="visible", timeout=UI_TIMEOUT)
        except Exception:
            is_valid = False

        close_btn = modal.get_by_role("button", name="Close").first
        close_btn.click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_valid

    def edit_account_group(self, old_name: str, new_name: str) -> bool:
        if not self.search_account_group(old_name):
            return False

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(old_name).get_by_title("edit").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        name_input = modal.get_by_role(
            "textbox", name="Enter Account group name"
        )
        expect(name_input).to_have_value(old_name, timeout=LIST_TIMEOUT)
        name_input.fill(new_name)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_update_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Update Account Group"
                ).click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def delete_account_group(self, name: str) -> bool:
        if not self.search_account_group(name):
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
                modal.get_by_role("button", name="Delete").click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def retrieve_account_group(self, name: str) -> bool:
        if not self.search_account_group(name):
            return False

        self._row(name).locator(RETRIEVE_ICON_BUTTON).click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Retrieve").click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def validate_required_fields(self) -> bool:
        self.page.get_by_role("button", name="Add Account Group").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=5000)

        modal.get_by_role("button", name="Create Account Group").click()
        name_err = self.page.get_by_text("Name is required")

        try:
            name_err.wait_for(state="visible", timeout=5000)
            is_valid = True
        except Exception:
            is_valid = False

        self.navigate()
        return is_valid
