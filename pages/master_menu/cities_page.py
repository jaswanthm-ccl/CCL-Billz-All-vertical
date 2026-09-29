from __future__ import annotations

import re
from urllib.parse import unquote_plus, urlsplit, urlunsplit

from playwright.sync_api import Page, Response, expect

from utils.constants import (
    SEARCH_DEBOUNCE_MS,
    LIST_TIMEOUT,
    UI_TIMEOUT,
    SETTLED_TIMEOUT,
)
from utils.random_data import generate_random_name
from utils.tenants import RETAIL, Tenant
from pages.common.base_page import BasePage
from pages.common.form_page import has_validation_feedback

# ── Selectors ────────────────────────────────────────────────────────────────
DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RETRIEVE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'
EDIT_ICON_BUTTON = 'button[title="edit"]'

DELETED_TOAST = re.compile(r"deleted successfully", re.IGNORECASE)
RETRIEVED_TOAST = re.compile(r"retrieved successfully", re.IGNORECASE)
UPDATED_TOAST = re.compile(r"city updated successfully", re.IGNORECASE)
CREATED_TOAST = re.compile(r"city created successfully", re.IGNORECASE)


class CitiesPage(BasePage):
    PATH = "/cities"

    def __init__(self, page: Page, tenant: Tenant = RETAIL) -> None:
        super().__init__(page, tenant)
        self._list_api_url: str | None = None
        self._list_headers: dict[str, str] = {}

    # Legacy alias: unmigrated callers still assign city_url directly.
    @property
    def city_url(self) -> str:
        return self.url

    @city_url.setter
    def city_url(self, value: str) -> None:
        self.url = value

    # ── Properties (Rule 5: dynamic locators) ────────────────────────────────

    @property
    def add_city_button(self):
        return self.page.get_by_role("button", name="Add City")

    @property
    def search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def city_name_input(self):
        return self.page.locator('input[name="name"]')

    @property
    def create_button(self):
        return self.page.get_by_role("button", name="Create")

    @property
    def update_button(self):
        return self.page.get_by_role("button", name="Update")

    @property
    def state_select(self):
        return self.page.locator(".react-select__input-container").nth(1)

    @property
    def is_default_checkbox(self):
        return self.page.get_by_role("checkbox", name="Is default")

    # ── Navigation & state ───────────────────────────────────────────────────

    def navigate(self) -> None:
        with self.page.expect_response(
            self._is_list_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.page.goto(self.url)
        response = response_info.value
        parts = urlsplit(response.url)
        self._list_api_url = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, "", "")
        )
        allowed_headers = {
            "accept",
            "authorization",
            "x-tenant-id",
            "x-financial-year-id",
            "x-fy-start-date",
            "x-fy-end-date",
            "x-fy-mode",
        }
        self._list_headers = {
            name: value
            for name, value in response.request.all_headers().items()
            if name.lower() in allowed_headers
        }
        ui_parts = urlsplit(self.url)
        origin = f"{ui_parts.scheme}://{ui_parts.netloc}"
        self._list_headers["Origin"] = origin
        self._list_headers["Referer"] = f"{origin}/"
        self.add_city_button.wait_for(state="visible", timeout=UI_TIMEOUT)

    def is_cities_visible(self) -> bool:
        try:
            self.add_city_button.wait_for(state="visible", timeout=UI_TIMEOUT)
            return True
        except Exception:
            return False

    # ── Internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        """GET .../cities or .../cities?<query> — the list fetch."""
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"fetch", "xhr"}
            and re.search(r"/cities(\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        """POST .../cities — the create request."""
        return (
            response.request.method == "POST"
            and "/cities" in response.url
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        """PUT .../cities/<id> — the update request."""
        return (
            response.request.method == "PUT"
            and re.search(r"/cities/\d+", response.url) is not None
        )

    @staticmethod
    def _is_delete_response(response: Response) -> bool:
        """DELETE .../cities/<id> — the delete/retrieve request."""
        return (
            response.request.method == "DELETE"
            and re.search(r"/cities/\d+", response.url) is not None
        )

    def _row(self, city_name: str):
        """The single table row for this city, scoped to the table body."""
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(city_name, exact=True)
        ).first

    def _toast_visible(self, pattern: re.Pattern[str]) -> bool:
        try:
            self.page.get_by_text(pattern).first.wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
            return True
        except Exception:
            return False

    def filter_cities(self, query: str) -> None:
        """Type into the search box and block until the debounced list request
        has come back, so the table is genuinely filtered before we touch it."""
        self.search_box.wait_for(state="visible", timeout=UI_TIMEOUT)
        if self.search_box.input_value() == query:
            return
        # A post-create list refresh also matches _is_list_response, so wait for the one carrying the query.
        with self.page.expect_response(
            lambda response: self._is_list_response(response) and query in unquote_plus(response.url),
            timeout=LIST_TIMEOUT,
        ):
            self.search_box.fill(query)

    # ── Actions ──────────────────────────────────────────────────────────────

    def add_city(
        self,
        city_name: str | None = None,
        *,
        is_default: bool = False,
    ) -> str:
        """Create a city and return its name. Verifies both toast and API 201."""
        if city_name is None:
            city_name = generate_random_name("City")

        self.add_city_button.click()
        self.state_select.click()
        self.page.get_by_role("option", name="Tamil Nadu").click()
        self.city_name_input.fill(city_name)
        if is_default:
            self.is_default_checkbox.check()

        with self.page.expect_response(self._is_create_response, timeout=LIST_TIMEOUT) as resp_info:
            self.create_button.click()

        assert resp_info.value.status in (200, 201), (
            f"City create API returned {resp_info.value.status}"
        )
        assert self._toast_visible(CREATED_TOAST), (
            "City success toast should be visible after creation"
        )
        return city_name

    def search_city(self, city_name: str) -> bool:
        """Filter and verify a city row is visible."""
        self.filter_cities(city_name)
        try:
            self._row(city_name).wait_for(state="visible", timeout=SETTLED_TIMEOUT)
            return True
        except Exception:
            return False

    def edit_city(self, old_city_name: str, new_city_name: str) -> bool:
        """Edit a city name and verify via API response and toast."""
        self.filter_cities(old_city_name)
        city_row = self._row(old_city_name)
        city_row.wait_for(state="visible", timeout=UI_TIMEOUT)

        city_row.locator(EDIT_ICON_BUTTON).click(timeout=UI_TIMEOUT)
        self.city_name_input.fill(new_city_name)

        with self.page.expect_response(self._is_update_response, timeout=LIST_TIMEOUT) as resp_info:
            self.update_button.click()

        if resp_info.value.status not in (200, 204):
            return False

        return self._toast_visible(UPDATED_TOAST)

    def verify_city_name(self, city_name: str) -> bool:
        """Reopen Edit because Cities has no View action."""
        self.filter_cities(city_name)
        city_row = self._row(city_name)
        city_row.wait_for(state="visible", timeout=UI_TIMEOUT)
        city_row.locator(EDIT_ICON_BUTTON).click(timeout=UI_TIMEOUT)

        try:
            expect(self.city_name_input).to_have_value(
                city_name, timeout=SETTLED_TIMEOUT
            )
            persisted = True
        except Exception:
            persisted = False

        self.page.get_by_role("button", name="Cancel").click()
        return persisted

    def delete_city(self, city_name: str) -> bool:
        """Soft-delete a city and verify via API response and toast."""
        self.filter_cities(city_name)
        city_row = self._row(city_name)
        city_row.wait_for(state="visible", timeout=UI_TIMEOUT)

        city_row.locator(DELETE_ICON_BUTTON).click(timeout=UI_TIMEOUT)

        with self.page.expect_response(self._is_delete_response, timeout=LIST_TIMEOUT) as resp_info:
            self.page.get_by_role("button", name="Delete City").click()

        if resp_info.value.status not in (200, 204):
            return False

        return self._toast_visible(DELETED_TOAST)

    def ensure_deleted(self, city_name: str) -> bool:
        """Soft-delete the city unless it is already deleted or absent."""
        self.navigate()
        if not self.search_city(city_name):
            return True
        if self._row(city_name).locator(RETRIEVE_ICON_BUTTON).count() > 0:
            return True
        return self.delete_city(city_name)

    def retrieve_city(self, city_name: str) -> bool:
        """Restore a soft-deleted city and verify via API response and toast."""
        city_row = self._row(city_name)
        retrieve_button = city_row.locator(RETRIEVE_ICON_BUTTON)
        retrieve_button.wait_for(state="visible", timeout=UI_TIMEOUT)

        retrieve_button.click(timeout=UI_TIMEOUT)

        with self.page.expect_response(self._is_delete_response, timeout=LIST_TIMEOUT) as resp_info:
            self.page.get_by_role("button", name="Retrieve City").click()

        if resp_info.value.status not in (200, 204):
            return False

        return self._toast_visible(RETRIEVED_TOAST)

    def set_city_as_default(self, city_name: str) -> bool:
        """Mark a city as the default via the edit modal."""
        self.filter_cities(city_name)
        city_row = self._row(city_name)
        city_row.wait_for(state="visible", timeout=UI_TIMEOUT)

        city_row.locator(EDIT_ICON_BUTTON).click(timeout=UI_TIMEOUT)
        self.is_default_checkbox.check()

        with self.page.expect_response(self._is_update_response, timeout=LIST_TIMEOUT) as resp_info:
            self.update_button.click()

        if resp_info.value.status not in (200, 204):
            return False

        return self._toast_visible(UPDATED_TOAST)

    def is_city_default(self, city_name: str) -> bool:
        self.navigate()
        self.filter_cities(city_name)
        city_row = self._row(city_name)
        city_row.wait_for(state="visible", timeout=UI_TIMEOUT)
        return city_row.get_by_text("Yes", exact=True).is_visible()

    def get_default_city_name(self, state_name: str) -> str | None:
        if not self._list_api_url:
            raise AssertionError("Cities list API URL was not captured")

        response = self.page.request.get(
            self._list_api_url,
            headers=self._list_headers,
            params={"is_default": "true", "per_page": 100},
        )
        assert response.status == 200, (
            f"Default City list API returned {response.status}: {response.text()}"
        )
        payload = response.json()
        data = payload.get("data", {})
        cities = data.get("data", data if isinstance(data, list) else [])
        for city in cities:
            if city.get("state", {}).get("name") == state_name:
                return city.get("name")
        return None

    def delete_city_expect_fail(self, city_name: str) -> bool:
        """Attempt to delete a city that is in use and verify it is blocked."""
        self.filter_cities(city_name)
        city_row = self._row(city_name)
        city_row.wait_for(state="visible", timeout=UI_TIMEOUT)

        city_row.locator(DELETE_ICON_BUTTON).click(timeout=UI_TIMEOUT)

        with self.page.expect_response(self._is_delete_response, timeout=LIST_TIMEOUT) as resp_info:
            self.page.get_by_role("button", name="Delete City").click()

        # Expect a non-success status (e.g. 422, 409, 500)
        if resp_info.value.status in (200, 204):
            return False

        # Verify city still exists after navigating back
        self.navigate()
        return self.search_city(city_name)

    # ── Validation helpers ───────────────────────────────────────────────────

    def validate_duplicate_city(self, city_name: str) -> bool:
        """Submit a duplicate city and verify validation feedback + API rejection."""
        self.add_city_button.click()
        self.state_select.click()
        self.page.get_by_role("option", name="Tamil Nadu").click()
        self.city_name_input.fill(city_name)

        with self.page.expect_response(self._is_create_response, timeout=LIST_TIMEOUT) as resp_info:
            self.create_button.click()

        assert resp_info.value.status == 422, (
            f"Expected 422 for duplicate city, got {resp_info.value.status}"
        )

        return has_validation_feedback(
            self.page,
            r"already been taken",
            r"already exists",
            r"duplicate",
        )

    def validate_required_name(self) -> bool:
        submitted_requests = []

        def record_submission(request):
            if (
                request.method == "POST"
                and re.search(r"/cities(?:\?|$)", request.url)
            ):
                submitted_requests.append(request)

        self.add_city_button.click()
        self.page.on("request", record_submission)
        try:
            self.create_button.click()
            error = self.city_name_input.locator("xpath=..").locator(
                ".invalid-feedback"
            )
            error.get_by_text("Name is required", exact=True).wait_for(
                state="visible", timeout=UI_TIMEOUT
            )
        finally:
            self.page.remove_listener("request", record_submission)

        return not submitted_requests

    def validate_name_too_long(self, city_name: str) -> bool:
        submitted_requests = []

        def record_submission(request):
            if (
                request.method == "POST"
                and re.search(r"/cities(?:\?|$)", request.url)
            ):
                submitted_requests.append(request)

        self.add_city_button.click()
        self.city_name_input.fill(city_name)
        self.page.on("request", record_submission)
        try:
            self.create_button.click()
            error = self.city_name_input.locator("xpath=..").locator(
                ".invalid-feedback"
            )
            error.wait_for(state="visible", timeout=UI_TIMEOUT)
            message = error.inner_text()
        finally:
            self.page.remove_listener("request", record_submission)

        return (
            not submitted_requests
            and "100" in message
            and re.search(r"at most|maximum|exceed|long", message, re.I) is not None
        )

    def validate_invalid_city_name(self, city_name: str) -> bool:
        """Submit a city with invalid characters and verify validation feedback."""
        self.add_city_button.click()
        self.state_select.click()
        self.page.get_by_role("option", name="Tamil Nadu").click()
        self.city_name_input.fill(city_name)
        self.create_button.click()

        return has_validation_feedback(
            self.page,
            r"city.*(?:letters|alphabet|invalid|numbers)",
            r"name.*(?:letters|alphabet|invalid|numbers)",
        )
