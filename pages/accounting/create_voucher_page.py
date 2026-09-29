from __future__ import annotations

import re
from urllib.parse import urlparse

from decimal import Decimal
from playwright.sync_api import Page, Response, TimeoutError as PlaywrightTimeoutError, expect

from pages.common.base_page import BasePage
from utils.models import VoucherResult
from utils.tenants import Tenant


class CreateVoucherPage(BasePage):
    """Page object for voucher creation forms."""

    TYPE_LABELS = {
        "Payment": "Payment Voucher",
        "Receipt": "Receipt Voucher",
        "Contra": "Contra Voucher",
        "Journal": "Journal Voucher",
        "Chit Entry": "Chit Entry",
        "MDR Settlement": "MDR Settlement",
    }

    PATH = "/vouchers/create"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)
        self._selected_type = ""
        self._submission_succeeded = False
        self.last_voucher_response: Response | None = None
        self.create_voucher_url = self.tenant.url("/vouchers/create")
        self.payment_voucher_url = self.tenant.url("/vouchers/payment/create")
        self.receipt_voucher_url = self.tenant.url("/vouchers/receipt/create")
        self.contra_voucher_url = self.tenant.url("/vouchers/contra/create")
        self.journal_voucher_url = self.tenant.url("/vouchers/journal/create")
        self.mdr_settlement_url = self.tenant.url("/vouchers/mdr/create")

    def navigate(self) -> None:
        self.page.goto(self.create_voucher_url)

    def _open_form(self, url: str) -> None:
        self.page.goto(url)
        self._form().wait_for(state="visible", timeout=10000)

    def navigate_contra(self) -> None:
        self._open_form(self.contra_voucher_url)

    def navigate_journal(self) -> None:
        self._open_form(self.journal_voucher_url)

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
            controls.nth(fallback_index).click()
            self.page.keyboard.type(option_text)
            matches = self.page.locator(".react-select__option").filter(has_text=option_text)
            # Same-named ledgers exist per branch (e.g. "Cash Ledger"); prefer the one labelled with the branch.
            if filter_text:
                branch_match = matches.filter(has_text=filter_text)
                try:
                    expect(branch_match.first).to_be_visible(timeout=3000)
                    branch_match.first.click()
                    return
                except AssertionError:
                    pass
            matches.first.click()
            return

        native = self._form().locator(f"select[name='{field_name}']")
        if native.count() > 0 and native.first.is_visible():
            native.first.select_option(label=option_text)
            return

        self._form().locator("select").nth(fallback_index).select_option(label=option_text)

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

    @staticmethod
    def _is_voucher_post(response) -> bool:
        return response.request.method == "POST" and "/vouchers" in urlparse(response.url).path

    @staticmethod
    def _is_mdr_post(response) -> bool:
        path = urlparse(response.url).path
        return response.request.method == "POST" and (
            "/vouchers" in path or ("mdr-settlement" in path and not path.endswith("/preview"))
        )

    def _submit_and_confirm(self, button, is_save_response=None) -> Response | None:
        """Click submit and judge success by the save API; toasts are too short-lived to rely on."""
        try:
            with self.page.expect_response(is_save_response or self._is_voucher_post, timeout=15000) as info:
                button.click()
        except PlaywrightTimeoutError:
            self._submission_succeeded = self.wait_for_success_toast(timeout=3000)
            return None
        self.last_voucher_response = info.value
        self._submission_succeeded = info.value.ok
        return info.value

    def _fill_reference_if_required(self, reference: str) -> None:
        ref_input = self._form().locator(
            "input[placeholder*='MIG001'], input[placeholder*='e.g.'], input[name='referencePortion']"
        )
        if ref_input.count() > 0 and ref_input.first.is_visible():
            ref_input.first.fill(reference)

    def _ready_submit_button(self):
        """Wait for outstanding bills to load; if the form still needs a bill picked, pick the first one."""
        submit_btn = self._form().locator("button[type='submit']").first
        try:
            expect(submit_btn).to_be_enabled(timeout=10000)
        except AssertionError:
            bill_checkbox = self._form().locator("tbody input[type='checkbox']").first
            if bill_checkbox.count() > 0 and bill_checkbox.is_visible():
                bill_checkbox.check()
            expect(submit_btn).to_be_enabled(timeout=5000)
        return submit_btn

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
        """Pick a ledger in a native select, preferring the option labelled with the branch."""
        if not select_locator.is_enabled():
            return
        try:
            value = self.page.wait_for_function(
                """([el, ledgerName, branchName]) => {
                    const options = Array.from(el.options);
                    const has = (o, text) => o.text.toLowerCase().includes(text.toLowerCase());
                    const match = (branchName && options.find(o => has(o, ledgerName) && has(o, branchName)))
                        || options.find(o => o.text.trim() === ledgerName)
                        || options.find(o => has(o, ledgerName));
                    return match ? match.value : null;
                }""",
                arg=[select_locator.element_handle(), ledger_name, branch],
                timeout=10000,
            ).json_value()
        except PlaywrightTimeoutError:
            raise AssertionError(f"Ledger '{ledger_name}' never appeared in the dropdown") from None
        select_locator.select_option(value=value)

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
        if debit_ledger:
            self._select_native_option(self._debit_ledger_select, debit_ledger, branch)
        if credit_ledger:
            self._select_native_option(self._credit_ledger_select, credit_ledger, branch)
        self._amount_input.fill(amount)
        if remarks:
            self._remarks_textarea.fill(remarks)
        self._submit_and_confirm(self._contra_submit_button)

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
        radios = {
            "auto": "#alloc-auto, input[value='auto']",
            "on_account": "#alloc-on_account, #alloc-on-account, input[value='on_account'], input[value='on-account']",
            "manual": "#alloc-manual, input[value='manual']",
        }
        mode = "on_account" if allocation in {"on_account", "on-account", "advance"} else allocation
        if mode not in radios:
            raise ValueError(f"Unsupported allocation mode: {allocation}")

        radio = self.page.locator(radios[mode]).first
        try:
            expect(radio).to_be_visible(timeout=5000)
        except AssertionError:
            # Auto is the form default and the radios are hidden when the party has no bills.
            if mode == "auto":
                return
            raise AssertionError(f"Allocation option '{mode}' is not available on the form") from None
        radio.check()

        if mode == "manual":
            rows = self._form().locator("tbody tr")
            row = rows.filter(has_text=bill_reference).first if bill_reference else rows.first
            row.locator("input[type='checkbox']").first.check()

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
        self._open_form(self.payment_voucher_url)

        target_branch = branch if branch else "Branch-neutral"
        self._select_field("branchId", target_branch, fallback_index=0)
        self._select_field("debitId", supplier_ledger, fallback_index=1)
        self._select_field("creditId", cash_bank_ledger, fallback_index=2, filter_text=branch)
        self.fill_amount(amount)
        self._set_allocation(allocation, bill_reference)
        if remarks:
            self.fill_remarks(remarks)
        self._fill_reference_if_required(reference or "PAY001")

        submit_btn = self._ready_submit_button()
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
        self.last_voucher_response = response
        self._submission_succeeded = True

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
        self._open_form(self.receipt_voucher_url)

        target_branch = branch if branch else "Branch-neutral"
        self._select_field("branchId", target_branch, fallback_index=0)
        self._select_field("debitId", cash_bank_ledger, fallback_index=1, filter_text=branch)
        self._select_field("creditId", customer_ledger, fallback_index=2)
        self.fill_amount(amount)
        self._set_allocation(allocation)
        if remarks:
            self.fill_remarks(remarks)
        self._fill_reference_if_required(reference or "REC001")

        response = self._submit_and_confirm(self._ready_submit_button())
        if not self._submission_succeeded and not self.wait_for_redirect_to_history(timeout=5000):
            err_text = response.text()[:500] if response else self.get_contra_validation_error()
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

        ledger_select = row.locator("select").first
        if ledger_select.count() > 0 and ledger_select.is_visible():
            self._select_native_option(ledger_select, ledger)
        else:
            row.locator(".react-select__control").first.click()
            self.page.keyboard.type(ledger)
            self.page.locator(".react-select__option").filter(
                has_text=re.compile(re.escape(ledger), re.I)
            ).first.click()

        target_is_dr = dr_cr.lower() in {"dr", "debit"}
        dr_cr_select = row.locator("select").nth(1)
        if dr_cr_select.count() > 0 and dr_cr_select.is_visible():
            value = dr_cr_select.evaluate(
                """(el, prefix) => {
                    const o = Array.from(el.options).find(o => (o.value + o.text).trim().toLowerCase().startsWith(prefix));
                    return o ? o.value : null;
                }""",
                "d" if target_is_dr else "c",
            )
            if value is None:
                raise AssertionError(f"No {'Dr' if target_is_dr else 'Cr'} option in journal line {index}")
            dr_cr_select.select_option(value=value)

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
        if self.is_submit_enabled():
            self._submit_and_confirm(self.submit_button())

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
            self._submit_and_confirm(self.submit_button())

    def prepare_mdr(self, bank_name: str, mdr_amount: str, settlement_date: str = "") -> None:
        self._open_form(self.mdr_settlement_url)

        if settlement_date:
            date_input = self._form().locator("input[type='date']").first
            if date_input.count() > 0 and date_input.is_visible():
                date_input.fill(settlement_date)

        bank_select = self._form().locator("select").first
        try:
            with self.page.expect_response(
                lambda r: "/accounting/mdr-settlement/preview" in r.url, timeout=10000
            ):
                self._select_native_option(bank_select, bank_name)
        except PlaywrightTimeoutError:
            pass  # The preview only loads when the bank has unsettled card sales.

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

        expect(submit_btn).to_be_enabled(timeout=10000)
        self._submit_and_confirm(submit_btn, self._is_mdr_post)
        if self._submission_succeeded:
            self.wait_for_redirect_to_history(timeout=10000)

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
