from __future__ import annotations

import re
from playwright.sync_api import Page, Response, expect

from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)
from utils.tenants import Tenant
from pages.common.base_page import BasePage
from pages.common.form_page import has_validation_feedback

DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class ProductAttributesPage(BasePage):
    PATH = "/product-unit-attributes"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)
        self._list_api_url: str | None = None
        self._list_headers: dict | None = None

    # Legacy alias: unmigrated callers still assign product_attributes_url directly.
    @property
    def product_attributes_url(self) -> str:
        return self.url

    @product_attributes_url.setter
    def product_attributes_url(self, value: str) -> None:
        self.url = value

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Product Unit Attribute")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def create_button(self):
        return self.dialog.get_by_role("button", name="Create")

    @property
    def name_input(self):
        return self.dialog.locator('input[name="name"]')

    @property
    def sort_order_input(self):
        return self.dialog.locator('input[name="sort_order"]')

    @property
    def unique_checkbox(self):
        return self.dialog.locator('input#unique, input[name="unique"]').first

    @property
    def description_button(self):
        return self.dialog.get_by_role("button", name="Add Description")

    @property
    def description_input(self):
        return self.dialog.locator('textarea[name="notes"]')

    @property
    def update_button(self):
        return self.dialog.get_by_role("button", name="Update")

    @property
    def delete_button(self):
        return self.dialog.get_by_role("button", name="Delete").first

    @property
    def retrieve_button(self):
        return self.dialog.get_by_role("button", name="Retrieve").first

    @property
    def close_button(self):
        return self.dialog.locator(".btn-close")

    @property
    def toast(self):
        return self.page.get_by_text("successfully")

    @property
    def error_locator(self):
        return self.page.get_by_text("Name is required")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def toast_delete(self):
        return self.page.get_by_text("Deleted successfully.")

    @property
    def toast_retrieve(self):
        return self.page.get_by_text("Retrieved successfully.")

    @property
    def spinner(self):
        return self.dialog.locator(".spinner-border")

    @property
    def name_too_long_error(self):
        return self.page.get_by_text("Name cannot be longer than 255 characters")

    def _is_list_response(self, response: Response) -> bool:
        if (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/product-unit-attributes(?:\?|$)", response.url) is not None
        ):
            self._list_api_url = response.url.split("?")[0]
            return True
        return False

    def _capture_api_headers(self, response: Response) -> None:
        # request.headers omits the tenant and financial-year headers the API requires.
        allowed = {"accept", "authorization", "x-tenant-id", "x-financial-year-id",
                   "x-fy-start-date", "x-fy-end-date", "x-fy-mode"}
        self._list_headers = {
            name: value
            for name, value in response.request.all_headers().items()
            if name.lower() in allowed
        }
        origin = self.tenant.url()
        self._list_headers["Origin"] = origin
        self._list_headers["Referer"] = f"{origin}/"

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/product-unit-attributes(?:\?|$)", response.url) is not None
        )

    def navigate(self) -> None:
        try:
            with self.page.expect_response(self._is_list_response, timeout=LIST_TIMEOUT) as response_info:
                self.page.goto(self.url)
            self._capture_api_headers(response_info.value)
        except Exception:
            self.page.goto(self.url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_product_attributes_visible(self) -> bool:
        return self.add_button.is_visible()

    def add_product_attribute(self, name: str, sort_order: int | None = None, unique: bool = False, description: str | None = None) -> Response | None:
        self.add_button.click()
        expect(self.dialog).to_be_visible()

        self.name_input.fill(name)
        if sort_order is not None:
            self.sort_order_input.fill(str(sort_order))
        if unique:
            self.unique_checkbox.check()
        if description:
            self.description_button.click()
            self.description_input.fill(description)

        try:
            with self.page.expect_response(self._is_create_response, timeout=LIST_TIMEOUT) as resp_info:
                self.create_button.click()
            return resp_info.value
        except Exception:
            self.create_button.click()
            return None

    def search_product_attribute(self, name: str) -> bool:
        if self.search_box.input_value() != name:
            self.search_box.fill(name)
            try:
                with self.page.expect_response(self._is_list_response, timeout=LIST_TIMEOUT):
                    self.search_box.press("Enter")
            except Exception:
                self.search_box.press("Enter")

        locator = self.page.get_by_text(name, exact=True).first
        try:
            expect(locator).to_be_visible(timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def get_unique_flag(self, name: str) -> str | None:
        """Text of the UNIQUE column ('yes'/'no') for the attribute, or None if not listed."""
        if not self.search_product_attribute(name):
            return None
        headers = [h.strip().upper() for h in self.page.locator("thead th").all_inner_texts()]
        unique_index = headers.index("UNIQUE") if "UNIQUE" in headers else 2
        return self._row(name).locator("td").nth(unique_index).inner_text().strip().lower()

    def ensure_deleted(self, name: str) -> bool:
        """Delete through the API, because the list hides row actions for admins."""
        self.navigate()
        if not self.search_product_attribute(name):
            return True
        return self.delete_attribute_by_api(name)

    def validate_duplicate_name(self, name: str) -> bool:
        self.add_button.click()
        expect(self.dialog).to_be_visible()
        self.name_input.fill(name)

        resp = None
        try:
            with self.page.expect_response(self._is_create_response, timeout=LIST_TIMEOUT) as resp_info:
                self.create_button.click()
            resp = resp_info.value
        except Exception:
            pass

        is_http_failed = resp is not None and resp.status in {400, 409, 422}
        is_ui_feedback = has_validation_feedback(
            self.page,
            r"already exists",
            r"already taken",
            r"duplicate",
            r"must be unique",
            r"already been taken",
        )
        return is_http_failed and is_ui_feedback

    def delete_attribute_by_api(self, name: str) -> bool:
        try:
            req_url = self._list_api_url or self.url
            headers = self._list_headers or {}
            response = self.page.request.get(
                req_url, headers=headers, params={"search": name, "with_trashed": "yes", "per_page": 100}
            )
            if response.status != 200:
                print(f"API Teardown lookup for {name} returned {response.status}: {response.text()[:200]}")
            if response.status == 200:
                payload = response.json()
                data = payload.get("data", {})
                items = data.get("data", data if isinstance(data, list) else [])
                for item in items:
                    if item.get("name") == name:
                        if item.get("deleted_at"):
                            return True
                        item_id = item.get("id")
                        if item_id:
                            base_api = req_url.split("?")[0]
                            del_resp = self.page.request.delete(f"{base_api}/{item_id}", headers=headers)
                            return del_resp.status in {200, 204}
        except Exception as e:
            print(f"API Teardown failed for {name}: {e}")
        return False

    def has_row_actions(self, name: str) -> bool:
        self.search_product_attribute(name)
        row = self.page.locator("tr", has=self.page.get_by_text(name, exact=True))
        try:
            expect(row).to_be_visible(timeout=SETTLED_TIMEOUT)
        except Exception:
            return False
        return all(
            row.get_by_title(action).count() > 0
            for action in ("view", "edit", "delete")
        )

    def view_product_attribute(self, name: str) -> bool:
        self.search_product_attribute(name)
        row = self.page.locator("tr", has=self.page.get_by_text(name, exact=True))
        expect(row).to_be_visible()

        row.get_by_title("view").click()
        expect(self.dialog).to_be_visible()

        try:
            expect(self.dialog.get_by_text(name, exact=True).first).to_be_visible(timeout=SETTLED_TIMEOUT)
            is_visible = True
        except Exception:
            is_visible = False

        self.close_button.click()
        return is_visible

    def edit_product_attribute(self, old_name: str, new_name: str) -> bool:
        self.search_product_attribute(old_name)
        row = self.page.locator("tr", has=self.page.get_by_text(old_name, exact=True))
        expect(row).to_be_visible()

        row.get_by_title("edit").click()
        expect(self.dialog).to_be_visible()

        try:
            expect(self.spinner).to_be_hidden(timeout=SETTLED_TIMEOUT)
        except Exception:
            pass

        self.name_input.fill(new_name)
        self.update_button.click()

        try:
            expect(self.toast).to_be_visible(timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def delete_product_attribute(self, name: str) -> bool:
        self.search_product_attribute(name)
        row = self.page.locator("tr", has=self.page.get_by_text(name, exact=True))
        expect(row).to_be_visible()

        row.locator(DELETE_ICON_BUTTON).first.click()
        expect(self.dialog).to_be_visible()
        self.delete_button.click()

        try:
            expect(self.toast_delete).to_be_visible(timeout=LIST_TIMEOUT)
            return True
        except Exception:
            return False

    def retrieve_product_attribute(self, name: str) -> bool:
        self.search_product_attribute(name)
        row = self.page.locator("tr", has=self.page.get_by_text(name, exact=True))
        expect(row).to_be_visible()

        restore_btn = row.locator(RETRIEVE_ICON_BUTTON).first
        expect(restore_btn).to_be_visible()
        restore_btn.click()
        expect(self.dialog).to_be_visible()
        self.retrieve_button.click()

        try:
            expect(self.toast_retrieve).to_be_visible(timeout=LIST_TIMEOUT)
            return True
        except Exception:
            return False

    def validate_required_fields(self) -> bool:
        self.add_button.click()
        expect(self.dialog).to_be_visible()
        self.create_button.click()

        try:
            expect(self.error_locator).to_be_visible(timeout=SETTLED_TIMEOUT)
            is_valid = True
        except Exception:
            is_valid = False

        self.navigate()
        return is_valid

    def validate_name_too_long(self, name: str) -> bool:
        self.add_button.click()
        expect(self.dialog).to_be_visible()
        self.name_input.fill(name)
        self.create_button.click()
        return has_validation_feedback(
            self.page,
            r"name.*(?:maximum|max|characters|too long)",
            r"(?:maximum|max).*name",
        )
