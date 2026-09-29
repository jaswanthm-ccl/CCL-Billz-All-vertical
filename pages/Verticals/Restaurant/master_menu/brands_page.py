from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from utils.res_constants import RESTAURANT_BASE_URL
from utils.constants import (
    LIST_TIMEOUT,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)
from pages.common.form_page import has_validation_feedback


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class BrandsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.brands_url = f"{RESTAURANT_BASE_URL}/brands"

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add Brand")

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def name_input(self):
        return self.dialog.locator("input[name='name']")

    @property
    def description_input(self):
        return self.dialog.locator('textarea[name="description"]')

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/brands(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/brands(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/brands/\d+(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(r"/brands/\d+", response.url) is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/brands/\d+", response.url) is not None
        )

    def navigate(self) -> None:
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            self.page.goto(self.brands_url)
        self.add_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_brands_visible(self) -> bool:
        return self.add_button.is_visible()

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def is_brand_active(self, name: str) -> bool:
        if not self.search_brand(name):
            return False
        row = self._row(name)
        delete_btn = row.locator(DELETE_ICON_BUTTON)
        try:
            delete_btn.wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def search_brand(self, brand_name: str) -> bool:
        if self.search_box.input_value() != brand_name:
            with self.page.expect_response(
                self._is_list_response, timeout=LIST_TIMEOUT
            ):
                self.search_box.fill(brand_name)
        try:
            self._row(brand_name).wait_for(
                state="visible", timeout=SETTLED_TIMEOUT
            )
            return True
        except Exception:
            return False

    def add_brand(self, name: str, description: str = "") -> str:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(name)
        if description:
            self.description_input.fill(description)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_create_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.locator("button[type='submit']").click()

        assert response_info.value.status in (200, 201)
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return name

    def edit_brand(
        self, old_name: str, new_name: str, new_description: str | None = None
    ) -> bool:
        if not self.search_brand(old_name):
            return False

        row = self._row(old_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(new_name)
        if new_description is not None:
            self.description_input.fill(new_description)

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

    def view_brand(
        self, name: str, expected_description: str | None = None
    ) -> bool:
        if not self.search_brand(name):
            return False

        row = self._row(name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ):
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

    def delete_brand(self, brand_name: str) -> bool:
        if not self.search_brand(brand_name):
            return False

        row = self._row(brand_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        row.locator(DELETE_ICON_BUTTON).click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        try:
            with self.page.expect_response(
                self._is_list_response, timeout=LIST_TIMEOUT
            ):
                with self.page.expect_response(
                    self._is_delete_response, timeout=LIST_TIMEOUT
                ) as response_info:
                    modal.get_by_role("button", name="Delete Brand").click()

            if response_info.value.status not in (200, 204):
                try:
                    modal.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()
                except Exception:
                    pass
                return False
            modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
            return True
        except Exception:
            try:
                modal.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()
            except Exception:
                pass
            return False

    def retrieve_brand(self, brand_name: str) -> bool:
        if not self.search_brand(brand_name):
            return False

        row = self._row(brand_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)

        retrieve_btn = row.locator(RETRIEVE_ICON_BUTTON)
        retrieve_btn.wait_for(state="visible", timeout=UI_TIMEOUT)
        retrieve_btn.click()

        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ):
            with self.page.expect_response(
                self._is_delete_response, timeout=LIST_TIMEOUT
            ) as response_info:
                modal.get_by_role(
                    "button", name="Retrieve Brand"
                ).click()

        if response_info.value.status not in (200, 204):
            return False
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return True

    def validate_required_fields(self) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        requests: list[str] = []
        listener = lambda request: requests.append(request.url)
        self.page.on("request", listener)
        try:
            modal.locator("button[type='submit']").click()
            has_error = has_validation_feedback(
                self.page,
                r"Brand Name is required",
                r"brand name.*required",
                r"field is required",
                r"required",
            )
            api_calls = [
                url for url in requests if re.search(r"/brands(?:\?|$)", url)
            ]
            is_valid = has_error and len(api_calls) == 0
        finally:
            self.page.remove_listener("request", listener)

        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return is_valid

    def validate_blank_only_name(self) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill("   ")
        if self.description_input.is_visible():
            self.description_input.fill("validation test")

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.locator("button[type='submit']").click()

        has_error = has_validation_feedback(
            self.page,
            r"Brand Name is required",
            r"brand name.*required",
            r"name.*blank",
            r"name.*empty",
            r"required",
        )
        rejected = response_info.value.status in (400, 409, 422)
        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return rejected and has_error

    def validate_duplicate_brand(self, name: str, description: str) -> bool:
        self.add_button.click()
        modal = self.dialog
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)

        self.name_input.fill(name)
        if description:
            self.description_input.fill(description)

        with self.page.expect_response(
            self._is_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.locator("button[type='submit']").click()

        rejected = response_info.value.status in (400, 409, 422)
        has_error = has_validation_feedback(
            self.page,
            r"brand.*name.*already.*taken",
            r"name.*already.*taken",
            r"already been taken",
            r"duplicate",
        )
        modal.get_by_role("button", name="Cancel").click()
        modal.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return rejected and has_error


BrandPage = BrandsPage
