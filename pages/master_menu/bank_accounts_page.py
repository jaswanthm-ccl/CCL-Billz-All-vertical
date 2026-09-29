from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from pages.common.base_page import BasePage
from utils.tenants import Tenant
from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)
from pages.common.form_page import has_validation_feedback


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class BankAccountPage(BasePage):
    PATH = "/bank-accounts"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign bank_account_url directly.
    @property
    def bank_account_url(self) -> str:
        return self.url

    @bank_account_url.setter
    def bank_account_url(self, value: str) -> None:
        self.url = value

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/bank-accounts(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/bank-accounts(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/bank-accounts/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method == "PUT"
            and re.search(r"/bank-accounts/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/bank-accounts/\d+(?:\?|$)", response.url)
            is not None
        )

    def _row(self, bank_name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(bank_name, exact=True)
        ).first

    def navigate(self) -> None:
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            self.page.goto(self.url)
        self.page.get_by_role("button", name="Add Bank Account").wait_for(
            state="visible", timeout=UI_TIMEOUT
        )

    def is_bank_account_visible(self) -> bool:
        return self.page.get_by_role("button", name="Add Bank Account").is_visible()

    def add_bank_account(self, bank_name: str, branch: str, account_number: str, ifsc_code: str) -> None:
        self.page.get_by_role("button", name="Add Bank Account").click()
        
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        
        modal.locator("input[name=\"bank_name\"]").fill(bank_name)
        modal.locator("input[name=\"branch\"]").fill(branch)
        modal.locator("input[name=\"account_number\"]").fill(account_number)
        modal.locator("input[name=\"ifsc_code\"]").fill(ifsc_code)
        
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_create_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role("button", name="Create").click()

        assert response_info.value.status in (200, 201), (
            f"Bank account create API returned {response_info.value.status}"
        )
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)

    def search_bank_account(self, bank_name: str) -> bool:
        search_box = self.page.get_by_role("textbox", name="Search...")
        if search_box.input_value() != bank_name:
            with self.page.expect_response(
                self._is_list_response, timeout=LIST_TIMEOUT
            ):
                search_box.fill(bank_name)

        locator = self._row(bank_name)
        try:
            locator.wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def view_bank_account(
        self,
        bank_name: str,
        *,
        expected_branch: str | None = None,
        expected_account_number: str | None = None,
        expected_ifsc: str | None = None,
    ) -> bool:
        if not self.search_bank_account(bank_name):
            return False

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(bank_name).get_by_title("view").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        
        try:
            modal.get_by_text(bank_name, exact=True).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            for expected_value in (
                expected_branch,
                expected_account_number,
                expected_ifsc,
            ):
                if expected_value is not None:
                    modal.get_by_text(
                        expected_value, exact=True
                    ).first.wait_for(
                        state="visible", timeout=UI_TIMEOUT
                    )
            is_visible = True
        except Exception:
            is_visible = False
            
        close_btn = modal.locator(".btn-close")
        if close_btn.count() > 0:
            close_btn.click()
        else:
            modal.get_by_role("button").filter(has_text="").first.click()
            
        return is_visible

    def edit_bank_account(
        self,
        old_name: str,
        new_name: str,
        *,
        new_branch: str | None = None,
        new_account_number: str | None = None,
        new_ifsc: str | None = None,
    ) -> bool:
        if not self.search_bank_account(old_name):
            return False

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            self._row(old_name).get_by_title("edit").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        
        modal.locator("input[name=\"bank_name\"]").fill(new_name)
        if new_branch is not None:
            modal.locator('input[name="branch"]').fill(new_branch)
        if new_account_number is not None:
            modal.locator('input[name="account_number"]').fill(
                new_account_number
            )
        if new_ifsc is not None:
            modal.locator('input[name="ifsc_code"]').fill(new_ifsc)
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

    def delete_bank_account(self, bank_name: str) -> bool:
        if not self.search_bank_account(bank_name):
            return False

        self._row(bank_name).locator(DELETE_ICON_BUTTON).click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role("button", name="Delete Account").click()

        if response_info.value.status not in (200, 204):
            return False
        
        toast = self.page.get_by_text("Deleted successfully.")
        try:
            toast.wait_for(state="visible", timeout=UI_TIMEOUT)
            return True
        except Exception:
            return False

    def retrieve_bank_account(self, bank_name: str) -> bool:
        if not self.search_bank_account(bank_name):
            return False

        self._row(bank_name).locator(RETRIEVE_ICON_BUTTON).click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role("button", name="Retrieve Account").click()

        if response_info.value.status not in (200, 204):
            return False
        
        toast = self.page.get_by_text("Retrieved successfully.")
        try:
            toast.wait_for(state="visible", timeout=UI_TIMEOUT)
            return True
        except Exception:
            return False

    def validate_required_fields(self) -> bool:
        self.page.get_by_role("button", name="Add Bank Account").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=5000)
        
        modal.get_by_role("button", name="Create").click()
        
        error_locator = self.page.get_by_text("Bank Name is required")
        try:
            error_locator.wait_for(state="visible", timeout=5000)
            is_valid = True
        except Exception:
            is_valid = False
            
        self.navigate()
        return is_valid

    def validate_invalid_format(self, field: str, value: str) -> bool:
        self.page.get_by_role("button", name="Add Bank Account").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=5000)

        values = {
            "bank_name": "Automation Validation Bank",
            "branch": "Automation Branch",
            "account_number": "123456789012",
            "ifsc_code": "IDFC0000899",
        }
        values[field] = value
        for name, field_value in values.items():
            modal.locator(f'input[name="{name}"]').fill(field_value)
        modal.get_by_role("button", name="Create").click()

        patterns = {
            "account_number": (
                r"account.*(?:invalid|valid|digits|number|length)",
                r"invalid.*account",
            ),
            "ifsc_code": (
                r"ifsc.*(?:invalid|valid|format|characters)",
                r"invalid.*ifsc",
            ),
        }
        return has_validation_feedback(self.page, *patterns[field])
