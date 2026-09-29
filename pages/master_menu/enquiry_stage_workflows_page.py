from __future__ import annotations

import re
from urllib.parse import urlencode, urlsplit

from playwright.sync_api import Locator, Page, Response

from utils.constants import (
    ENQUIRY_STAGE_WORKFLOWS_URL,
    LIST_TIMEOUT,
    UI_TIMEOUT,
)


DELETE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-trash)'
RESTORE_ICON_BUTTON = 'button[title="delete"]:has(i.bi-arrow-clockwise)'


class EnquiryStageWorkflowsPage:
    SCOPE_LABELS = {
        "global": "Global Default",
        "type": "Enquiry Type Override",
        "branch": "Branch Override",
        "branch_type": "Branch + Type Override",
    }

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = ENQUIRY_STAGE_WORKFLOWS_URL
        self._api_list_url: str | None = None

    @staticmethod
    def _is_workflow_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"xhr", "fetch"}
            and re.search(r"/enquiry-stage-workflows(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_workflow_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(
                r"/enquiry-stage-workflows/\d+(?:\?|$)", response.url
            )
            is not None
        )

    @staticmethod
    def _is_stage_create_response(response: Response) -> bool:
        return (
            response.request.method == "POST"
            and re.search(r"/enquiry-stages(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_stage_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/enquiry-stages/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_stage_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH", "POST"}
            and re.search(r"/enquiry-stages/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_stage_delete_response(response: Response) -> bool:
        return (
            response.request.method == "DELETE"
            and re.search(r"/enquiry-stages/\d+(?:\?|$)", response.url)
            is not None
        )

    def navigate(self) -> None:
        with self.page.expect_response(
            lambda response: "enquiry-stage-workflows" in response.url
            and response.request.method == "GET"
            and response.request.resource_type in ("xhr", "fetch")
            and "/resolve" not in response.url
        ) as response_info:
            self.page.goto(self.url)
        self._api_list_url = response_info.value.url.split("?", 1)[0]
        self.page.get_by_role("button", name="Add Workflow").wait_for(
            state="visible", timeout=10000
        )

    def is_workflows_visible(self) -> bool:
        return self.page.get_by_role("button", name="Add Workflow").is_visible()

    def open_add_form(self) -> Locator:
        self.page.get_by_role("button", name="Add Workflow").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=5000)
        return modal

    def select_scope(self, modal: Locator, scope: str) -> None:
        modal.locator("input[name='scope']").locator("xpath=..").locator(
            ".react-select__input-container"
        ).click()
        self.page.get_by_role("option", name=self.SCOPE_LABELS[scope], exact=True).click()

    def select_form_option(self, modal: Locator, field: str, option: str) -> None:
        modal.locator(f"input[name='{field}']").locator("xpath=..").locator(
            ".react-select__input-container"
        ).click()
        self.page.get_by_role("option", name=option, exact=True).click()

    def add_workflow(
        self,
        scope: str,
        workflow_name: str,
        enquiry_type: str | None = None,
        branch: str | None = None,
    ) -> None:
        modal = self.open_add_form()
        self.select_scope(modal, scope)

        if scope in ("type", "branch_type"):
            if enquiry_type is None:
                raise ValueError("enquiry_type is required for this workflow scope")
            self.select_form_option(modal, "enquiry_type_id", enquiry_type)

        if scope in ("branch", "branch_type"):
            if branch is None:
                raise ValueError("branch is required for this workflow scope")
            self.select_form_option(modal, "branch_id", branch)

        if scope != "global":
            modal.locator("input[name='workflow_name']").fill(workflow_name)

        modal.get_by_role("button", name="Create", exact=True).click()
        modal.wait_for(state="hidden", timeout=10000)

    def close_form(self, modal: Locator) -> None:
        if not modal.is_visible():
            return
        modal.get_by_role("button", name="Cancel", exact=True).click()
        modal.wait_for(state="hidden", timeout=5000)

    def search_workflow(self, name: str) -> bool:
        search_box = self.page.get_by_placeholder("Search workflows...")
        if search_box.input_value() != name:
            with self.page.expect_response(
                self._is_workflow_list_response, timeout=LIST_TIMEOUT
            ):
                search_box.fill(name)
        try:
            self.workflow_row(name).wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def workflow_row(self, name: str) -> Locator:
        return self.page.locator("table tbody tr", has=self.page.get_by_text(name, exact=True))

    def get_workflow_row_data(self, name: str) -> dict[str, str]:
        row = self.workflow_row(name)
        row.wait_for(state="visible", timeout=5000)
        cells = row.locator("td")
        return {
            "name": cells.nth(0).inner_text().strip(),
            "scope": cells.nth(1).inner_text().strip(),
            "enquiry_type": cells.nth(2).inner_text().strip(),
            "branch": cells.nth(3).inner_text().strip(),
            "stages": cells.nth(4).inner_text().strip(),
            "active": cells.nth(5).inner_text().strip(),
        }

    def open_edit_form(self, name: str) -> Locator:
        self.search_workflow(name)
        self.workflow_row(name).get_by_title("edit").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=5000)
        modal.get_by_text("Workflow Scope", exact=False).wait_for(
            state="visible", timeout=5000
        )
        return modal

    @staticmethod
    def _selected_form_option(modal: Locator, field: str) -> str:
        return (
            modal.locator(f"input[name='{field}']")
            .locator("xpath=..")
            .locator(".react-select__single-value")
            .inner_text()
            .strip()
        )

    def edit_workflow(
        self, old_name: str, new_name: str, *, active: bool
    ) -> bool:
        modal = self.open_edit_form(old_name)
        modal.locator("input[name='workflow_name']").fill(new_name)
        modal.get_by_role("checkbox", name="Active").set_checked(active)
        with self.page.expect_response(
            self._is_workflow_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Update", exact=True).click()
        modal.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 201, 204}

    def get_workflow_edit_values(self, name: str) -> dict[str, str | bool]:
        modal = self.open_edit_form(name)
        values: dict[str, str | bool] = {
            "workflow_name": modal.locator(
                "input[name='workflow_name']"
            ).input_value(),
            "active": modal.get_by_role("checkbox", name="Active").is_checked(),
        }
        if modal.locator("input[name='enquiry_type_id']").count():
            values["enquiry_type"] = self._selected_form_option(
                modal, "enquiry_type_id"
            )
        if modal.locator("input[name='branch_id']").count():
            values["branch"] = self._selected_form_option(modal, "branch_id")
        self.close_form(modal)
        return values

    def manage_workflow(self, name: str) -> None:
        self.search_workflow(name)
        self.workflow_row(name).get_by_title("manage").click()
        self.page.get_by_role("button", name="Add Stage").wait_for(
            state="visible", timeout=10000
        )

    def delete_workflow(self, name: str) -> bool:
        self.search_workflow(name)
        self.workflow_row(name).get_by_title("delete").click()
        modal = self.page.get_by_role("dialog")
        modal.get_by_role("button", name="Delete Workflow").click()
        try:
            self.page.get_by_text("Deleted successfully.").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def restore_workflow(self, name: str) -> bool:
        self.search_workflow(name)
        self.workflow_row(name).get_by_title("delete").click()
        modal = self.page.get_by_role("dialog")
        modal.get_by_role("button", name="Restore Workflow").click()
        try:
            self.page.get_by_text("Retrieved successfully.").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def add_stage(
        self,
        name: str,
        sort_order: int,
        *,
        default: bool = False,
        final: bool = False,
        converted: bool = False,
        cancelled: bool = False,
        description: str | None = None,
    ) -> Response:
        self.page.get_by_role("button", name="Add Stage").click()
        drawer = self.page.get_by_role("dialog", name="Add Stage")
        drawer.wait_for(state="visible", timeout=5000)
        drawer.locator("input[name='stage_name']").fill(name)
        drawer.locator("input[name='sort_order']").fill(str(sort_order))
        if description is not None:
            drawer.locator("textarea[name='description']").fill(description)

        flags = {
            "Default Stage": default,
            "Final Stage": final,
            "Converted Stage": converted,
            "Cancelled / Lost Stage": cancelled,
        }
        for label, enabled in flags.items():
            if enabled:
                drawer.get_by_role("checkbox", name=label).check()

        with self.page.expect_response(
            self._is_stage_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            drawer.get_by_role("button", name="Create", exact=True).click()
        drawer.wait_for(state="hidden", timeout=10000)
        return response_info.value

    def add_complete_stage_set(self, prefix: str) -> None:
        self.add_stage(f"{prefix} New", 1, default=True)
        self.add_stage(f"{prefix} Converted", 2, final=True, converted=True)
        self.add_stage(f"{prefix} Cancelled", 3, final=True, cancelled=True)

    def stage_row(self, name: str) -> Locator:
        return self.page.locator("table tbody tr", has=self.page.get_by_text(name, exact=True))

    def get_stage_row_data(self, name: str) -> dict[str, str]:
        row = self.stage_row(name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)
        cells = row.locator("td")
        return {
            "sort_order": cells.nth(0).inner_text().strip(),
            "name": cells.nth(1).inner_text().strip(),
            "active": cells.nth(3).inner_text().strip(),
            "default": cells.nth(4).inner_text().strip(),
            "final": cells.nth(5).inner_text().strip(),
            "converted": cells.nth(6).inner_text().strip(),
            "cancelled": cells.nth(7).inner_text().strip(),
        }

    def edit_stage(
        self,
        old_name: str,
        new_name: str,
        *,
        sort_order: int,
        description: str,
    ) -> bool:
        row = self.stage_row(old_name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_stage_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").click()
        drawer = self.page.get_by_role("dialog", name="Edit Stage")
        drawer.wait_for(state="visible", timeout=UI_TIMEOUT)
        drawer.locator("input[name='stage_name']").fill(new_name)
        drawer.locator("input[name='sort_order']").fill(str(sort_order))
        drawer.locator("textarea[name='description']").fill(description)
        with self.page.expect_response(
            self._is_stage_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            drawer.get_by_role("button", name="Update", exact=True).click()
        drawer.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 201, 204}

    def get_stage_edit_values(self, name: str) -> dict[str, str]:
        row = self.stage_row(name)
        with self.page.expect_response(
            self._is_stage_show_response, timeout=LIST_TIMEOUT
        ):
            row.get_by_title("edit").click()
        drawer = self.page.get_by_role("dialog", name="Edit Stage")
        drawer.wait_for(state="visible", timeout=UI_TIMEOUT)
        values = {
            "name": drawer.locator("input[name='stage_name']").input_value(),
            "sort_order": drawer.locator(
                "input[name='sort_order']"
            ).input_value(),
            "description": drawer.locator(
                "textarea[name='description']"
            ).input_value(),
        }
        drawer.get_by_role("button", name="Cancel", exact=True).click()
        drawer.wait_for(state="hidden", timeout=UI_TIMEOUT)
        return values

    def delete_stage(self, name: str) -> bool:
        self.stage_row(name).locator(DELETE_ICON_BUTTON).click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_stage_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Delete Stage").click()
        modal.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 204}

    def restore_stage(self, name: str) -> bool:
        button = self.stage_row(name).locator(RESTORE_ICON_BUTTON)
        button.wait_for(state="visible", timeout=UI_TIMEOUT)
        button.click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_stage_delete_response, timeout=LIST_TIMEOUT
        ) as response_info:
            modal.get_by_role("button", name="Restore Stage").click()
        modal.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        restored = response_info.value.status in {200, 204}
        if restored:
            self.stage_row(name).wait_for(
                state="visible", timeout=LIST_TIMEOUT
            )
        return restored

    def add_replacement_default_stage(self, name: str, sort_order: int) -> bool:
        self.page.get_by_role("button", name="Add Stage").click()
        drawer = self.page.get_by_role("dialog", name="Add Stage")
        drawer.wait_for(state="visible", timeout=UI_TIMEOUT)
        drawer.locator("input[name='stage_name']").fill(name)
        drawer.locator("input[name='sort_order']").fill(str(sort_order))
        drawer.get_by_role("checkbox", name="Default Stage").check()
        with self.page.expect_response(
            self._is_stage_create_response, timeout=LIST_TIMEOUT
        ) as response_info:
            drawer.get_by_role("button", name="Create", exact=True).click()
        drawer.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 201}

    def filter_by_scope(self, scope_label: str) -> None:
        self.page.get_by_role("button", name="Filters").click()
        self.page.get_by_label("Scope").select_option(label=scope_label)
        self.page.wait_for_timeout(700)

    def resolve_workflow(self, enquiry_type_id: int, branch_id: int | None = None) -> dict:
        if self._api_list_url is None:
            self.navigate()
        params = {"enquiry_type_id": enquiry_type_id}
        if branch_id is not None:
            params["branch_id"] = branch_id
        response = self.page.request.get(
            f"{self._api_list_url}/resolve?{urlencode(params)}",
            headers=self._api_headers(),
        )
        assert response.ok, f"Workflow resolve failed ({response.status}): {response.text()}"
        return response.json()["data"]

    def get_dropdown_id(self, resource: str, name: str) -> int:
        if self._api_list_url is None:
            self.navigate()
        api_root = self._api_list_url.rsplit("/enquiry-stage-workflows", 1)[0]
        response = self.page.request.get(
            f"{api_root}/lists/{resource}",
            headers=self._api_headers(),
        )
        assert response.ok, f"Failed to load {resource} ({response.status}): {response.text()}"
        for item in response.json().get("data", []):
            if item.get("name") == name:
                return int(item["id"])
        raise AssertionError(f"{name!r} was not found in {resource} dropdown data")

    def _api_headers(self) -> dict[str, str]:
        token = self.page.evaluate("localStorage.getItem('access_token')")
        current = urlsplit(self.page.url)
        origin = f"{current.scheme}://{current.netloc}"
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Origin": origin,
            "Referer": f"{origin}/",
        }
