from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from pages.common.base_page import BasePage
from utils.tenants import RETAIL, Tenant
from utils.constants import (
    SEARCH_DEBOUNCE_MS,
    LIST_TIMEOUT,
    UI_TIMEOUT,
    SETTLED_TIMEOUT,
)
from utils.random_data import generate_random_name, generate_random_description

# ── Selectors ────────────────────────────────────────────────────────────────
DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'
VIEW_ICON_BUTTON = 'button[title="view"]'
EDIT_ICON_BUTTON = 'button[title="edit"]'

DELETED_TOAST = re.compile(r"deleted successfully", re.IGNORECASE)
RETRIEVED_TOAST = re.compile(r"retrieved successfully", re.IGNORECASE)
UPDATED_TOAST = re.compile(r"role updated successfully", re.IGNORECASE)
CREATED_TOAST = re.compile(r"role created successfully", re.IGNORECASE)


class RolesPage(BasePage):
    PATH = "/roles"

    def __init__(self, page: Page, tenant: Tenant = RETAIL) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign roles_url directly.
    @property
    def roles_url(self) -> str:
        return self.url

    @roles_url.setter
    def roles_url(self, value: str) -> None:
        self.url = value

    @property
    def add_role_button(self):
        return self.page.get_by_role("button", name="Add Role")

    @property
    def role_dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def role_name_input(self):
        return self.role_dialog.get_by_role("textbox", name="Enter role name")

    @property
    def role_description_input(self):
        return self.role_dialog.get_by_role(
            "textbox", name="Enter role description"
        )

    @property
    def sort_order_input(self):
        return self.role_dialog.locator('input[name="sort_order"]')

    @property
    def create_role_button(self):
        return self.role_dialog.get_by_role("button", name="Create Role")

    # ── Navigation & state ───────────────────────────────────────────────────

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.add_role_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_roles_visible(self) -> bool:
        try:
            self.add_role_button.wait_for(state="visible", timeout=UI_TIMEOUT)
            return True
        except Exception:
            return False

    # ── Internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        """GET .../roles or .../roles?<query> — the list fetch, not show/statistics."""
        return (
            response.request.method == "GET"
            and re.search(r"/roles(\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/roles(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/roles/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method == "PUT"
            and re.search(r"/roles/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/roles/\d+", response.url) is not None
        )

    def filter_roles(self, query: str) -> None:
        """Type into the search box and block until the debounced list request
        has come back, so the table is genuinely filtered before we touch it."""
        search_box = self.page.get_by_role("textbox", name="Search roles...")
        search_box.wait_for(state="visible", timeout=UI_TIMEOUT)
        if search_box.input_value() == query:
            return  # already filtered; SearchBar would not fire a request
        with self.page.expect_response(self._is_list_response, timeout=LIST_TIMEOUT):
            search_box.fill(query)

    def _row(self, role_name: str):
        """The single table row for this role, scoped to the table body."""
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(role_name, exact=True)
        ).first

    def _confirm(self, button_name: str) -> None:
        """Click a ConfirmModal button and wait for the list refresh it triggers."""
        with self.page.expect_response(self._is_list_response, timeout=LIST_TIMEOUT):
            self.page.get_by_role("button", name=button_name).click(timeout=UI_TIMEOUT)

    def _toast_visible(self, pattern: re.Pattern[str]) -> bool:
        try:
            self.page.get_by_text(pattern).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            return True
        except Exception:
            return False

    # ── Actions ──────────────────────────────────────────────────────────────

    def add_roles(self) -> dict[str, str]:
        role_name = generate_random_name("Role")
        role_description = generate_random_description("description")
        self.add_role_button.click()
        self.role_name_input.fill(role_name)
        self.role_description_input.fill(role_description)
        self.page.locator("#group-products").check()
        self.page.get_by_role("checkbox", name="Create Suppliers").check()
        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.create_role_button.click()
        assert response_info.value.status in (200, 201), (
            f"Role create API returned {response_info.value.status}"
        )
        self.page.get_by_text(CREATED_TOAST).first.wait_for(
            state="visible", timeout=UI_TIMEOUT
        )
        return {"name": role_name, "description": role_description}

    def add_role_with_permissions(
        self,
        role_name: str,
        permission_names: list[str],
    ) -> None:
        self.add_role_button.click()
        self.role_name_input.fill(role_name)
        self.role_description_input.fill(
            "Automated RBAC verification role"
        )

        for permission_name in permission_names:
            checkbox = self.page.locator(f"#perm-{permission_name}")
            checkbox.wait_for(state="visible", timeout=LIST_TIMEOUT)
            checkbox.check()

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.create_role_button.click()
        assert response_info.value.status in (200, 201), (
            f"Role create API returned {response_info.value.status}"
        )
        self.page.get_by_text(CREATED_TOAST).first.wait_for(
            state="visible", timeout=UI_TIMEOUT
        )

    def search_roles(self, role_name: str) -> bool:
        self.filter_roles(role_name)
        try:
            self._row(role_name).wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def is_role_active(self, role_name: str) -> bool:
        """True when the row shows the trash icon (not soft-deleted).
        Needed because both states share title="delete" — see note at top."""
        self.filter_roles(role_name)
        try:
            self._row(role_name).locator(DELETE_ICON_BUTTON).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False

    def view_roles(
        self,
        role_name: str,
        expected_description: str | None = None,
    ) -> bool:
        self.filter_roles(role_name)
        role_row = self._row(role_name)
        role_row.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            role_row.locator(VIEW_ICON_BUTTON).click(timeout=UI_TIMEOUT)
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        success = False
        try:
            modal.get_by_text(role_name, exact=True).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            if expected_description is not None:
                modal.get_by_text(
                    expected_description, exact=True
                ).first.wait_for(state="visible", timeout=UI_TIMEOUT)
            success = True
        except Exception:
            success = False
        finally:
            try:
                close_btn = modal.get_by_role("button", name="Close")
                if close_btn.count() > 0 and close_btn.first.is_visible():
                    close_btn.first.click()
                elif modal.locator(".btn-close").count() > 0 and modal.locator(".btn-close").first.is_visible():
                    modal.locator(".btn-close").first.click()
                else:
                    self.page.keyboard.press("Escape")
                modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
            except Exception:
                pass

        return success

    def edit_role(self, old_role_name: str, new_role_name: str, new_description: str | None = None) -> bool:
        self.filter_roles(old_role_name)
        role_row = self._row(old_role_name)
        role_row.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            role_row.locator(EDIT_ICON_BUTTON).click(timeout=UI_TIMEOUT)
        
        # Update name and description
        self.page.locator('input[name="name"]').fill(new_role_name)
        if new_description:
            desc_box = self.page.get_by_role("textbox", name="Enter role description")
            if desc_box.count() > 0 and desc_box.first.is_visible():
                desc_box.first.fill(new_description)

        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.page.get_by_role("button", name="Update").click()

        return (
            response_info.value.status in (200, 204)
            and self._toast_visible(UPDATED_TOAST)
        )

    def delete_role(self, role_name: str) -> bool:
        self.filter_roles(role_name)
        role_row = self._row(role_name)
        role_row.wait_for(state="visible", timeout=UI_TIMEOUT)

        role_row.locator(DELETE_ICON_BUTTON).click(timeout=UI_TIMEOUT)
        self._confirm("Delete Role")

        return self._toast_visible(DELETED_TOAST)

    def retrieve_role(self, role_name: str) -> bool:
        role_row = self._row(role_name)
        retrieve_button = role_row.locator(RETRIEVE_ICON_BUTTON)
        retrieve_button.wait_for(state="visible", timeout=UI_TIMEOUT)
        retrieve_button.click(timeout=UI_TIMEOUT)
        self._confirm("Retrieve Role")

        return self._toast_visible(RETRIEVED_TOAST)

    def validate_required_fields(self) -> bool:
        submitted_requests = []

        def record_submission(request):
            if (
                request.method == "POST"
                and re.search(r"/roles(?:\?|$)", request.url)
            ):
                submitted_requests.append(request)

        self.add_role_button.click()
        self.page.on("request", record_submission)
        try:
            self.create_role_button.click()
            self.role_dialog.get_by_text(
                "Role name is required", exact=True
            ).wait_for(state="visible", timeout=UI_TIMEOUT)
            self.role_dialog.get_by_text(
                "Description is required", exact=True
            ).wait_for(state="visible", timeout=UI_TIMEOUT)
            self.role_dialog.get_by_text(
                "At least one permission must be selected", exact=True
            ).wait_for(state="visible", timeout=UI_TIMEOUT)
        finally:
            self.page.remove_listener("request", record_submission)

        return not submitted_requests

    def validate_duplicate_role(self, role_name: str) -> bool:
        self.add_role_button.click()
        self.role_name_input.fill(role_name)
        self.role_description_input.fill("Duplicate role validation")
        self.page.get_by_role("checkbox", name="Create Suppliers").check()

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.create_role_button.click()

        if response_info.value.status in (200, 201):
            return False

        error = self.role_name_input.locator("xpath=..").locator(
            ".invalid-feedback"
        )
        error.wait_for(state="visible", timeout=UI_TIMEOUT)
        return bool(re.search(r"already|duplicate|taken", error.inner_text(), re.I))

    def validate_invalid_sort_order(
        self,
        role_name: str,
        sort_order: str,
    ) -> bool:
        responses = []

        def record_response(response):
            if self._is_create_response(response):
                responses.append(response)

        self.add_role_button.click()
        self.role_name_input.fill(role_name)
        self.role_description_input.fill("Invalid sort order validation")
        self.page.get_by_role("checkbox", name="Create Suppliers").check()
        self.sort_order_input.fill(sort_order)

        sort_error = self.sort_order_input.locator("xpath=..").locator(
            ".invalid-feedback"
        )
        success_toast = self.page.get_by_text(CREATED_TOAST).first

        self.page.on("response", record_response)
        try:
            self.create_role_button.click()
            sort_error.or_(success_toast).first.wait_for(
                state="visible", timeout=LIST_TIMEOUT
            )
        finally:
            self.page.remove_listener("response", record_response)

        if success_toast.is_visible():
            return False

        return sort_error.is_visible() and not any(
            response.status in (200, 201) for response in responses
        )

    def delete_role_expect_blocked(self, role_name: str) -> bool:
        self.filter_roles(role_name)
        role_row = self._row(role_name)
        role_row.wait_for(state="visible", timeout=UI_TIMEOUT)
        role_row.locator(DELETE_ICON_BUTTON).click(timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.page.get_by_role("button", name="Delete Role").click()

        if response_info.value.status in (200, 204):
            return False

        self.navigate()
        return self.search_roles(role_name) and self.is_role_active(role_name)
