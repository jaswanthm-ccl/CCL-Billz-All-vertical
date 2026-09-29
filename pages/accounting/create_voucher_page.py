from __future__ import annotations

import re
from urllib.parse import urlparse

from decimal import Decimal
from playwright.sync_api import Page

from utils.constants import BASE_URL
from utils.models import VoucherResult


CREATE_VOUCHER_URL = f"{BASE_URL}/vouchers/create"
RECEIPT_VOUCHER_URL = f"{BASE_URL}/vouchers/receipt/create"
PAYMENT_VOUCHER_URL = f"{BASE_URL}/vouchers/payment/create"
CONTRA_VOUCHER_URL = f"{BASE_URL}/vouchers/contra/create"
JOURNAL_VOUCHER_URL = f"{BASE_URL}/vouchers/journal/create"


class CreateVoucherPage:
    """Page object for voucher creation forms."""

    TYPE_LABELS = {
        "Payment": "Payment Voucher",
        "Receipt": "Receipt Voucher",
        "Contra": "Contra Voucher",
        "Journal": "Journal Voucher",
        "Chit Entry": "Chit Entry",
        "MDR Settlement": "MDR Settlement",
    }

    def __init__(self, page: Page) -> None:
        self.page = page
        self._selected_type = ""
        self._submission_succeeded = False
        self.create_voucher_url = CREATE_VOUCHER_URL
        self.payment_voucher_url = PAYMENT_VOUCHER_URL
        self.receipt_voucher_url = RECEIPT_VOUCHER_URL
        self.contra_voucher_url = CONTRA_VOUCHER_URL
        self.journal_voucher_url = JOURNAL_VOUCHER_URL

    def navigate(self) -> None:
        self.page.goto(self.create_voucher_url)
        self.page.wait_for_load_state("networkidle")

    def navigate_contra(self) -> None:
        self.page.goto(self.contra_voucher_url)
        self.page.wait_for_load_state("networkidle")
        self._form().wait_for(state="visible", timeout=10000)

    def navigate_journal(self) -> None:
        self.page.goto(self.journal_voucher_url)
        self.page.wait_for_load_state("networkidle")
        self._form().wait_for(state="visible", timeout=10000)

    def select_voucher_type(self, voucher_type: str) -> None:
        label = self.TYPE_LABELS.get(voucher_type, voucher_type)
        self.page.get_by_text(label, exact=True).click()
        self._selected_type = voucher_type
        self._form().wait_for(state="visible", timeout=10000)

    def _form(self):
        return self.page.locator("form:visible").first

    def submit_button(self):
        return self._form().locator("button[type='submit']")

    def is_submit_enabled(self) -> bool:
        return self.submit_button().is_enabled()

    def click_submit(self) -> None:
        self.submit_button().click()

    def fill_amount(self, amount: str) -> None:
        self._form().locator("input[type='number']").first.fill(amount)

    def fill_date(self, date_str: str) -> None:
        self._form().locator("input[type='date']").fill(date_str)

    def fill_remarks(self, remarks: str) -> None:
        self._form().locator("textarea").first.fill(remarks)

    def select_native(self, index: int, option_text: str) -> None:
        self._form().locator("select").nth(index).select_option(label=option_text)

    def _select_field(self, field_name: str, option_text: str, fallback_index: int = 0, filter_text: str = "") -> None:
        """Selects an option from either a React-Select container or native <select>."""
        # 1. Target specific React-Select control by index
        controls = self._form().locator(".react-select__control")
        if controls.count() > fallback_index:
            rs_control = controls.nth(fallback_index)
            rs_control.click()
            self.page.wait_for_timeout(300)
            self.page.keyboard.type(option_text)
            self.page.wait_for_timeout(500)

            # Match by filter_text if provided (e.g. branch name inside Cash Ledger label)
            if filter_text:
                filtered = self.page.locator(".react-select__option").filter(has_text=filter_text).first
                if filtered.count() > 0 and filtered.is_visible():
                    filtered.click()
                    self.page.wait_for_timeout(300)
                    return

            opt = self.page.locator(".react-select__option").filter(has_text=option_text).first
            if opt.count() > 0 and opt.is_visible():
                opt.click()
                self.page.wait_for_timeout(300)
                return
            first_opt = self.page.locator(".react-select__option").first
            if first_opt.count() > 0 and first_opt.is_visible():
                first_opt.click()
                self.page.wait_for_timeout(300)
                return
            self.page.keyboard.press("Enter")
            self.page.wait_for_timeout(300)
            return

        # 2. Try native <select name='...'>
        native = self._form().locator(f"select[name='{field_name}']")
        if native.count() > 0 and native.first.is_visible():
            try:
                native.first.select_option(label=option_text)
            except Exception:
                native.first.select_option(index=1)
            return

        # 3. Fallback to nth native select
        selects = self._form().locator("select")
        if selects.count() > fallback_index:
            try:
                selects.nth(fallback_index).select_option(label=option_text)
            except Exception:
                selects.nth(fallback_index).select_option(index=1)

    def wait_for_success_toast(self, timeout: int = 10000) -> bool:
        try:
            toast = self.page.locator(".Toastify__toast--success, .alert-success").first
            if toast.count() > 0 and toast.is_visible():
                return True
            toast.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            pass
        try:
            self.page.locator(".Toastify__toast, .alert, [role='alert']").filter(
                has_text=re.compile(r"(?:voucher|payment|receipt|entry|settlement).*(?:created|success)|successfully", re.IGNORECASE)
            ).first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    def wait_for_redirect_to_history(self, timeout: int = 15000) -> bool:
        if self._submission_succeeded:
            return True
        try:
            self.page.wait_for_url(lambda url: "/vouchers/history" in url or "/accounting" in url, timeout=timeout)
            return True
        except Exception:
            return False

    def _submit_embedded(self) -> None:
        """Submit a drawer form and verify its success toast before it disappears."""
        self.click_submit()
        self._submission_succeeded = self.wait_for_success_toast(timeout=10000)

    def has_validation_error(self, text: str = "", timeout: int = 1500) -> bool:
        if text:
            try:
                self.page.locator(".invalid-feedback, .alert-danger, .text-danger, [role='alert']").filter(
                    has_text=re.compile(re.escape(text), re.IGNORECASE)
                ).first.wait_for(state="visible", timeout=timeout)
                return True
            except Exception:
                return False
        try:
            err = self.page.locator(".invalid-feedback:visible, .alert-danger:visible, .text-danger:visible").first
            return err.count() > 0 and err.is_visible()
        except Exception:
            return False


    def get_voucher_number(self) -> str:
        field = self._form().locator(
            "input[name='voucher_number'], input[name='voucherNumber']"
        )
        return field.first.input_value() if field.count() else ""

    @property
    def _preset_select(self):
        return self._form().locator("select").nth(0)

    @property
    def _debit_ledger_select(self):
        return self._form().locator("select").nth(1)

    @property
    def _credit_ledger_select(self):
        return self._form().locator("select").nth(2)

    @property
    def _amount_input(self):
        return self._form().locator("input[type='number']")

    @property
    def _remarks_textarea(self):
        return self._form().locator("textarea")

    @property
    def _contra_submit_button(self):
        return self._form().get_by_role("button", name="Create contra")

    def _select_native_option(self, select_locator, ledger_name: str, branch: str = "") -> None:
        if not select_locator.is_enabled():
            return
        val = select_locator.evaluate(
            """(el, args) => {
                const { ledgerName, branchName } = args;
                const options = Array.from(el.options);
                if (branchName) {
                    const match = options.find(o => o.text.includes(ledgerName) && o.text.includes(branchName));
                    if (match) return match.value;
                }
                const exactMatch = options.find(o => o.text.trim() === ledgerName);
                if (exactMatch) return exactMatch.value;

                const partialMatch = options.find(o => o.text.includes(ledgerName));
                if (partialMatch) return partialMatch.value;

                return null;
            }""",
            {"ledgerName": ledger_name, "branchName": branch},
        )
        if val is not None:
            select_locator.select_option(value=val)
        else:
            try:
                select_locator.select_option(label=ledger_name)
            except Exception:
                pass

    def create_contra_voucher(
        self,
        debit_ledger: str = "",
        credit_ledger: str = "",
        amount: str = "",
        *,
        preset: str = "custom",
        branch: str = "",
        remarks: str = "",
    ) -> None:
        self._preset_select.select_option(preset)
        self.page.wait_for_timeout(300)
        if debit_ledger:
            self._select_native_option(self._debit_ledger_select, debit_ledger, branch)
        if credit_ledger:
            self._select_native_option(self._credit_ledger_select, credit_ledger, branch)
        self._amount_input.fill(amount)
        if remarks:
            self._remarks_textarea.fill(remarks)
        self._contra_submit_button.click()

    def create_contra_custom(
        self, debit_ledger: str, credit_ledger: str, amount: str, remarks: str = "", branch: str = ""
    ) -> None:
        self.create_contra_voucher(
            debit_ledger, credit_ledger, amount, preset="custom", branch=branch, remarks=remarks
        )

    def create_contra_preset(
        self, preset: str, amount: str, remarks: str = "", debit_ledger: str = "", credit_ledger: str = "", branch: str = ""
    ) -> None:
        self.create_contra_voucher(
            debit_ledger=debit_ledger,
            credit_ledger=credit_ledger,
            amount=amount,
            preset=preset,
            branch=branch,
            remarks=remarks,
        )

    def submit_contra_without_redirect(self) -> None:
        if self._contra_submit_button.is_enabled():
            self._contra_submit_button.click()

    def is_same_ledger_error_visible(self) -> bool:
        return self.has_validation_error("same")

    def get_contra_validation_error(self) -> str:
        error = self.page.locator(".invalid-feedback:visible, .alert-danger:visible, .Toastify__toast--error:visible")
        return error.first.inner_text() if error.count() and error.first.is_visible() else ""

    def fund_first_bank(self, amount: str = "5000") -> str:
        self.navigate_contra()
        self._preset_select.select_option("cash_to_bank")
        bank_name = self._debit_ledger_select.locator("option:checked").inner_text()
        self._amount_input.fill(amount)
        self._contra_submit_button.click()
        self.page.wait_for_url(lambda url: "/vouchers/history" in url, timeout=15000)
        return bank_name

    def fund_bank_account(self, bank_name: str, amount: str = "5000") -> None:
        self.navigate_contra()
        self.create_contra_custom(bank_name, "Cash Ledger", amount, f"Fund {bank_name}")
        self.page.wait_for_url(lambda url: "/vouchers/history" in url, timeout=15000)

    def _set_allocation(self, allocation: str, bill_reference: str = "") -> None:
        if allocation == "auto":
            auto_radio = self.page.locator("#alloc-auto, input[value='auto']")
            if auto_radio.count() and auto_radio.first.is_visible():
                auto_radio.first.check()
        elif allocation in {"on_account", "on-account", "advance"}:
            oa_radio = self.page.locator("#alloc-on_account, #alloc-on-account, input[value='on_account'], input[value='on-account']")
            if oa_radio.count() and oa_radio.first.is_visible():
                oa_radio.first.check()
        elif allocation == "manual":
            manual_radio = self.page.locator("#alloc-manual, input[value='manual']")
            if manual_radio.count() and manual_radio.first.is_visible():
                manual_radio.first.check()

            rows = self._form().locator("tbody tr")
            if rows.count() > 0:
                row = rows.filter(has_text=bill_reference).first if bill_reference else rows.first
                if row.count() > 0 and row.is_visible():
                    checkbox = row.locator("input[type='checkbox']")
                    if checkbox.count() > 0 and checkbox.is_visible():
                        checkbox.first.check()
        else:
            raise ValueError(f"Unsupported allocation mode: {allocation}")

    @staticmethod
    def _is_payment_response(response) -> bool:
        return (
            urlparse(response.url).path.rstrip("/").endswith("/vouchers/payment")
            and response.request.method == "POST"
        )

    def create_payment_voucher(
        self,
        supplier_ledger: str,
        cash_bank_ledger: str,
        amount: str,
        *,
        branch: str = "",
        allocation: str = "auto",
        bill_reference: str = "",
        remarks: str = "",
        reference: str = "",
    ) -> VoucherResult:
        self.page.goto(self.payment_voucher_url)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)

        # 1. Select Branch (0th select)
        target_branch = branch if branch else "Branch-neutral"
        self._select_field("branchId", target_branch, fallback_index=0)
        self.page.wait_for_timeout(400)

        # 2. Select Debit ledger (1st select - Supplier / Party being paid)
        self._select_field("debitId", supplier_ledger, fallback_index=1)
        self.page.wait_for_timeout(500)

        # 3. Select Credit ledger (2nd select - Cash/Bank funding)
        self._select_field("creditId", cash_bank_ledger, fallback_index=2, filter_text=branch)
        self.page.wait_for_timeout(400)

        self.fill_amount(amount)
        self.page.wait_for_timeout(500)

        self._set_allocation(allocation, bill_reference)
        self.page.wait_for_timeout(300)

        if remarks:
            self.fill_remarks(remarks)

        # Handle manual reference portion if visible / required
        ref_input = self._form().locator("input[placeholder*='MIG001'], input[placeholder*='e.g.'], input[name='referencePortion']")
        if ref_input.count() > 0 and ref_input.first.is_visible():
            ref_input.first.fill(reference or "PAY001")
            self.page.wait_for_timeout(300)

        submit_btn = self._form().locator("button[type='submit']").first
        submit_btn.wait_for(state="visible", timeout=5000)

        # Wait for async outstanding bills to load and enable the submit button
        try:
            self.page.wait_for_function(
                "() => { const b = document.querySelector('form button[type=\"submit\"]'); return b && !b.disabled; }",
                timeout=10000,
            )
        except Exception:
            pass

        if submit_btn.is_disabled():
            bills_cb = self._form().locator("tbody input[type='checkbox']").first
            if bills_cb.count() > 0 and bills_cb.is_visible():
                bills_cb.check()
                self.page.wait_for_timeout(500)

        with self.page.expect_response(self._is_payment_response, timeout=15000) as info:
            submit_btn.click()

        response = info.value
        response_body = response.json()
        if not response.ok:
            message = response_body.get("message") or self.get_contra_validation_error()
            code = response_body.get("code") or "UNKNOWN"
            errors = response_body.get("errors") or {}
            raise RuntimeError(
                f"Payment voucher submission failed for {supplier_ledger}: "
                f"{message} (code={code}, errors={errors})"
            )

        response_data = response_body.get("data") or {}
        voucher_data = response_data.get("voucher") or {}
        self._submission_succeeded = self.wait_for_success_toast(timeout=10000)
        if not self._submission_succeeded and not self.wait_for_redirect_to_history(timeout=5000):
            err_text = self.get_contra_validation_error()
            raise RuntimeError(f"Payment voucher submission failed for {supplier_ledger}. Error: {err_text}")

        return VoucherResult(
            voucher_no=str(voucher_data.get("voucher_no") or reference),
            voucher_type="Payment",
            amount=Decimal(str(amount)),
            debit_ledger=supplier_ledger,
            credit_ledger=cash_bank_ledger,
            branch_name=target_branch,
            voucher_id=str(voucher_data.get("id")) if voucher_data.get("id") is not None else None,
        )

    def create_payment_voucher_minimal(
        self, supplier_ledger: str, cash_bank_ledger: str, amount: str
    ) -> VoucherResult:
        return self.create_payment_voucher(supplier_ledger, cash_bank_ledger, amount)

    def prepare_payment(
        self, supplier_ledger: str, cash_bank_ledger: str, amount: str, *, branch: str = ""
    ) -> None:
        self.navigate()
        self.select_voucher_type("Payment")
        if branch:
            self._select_field("branchId", branch, fallback_index=0)
        self._select_field("debitId", supplier_ledger, fallback_index=0 if not branch else 1)
        self._select_field("creditId", cash_bank_ledger, fallback_index=1 if not branch else 2)
        self.fill_amount(amount)

    def create_receipt_voucher(
        self,
        customer_ledger: str,
        cash_bank_ledger: str,
        amount: str,
        *,
        branch: str = "",
        allocation: str = "auto",
        remarks: str = "",
        reference: str = "",
    ) -> VoucherResult:
        self.page.goto(self.receipt_voucher_url)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)

        target_branch = branch if branch else "Branch-neutral"
        self._select_field("branchId", target_branch, fallback_index=0)
        self.page.wait_for_timeout(400)

        self._select_field("debitId", cash_bank_ledger, fallback_index=1, filter_text=branch)
        self.page.wait_for_timeout(400)

        self._select_field("creditId", customer_ledger, fallback_index=2)
        self.page.wait_for_timeout(500)

        self.fill_amount(amount)
        self.page.wait_for_timeout(500)

        self._set_allocation(allocation)
        self.page.wait_for_timeout(300)

        if remarks:
            self.fill_remarks(remarks)

        # Handle manual reference portion if visible / required
        ref_input = self._form().locator("input[placeholder*='MIG001'], input[placeholder*='e.g.'], input[name='referencePortion']")
        if ref_input.count() > 0 and ref_input.first.is_visible():
            ref_input.first.fill(reference or "REC001")
            self.page.wait_for_timeout(300)

        submit_btn = self._form().locator("button[type='submit']").first
        submit_btn.wait_for(state="visible", timeout=5000)

        # Wait for async outstanding bills to load and enable the submit button
        try:
            self.page.wait_for_function(
                "() => { const b = document.querySelector('form button[type=\"submit\"]'); return b && !b.disabled; }",
                timeout=10000,
            )
        except Exception:
            pass

        if submit_btn.is_disabled():
            bills_cb = self._form().locator("tbody input[type='checkbox']").first
            if bills_cb.count() > 0 and bills_cb.is_visible():
                bills_cb.check()
                self.page.wait_for_timeout(500)

        submit_btn.click()
        self._submission_succeeded = self.wait_for_success_toast(timeout=10000)
        if not self._submission_succeeded and not self.wait_for_redirect_to_history(timeout=5000):
            err_text = self.get_contra_validation_error()
            raise RuntimeError(f"Receipt voucher submission failed for {customer_ledger}. Error: {err_text}")

        return VoucherResult(
            voucher_no=reference or "REC001",
            voucher_type="Receipt",
            amount=Decimal(str(amount)),
            debit_ledger=cash_bank_ledger,
            credit_ledger=customer_ledger,
            branch_name=target_branch,
        )

    def create_receipt_voucher_minimal(
        self, customer_ledger: str, cash_bank_ledger: str, amount: str
    ) -> None:
        self.create_receipt_voucher(customer_ledger, cash_bank_ledger, amount)

    def prepare_receipt(
        self, customer_ledger: str, cash_bank_ledger: str, amount: str, *, branch: str = ""
    ) -> None:
        self.navigate()
        self.select_voucher_type("Receipt")
        if branch:
            self._select_field("branchId", branch, fallback_index=0)
        self._select_field("debitId", cash_bank_ledger, fallback_index=0 if not branch else 1)
        self._select_field("creditId", customer_ledger, fallback_index=1 if not branch else 2)
        self.fill_amount(amount)

    def _journal_rows(self):
        return self._form().locator(".row.g-2.mb-2.align-items-end")

    def _fill_journal_line(
        self, index: int, ledger: str, dr_cr: str, amount: str
    ) -> None:
        row = self._journal_rows().nth(index)
        row.wait_for(state="visible", timeout=5000)

        # 1. Select ledger
        ledger_select = row.locator("select").first
        if ledger_select.count() > 0 and ledger_select.is_visible():
            val = ledger_select.evaluate(
                """(el, name) => {
                    const options = Array.from(el.options);
                    const opt = options.find(o => o.text.toLowerCase().includes(name.toLowerCase()));
                    return opt ? opt.value : null;
                }""",
                ledger,
            )
            if val is not None:
                ledger_select.select_option(value=val)
            elif ledger_select.locator("option").count() > index + 1:
                ledger_select.select_option(index=index + 1)
        elif row.locator(".react-select__control").count() > 0:
            rs_control = row.locator(".react-select__control").first
            rs_control.click()
            self.page.keyboard.type(ledger)
            self.page.wait_for_timeout(300)
            opt = self.page.locator(".react-select__option").filter(has_text=re.compile(re.escape(ledger), re.I)).first
            if opt.count() > 0 and opt.is_visible():
                opt.click()
            else:
                self.page.keyboard.press("Enter")

        # 2. Select DR / CR
        target_is_dr = dr_cr.lower() in {"dr", "debit"}
        dr_cr_select = row.locator("select").nth(1)
        if dr_cr_select.count() > 0 and dr_cr_select.is_visible():
            try:
                dr_cr_select.select_option(value="dr" if target_is_dr else "cr")
            except Exception:
                try:
                    dr_cr_select.select_option(index=0 if target_is_dr else 1)
                except Exception:
                    pass

        # 3. Fill amount
        num_input = row.locator("input[type='number']").first
        num_input.fill(str(amount))

    def _add_journal_line(self) -> None:
        self._form().get_by_role("button", name="Add line").click()

    def _remove_journal_line(self, index: int) -> None:
        self._journal_rows().nth(index).get_by_role("button", name="Remove").click()

    def create_journal_voucher(
        self, entries: list[dict], *, remarks: str = "", reference: str = ""
    ) -> None:
        self.navigate_journal()
        for index, entry in enumerate(entries):
            if index >= self._journal_rows().count():
                self._add_journal_line()
            self._fill_journal_line(
                index, entry["ledger"], entry["type"], entry["amount"]
            )
        if remarks:
            self.fill_remarks(remarks)
        self.page.wait_for_timeout(300)
        if self.is_submit_enabled():
            with self.page.expect_response(
                lambda r: "/vouchers" in r.url and r.request.method == "POST", timeout=15000
            ) as resp_info:
                self.click_submit()
            if resp_info.value.status in (200, 201):
                self._submission_succeeded = True

    def submit_journal_without_redirect(self) -> None:
        if self.is_submit_enabled():
            self.click_submit()

    def is_unbalanced_error_visible(self) -> bool:
        return self.page.get_by_text(re.compile(r"must\s*balance|unbalance|not\s*balance|mismatch", re.IGNORECASE)).first.is_visible()

    def create_chit_entry_voucher(
        self, chit_ledger: str, cash_bank_ledger: str, amount: str, *, remarks: str = ""
    ) -> None:
        self.navigate()
        self.select_voucher_type("Chit Entry")
        self.select_native(0, chit_ledger)
        self.fill_amount(amount)
        self.select_native(1, cash_bank_ledger)
        if self.is_submit_enabled():
            self.click_submit()

    def prepare_mdr(self, bank_name: str, mdr_amount: str, settlement_date: str = "") -> None:
        try:
            self.page.goto(f"{BASE_URL}/vouchers/mdr/create")
            self.page.wait_for_load_state("networkidle")
        except Exception:
            self.navigate()
            self.select_voucher_type("MDR Settlement")
        self.page.wait_for_timeout(500)

        if settlement_date:
            date_input = self._form().locator("input[type='date']").first
            if date_input.count() > 0 and date_input.is_visible():
                date_input.fill(settlement_date)
                self.page.wait_for_timeout(200)

        bank_select = self._form().locator("select").first
        bank_select.wait_for(state="visible", timeout=10000)
        try:
            self.page.wait_for_function(
                """(sel) => sel && sel.options && sel.options.length > 1""",
                bank_select.element_handle(),
                timeout=8000,
            )
        except Exception:
            pass

        bank_value = bank_select.evaluate(
            """(select, wanted) => {
                const option = Array.from(select.options).find(
                    item => item.text.trim() === wanted || item.text.toLowerCase().includes(wanted.toLowerCase())
                );
                return option ? option.value : null;
            }""",
            bank_name,
        )

        if bank_value:
            bank_select.select_option(value=bank_value)
            bank_select.dispatch_event("change")
            try:
                self.page.wait_for_response(
                    lambda r: "/accounting/mdr-settlement/preview" in r.url,
                    timeout=10000,
                )
            except Exception:
                pass
        else:
            options = bank_select.locator("option").all()
            if len(options) > 1:
                bank_select.select_option(index=1)
                bank_select.dispatch_event("change")
                try:
                    self.page.wait_for_response(
                        lambda r: "/accounting/mdr-settlement/preview" in r.url,
                        timeout=10000,
                    )
                except Exception:
                    pass

        self.page.wait_for_timeout(500)
        num_input = self._form().locator("input[type='number']").first
        if num_input.count() > 0 and num_input.is_visible():
            num_input.fill(str(mdr_amount))

    def create_mdr_settlement_voucher(
        self,
        bank_ledger: str,
        mdr_charge_ledger: str = "",
        settlement_amount: str = "",
        mdr_amount: str = "",
        *,
        settlement_date: str = "",
        remarks: str = "",
    ) -> None:
        charge = mdr_amount or settlement_amount
        self.prepare_mdr(bank_ledger, charge, settlement_date=settlement_date)
        if remarks:
            self.fill_remarks(remarks)

        submit_btn = self._form().locator("button[type='submit']")
        if submit_btn.count() == 0 or not submit_btn.is_visible():
            submit_btn = self._form().get_by_role("button", name=re.compile(r"Create|Submit", re.I)).first

        submit_btn.wait_for(state="visible", timeout=10000)
        try:
            self.page.wait_for_function(
                "(btn) => !btn.disabled",
                submit_btn.element_handle(),
                timeout=10000,
            )
        except Exception:
            pass

        if submit_btn.is_enabled():
            submit_btn.click()
            self._submission_succeeded = True
            try:
                self.wait_for_redirect_to_history(timeout=10000)
            except Exception:
                pass

    def submit_payment_without_redirect(self) -> None:
        if self.is_submit_enabled():
            self.click_submit()

    def submit_receipt_without_redirect(self) -> None:
        if self.is_submit_enabled():
            self.click_submit()

    def has_allocation_table(self) -> bool:
        return self._form().locator("table").count() > 0

    def is_amount_exceeds_outstanding_error(self) -> bool:
        return self.page.get_by_text(
            re.compile(r"exceed.*outstanding|amount.*outstanding|on\s*account|advance|remaining\s*amount", re.IGNORECASE)
        ).first.is_visible()
