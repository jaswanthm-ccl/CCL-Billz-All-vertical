from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response, TimeoutError as PlaywrightTimeoutError, expect

from pages.common.base_page import BasePage
from utils.tenants import Tenant

VIEW_BUTTON = (
    "button[title='view'], button[title='View'], a[title='view'], a[title='View'], "
    ".btn-info, button:has-text('View'), i.bi-eye"
)
EDIT_BUTTON = (
    "button[title='edit'], button[title='Edit'], a[title='edit'], a[title='Edit'], "
    ".btn-warning, button:has-text('Edit'), i.bi-pencil"
)
FIELD_ERRORS = ".text-danger, .invalid-feedback"
EMPTY_TEXT = "No Chits found"


class ChitsPage(BasePage):
    """Page object for the Chits module (/chits).

    Chits are fund-based financial instruments. Full CRUD plus
    Record Payment and Record Commission actions.

    Form fields: chit_name, branch_id, foreman_name, chit_value,
                 tenure_months, monthly_amount, start_date, commission_amount, notes
    Table: NAME, DATE, FORMAN NAME, DESCRIPTION, CLOSED, Actions
    Search: placeholder='Search...' (live, debounced)

    API: list GET /chits?search=..; per chit GET /chits/{id}/payments|commissions|summary;
    the Pay/Commission dropdown loads GET /lists/chits; every save is a non-GET call under /chits.
    """

    PATH = "/chits"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)
        self.last_save_response: Response | None = None

    # ─── Waiting helpers ───────────────────────────────────────────────────────

    @property
    def _rows(self):
        return self.page.locator("table tbody tr")

    @property
    def _modal(self):
        return self.page.get_by_role("dialog")

    @staticmethod
    def _is_list_response(response: Response, search: str | None = None) -> bool:
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/chits")
        ):
            return False
        return search is None or parse_qs(url.query).get("search", [""])[-1] == search

    def _reload_list(self, action: Callable[[], object], search: str | None = None) -> None:
        with self.page.expect_response(lambda r: self._is_list_response(r, search), timeout=15000):
            action()
        self._rows.first.wait_for(state="visible", timeout=10000)

    def _wait_for_get(self, path_suffix: str, action: Callable[[], object]) -> None:
        """Run `action` and wait for the GET whose path ends with `path_suffix` (e.g. '/payments')."""
        with self.page.expect_response(
            lambda r: r.request.method == "GET" and urlparse(r.url).path.rstrip("/").endswith(path_suffix),
            timeout=15000,
        ):
            action()

    def _save(self, action: Callable[[], object]) -> bool:
        """Run a submit/confirm `action`, wait for its save call under /chits and report whether the API accepted it.

        Returns False without a response when the form blocks the submit (client-side validation)."""
        self.last_save_response = None
        try:
            with self.page.expect_response(
                lambda r: r.request.method != "GET" and "/chits" in urlparse(r.url).path, timeout=15000
            ) as info:
                action()
        except PlaywrightTimeoutError:
            return False
        self.last_save_response = info.value
        return info.value.ok

    def _visible_field_errors(self) -> list[str]:
        texts = (text.strip() for text in self._modal.locator(FIELD_ERRORS).all_inner_texts())
        return [text for text in texts if text and text != "*"]

    def _pick(self, control, text: str) -> None:
        """Choose `text` in a react-select; fails if no option contains it (never picks another option)."""
        control.click()
        self.page.keyboard.type(text)
        self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=text).first.click()

    # ─── Navigation ────────────────────────────────────────────────────────────

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))

    def is_chits_visible(self) -> bool:
        """Verify the chits page loaded."""
        try:
            expect(self.page.get_by_text("Chit Management").first).to_be_visible(timeout=5000)
            return True
        except AssertionError:
            return False

    # ─── Create ────────────────────────────────────────────────────────────────

    def add_chit(
        self,
        chit_name: str,
        branch: str,
        chit_value: str,
        tenure_months: str,
        monthly_amount: str,
        foreman_name: str = "",
        commission_amount: str = "",
        notes: str = "",
    ) -> None:
        """Create a new chit; raises with the field errors or API reply if it isn't saved."""
        self.page.get_by_role("button", name="Add Chit").click()
        modal = self._modal
        modal.wait_for(state="visible", timeout=10000)

        modal.locator("input[name='chit_name']").fill(chit_name)
        branch_control = modal.locator("input[name='branch_id']").locator("xpath=..").locator(".react-select__input-container")
        branch_control.click()
        self.page.keyboard.type(branch)
        self.page.get_by_role("option", name=branch).click()

        if foreman_name:
            modal.locator("input[name='foreman_name']").fill(foreman_name)
        modal.locator("input[name='chit_value']").fill(chit_value)
        modal.locator("input[name='tenure_months']").fill(tenure_months)
        modal.locator("input[name='monthly_amount']").fill(monthly_amount)
        if commission_amount:
            modal.locator("input[name='commission_amount']").fill(commission_amount)
        if notes:
            modal.get_by_role("button", name="Add Description").click()
            modal.locator("textarea[name='notes']").fill(notes)

        if not self._save(modal.get_by_role("button", name="Create").click):
            reply = self.last_save_response.text()[:300] if self.last_save_response else "no request sent"
            raise AssertionError(f"Chit '{chit_name}' was not created: {self._visible_field_errors() or reply}")
        modal.wait_for(state="hidden", timeout=10000)

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_chit(self, query: str) -> bool:
        """Search chits (live search, debounced). True if at least one row matches."""
        search_box = self.page.get_by_placeholder("Search...")
        if search_box.input_value() != query:
            self._reload_list(lambda: search_box.fill(query), search=query)
        return self.get_row_count() > 0

    # ─── Table ─────────────────────────────────────────────────────────────────

    def get_row_count(self) -> int:
        """Return visible row count (0 for the empty-state row)."""
        self._rows.first.wait_for(state="visible", timeout=10000)
        if EMPTY_TEXT in (self._rows.first.text_content() or ""):
            return 0
        return self._rows.count()

    def get_first_row_data(self) -> dict:
        """Read first row data. Columns: NAME, DATE, FORMAN NAME, DESCRIPTION, CLOSED, Actions."""
        self._rows.first.wait_for(state="visible", timeout=10000)
        cells = [text.strip() for text in self._rows.first.locator("td").all_text_contents()] + [""] * 5
        return dict(zip(("name", "date", "foreman_name", "description", "is_closed"), cells))

    # ─── View ──────────────────────────────────────────────────────────────────

    def view_chit(self, query: str) -> bool:
        """Search for a chit and open its view modal."""
        if not self.search_chit(query):
            return False
        self.page.locator(VIEW_BUTTON).first.click()
        self._modal.wait_for(state="visible", timeout=10000)
        return True

    def close_modal(self) -> None:
        """Close the currently open modal."""
        close_button = self.page.locator(".btn-close, button.close, [aria-label='Close']").first
        if close_button.count() and close_button.is_visible():
            close_button.click()
        else:
            self.page.keyboard.press("Escape")
        self._modal.wait_for(state="hidden", timeout=5000)

    # ─── Edit ──────────────────────────────────────────────────────────────────

    def edit_chit(self, query: str, new_foreman: str) -> bool:
        """Search for a chit, change its foreman name and save. True when the API accepts the update."""
        if not self.search_chit(query):
            return False
        self.page.locator(EDIT_BUTTON).first.click()
        modal = self._modal
        modal.locator("input[name='chit_name']").wait_for(state="visible", timeout=10000)
        modal.locator("input[name='foreman_name']").fill(new_foreman)
        if not self._save(modal.get_by_role("button", name="Update").click):
            return False
        modal.wait_for(state="hidden", timeout=10000)
        return True

    def is_edit_available(self, query: str) -> bool:
        """Check if the edit action button is visible for the searched chit row."""
        if not self.search_chit(query):
            return False
        edit_button = self._rows.first.locator(EDIT_BUTTON)
        return edit_button.count() > 0 and edit_button.first.is_visible()

    # ─── Close Chit ────────────────────────────────────────────────────────────

    def close_chit(self, query: str) -> bool:
        """Open the chit's view, click 'Close Chit' and confirm. True only when the API accepts the close."""
        if not self.view_chit(query):
            return False

        close_button = self._modal.locator("button").filter(has_text=re.compile(r"close\s*chit", re.I)).first
        try:
            expect(close_button).to_be_visible(timeout=5000)
        except AssertionError:
            self.close_modal()  # Already closed: the view has no Close Chit button.
            return False
        close_button.click()

        confirm = self.page.locator("button").filter(has_text=re.compile(r"^(yes|confirm|ok)", re.I)).last
        return self._save(confirm.click)

    # ─── Record Payment ────────────────────────────────────────────────────────

    def record_payment(
        self,
        chit_name: str,
        amount: str,
        payment_mode: str = "Cash",
        bank_account: str = "",
        bonus_amount: str = "",
        payment_month: str = "",
        narration: str = "",
    ) -> bool:
        """Record a payment from the list page's 'Pay' button. True when the API accepts it."""
        self.page.get_by_role("button", name="Pay").click()
        modal = self._modal
        modal.wait_for(state="visible", timeout=10000)
        controls = modal.locator(".react-select__control")
        self._pick(controls.first, chit_name)

        modal.locator("input[name='amount']").fill(amount)
        if bonus_amount:
            modal.locator("input[name='bonus_amount']").fill(bonus_amount)
        if payment_month:
            modal.locator("input[name='payment_month']").fill(payment_month)
        if payment_mode != "Cash":
            self._pick(controls.nth(1), payment_mode)
            if bank_account:
                self._pick(controls.nth(2), bank_account)
        if narration:
            modal.locator("textarea[name='narration']").fill(narration)

        if not self._save(modal.get_by_role("button", name="Pay").click):
            return False
        modal.wait_for(state="hidden", timeout=10000)
        return True

    # ─── Record Commission ─────────────────────────────────────────────────────

    def record_commission(
        self,
        chit_name: str,
        amount: str,
        commission_month: str = "",
        narration: str = "",
    ) -> bool:
        """Record a commission from the list page's 'Commission' button. True when the API accepts it."""
        self.page.get_by_role("button", name="Commission").click()
        modal = self._modal
        modal.wait_for(state="visible", timeout=10000)
        modal.locator("[class*='react-select']").first.click()
        self.page.get_by_role("option", name=chit_name).click()

        modal.locator("input[name='amount']").fill(amount)
        if commission_month:
            modal.locator("input[name='commission_month']").fill(commission_month)
        if narration:
            modal.locator("textarea[name='narration']").fill(narration)

        if not self._save(modal.get_by_role("button", name="Add").click):
            return False
        modal.wait_for(state="hidden", timeout=10000)
        return True

    # ─── Payment / Commission lists and Summary ────────────────────────────────

    def _open_row_modal(self, query: str, action_title: str, path_suffix: str, heading: str) -> bool:
        """Search the chit, click a row action and wait for both its data call and its heading."""
        if not self.search_chit(query):
            return False
        self._wait_for_get(path_suffix, self.page.get_by_title(action_title).first.click)
        self._modal.get_by_text(heading).first.wait_for(state="visible", timeout=10000)
        return True

    def view_payment_list(self, query: str) -> bool:
        """Search for a chit and open its payment list."""
        return self._open_row_modal(query, "payment list", "/payments", "Payment List")

    def view_commission_list(self, query: str) -> bool:
        """Search for a chit and open its commission list."""
        return self._open_row_modal(query, "commission list", "/commissions", "Commission List")

    def view_summary(self, query: str) -> bool:
        """Search for a chit and open its summary."""
        return self._open_row_modal(query, "summary", "/summary", "Total Contribution")

    def get_summary_data(self) -> dict:
        """Read the label/value pairs from the open summary modal (call after view_summary())."""
        labels = self._modal.locator(".text-muted.small").all_text_contents()
        values = self._modal.locator(".fw-bold.fs-6").all_text_contents()
        return {label.strip(): value.strip() for label, value in zip(labels, values)}

    def get_payment_list_rows(self) -> list[dict[str, str]]:
        """Read the top-level rows from an open payment-list modal."""
        rows: list[dict[str, str]] = []
        for row in self._modal.locator("table").first.locator("tbody > tr").all():
            cells = [text.strip() for text in row.locator(":scope > td").all_text_contents()]
            if len(cells) == 5:
                rows.append({"voucher_no": cells[0], "narration": cells[1], "date": cells[2], "total": cells[3]})
        return rows

    def get_payment_list_row_count(self) -> int:
        """Rows in the open payment/commission list modal (0 for its "No ... found" row).

        The data call already finished in view_payment_list()/view_commission_list()."""
        rows = self._modal.locator("table tbody tr")
        rows.first.wait_for(state="visible", timeout=10000)
        if any("No " in text and "found" in text for text in rows.all_text_contents()):
            return 0
        return rows.count()

    @staticmethod
    def parse_amount(value: str) -> Decimal:
        cleaned = re.sub(r"[^\d.-]", "", value)
        return Decimal(cleaned or "0").quantize(Decimal("0.01"))

    # ─── Delete / Restore ──────────────────────────────────────────────────────

    def _confirm_row_action(self, query: str, title: str) -> bool:
        if not self.search_chit(query):
            return False
        button = self.page.get_by_title(title)
        if button.count() == 0:
            return False
        button.first.click()
        return self._save(self.page.get_by_role("button", name="yes").click)

    def delete_chit(self, query: str) -> bool:
        """Search for a chit and delete it. True when the API accepts the delete."""
        return self._confirm_row_action(query, "delete")

    def restore_chit(self, query: str) -> bool:
        """Search for a deleted chit and restore it. True when the API accepts the restore."""
        return self._confirm_row_action(query, "retrieve")

    # ─── Validation Helpers ────────────────────────────────────────────────────

    def _submit_empty(self, open_button: str, submit_button: str, clear_amount: bool) -> list[str]:
        """Open a form, submit it without filling it, return the field errors shown, then close it."""
        self.page.get_by_role("button", name=open_button).click()
        modal = self._modal
        modal.wait_for(state="visible", timeout=10000)
        if clear_amount:
            modal.locator("input[name='amount']").fill("")  # Defaults to 0.
        modal.get_by_role("button", name=submit_button).click()
        try:
            modal.locator(FIELD_ERRORS).filter(has_text=re.compile(r"\w")).first.wait_for(state="visible", timeout=5000)
        except PlaywrightTimeoutError:
            pass  # No field errors shown; the caller asserts on the empty list.
        errors = self._visible_field_errors()
        self.close_modal()
        return errors

    def submit_empty_add_form(self) -> list[str]:
        """Submit an empty Add Chit form; returns the visible validation messages."""
        return self._submit_empty("Add Chit", "Create", clear_amount=False)

    def submit_empty_payment_form(self) -> list[str]:
        """Submit an empty Record Payment form; returns the visible validation messages."""
        return self._submit_empty("Pay", "Pay", clear_amount=True)

    def submit_empty_commission_form(self) -> list[str]:
        """Submit an empty Record Commission form; returns the visible validation messages."""
        return self._submit_empty("Commission", "Add", clear_amount=True)

    def is_chit_in_payment_dropdown(self, chit_name: str) -> bool:
        """Whether the chit is offered in the Record Payment form's chit dropdown."""
        self.page.get_by_role("button", name="Pay").click()
        self._modal.wait_for(state="visible", timeout=10000)
        self._modal.locator("[class*='react-select']").first.click()
        options = self.page.locator("[class*='react-select__option']")
        options.first.wait_for(state="visible", timeout=5000)
        found = any(chit_name in text for text in options.all_text_contents())
        self.close_modal()
        return found
