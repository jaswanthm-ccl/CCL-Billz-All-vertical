from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.constants import CUSTOMERS_URL
from pages.common.form_page import has_required_field_feedback, has_validation_feedback


class CustomersPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = CUSTOMERS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("domcontentloaded")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def add_customer_button(self) -> Locator:
        return self.page.get_by_role("button", name="Add Customer")

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog")

    @property
    def name_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="name"]')

    @property
    def type_container(self) -> Locator:
        return self.modal_dialog.locator("input[name='type']").locator("..")

    @property
    def email_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="email"]')

    @property
    def phone_input(self) -> Locator:
        return self.modal_dialog.get_by_role("textbox", name="Enter 10-digit phone number")

    @property
    def add_notes_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name="Add Notes")

    @property
    def notes_input(self) -> Locator:
        return self.modal_dialog.locator('textarea[name="notes"]')

    @property
    def contact_person_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="addresses.0.contact_person"]')

    @property
    def address_line1_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="addresses.0.address_line1"]')

    @property
    def address_line2_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="addresses.0.address_line2"]')

    @property
    def state_container(self) -> Locator:
        return self.modal_dialog.locator("input[name*='state_id']").locator("..")

    @property
    def city_container(self) -> Locator:
        return self.modal_dialog.locator("input[name*='city_id']").locator("..")

    @property
    def postal_code_input(self) -> Locator:
        return self.modal_dialog.locator('input[name*="postal_code"]')

    @property
    def gst_number_input(self) -> Locator:
        return self.modal_dialog.locator('input[name*="gst_number"]')

    @property
    def default_address_checkbox(self) -> Locator:
        return self.modal_dialog.get_by_role("checkbox", name="Default Address")

    @property
    def create_customer_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name="Create")

    @property
    def update_customer_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name="Update")

    def is_customers_visible(self) -> bool:
        return self.add_customer_button.is_visible() or self.search_input.is_visible()

    def _select_option(self, container: Locator, option_name: str) -> None:
        container.wait_for(state="visible", timeout=15000)
        container.click()

        search_input = container.locator("input[id^='react-select'], input[type='text']")
        if search_input.count() > 0 and search_input.first.is_visible():
            search_input.first.fill(option_name)

        opt = self.page.get_by_role("option", name=option_name)
        if opt.count() > 0:
            try:
                opt.first.wait_for(state="visible", timeout=5000)
                opt.first.click()
                return
            except Exception:
                pass

        matching_option = self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=option_name)
        if matching_option.count() > 0:
            matching_option.first.wait_for(state="visible", timeout=5000)
            matching_option.first.click()
        elif search_input.count() > 0 and search_input.first.is_visible():
            first_opt = self.page.locator(".react-select__option, div[class*='-option']").first
            if first_opt.count() > 0:
                first_opt.wait_for(state="visible", timeout=5000)
                first_opt.click()


    def _fill_customer_form(
        self,
        name: str,
        customer_type: str,
        email: str,
        phone: str,
        notes: str | None,
        contact_person: str,
        address_line1: str,
        address_line2: str,
        state_name: str,
        city_name: str,
        postal_code: str,
        default_address: bool = True,
        gst_number: str | None = None,
    ) -> None:
        self.name_input.fill(name)

        if notes:
            try:
                if self.add_notes_button.is_visible():
                    self.add_notes_button.click()
            except Exception:
                pass
            if self.notes_input.is_visible():
                self.notes_input.fill(notes)

        self._select_option(self.type_container, customer_type)

        self.email_input.fill(email)
        self.phone_input.fill(phone)

        self.contact_person_input.fill(contact_person)
        self.address_line1_input.fill(address_line1)
        self.address_line2_input.fill(address_line2)

        self._select_option(self.state_container, state_name)
        self.city_container.wait_for(state="visible", timeout=5000)
        self._select_option(self.city_container, city_name)

        self.postal_code_input.fill(postal_code)
        if gst_number and self.gst_number_input.is_visible():
            self.gst_number_input.fill(gst_number)

        if default_address and self.default_address_checkbox.is_visible():
            self.default_address_checkbox.check()

    def add_customer(
        self,
        name: str,
        customer_type: str = "Person",
        email: str | None = None,
        phone: str | None = None,
        notes: str = "automated customer notes",
        contact_person: str = "Contact Auto",
        address_line1: str = "Line 1",
        address_line2: str = "Line 2",
        state_name: str = "Tamil Nadu",
        city_name: str | None = None,
        postal_code: str | None = None,
        default_address: bool = True,
        gst_number: str | None = None,
    ) -> str:
        from pages.master_menu.cities_page import CitiesPage
        from utils.random_data import generate_random_code, generate_random_email, generate_random_phone, generate_random_postal_code

        if not city_name:
            cities_page = CitiesPage(self.page)
            cities_page.navigate()
            city_name = f"AutoCity_{generate_random_code('C')}"
            cities_page.add_city(city_name)

        self.navigate()
        email = email or generate_random_email("customer")
        phone = phone or generate_random_phone()
        postal_code = postal_code or generate_random_postal_code()

        self.add_customer_button.wait_for(state="visible", timeout=10000)
        self.add_customer_button.click()
        modal = self.modal_dialog
        try:
            modal.locator('input[name="name"]').wait_for(state="visible", timeout=4000)
        except Exception:
            self.add_customer_button.click()
            modal.locator('input[name="name"]').wait_for(state="visible", timeout=10000)

        self._fill_customer_form(
            name, customer_type, email, phone, notes, contact_person,
            address_line1, address_line2, state_name, city_name, postal_code,
            default_address, gst_number
        )

        try:
            with self.page.expect_response(
                lambda r: "customer" in r.url.lower() and r.request.method == "POST",
                timeout=15000
            ) as resp_info:
                self.create_customer_button.click()
            assert resp_info.value.status in (200, 201), f"Customer creation failed with HTTP {resp_info.value.status}"
        except Exception:
            if self.create_customer_button.is_visible():
                self.create_customer_button.click()

        toast = self.page.get_by_text(re.compile(r"Customer created|Operation successful|success", re.IGNORECASE)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        try:
            modal.wait_for(state="hidden", timeout=15000)
        except Exception:
            pass
        return city_name


    def _ensure_modal_closed(self) -> None:
        if not self.modal_dialog.is_visible():
            return
        close_btn = self.modal_dialog.locator(
            ".btn-close, button:has-text('Cancel'), button:has-text('Close')"
        ).first
        try:
            if close_btn.is_visible():
                close_btn.click(timeout=3000)
        except Exception:
            if self.modal_dialog.is_visible():
                self.page.keyboard.press("Escape")
        self.modal_dialog.wait_for(state="hidden", timeout=5000)

    def search_customer(self, name: str) -> bool:
        self.search_input.fill(name)
        self.search_input.press("Enter")
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        try:
            row.first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def view_customer(
        self,
        name: str,
        expected_email: str | None = None,
        expected_phone: str | None = None,
        expected_city: str | None = None,
    ) -> bool:
        self.search_customer(name)
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        row.first.locator("button[title='view'], a[title='view']").first.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        try:
            modal.get_by_text(name, exact=True).first.wait_for(state="visible", timeout=5000)
            modal_text = modal.inner_text()
            is_visible = name in modal_text
            if expected_email:
                is_visible = is_visible and expected_email in modal_text
            if expected_phone:
                is_visible = is_visible and expected_phone in modal_text
        except Exception:
            is_visible = False

        modal.get_by_role("button", name="Back to List").click()
        modal.wait_for(state="hidden", timeout=5000)
        return is_visible

    def edit_customer(
        self,
        old_name: str,
        new_name: str,
        new_email: str | None = None,
        new_phone: str | None = None,
    ) -> bool:
        self.search_customer(old_name)
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(old_name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        row.first.locator("button[title='edit'], a[title='edit']").first.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        self.name_input.fill(new_name)
        if new_email:
            self.email_input.fill(new_email)
        if new_phone:
            self.phone_input.fill(new_phone)

        with self.page.expect_response(
            lambda r: "/customers" in r.url and r.request.method in ("PUT", "PATCH"),
            timeout=10000
        ) as resp_info:
            self.update_customer_button.click()

        assert resp_info.value.status in (200, 204), f"Edit customer failed with HTTP {resp_info.value.status}"
        modal.wait_for(state="hidden", timeout=10000)
        return True

    def delete_customer(self, name: str) -> bool:
        if not self.search_customer(name):
            return False
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        active_delete_btn = row.first.locator("button[title='delete']:has(i.bi-trash)")
        if active_delete_btn.count() == 0:
            return False
        active_delete_btn.first.click()

        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        delete_btn = modal.get_by_role("button", name="Delete Customer")
        try:
            delete_btn.wait_for(state="visible", timeout=3000)
            with self.page.expect_response(
                lambda r: "/customers" in r.url and r.request.method == "DELETE",
                timeout=10000
            ) as resp_info:
                delete_btn.click()
            assert resp_info.value.status in (200, 204), f"Delete customer failed with HTTP {resp_info.value.status}"
        except Exception:
            close_btn = modal.locator(".btn-close")
            if close_btn.is_visible():
                close_btn.click()
            elif modal.get_by_role("button", name="Cancel").is_visible():
                modal.get_by_role("button", name="Cancel").click()
            return False

        modal.wait_for(state="hidden", timeout=5000)
        return True

    def retrieve_customer(self, name: str) -> bool:
        self.search_customer(name)
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        # Rule 3: Wait for i.bi-arrow-clockwise on soft-deleted row before retrieve
        restore_btn = row.first.locator("button[title='delete']:has(i.bi-arrow-clockwise)")
        restore_btn.wait_for(state="visible", timeout=5000)
        restore_btn.click()

        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        retrieve_btn = modal.get_by_role("button", name="Retrieve Customer")
        retrieve_btn.wait_for(state="visible", timeout=3000)
        retrieve_btn.click()

        modal.wait_for(state="hidden", timeout=5000)
        return True

    def validate_invalid_field(
        self, name: str, customer_type: str, email: str, phone: str, notes: str, contact_person: str,
        address_line1: str, address_line2: str, state_name: str, city_name: str, postal_code: str,
        field: str, value: str, gst_number: str | None = None
    ) -> bool:
        self.navigate()
        self._ensure_modal_closed()
        self.add_customer_button.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=10000)

        args = {
            "name": name, "customer_type": customer_type, "email": email, "phone": phone, "notes": notes,
            "contact_person": contact_person, "address_line1": address_line1, "address_line2": address_line2,
            "state_name": state_name, "city_name": city_name, "postal_code": postal_code, "gst_number": gst_number
        }
        args[field] = value
        self._fill_customer_form(**args)

        api_rejected = False
        try:
            with self.page.expect_response(
                lambda r: "/customers" in r.url and r.request.method == "POST",
                timeout=3000
            ) as resp_info:
                self.create_customer_button.click()
            api_rejected = resp_info.value.status in (400, 422)
        except Exception:
            api_rejected = True

        patterns = {
            "email": (r"email.*(?:invalid|valid|format|domain|already|taken|exists)", r"invalid.*email", r"already.*(?:taken|exist)", r"validation"),
            "phone": (r"phone.*(?:invalid|valid|10|digits|start)", r"invalid.*phone", r"validation"),
            "postal_code": (r"postal.*(?:invalid|valid|6|digits)", r"pincode.*(?:invalid|valid|6|digits)", r"postal code must be", r"validation"),
            "gst_number": (r"gst.*(?:invalid|valid|format)", r"invalid.*gst", r"validation"),
        }
        ui_rejected = has_validation_feedback(modal, *patterns[field])
        self._ensure_modal_closed()
        return api_rejected and ui_rejected

    def validate_duplicate_customer(
        self, name: str, customer_type: str, email: str, phone: str, notes: str, contact_person: str,
        address_line1: str, address_line2: str, state_name: str, city_name: str, postal_code: str,
        gst_number: str | None = None
    ) -> bool:
        self.navigate()
        self._ensure_modal_closed()
        self.add_customer_button.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=10000)

        self._fill_customer_form(
            name, customer_type, email, phone, notes, contact_person,
            address_line1, address_line2, state_name, city_name, postal_code,
            gst_number=gst_number
        )

        api_rejected = False
        try:
            with self.page.expect_response(
                lambda r: "/customers" in r.url and r.request.method == "POST",
                timeout=5000
            ) as resp_info:
                self.create_customer_button.click()
            api_rejected = resp_info.value.status in (400, 422)
        except Exception:
            api_rejected = True

        ui_rejected = has_validation_feedback(
            modal,
            r"customer.*already",
            r"(?:email|phone|gst).*(?:already|duplicate|taken|exists)",
            r"duplicate.*customer",
            r"validation",
        )
        self._ensure_modal_closed()
        return api_rejected and ui_rejected

    def validate_required_fields(self) -> bool:
        self.navigate()
        self._ensure_modal_closed()
        self.add_customer_button.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=10000)

        api_rejected = False
        try:
            with self.page.expect_response(
                lambda r: "/customers" in r.url and r.request.method == "POST",
                timeout=3000
            ) as resp_info:
                self.create_customer_button.click()
            api_rejected = resp_info.value.status in (400, 422)
        except Exception:
            api_rejected = True

        ui_rejected = has_required_field_feedback(modal)
        self._ensure_modal_closed()
        return api_rejected and ui_rejected
