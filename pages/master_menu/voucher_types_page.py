from __future__ import annotations

import re

from playwright.sync_api import Page, Response

from pages.common.base_page import BasePage
from pages.common.form_page import has_validation_feedback
from utils.tenants import RETAIL, Tenant
from utils.constants import (
    LIST_TIMEOUT,
    UI_TIMEOUT,
)


class VoucherTypesPage(BasePage):
    PATH = "/voucher-types"

    def __init__(self, page: Page, tenant: Tenant = RETAIL) -> None:
        super().__init__(page, tenant)

    # Legacy alias: unmigrated callers still assign voucher_types_url directly.
    @property
    def voucher_types_url(self) -> str:
        return self.url

    @voucher_types_url.setter
    def voucher_types_url(self, value: str) -> None:
        self.url = value

    @property
    def dialog(self):
        return self.page.get_by_role("dialog")

    @staticmethod
    def _is_list_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and response.request.resource_type in {"xhr", "fetch"}
            and re.search(r"/voucher-types(?:\?|$)", response.url) is not None
        )

    @staticmethod
    def _is_show_response(response: Response) -> bool:
        return (
            response.request.method == "GET"
            and re.search(r"/voucher-types/\d+(?:\?|$)", response.url)
            is not None
        )

    @staticmethod
    def _is_update_response(response: Response) -> bool:
        return (
            response.request.method in {"PUT", "PATCH"}
            and re.search(r"/voucher-types/\d+(?:\?|$)", response.url)
            is not None
        )

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.get_by_text("Payment Voucher", exact=True).wait_for(
            state="visible", timeout=LIST_TIMEOUT
        )

    def is_voucher_types_visible(self) -> bool:
        return self.page.get_by_text("Payment Voucher", exact=True).is_visible()

    def _row(self, name: str):
        return self.page.locator("tbody tr").filter(
            has=self.page.get_by_text(name, exact=True)
        ).first

    def _open_edit(self, name: str) -> dict:
        row = self._row(name)
        row.wait_for(state="visible", timeout=UI_TIMEOUT)
        with self.page.expect_response(
            self._is_show_response, timeout=LIST_TIMEOUT
        ) as response_info:
            row.get_by_title("edit").click()
        self.dialog.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.dialog.locator('input[name="prefix"]').wait_for(
            state="visible", timeout=LIST_TIMEOUT
        )
        return response_info.value.json()["data"]

    def _selected_label(self, field: str) -> str:
        return (
            self.dialog.locator(f'input[name="{field}"]')
            .locator("xpath=..")
            .locator(".react-select__single-value")
            .inner_text()
            .strip()
        )

    def _select(self, field: str, label: str) -> None:
        container = self.dialog.locator(f'input[name="{field}"]').locator(
            "xpath=.."
        )
        container.locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=label, exact=True).click()

    def _close(self) -> None:
        self.dialog.get_by_role("button", name="Cancel", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=UI_TIMEOUT)

    def get_configuration(self, name: str) -> dict[str, str | bool]:
        data = self._open_edit(name)
        numbering_labels = {
            "automatic": "Automatic Sequence",
            "manual": "Manual Entry",
        }
        reset_labels = {
            "never": "Never",
            "yearly": "Yearly (Financial Year)",
        }
        values: dict[str, str | bool] = {
            "prefix": data.get("prefix") or "",
            "numbering_method": numbering_labels.get(data.get("numbering_method", "automatic"), "Automatic Sequence"),
            "reset_frequency": reset_labels.get(data.get("reset_frequency", "yearly"), "Yearly (Financial Year)"),
            "branch_wise_numbering": bool(data.get("branch_wise_numbering", False)),
            "allow_post_dated": bool(data.get("allow_post_dated", False)),
            "affects_inventory": bool(data.get("affects_inventory", False)),
            "is_optional": bool(data.get("is_optional", False)),
            "print_template": data.get("print_template") or "",
        }
        self._close()
        return values

    def get_sample_number_preview(self) -> str:
        code_el = self.dialog.locator("code")
        code_el.wait_for(state="visible", timeout=UI_TIMEOUT)
        return code_el.inner_text().strip()

    def edit_voucher_type(
        self, name: str, config: dict[str, str | bool]
    ) -> bool:
        self._open_edit(name)
        self.dialog.locator('input[name="prefix"]').fill(str(config["prefix"]))
        self._select("numbering_method", str(config["numbering_method"]))
        if config["numbering_method"] != "Manual Entry":
            self._select("reset_frequency", str(config["reset_frequency"]))

        for key, label in (
            ("branch_wise_numbering", "Branch-wise numbering (separate sequence per branch)"),
            ("allow_post_dated", "Allow post-dated"),
            ("affects_inventory", "Affects inventory"),
            ("is_optional", "Is optional"),
        ):
            if key in config:
                checkbox = self.dialog.get_by_role("checkbox", name=label)
                checkbox.set_checked(bool(config[key]))

        if "print_template" in config:
            self.dialog.locator('input[name="print_template"]').fill(
                str(config["print_template"])
            )
        with self.page.expect_response(
            self._is_update_response, timeout=LIST_TIMEOUT
        ) as response_info:
            self.dialog.get_by_role("button", name="Save", exact=True).click()
        self.dialog.wait_for(state="hidden", timeout=LIST_TIMEOUT)
        return response_info.value.status in {200, 201, 204}

    def manual_numbering_sets_never(self, name: str) -> bool:
        self._open_edit(name)
        self._select("numbering_method", "Manual Entry")
        reset_control = self.dialog.get_by_text(
            "Reset frequency", exact=True
        ).locator("xpath=..").locator(".react-select__control--is-disabled")
        result = (
            reset_control.count() == 1
            and self.dialog.get_by_text(
                "Reset applies only to automatic numbering.", exact=True
            ).is_visible()
        )
        self._close()
        return result

    def display_fields_are_read_only(self, name: str) -> bool:
        data = self._open_edit(name)
        # Verify name, slug, sort_order are rendered in read-only text container, not as form inputs
        no_inputs = all(
            self.dialog.locator(f'input[name="{field}"]').count() == 0
            for field in ("name", "slug", "sort_order", "last_number", "reset_date")
        )
        has_display_text = self.dialog.get_by_text(data["name"], exact=True).is_visible()
        self._close()
        return no_inputs and has_display_text

    def validate_prefix_invalid_pattern(self, name: str) -> bool:
        self._open_edit(name)
        requests: list[str] = []

        def capture(request) -> None:
            if request.method in {"PUT", "PATCH"} and re.search(
                r"/voucher-types/\d+(?:\?|$)", request.url
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            # Slashes or spaces violate PREFIX_PATTERN /^[A-Za-z0-9._-]+$/
            self.dialog.locator('input[name="prefix"]').fill("PAY / 01")
            self.dialog.get_by_role("button", name="Save", exact=True).click()
            feedback = has_validation_feedback(
                self.dialog, r"Prefix may only contain|letters, numbers"
            )
            valid = feedback and not requests
        finally:
            self.page.remove_listener("request", capture)
        self._close()
        return bool(valid)

    def validate_prefix_max_length(self, name: str) -> bool:
        self._open_edit(name)
        requests: list[str] = []

        def capture(request) -> None:
            if request.method in {"PUT", "PATCH"} and re.search(
                r"/voucher-types/\d+(?:\?|$)", request.url
            ):
                requests.append(request.url)

        self.page.on("request", capture)
        try:
            self.dialog.locator('input[name="prefix"]').fill("P" * 15)
            self.dialog.get_by_role("button", name="Save", exact=True).click()
            feedback = has_validation_feedback(
                self.dialog, r"prefix.*(?:10|maximum|max|characters)"
            )
            valid = feedback and not requests
        finally:
            self.page.remove_listener("request", capture)
        self._close()
        return bool(valid)
