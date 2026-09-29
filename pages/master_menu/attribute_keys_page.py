from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from pages.common.base_page import BasePage
from pages.common.form_page import has_validation_feedback
from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)
from utils.tenants import Tenant


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class AttributeKeysPage(BasePage):
    PATH = "/attribute-keys"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign attribute_keys_url directly.
    @property
    def attribute_keys_url(self) -> str:
        return self.url

    @attribute_keys_url.setter
    def attribute_keys_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Attribute Keys")

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
            and re.search(r"/attribute-keys(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/attribute-keys(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(r"/attribute-keys/\d+", response.url) is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/attribute-keys/\d+", response.url) is not None
        )

    def navigate(self) -> None:
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            self.page.goto(self.url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_attribute_keys_visible(self) -> bool:
        return self.add_button.is_visible()

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def is_attribute_key_active(self, name: str) -> bool:
        if not self.search_attribute_key(name):
            return False
        row = self._row(name)
        delete_btn = row.locator(DELETE_ICON_BUTTON)
        try:
            delete_btn.wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def is_attribute_key_deleted(self, name: str) -> bool:
        if not self.search_attribute_key(name):
            return False
        return self._row(name).locator(RETRIEVE_ICON_BUTTON).count() > 0

    def ensure_deleted(self, name: str) -> bool:
        """Soft-delete the key unless it is already deleted or absent."""
        self.navigate()
        if not self.search_attribute_key(name):
            return True
        if self._row(name).locator(RETRIEVE_ICON_BUTTON).count() > 0:
            return True
        return self.delete_attribute_key(name)

    def search_attribute_key(self, name: str) -> bool:
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

    def add_attribute_key(
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
            add_desc_btn = modal.get_by_role("button", name="Add Description")
            if add_desc_btn.is_visible():
                add_desc_btn.click()
            self.description_input.fill(description)

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Create").click()

        assert response_info.value.status in (200, 201)
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)

    def view_attribute_key(
        self, name: str, expected_description: str | None = None
    ) -> bool:
        if not self.search_attribute_key(name):
            return False

        row = self._row(name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        row.get_by_title("view").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        try:
            modal.get_by_text(name, exact=True).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            if expected_description:
                modal.get_by_text(expected_description, exact=False).first.wait_for(
                    state="visible", timeout=UI_TIMEOUT
                )
            is_visible = True
        except Exception:
            is_visible = False

        modal.get_by_role("button", name="Back to List").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_visible

    def edit_attribute_key(
        self, old_name: str, new_name: str, new_description: str | None = None
    ) -> bool:
        if not self.search_attribute_key(old_name):
            return False

        row = self._row(old_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        row.get_by_title("edit").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(new_name)
        if new_description is not None and self.description_input.is_visible():
            self.description_input.fill(new_description)

        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Update").click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def delete_attribute_key(self, name: str) -> bool:
        if not self.search_attribute_key(name):
            return False

        row = self._row(name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        row.locator(DELETE_ICON_BUTTON).click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Delete Attribute Key").click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def retrieve_attribute_key(self, name: str) -> bool:
        if not self.search_attribute_key(name):
            return False

        row = self._row(name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        retrieve_btn = row.locator(RETRIEVE_ICON_BUTTON)
        retrieve_btn.wait_for(state="visible", timeout=UI_TIMEOUT)
        retrieve_btn.click()

        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        modal.get_by_role("button", name="Retrieve Attribute Key").click()

        toast = self.page.get_by_text("Retrieved successfully.").first
        try:
            toast.wait_for(state="visible", timeout=UI_TIMEOUT)
            modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
            return True
        except Exception:
            return False

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
                r"Name is required",
                r"Attribute Key Name is required",
                r"field is required",
                r"required",
            )
            api_calls = [
                url
                for url in requests
                if re.search(r"/attribute-keys(?:\?|$)", url)
            ]
            is_valid = has_error and len(api_calls) == 0
        finally:
            self.page.remove_listener("request", listener)

        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_valid
