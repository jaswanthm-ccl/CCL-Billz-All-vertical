"""Restaurant adapter for the shared Branches page object."""
from __future__ import annotations

import re

from playwright.sync_api import Page
from pages.master_menu.branches_page import BranchesPage as BaseBranchesPage
from utils.constants import LIST_TIMEOUT, UI_TIMEOUT
from utils.tenants import RESTAURANT, Tenant
from utils.random_data import (
    generate_random_address,
    generate_random_code,
    generate_random_email,
    generate_random_name,
    generate_random_phone,
    generate_random_postal_code,
)


class BranchesPage(BaseBranchesPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)

    def add_branch(
        self,
        city_name: str | None = None,
        name: str | None = None,
        code: str | None = None,
    ) -> str:
        """Create a Restaurant branch using an existing city."""
        branch_name = name or generate_random_name("ResBranch")
        branch_code = code or generate_random_code("RB")

        self.navigate()
        self.page.get_by_role("button", name="Add Branch").click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        dialog.locator('input[name="name"]').fill(branch_name)
        dialog.locator('input[name="code"]').fill(branch_code)
        dialog.locator('input[name="address"]').fill(generate_random_address())

        dialog.locator("input[name='state_id']").locator("xpath=..").locator(
            ".react-select__input-container"
        ).click()
        self.page.get_by_role("option", name="Tamil Nadu", exact=True).click()

        city_input = dialog.locator("input[name='city_id']")
        city_input.locator("xpath=..").locator(
            ".react-select__input-container"
        ).click()
        if city_name:
            city_input.fill(city_name)
            city_option = self.page.get_by_role(
                "option", name=city_name, exact=False
            ).first
        else:
            city_option = self.page.get_by_role("option").first
        city_option.wait_for(state="visible", timeout=UI_TIMEOUT)
        city_option.click()

        dialog.locator('input[name="postal_code"]').fill(
            generate_random_postal_code()
        )
        dialog.get_by_role(
            "textbox", name="Enter 10-digit phone number"
        ).fill(generate_random_phone())
        dialog.locator('input[name="email"]').fill(generate_random_email())
        dialog.get_by_role("spinbutton").fill("3")

        with self.page.expect_response(
            lambda response: (
                response.request.method == "POST"
                and re.search(r"/branches(?:\?|$)", response.url) is not None
            ),
            timeout=LIST_TIMEOUT,
        ) as response_info:
            dialog.get_by_role("button", name="Create").click()

        assert response_info.value.status in {200, 201}
        self.page.get_by_text("Branch created successfully.").wait_for(
            state="visible", timeout=UI_TIMEOUT
        )
        return branch_name
