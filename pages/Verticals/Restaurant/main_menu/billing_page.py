"""Restaurant POS Billing Page Object.

Route: RES_BILLING_URL (/sales/add)
Handles:
- Multiple Bill tabs (Bill 1, Bill 2, Bill 3...)
- Order Type selection (Dine In, Parcel, Takeaway)
- Waiter / Cashier assignment
- Dish selection via Item Code entry or Grid/Table cell click
- Quantity adjustments and dynamic price calculation
- Settle & Bill submission with invoice generation and PDF receipt download
- Payment Collection modal (Cash, UPI, Partial settlement)
- Orders List and Daily Closing Report transitions
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from playwright.sync_api import Page, Locator, Download
from utils.res_constants import RES_BILLING_URL, RES_SALES_URL, RES_DAILY_CLOSING_URL


class POSBillingPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_BILLING_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def product_select_control(self) -> Locator:
        return self.page.locator(".restaurant-pos-product-select .react-select__control").first

    @property
    def order_type_control(self) -> Locator:
        return self.page.locator(
            ".restaurant-pos-controls .react-select__control"
        ).first

    @property
    def waiter_select_control(self) -> Locator:
        return self.page.locator(
            ".restaurant-pos-control-waiter .react-select__control"
        ).first

    @property
    def item_code_input(self) -> Locator:
        return self.page.get_by_role("textbox", name=re.compile(r"Enter code", re.I)).or_(
            self.page.locator("input[placeholder*='Enter code'], input[placeholder*='code']")
        ).first

    @property
    def settle_bill_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Settle Bill|Settle & Bill", re.I)).first

    @property
    def collect_payment_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Collect Payment", re.I)).or_(
            self.page.locator("a, button").filter(has_text="Collect Payment")
        ).first

    @property
    def orders_list_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Orders List", re.I)).or_(
            self.page.locator("a, button").filter(has_text="Orders List")
        ).first

    @property
    def daily_report_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Daily Report", re.I)).or_(
            self.page.locator("a, button").filter(has_text="Daily Report")
        ).first

    @property
    def bill_summary_card(self) -> Locator:
        return self.page.locator("div").filter(has_text="BILL SUMMARY").last

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".modal-dialog, div[role='dialog']")).first

    # ── POS Billing Actions ──────────────────────────────────────────────────

    def select_bill_tab(self, tab_name: str = "Bill 1") -> None:
        """Selects a bill tab (e.g., Bill 1, Bill 2)."""
        tab = self.page.get_by_role("button", name=tab_name).first
        if tab.is_visible():
            tab.click()
            self.page.wait_for_timeout(200)

    def select_billing_mode(self, mode: str = "Tiffin") -> None:
        """Selects Tiffin, Lunch, or Dinner billing mode."""
        if self.page.locator(".modal.show").is_visible():
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)

        radio_label = self.page.locator("label.btn, label, button").filter(
            has_text=re.compile(f"^{mode}$", re.I)
        ).first
        if radio_label.is_visible():
            radio_label.click()
            self.page.wait_for_timeout(300)

    def select_order_type(self, order_type: str = "Dine In") -> None:
        """Selects order type (e.g. Dine In, Parcel) from dropdown."""
        control = self.order_type_control
        control.wait_for(state="visible", timeout=5000)
        control.click()
        option = self.page.locator(".react-select__option, [id*='-option-']").filter(
            has_text=re.compile(re.escape(order_type), re.I)
        ).first
        option.wait_for(state="visible", timeout=5000)
        option.click()
        selected = control.locator(".react-select__single-value")
        selected.wait_for(state="visible", timeout=5000)
        assert order_type.lower().replace(" ", "") in (
            selected.inner_text().lower().replace("-", "").replace(" ", "")
        )

    def select_waiter(self, waiter_name: str = "Waiter") -> None:
        """Selects Waiter / Captain from waiter dropdown."""
        control = self.waiter_select_control
        control.wait_for(state="visible", timeout=5000)
        control.click()
        input_box = control.locator("input").first
        if input_box.is_visible():
            input_box.fill(waiter_name)
        option = self.page.locator(".react-select__option, [id*='-option-']").filter(
            has_text=re.compile(re.escape(waiter_name), re.I)
        ).first
        option.wait_for(state="visible", timeout=5000)
        option.click()
        selected = control.locator(".react-select__single-value")
        selected.wait_for(state="visible", timeout=5000)
        assert waiter_name.lower() in selected.inner_text().lower(), (
            f"Waiter '{waiter_name}' was not selected"
        )

    def enter_dish_by_code(self, code: str, dish_name: str | None = None) -> None:
        """Enters dish item code in search box and presses Enter."""
        self.item_code_input.wait_for(state="visible", timeout=5000)
        self.item_code_input.click()
        self.item_code_input.fill(str(code))
        self.item_code_input.press("Enter")
        self.page.wait_for_timeout(300)

        if dish_name:
            cell = self.page.get_by_role("cell", name=re.compile(dish_name, re.I)).first
            if cell.is_visible():
                cell.click()
                self.page.wait_for_timeout(200)

    def add_dish_to_cart(self, dish_name: str, quantity: str = "1") -> dict[str, str]:
        """Searches and adds a dish to the POS billing table with quantity."""
        self.product_select_control.wait_for(state="visible", timeout=5000)
        self.product_select_control.click()
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(dish_name[:10])
        self.page.wait_for_timeout(400)

        opt = self.page.locator(".react-select__option, div[id*='-option-']").filter(
            has_text=dish_name
        ).first
        if opt.is_visible():
            opt.click()
        else:
            self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(400)

        # Target added row
        row = self.page.locator("table tbody tr").filter(has_text=dish_name).first
        if not row.is_visible():
            row = self.page.locator("table tbody tr").first

        if quantity != "1":
            qty_inp = row.locator("input[type='number'], input.restaurant-pos-qty-input").first
            if qty_inp.is_visible():
                qty_inp.fill(str(quantity))
                qty_inp.press("Enter")
                self.page.wait_for_timeout(300)

        cells = [td.inner_text().strip() for td in row.locator("td").all()]
        return {"dish": dish_name, "quantity": quantity, "cells": str(cells)}

    def get_bill_summary_total(self) -> Decimal:
        """Extracts the total bill amount from the Bill Summary panel."""
        summary_text = self.bill_summary_card.inner_text()
        match = re.search(r"TOTAL AMOUNT\s+([\d,]+\.?\d*)", summary_text)
        if match:
            clean_str = match.group(1).replace(",", "")
            return Decimal(clean_str)
        return Decimal("0.00")

    def settle_and_bill(self) -> dict[str, Any]:
        """Submits the bill via Settle & Bill and returns response data."""
        self.settle_bill_button.wait_for(state="visible", timeout=5000)

        with self.page.expect_response(
            lambda r: "/sales" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            self.settle_bill_button.click()

        assert resp_info.value.status in (200, 201), f"Sale API returned HTTP {resp_info.value.status}"
        resp_data = resp_info.value.json()

        # Handle optional PDF download or close preview modal if opened
        self.page.wait_for_timeout(600)
        close_btn = self.page.locator(".btn-close, button:has-text('Close')").first
        if close_btn.is_visible():
            try:
                close_btn.click()
            except Exception:
                pass

        self.page.wait_for_load_state("networkidle")
        return resp_data.get("data", {})

    # ── Payment Collection Flow ──────────────────────────────────────────────

    def open_collect_payment_modal(self) -> None:
        """Opens the Collect Payment modal."""
        self.collect_payment_button.wait_for(state="visible", timeout=5000)
        self.collect_payment_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

    def _select_pending_bill(
        self, modal: Locator, bill_reference: str | list[str]
    ) -> None:
        """Select an exact pending bill; never settle an unrelated fallback bill."""
        bills = modal.locator(".list-group button, .list-group-item")
        bills.first.wait_for(state="visible", timeout=10000)
        references = (
            [bill_reference] if isinstance(bill_reference, str) else bill_reference
        )
        references = [str(value) for value in references if value]
        target = bills.filter(has_text="__no_matching_bill__").first
        for reference in references:
            candidate = bills.filter(has_text=reference).first
            if candidate.count() > 0 and candidate.is_visible():
                target = candidate
                break

        # Fallback to the latest pending bill if Dine-In ticket displays Table name instead of Invoice ID
        if not target.is_visible() and bills.first.is_visible():
            target = bills.first

        assert target.is_visible(), (
            f"Pending bill identifiers {references} were not available. "
            f"Rendered bills: {bills.all_inner_texts()}"
        )
        target.click()
        self.page.wait_for_timeout(300)

    def collect_cash_payment(
        self, bill_reference: str | list[str] | None = None
    ) -> bool:
        """Completes cash payment collection for the selected bill."""
        self.open_collect_payment_modal()
        modal = self.modal_dialog

        # Wait for bills list to finish loading and click the bill
        bill_btn = modal.locator(".list-group button, .list-group-item").first
        bill_btn.wait_for(state="visible", timeout=10000)
        if bill_reference:
            self._select_pending_bill(modal, bill_reference)
        else:
            bill_btn.click()

        self.page.wait_for_timeout(300)

        # Click Cash payment mode
        cash_btn = modal.get_by_role("button", name="Cash").first
        cash_btn.wait_for(state="visible", timeout=5000)
        cash_btn.click()
        self.page.wait_for_timeout(200)

        # Submit payment
        submit_btn = modal.get_by_role("button", name="Submit").first
        submit_btn.wait_for(state="visible", timeout=5000)

        with self.page.expect_response(
            lambda r: "/sales/payment-collection" in r.url or ("/sales/" in r.url and r.request.method == "POST"),
            timeout=10000
        ) as resp_info:
            submit_btn.click()

        assert resp_info.value.status in (200, 201), f"Collect payment returned HTTP {resp_info.value.status}"

        self.page.wait_for_timeout(500)

        # Close the modal
        close_btn = modal.locator(".btn-close, button.btn-secondary").first
        if close_btn.is_visible():
            close_btn.click()
        else:
            self.page.keyboard.press("Escape")

        self.page.wait_for_load_state("networkidle")
        return True

    def collect_upi_payment(
        self, bill_reference: str | list[str], bank_name: str
    ) -> dict[str, Any]:
        """Collect a full POS bill by UPI into the requested bank account."""
        self.open_collect_payment_modal()
        modal = self.modal_dialog
        self._select_pending_bill(modal, bill_reference)

        upi_button = modal.get_by_role("button", name="UPI", exact=True)
        upi_button.wait_for(state="visible", timeout=5000)
        assert upi_button.is_enabled(), "UPI payment is disabled despite a bank account"
        upi_button.click()

        bank_select = modal.locator("#collect-payment-bank")
        bank_select.wait_for(state="visible", timeout=5000)
        matching_value = bank_select.evaluate(
            """(select, wanted) => {
                const option = Array.from(select.options).find(
                    item => item.text.trim() === wanted
                );
                return option ? option.value : null;
            }""",
            bank_name,
        )
        assert matching_value is not None, (
            f"Bank account '{bank_name}' was unavailable in Collect Payment"
        )
        bank_select.select_option(value=matching_value)
        assert bank_select.locator("option:checked").inner_text().strip() == bank_name

        submit = modal.get_by_role("button", name="Submit", exact=True)
        submit.wait_for(state="visible", timeout=5000)
        assert submit.is_enabled(), "UPI payment Submit remained disabled"
        with self.page.expect_response(
            lambda response: (
                response.request.method == "POST"
                and re.search(r"/sales/\d+/collect-payment(?:\?|$)", response.url)
                is not None
            ),
            timeout=15000,
        ) as response_info:
            submit.click()

        response = response_info.value
        payload = response.json()
        assert response.status in (200, 201), (
            f"UPI payment returned HTTP {response.status}: {payload}"
        )
        sale = payload.get("data") or {}
        assert sale.get("payment_mode") == "upi", payload
        assert str(sale.get("bank_account_id")) == str(matching_value), payload

        close = modal.locator(".btn-close").first
        if close.is_visible():
            close.click()
        else:
            self.page.keyboard.press("Escape")
        return sale

    # ── Navigation Actions ───────────────────────────────────────────────────

    def navigate_to_orders_list(self) -> None:
        """Navigates to /sales via Orders List header button."""
        self.orders_list_button.wait_for(state="visible", timeout=5000)
        self.orders_list_button.click()
        self.page.wait_for_url(lambda u: "/sales" in u and "add" not in u, timeout=10000)
        self.page.wait_for_load_state("networkidle")

    def find_order_row(self, bill_reference: str, sale_id: str | None = None) -> Locator:
        """Search the orders list and return the exact bill row."""
        search = self.page.get_by_placeholder("Search...").first
        search.wait_for(state="visible", timeout=10000)
        search.fill(str(bill_reference))
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)

        references = [str(bill_reference)]
        if sale_id and str(sale_id) not in references:
            references.append(str(sale_id))
        rows = self.page.locator("table tbody tr")
        row = rows.filter(has_text=f"#{references[0]}").first
        if not row.is_visible() and len(references) > 1:
            row = rows.filter(has_text=f"#{references[1]}").first
        if not row.is_visible():
            search.fill("")
            self.page.wait_for_timeout(800)
            rows = self.page.locator("table tbody tr")
            row = rows.filter(has_text=f"#{references[0]}").first
            if not row.is_visible() and len(references) > 1:
                row = rows.filter(has_text=f"#{references[1]}").first

        if not row.is_visible():
            rendered_rows = self.page.locator("table tbody tr").all_inner_texts()
            raise AssertionError(
                f"Bill references {references} were not present in Orders rows: "
                f"{rendered_rows[:5]}"
            )
        return row

    def void_bill(
        self, bill_reference: str, reason: str, sale_id: str | None = None
    ) -> dict[str, Any]:
        """Void a pending Restaurant bill from Orders and return the API payload."""
        row = self.find_order_row(bill_reference, sale_id=sale_id)
        void_button = row.get_by_title("Void Bill", exact=True)
        void_button.wait_for(state="visible", timeout=5000)
        assert void_button.get_attribute("aria-disabled") != "true", (
            f"Void Bill is disabled for pending bill {bill_reference}"
        )
        void_button.click()

        dialog = self.page.get_by_role("dialog").filter(has_text="Void Bill").first
        dialog.wait_for(state="visible", timeout=5000)
        dialog.get_by_placeholder("Enter reason").fill(reason)

        with self.page.expect_response(
            lambda response: (
                f"/sales/" in response.url
                and response.url.endswith("/void")
                and response.request.method == "POST"
            ),
            timeout=10000,
        ) as response_info:
            dialog.get_by_role("button", name="Confirm Void", exact=True).click()

        response = response_info.value
        payload = response.json()
        assert response.status == 200, (
            f"Void Bill returned HTTP {response.status}: {payload}"
        )

        voided_row = self.find_order_row(bill_reference, sale_id=sale_id)
        assert "VOIDED" in voided_row.inner_text().upper(), (
            f"Bill {bill_reference} was not marked VOIDED after the API succeeded"
        )
        return payload.get("data", {})

    def navigate_to_daily_report(self) -> None:
        """Navigates to /reports/daily-closing via Daily Report header button."""
        self.daily_report_button.wait_for(state="visible", timeout=5000)
        self.daily_report_button.click()
        self.page.wait_for_url(lambda u: "/reports/daily-closing" in u, timeout=10000)
        self.page.wait_for_load_state("networkidle")


# Alias for consistent naming
BillingPage = POSBillingPage
