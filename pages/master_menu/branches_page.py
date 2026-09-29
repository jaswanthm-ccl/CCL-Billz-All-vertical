from __future__ import annotations

import re

from playwright.sync_api import Page, Response, expect

from utils.constants import LIST_TIMEOUT, UI_TIMEOUT
from utils.random_data import generate_random_address, generate_random_name, generate_random_code, generate_random_phone, generate_random_postal_code, generate_random_email
from utils.tenants import RETAIL, Tenant
from pages.common.base_page import BasePage
from pages.common.form_page import has_validation_feedback
from pages.master_menu.cities_page import CitiesPage

class BranchesPage(BasePage):
    PATH = "/branches"

    # Cities auto-created by add_branch/duplicate_branch_name, keyed by branch
    # name. Class-level so teardown fixtures that build a fresh BranchesPage
    # can still find and delete the cities that belong to a branch.
    _auto_cities: dict[str, list[str]] = {}

    def __init__(self, page: Page, tenant: Tenant = RETAIL) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign branches_url directly.
    @property
    def branches_url(self) -> str:
        return self.url

    @branches_url.setter
    def branches_url(self, value: str) -> None:
        self.url = value

    def cleanup_auto_city(self, branch_name: str) -> None:
        """Best-effort delete of the auto-created cities for a branch. Must
        run after the branch is deleted; the backend refuses to delete a city
        still assigned to a branch (including soft-deleted ones), so a
        failure here is logged, not raised."""

        city_names = self._auto_cities.pop(branch_name, [])
        if not city_names:
            return
        cities_page = self.open(CitiesPage)
        for city_name in city_names:
            try:
                cities_page.navigate()
                if cities_page.search_city(city_name):
                    cities_page.delete_city(city_name)
            except Exception as e:
                print(f"Teardown: could not delete auto city {city_name} for branch {branch_name}: {e}")
        
    def navigate(self) -> None:
        self.page.goto(self.url)
    
    def is_branches_visible(self) -> bool:
        return self.page.get_by_role("button", name="Add Branch").is_visible()

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/branches/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method == "PUT"
            and re.search(r"/branches/\d+(?:\?|$)", response.url)
            is not None
        )

    def has_actions_sorting_control(self) -> bool:
        header = self.page.get_by_role(
            "columnheader", name=re.compile(r"^actions?$", re.IGNORECASE)
        ).first
        if header.count() == 0:
            return False
        return (
            header.get_attribute("aria-sort") is not None
            or header.locator("button, [role='button'], [data-sort], .sort-icon").count() > 0
        )
    
    def add_branch(
        self,
        city_name: str | None = None,
        name: str | None = None,
        code: str | None = None,
    ) -> str:
        # 1. Create a dynamic city only if not provided by fixture
        if not city_name:
            cities_page = self.open(CitiesPage)
            cities_page.navigate()
            city_name = f"AutoCity_{generate_random_code('C')}"
            cities_page.add_city(city_name)
        
        # 2. Go back to branches page and add branch
        self.navigate()
        
        branch_name = name or generate_random_name("Branch")
        branch_code = code or generate_random_code("BR")
        self.page.get_by_role("button", name="Add Branch").click()
        self.page.locator("input[name=\"name\"]").fill(branch_name)
        self.page.locator("input[name=\"code\"]").fill(branch_code)
        self.page.locator("input[name=\"address\"]").fill(generate_random_address())
        
        self.page.locator("input[name='state_id']").locator("xpath=..").locator(".react-select__input-container").click()
        self.page.get_by_role("option", name="Tamil Nadu").click()
        
        city_container = self.page.locator("input[name='city_id']").locator("xpath=..").locator(".react-select__input-container")
        city_container.click()
        self.page.keyboard.type(city_name)
        self.page.get_by_role("option", name=city_name, exact=False).first.click()
        
        self.page.locator("input[name=\"postal_code\"]").fill(generate_random_postal_code())
        self.page.get_by_role("textbox", name="Enter 10-digit phone number").fill(generate_random_phone())
        self.page.locator("input[name=\"email\"]").fill(generate_random_email())
        self.page.get_by_role("spinbutton").fill("3")
        with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and re.search(r"/branches(?:\?|$)", response.url) is not None,
            timeout=LIST_TIMEOUT,
        ):
            self.page.get_by_role("button", name="Create").click()
        self._auto_cities.setdefault(branch_name, []).append(city_name)
        return branch_name
    
    
    def search_branch(self, branch_name: str) -> bool:
        search_box = self.page.get_by_role("textbox", name="Search branches...")
        search_box.fill(branch_name)
        search_box.press("Enter")
        self.page.wait_for_load_state("networkidle", timeout=5000)
        locator = self.page.get_by_text(branch_name, exact=True).first
        try:
            locator.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False
        
    def view_branch(
        self,
        branch_name: str,
        expected_values: dict[str, str] | None = None,
    ) -> bool:
        self.page.get_by_role("textbox", name="Search branches...").fill(branch_name)
        branch_row = self.page.locator("tr", has=self.page.get_by_text(branch_name, exact=True))
        branch_row.wait_for(state="visible", timeout=5000)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            branch_row.get_by_title("view").click()
        
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        name_locator = modal.get_by_text(branch_name, exact=True)
        try:
            name_locator.wait_for(state="visible", timeout=UI_TIMEOUT)
            for expected_value in (expected_values or {}).values():
                modal.get_by_text(
                    str(expected_value), exact=True
                ).first.wait_for(state="visible", timeout=UI_TIMEOUT)
            is_name_visible = True
        except Exception:
            is_name_visible = False
            
    
        modal.get_by_role("button", name="Back to List").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_name_visible
        
    def edit_branch(
        self,
        branch_name: str,
        updated_fields: dict[str, str] | None = None,
    ) -> bool:
        self.page.get_by_role("textbox", name="Search branches...").fill(branch_name)
        branch_row = self.page.locator("tr", has=self.page.get_by_text(branch_name, exact=True))
        branch_row.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            branch_row.get_by_title("edit").click()

        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        name_input = modal.locator('input[name="name"]')
        expect(name_input).to_have_value(
            branch_name, timeout=LIST_TIMEOUT
        )

        fields = updated_fields or {"name": branch_name + "_edited"}
        for field_name in (
            "name",
            "code",
            "address",
            "postal_code",
            "phone",
            "email",
            "sort_order",
        ):
            if field_name in fields:
                modal.locator(f'input[name="{field_name}"]').fill(
                    str(fields[field_name])
                )

        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Update").click()

        if response_info.value.status not in (200, 204):
            return False
        toast_locator = self.page.get_by_text("Branch updated successfully")
        try:
            toast_locator.wait_for(state="visible", timeout=UI_TIMEOUT)
            return True
        except Exception:
            return False
        
    def delete_branch(self, branch_name: str) -> bool:
        self.page.get_by_role("textbox", name="Search branches...").fill(branch_name)
        branch_row = self.page.locator("tr", has=self.page.get_by_text(branch_name, exact=True))
        branch_row.wait_for(state="visible", timeout=5000) 
        branch_row.locator(
            'button[title="delete"]:has(i.bi-trash)'
        ).click()
        self.page.get_by_role("button", name="Delete Branch").click()
        toast_locator = self.page.get_by_text("Deleted successfully.")
        try:
            toast_locator.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False    
        
    def ensure_deleted(self, branch_name: str) -> bool:
        """Soft-delete the branch unless it is already deleted or absent."""
        self.navigate()
        if not self.search_branch(branch_name):
            return True
        row = self.page.locator("tr", has=self.page.get_by_text(branch_name, exact=True))
        if row.locator('button[title="delete"]:has(i.bi-arrow-clockwise)').count() > 0:
            return True
        return self.delete_branch(branch_name)

    def retrieve_branch(self, branch_name: str) -> bool:
        self.page.get_by_role("textbox", name="Search branches...").fill(branch_name)
        branch_row = self.page.locator("tr", has=self.page.get_by_text(branch_name, exact=True))
        branch_row.wait_for(state="visible", timeout=5000) 
        branch_row.locator(
            'button[title="delete"]:has(i.bi-arrow-clockwise)'
        ).click()
        self.page.get_by_role("button", name="Retrieve Branch").click()
        toast_locator = self.page.get_by_text("Retrieved successfully.")
        try:
            toast_locator.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False
        
    def validate_branch_name(self) -> bool:
        self.page.get_by_role("button", name="Add Branch").click()
        self.page.locator("input[name=\"name\"]").fill("")
        self.page.get_by_role("button", name="Create").click()
        error_locator = self.page.get_by_text("Branch name is required")
        try:
            error_locator.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False
        
    def duplicate_branch_name(self, branch_name: str) -> bool:
        # Create a dynamic city
        cities_page = self.open(CitiesPage)
        cities_page.navigate()
        city_name = f"AutoCity_{generate_random_code('C')}"
        cities_page.add_city(city_name)
        self._auto_cities.setdefault(branch_name, []).append(city_name)

        self.navigate()

        self.page.get_by_role("button", name="Add Branch").click()
        self.page.locator("input[name=\"name\"]").fill(branch_name)
        self.page.locator("input[name=\"code\"]").fill(generate_random_code())
        self.page.locator("input[name=\"address\"]").fill(generate_random_address())
        
        self.page.locator("input[name='state_id']").locator("xpath=..").locator(".react-select__input-container").click()
        self.page.get_by_role("option", name="Tamil Nadu").click()
        
        city_container = self.page.locator("input[name='city_id']").locator("xpath=..").locator(".react-select__input-container")
        city_container.click()
        self.page.keyboard.type(city_name)
        self.page.get_by_role("option", name=city_name, exact=False).first.click()
        
        self.page.locator("input[name=\"postal_code\"]").fill(generate_random_postal_code())
        self.page.get_by_role("textbox", name="Enter 10-digit phone number").fill(generate_random_phone())
        self.page.locator('input[name="email"]').fill(generate_random_email())
        self.page.get_by_role("spinbutton").fill("3")
        self.page.get_by_role("button", name="Create").click()
        
        error_locator = self.page.get_by_text(re.compile(r"already.*taken|already.*exist|duplicate", re.IGNORECASE)).first
        try:
            error_locator.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def get_branch_code(self, branch_name: str) -> str:
        self.search_branch(branch_name)
        row = self.page.locator("tr", has=self.page.get_by_text(branch_name, exact=True))
        row.wait_for(state="visible", timeout=5000)
        return row.locator("td").nth(2).inner_text().strip()

    def duplicate_branch_code(self, duplicate_code: str, cleanup_owner: str) -> bool:
        cities_page = self.open(CitiesPage)
        cities_page.navigate()
        city_name = f"AutoCity_{generate_random_code('C')}"
        cities_page.add_city(city_name)
        self._auto_cities.setdefault(cleanup_owner, []).append(city_name)

        self.navigate()
        self.page.get_by_role("button", name="Add Branch").click()
        self.page.locator('input[name="name"]').fill(generate_random_name("duplicate_code"))
        self.page.locator('input[name="code"]').fill(duplicate_code)
        self.page.locator('input[name="address"]').fill(generate_random_address())
        self.page.locator("input[name='state_id']").locator("xpath=..").locator(
            ".react-select__input-container"
        ).click()
        self.page.get_by_role("option", name="Tamil Nadu").click()
        city_container = self.page.locator("input[name='city_id']").locator("xpath=..").locator(".react-select__input-container")
        city_container.click()
        self.page.keyboard.type(city_name)
        self.page.get_by_role("option", name=city_name, exact=False).first.click()
        self.page.locator('input[name="postal_code"]').fill(generate_random_postal_code())
        self.page.get_by_role("spinbutton").fill("3")
        self.page.get_by_role("button", name="Create").click()
        try:
            self.page.get_by_text("The code has already been taken.").wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def validate_required_field(self, field: str, error_text: str) -> bool:
        self.page.get_by_role("button", name="Add Branch").click()
        values = {
            "name": generate_random_name("required"),
            "code": generate_random_code("REQ"),
            "address": generate_random_address(),
        }
        values[field] = ""
        for name, value in values.items():
            self.page.locator(f'input[name="{name}"]').fill(value)
        self.page.get_by_role("button", name="Create").click()
        try:
            self.page.get_by_text(error_text, exact=True).wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def validate_field_format(self, field: str, value: str, *patterns: str) -> bool:
        self.page.get_by_role("button", name="Add Branch").click()
        self.page.locator('input[name="name"]').fill(generate_random_name("format"))
        self.page.locator('input[name="code"]').fill(generate_random_code("FMT"))
        self.page.locator('input[name="address"]').fill(generate_random_address())
        self.page.locator(f'input[name="{field}"]').fill(value)
        self.page.get_by_role("button", name="Create").click()
        if has_validation_feedback(self.page, *patterns):
            return True
        return not self.page.locator(f'input[name="{field}"]').evaluate(
            "element => element.checkValidity()"
        )

    def edit_with_blank_sort_order_is_handled(self, branch_name: str) -> bool:
        self.search_branch(branch_name)
        row = self.page.locator("tr", has=self.page.get_by_text(branch_name, exact=True))
        row.get_by_title("edit").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=5000)
        modal.locator('input[name="sort_order"]').fill("")
        modal.get_by_role("button", name="Update").click()
        try:
            self.page.get_by_text("Branch updated successfully").wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def city_is_unselected_by_default(self) -> bool:
        self.page.get_by_role("button", name="Add Branch").click()
        city = self.page.locator('input[name="city_id"]')
        city.wait_for(state="attached", timeout=10000)
        return city.input_value() == ""

    def get_selected_city_in_new_branch_form(self) -> str:
        self.page.get_by_role("button", name="Add Branch").click()
        container = self.page.locator("input[name='city_id']").locator("xpath=../..")
        return container.text_content().strip()

    def validate_invalid_phone(self, phone: str) -> bool:
        self.page.get_by_role("button", name="Add Branch").click()
        self.page.locator('input[name="name"]').fill(generate_random_name("invalid_phone"))
        self.page.locator('input[name="code"]').fill(generate_random_code())
        self.page.locator('input[name="address"]').fill(generate_random_address())

        self.page.locator("input[name='state_id']").locator("xpath=..").locator(".react-select__input-container").click()
        self.page.get_by_role("option", name="Tamil Nadu").click()

        self.page.locator('input[name="postal_code"]').fill(generate_random_postal_code())
        self.page.get_by_role("textbox", name="Enter 10-digit phone number").fill(phone)
        self.page.locator('input[name="email"]').fill(generate_random_email())
        self.page.get_by_role("spinbutton").fill("3")
        self.page.get_by_role("button", name="Create").click()

        return has_validation_feedback(
            self.page,
            r"phone.*(?:10|invalid|valid|digits)",
            r"10[- ]digit.*phone",
        )
