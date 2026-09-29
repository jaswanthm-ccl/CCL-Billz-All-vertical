"""Restaurant adapter for the shared Users page object."""

import re

from playwright.sync_api import Page

from pages.master_menu.users_page import UsersPage as SharedUsersPage
from utils.constants import LIST_TIMEOUT, UI_TIMEOUT
from utils.tenants import RESTAURANT, Tenant


class UsersPage(SharedUsersPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)

    def _select_labeled_option(self, label: str, option_name: str) -> None:
        field = self.user_dialog.locator("label").filter(
            has_text=re.compile(rf"^{re.escape(label)}\s*\*?\s*$", re.I)
        ).locator("xpath=..")
        select_input = field.locator(".react-select__input-container").first
        select_input.wait_for(state="visible", timeout=UI_TIMEOUT)
        select_input.click()
        option = self.page.locator(".react-select__option, [id*='-option-']").filter(
            has_text=re.compile(re.escape(option_name), re.I)
        ).or_(
            self.page.get_by_role("option", name=re.compile(re.escape(option_name), re.I))
        ).first
        option.wait_for(state="visible", timeout=UI_TIMEOUT)
        option.click()

    def add_user(
        self,
        name: str,
        email: str,
        password: str,
        branch_name: str | None,
        role_name: str,
        *,
        branch_id: int | None = None,
        can_login: bool = True,
        user_code: str | None = None,
    ) -> dict:
        if branch_id is not None:
            with self.page.expect_response(
                lambda response: (
                    response.request.method == "GET"
                    and re.search(r"/branches(?:\?|$)", response.url) is not None
                    and "per_page=1000" in response.url
                ),
                timeout=LIST_TIMEOUT,
            ) as branches_response_info:
                self.add_user_button.click()
            payload = branches_response_info.value.json()
            rows = ((payload.get("data") or {}).get("data") or [])
            matching_branch = next(
                (row for row in rows if int(row.get("id", 0)) == int(branch_id)),
                None,
            )
            assert matching_branch, (
                f"POS branch id {branch_id} was absent from the User branch list"
            )
            branch_name = matching_branch["name"]
        else:
            self.add_user_button.click()

        assert branch_name, "A Restaurant user requires a branch assignment"
        self.user_dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.user_name_input.fill(name)
        self.user_dialog.locator('input[name="email"]').fill(email)
        self.user_dialog.locator('input[name="password"]').fill(password)
        self._select_labeled_option("Branches", branch_name)
        self._select_labeled_option("Roles", role_name)

        login_toggle = self.user_dialog.locator("input[name='can_login']")
        login_toggle.wait_for(state="visible", timeout=UI_TIMEOUT)
        if login_toggle.is_checked() != can_login:
            login_toggle.click()
        if not can_login:
            assert user_code, "Restaurant non-login staff require a User Code"
            self.user_dialog.locator("input[name='user_code']").fill(user_code)

        # Keep staff lifecycle flags separate from permission selection.
        permission_checkbox = self.user_dialog.locator(
            "input[id^='perm-'], input[id^='group-']"
        ).first
        permission_checkbox.wait_for(state="visible", timeout=UI_TIMEOUT)
        permission_checkbox.check()

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.user_dialog.get_by_role("button", name="Create").click()

        assert response_info.value.status in {200, 201}, (
            f"User create API returned {response_info.value.status}"
        )
        submitted_user = response_info.value.request.post_data_json
        assert bool(submitted_user.get("can_login")) is can_login, (
            "Restaurant user request did not preserve the requested Can Login state: "
            f"{submitted_user}"
        )
        if not can_login:
            assert str(submitted_user.get("user_code")) == str(user_code), (
                "Restaurant staff request did not preserve its User Code: "
                f"{submitted_user}"
            )
        toast = self.page.get_by_text(re.compile(r"User created successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=UI_TIMEOUT)
        except Exception:
            pass
        submitted_user["_branch_name"] = branch_name
        return submitted_user

    def row_has_assignments(
        self, user_name: str, branch_name: str, role_name: str
    ) -> bool:
        if not self.search_user(user_name):
            return False
        row = self._row(user_name)
        return (
            row.get_by_text(branch_name, exact=True).count() > 0
            and row.get_by_text(role_name, exact=True).count() > 0
        )
