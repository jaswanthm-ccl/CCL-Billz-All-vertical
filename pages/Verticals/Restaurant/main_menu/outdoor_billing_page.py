"""Restaurant Outdoor Billing Page Object.

Route: RES_OUTDOOR_BILLING_URL (/outdoor-billing)
Handles:
- Outdoor Catering booking lifecycle (creation, menu dish assignment, delivery scheduling)
- Customer, Branch, and Item React-Select configuration
- Advance payment settlement & discount calculation
- View booking dialog (reading customer, dates, status/payment badges, items, amounts)
- Edit booking (updating item quantities, submitting updates)
- Record payment settlement against updated balance
- Close bill workflow
- Cancel booking & refund workflow
- Table row assertions and search filtering
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_OUTDOOR_BILLING_URL


class OutdoorBillingPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_OUTDOOR_BILLING_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def add_booking_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Booking", re.I)).or_(
            self.page.locator("a, button").filter(has_text="Add Booking")
        ).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".modal-dialog, div[role='dialog']")).first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first

    # ── Actions ─────────────────────────────────────────────────────────────

    def create_booking(
        self,
        branch_name: str,
        dish_name: str,
        customer_name: str | None = None,
        dish_code: str | None = None,
        quantity: str = "1",
        unit_price: str | None = None,
        delivery_date: str | None = None,
        delivery_time: str = "14:00",
        advance_amount: str = "0",
        advance_payment_mode: str = "cash",
        advance_notes: str = "Initial advance",
        notes: str = "Outdoor catering order",
    ) -> dict[str, Any]:
        """Creates an outdoor catering booking and returns API response data."""
        delivery_date = delivery_date or (date.today() + timedelta(days=1)).isoformat()
        self.add_booking_button.wait_for(state="visible", timeout=5000)
        self.add_booking_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        # 1. Branch Select
        branch_ctrl = self.modal_dialog.locator(".col-md-4, .col-md-6, .mb-3").filter(
            has_text=re.compile(r"^Branch", re.I)
        ).locator(".react-select__control").first
        branch_ctrl.wait_for(state="visible", timeout=5000)
        branch_ctrl.click()
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(branch_name[:10])
        self.page.wait_for_timeout(300)
        opt_b = self.page.locator(".react-select__option").filter(has_text=branch_name).first
        if opt_b.is_visible():
            opt_b.click()
        else:
            self.page.keyboard.press("Enter")

        # 2. Customer Select
        cust_ctrl = self.modal_dialog.locator(".col-md-4, .col-md-6, .mb-3").filter(
            has_text=re.compile(r"^Customer", re.I)
        ).locator(".react-select__control").first
        cust_ctrl.wait_for(state="visible", timeout=5000)
        cust_ctrl.click()
        self.page.wait_for_timeout(300)
        if customer_name:
            self.page.keyboard.type(customer_name[:10])
            self.page.wait_for_timeout(300)
            opt_c = self.page.locator(".react-select__option").filter(has_text=customer_name).first
            if opt_c.is_visible():
                opt_c.click()
            else:
                self.page.locator(".react-select__option").first.click()
        else:
            self.page.locator(".react-select__option").first.click()

        # 3. Delivery Date & Time
        del_date = self.modal_dialog.locator("input[name='delivery_date']")
        if del_date.is_visible() and delivery_date:
            del_date.fill(delivery_date)

        del_time = self.modal_dialog.locator("input[name='delivery_time']")
        if del_time.is_visible() and delivery_time:
            del_time.fill(delivery_time)

        # 4. Product Select in table
        code_inp = self.modal_dialog.locator("input.restaurant-pos-code-input, input[placeholder='Enter code']").first
        product_row = self.modal_dialog.locator("table tbody tr").filter(
            has_text=re.compile(re.escape(dish_name), re.I)
        ).first
        if dish_code and code_inp.is_visible():
            code_inp.fill(dish_code)
            code_inp.press("Enter")
            try:
                product_row.wait_for(state="visible", timeout=3000)
            except Exception:
                pass

        if not product_row.is_visible():
            prod_ctrl = self.modal_dialog.locator(".react-select__control").filter(
                has_text=re.compile(r"Select / Search Product", re.I)
            ).first
            if not prod_ctrl.is_visible():
                prod_ctrl = self.modal_dialog.locator(
                    ".restaurant-pos-product-select .react-select__control"
                ).first
            prod_ctrl.wait_for(state="visible", timeout=5000)
            prod_ctrl.click()
            prod_ctrl.locator("input").first.fill(dish_name)
            opt_p = self.page.locator(".react-select__option").filter(
                has_text=re.compile(re.escape(dish_name), re.I)
            ).first
            opt_p.wait_for(state="visible", timeout=5000)
            opt_p.click()

        product_row.wait_for(state="visible", timeout=5000)

        # 5. Quantity & Unit Price input (if provided)
        item_inputs = product_row.locator("input.restaurant-pos-compact-input")
        assert item_inputs.count() >= 2, (
            f"Outdoor booking row for '{dish_name}' lacked price/quantity controls"
        )
        qty_inp = item_inputs.nth(1)
        assert qty_inp.is_enabled(), (
            f"Outdoor booking quantity remained disabled for '{dish_name}'"
        )
        qty_inp.fill(str(quantity))
        self.page.wait_for_timeout(200)

        if unit_price:
            price_inp = item_inputs.first
            assert price_inp.is_enabled(), (
                f"Outdoor booking price remained disabled for '{dish_name}'"
            )
            price_inp.fill(str(unit_price))
            self.page.wait_for_timeout(200)

        # 6. Advance payment handling
        if advance_amount and float(advance_amount) > 0:
            adv_inp = self.modal_dialog.locator("input[name='advance_amount']")
            if adv_inp.is_visible():
                adv_inp.fill(str(advance_amount))

            adv_notes_inp = self.modal_dialog.locator("input[name='advance_notes']")
            if adv_notes_inp.is_visible() and advance_notes:
                adv_notes_inp.fill(advance_notes)

        # 7. Notes
        notes_inp = self.modal_dialog.locator("textarea[name='notes'], input[name='notes']")
        if notes_inp.is_visible() and notes:
            notes_inp.fill(notes)

        # 8. Submit Create Booking
        create_btn = self.modal_dialog.get_by_role("button", name="Create Booking").first
        with self.page.expect_response(
            lambda r: "/outdoor" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            create_btn.click()

        response = resp_info.value
        resp_data = response.json()
        assert response.status in (200, 201), (
            f"Outdoor booking failed with HTTP {response.status}: {resp_data}"
        )

        self.page.wait_for_load_state("networkidle")
        return resp_data.get("data", {})

    def search_booking(self, query: str) -> bool:
        """Filters outdoor bookings by search term."""
        self.search_input.wait_for(state="visible", timeout=5000)
        self.search_input.fill(query)
        self.page.wait_for_timeout(500)
        self.page.wait_for_load_state("networkidle")
        return self.is_booking_in_table(booking_ref=query)

    def is_booking_in_table(self, booking_ref: str | None = None, branch_name: str | None = None) -> bool:
        """Asserts booking row is visible in the outdoor billing table."""
        try:
            row = self.page.locator("table tbody tr")
            if booking_ref:
                row = row.filter(has_text=booking_ref)
            if branch_name:
                row = row.filter(has_text=branch_name)
            row.first.wait_for(state="visible", timeout=6000)
            return True
        except Exception:
            return False

    def view_booking(self, booking_ref: str) -> dict[str, Any]:
        """Opens the View Outdoor Booking dialog and reads summary details."""
        row = self.page.locator("table tbody tr").filter(has_text=booking_ref).first
        row.wait_for(state="visible", timeout=5000)
        view_btn = row.locator("button[title='View'], button:has(i.bi-eye)").first
        view_btn.click()

        self.modal_dialog.wait_for(state="visible", timeout=5000)
        self.page.wait_for_load_state("networkidle")
        try:
            self.modal_dialog.locator(".badge, button:has-text('Edit Booking'), button:has-text('Close Bill')").first.wait_for(state="visible", timeout=10000)
        except Exception:
            pass
        self.page.wait_for_timeout(300)

        content = self.modal_dialog.inner_text()
        return {
            "content": content,
            "dialog": self.modal_dialog,
        }

    def edit_booking_from_view(self, new_quantity: str | int = 2) -> bool:
        """Clicks 'Edit Booking' inside the View dialog, updates quantity, and submits."""
        edit_btn = self.modal_dialog.get_by_role("button", name="Edit Booking").first
        edit_btn.wait_for(state="visible", timeout=5000)
        edit_btn.click()

        self.page.wait_for_timeout(500)
        populated_row = self.modal_dialog.locator(
            "table tbody tr:has(.restaurant-pos-product-name)"
        ).first
        populated_row.wait_for(state="visible", timeout=5000)
        qty_inp = populated_row.locator(
            "input.restaurant-pos-compact-input"
        ).nth(1)
        qty_inp.wait_for(state="visible", timeout=5000)
        assert qty_inp.is_enabled(), "Outdoor booking edit quantity must be enabled"
        qty_inp.fill(str(new_quantity))
        qty_inp.press("Tab")
        self.page.wait_for_timeout(300)

        update_btn = self.modal_dialog.get_by_role("button", name="Update Booking").first
        update_btn.wait_for(state="visible", timeout=5000)

        with self.page.expect_response(
            lambda r: "/outdoor-bookings" in r.url and r.request.method in ("PUT", "PATCH"),
            timeout=10000
        ) as resp_info:
            update_btn.click()

        assert resp_info.value.status in (200, 204), f"Update booking failed with HTTP {resp_info.value.status}"
        self.page.wait_for_timeout(500)
        return True

    def record_settlement_payment(self, amount: str | float | int | None = None, notes: str = "Settlement Payment") -> dict[str, Any]:
        """Fills and saves a payment in the Record Payment section inside the modal."""
        amt_inp = self.modal_dialog.locator("input[name='amount']").first
        amt_inp.wait_for(state="visible", timeout=5000)
        if amount is not None:
            amt_inp.fill(str(amount))

        save_btn = self.modal_dialog.get_by_role("button", name="Save Payment").first
        with self.page.expect_response(
            lambda r: "/payments" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            save_btn.click()

        assert resp_info.value.status in (200, 201), f"Save payment failed with HTTP {resp_info.value.status}"
        self.page.wait_for_timeout(500)
        return resp_info.value.json().get("data", {})

    def close_bill(self) -> bool:
        """Clicks 'Close Bill' button in the modal dialog."""
        close_btn = self.modal_dialog.get_by_role("button", name="Close Bill").first
        close_btn.wait_for(state="visible", timeout=5000)

        with self.page.expect_response(
            lambda r: "/close" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            close_btn.click()

        assert resp_info.value.status in (200, 204), f"Close bill failed with HTTP {resp_info.value.status}"
        self.page.wait_for_timeout(500)
        return True

    def cancel_booking_with_refund(self, return_amount: str | float | int = "0", return_notes: str = "Cancelled by QA") -> bool:
        """Clicks 'Cancel Booking', enters return amount in modal, and confirms cancellation."""
        cancel_btn = self.modal_dialog.get_by_role("button", name="Cancel Booking").first
        cancel_btn.wait_for(state="visible", timeout=5000)
        cancel_btn.click()

        cancel_modal = self.page.locator(".modal-dialog").filter(has_text=re.compile(r"Cancel Booking", re.I)).last
        cancel_modal.wait_for(state="visible", timeout=5000)

        ret_amt_inp = cancel_modal.locator("input[name='return_amount']")
        if ret_amt_inp.is_visible() and float(return_amount) > 0:
            ret_amt_inp.fill(str(return_amount))

        ret_notes = cancel_modal.locator("textarea[name='return_notes'], input[name='return_notes']")
        if ret_notes.is_visible() and return_notes:
            ret_notes.fill(return_notes)

        confirm_btn = cancel_modal.locator("button.btn-danger").filter(has_text="Cancel Booking").first
        with self.page.expect_response(
            lambda r: "/cancel" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            confirm_btn.click()

        assert resp_info.value.status in (200, 204), f"Cancel booking failed with HTTP {resp_info.value.status}"
        self.page.wait_for_timeout(500)
        return True

    def close_modal(self) -> None:
        """Closes the currently open modal dialog."""
        close_btn = self.modal_dialog.locator(".btn-close, button:has-text('Back to List'), button:has-text('Cancel')").first
        if close_btn.is_visible():
            close_btn.click()
            self.page.wait_for_timeout(300)

    def get_booking_row_data(self, booking_ref: str | None = None) -> list[str]:
        """Reads columns of the target outdoor booking row."""
        row = self.page.locator("table tbody tr")
        if booking_ref:
            row = row.filter(has_text=booking_ref)
        return [td.inner_text().strip() for td in row.first.locator("td").all()]
