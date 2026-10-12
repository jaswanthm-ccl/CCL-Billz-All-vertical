from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response

from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)
from utils.tenants import Tenant
from pages.common.base_page import BasePage

DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RESTORE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class EmiProvidersPage(BasePage):
    PATH = "/emi-providers"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Provider")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search providers...")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def name_input(self):
        return self.page.get_by_role("textbox", name="e.g. Bajaj Finserv")

    @staticmethod
    def _is_list_response(response: Response, search: str | None = None) -> bool:
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/emi-providers")
        ):
            return False
        return search is None or parse_qs(url.query).get("search", [""])[-1] == search

    def _reload_list(self, action, search: str | None = None) -> None:
        with self.page.expect_response(
            lambda r: self._is_list_response(r, search), timeout=LIST_TIMEOUT
        ):
            action()
        self.page.locator("tbody tr").first.wait_for(state="visible", timeout=UI_TIMEOUT)

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/emi-providers(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/emi-providers/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH"}
            and re.search(r"/emi-providers/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/emi-providers/\d+(?:\?|$)", response.url) is not None
        )

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_emi_providers_visible(self) -> bool:
        return self.add_button.is_visible()

    def add_emi_provider(self, name: str) -> Response:
        self.add_button.click()
        self.name_input.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(name)

        create_btn = self.page.get_by_role("button", name="Create")
        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            create_btn.click()

        assert response_info.value.status in (200, 201), (
            f"EMI Provider create API returned {response_info.value.status}"
        )
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return response_info.value

    def validate_duplicate_name(self, name: str) -> bool:
        self.add_button.click()
        self.name_input.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(name)
        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Create").click()
        try:
            self.dialog.get_by_text("The name has already been taken.").wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            has_feedback = True
        except Exception:
            has_feedback = False
        self.dialog.get_by_role("button", name="Cancel").click()
        return response_info.value.status == 422 and has_feedback

    def get_linked_ledger(self, name: str) -> str | None:
        if not self.search_emi_provider(name):
            return None
        self._row(name).get_by_title("view").click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        ledger_text = self.dialog.get_by_text(re.compile(r"Linked ledger:", re.I)).first
        try:
            ledger_text.wait_for(state="visible", timeout=UI_TIMEOUT)
            value = re.sub(r"(?i)^\s*linked ledger:\s*", "", ledger_text.inner_text()).strip()
        except Exception:
            value = None
        close_btn = self.dialog.locator(".btn-close")
        if close_btn.count() > 0:
            close_btn.click()
        else:
            self.dialog.get_by_role("button", name="Close").click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return value

    def is_emi_provider_deleted(self, name: str) -> bool:
        if not self.search_emi_provider(name):
            return False
        return self._row(name).locator(RESTORE_ICON_BUTTON).count() > 0

    def ensure_deleted(self, name: str) -> bool:
        """Soft-delete the provider unless it is already deleted or absent."""
        self.navigate()
        if not self.search_emi_provider(name):
            return True
        if self._row(name).locator(RESTORE_ICON_BUTTON).count() > 0:
            return True
        return self.delete_emi_provider(name)

    def search_emi_provider(self, name: str) -> bool:
        self.search_box.wait_for(state="visible", timeout=UI_TIMEOUT)
        if self.search_box.input_value() != name:
            self._reload_list(lambda: self.search_box.fill(name), search=name)

        try:
            self._row(name).wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def view_emi_provider(self, name: str) -> bool:
        if not self.search_emi_provider(name):
            return False

        row = self._row(name)
        row.get_by_title("view").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        try:
            modal.get_by_text(name, exact=False).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            is_valid = True
        except Exception:
            is_valid = False

        close_btn = modal.locator(".btn-close")
        if close_btn.count() > 0:
            close_btn.click()
        else:
            modal.get_by_role("button", name="Close").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_valid

    def edit_emi_provider(self, old_name: str, new_name: str) -> bool:
        if not self.search_emi_provider(old_name):
            return False

        row = self._row(old_name)
        row.get_by_title("edit").click()
        self.name_input.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.name_input.fill(new_name)

        update_btn = self.page.get_by_role("button", name="Update")
        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            update_btn.click()

        if response_info.value.status not in (200, 204):
            return False
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def delete_emi_provider(self, name: str) -> bool:
        if not self.search_emi_provider(name):
            return False

        row = self._row(name)
        row.locator(DELETE_ICON_BUTTON).click()
        confirm_btn = self.page.get_by_role("button", name="Delete Provider")
        confirm_btn.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            confirm_btn.click()

        if response_info.value.status not in (200, 204):
            return False
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def restore_emi_provider(self, name: str) -> bool:
        if not self.search_emi_provider(name):
            return False

        row = self._row(name)
        row.locator(RESTORE_ICON_BUTTON).wait_for(state="visible", timeout=UI_TIMEOUT)
        row.locator(RESTORE_ICON_BUTTON).click()

        confirm_btn = self.page.get_by_role("button", name="Restore Provider")
        confirm_btn.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            lambda response: (
                response.request.method != "GET"
                and re.search(r"/emi-providers/\d+", response.url) is not None
            ),
            timeout=LIST_TIMEOUT,
        ) as response_info:
            confirm_btn.click()
        if response_info.value.status not in (200, 204):
            return False
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True
