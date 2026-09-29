"""Restaurant Universal Voucher page object."""

from __future__ import annotations

from decimal import Decimal
from urllib.parse import urlparse

from playwright.sync_api import Page, expect

from pages.accounting.create_voucher_page import CreateVoucherPage as DefaultCreateVoucherPage
from utils.res_constants import (
    RESTAURANT_BASE_URL,
    RES_MDR_SETTLEMENT_URL,
    RES_PAYMENT_VOUCHER_URL,
)
from utils.models import VoucherResult


class CreateVoucherPage(DefaultCreateVoucherPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.create_voucher_url = f"{RESTAURANT_BASE_URL}/vouchers/create"
        self.payment_voucher_url = RES_PAYMENT_VOUCHER_URL
        self.receipt_voucher_url = f"{RESTAURANT_BASE_URL}/vouchers/receipt/create"
        self.contra_voucher_url = f"{RESTAURANT_BASE_URL}/vouchers/contra/create"
        self.journal_voucher_url = f"{RESTAURANT_BASE_URL}/vouchers/journal/create"
        self.mdr_settlement_url = RES_MDR_SETTLEMENT_URL

    def navigate(self) -> None:
        self.page.goto(self.create_voucher_url)
        self.page.wait_for_load_state("networkidle")

    def navigate_payment_voucher(self) -> None:
        self.page.goto(self.payment_voucher_url)
        self.page.wait_for_load_state("networkidle")

    def navigate_receipt_voucher(self) -> None:
        self.page.goto(self.receipt_voucher_url)
        self.page.wait_for_load_state("networkidle")

    def navigate_contra(self) -> None:
        self.page.goto(self.contra_voucher_url)
        self.page.wait_for_load_state("networkidle")
        self._form().wait_for(state="visible", timeout=10000)

    def navigate_journal(self) -> None:
        self.page.goto(self.journal_voucher_url)
        self.page.wait_for_load_state("networkidle")
        self._form().wait_for(state="visible", timeout=10000)

    @staticmethod
    def _matches_post(response, endpoint: str) -> bool:
        return (
            response.request.method == "POST"
            and urlparse(response.url).path.rstrip("/").endswith(endpoint)
        )

    @staticmethod
    def _voucher_payload(response, voucher_type: str) -> dict:
        try:
            body = response.json()
        except Exception as exc:
            raise AssertionError(
                f"{voucher_type} API returned a non-JSON response"
            ) from exc
        assert response.ok, (
            f"{voucher_type} creation failed with HTTP {response.status}: {body}"
        )
        voucher = (body.get("data") or {}).get("voucher") or {}
        assert voucher.get("id"), f"{voucher_type} response has no voucher ID: {body}"
        assert voucher.get("voucher_no"), (
            f"{voucher_type} response has no voucher number: {body}"
        )
        return voucher

    def _select_field(
        self,
        field_name: str,
        option_text: str,
        fallback_index: int = 0,
        filter_text: str = "",
    ) -> None:
        """Select a field and prove the requested option was actually selected."""
        super()._select_field(
            field_name,
            option_text,
            fallback_index=fallback_index,
            filter_text=filter_text,
        )

        controls = self._form().locator(".react-select__control")
        if controls.count() > fallback_index:
            selected = controls.nth(fallback_index).locator(
                ".react-select__single-value"
            )
            selected.wait_for(state="visible", timeout=5000)
            selected_text = selected.inner_text().strip()
        else:
            native = self._form().locator(f"select[name='{field_name}']")
            if native.count() == 0:
                native = self._form().locator("select").nth(fallback_index)
            selected_text = native.locator("option:checked").inner_text().strip()

        assert option_text.lower() in selected_text.lower(), (
            f"Requested option '{option_text}' was not selected for {field_name}; "
            f"selected '{selected_text}'"
        )
        if filter_text:
            assert filter_text.lower() in selected_text.lower(), (
                f"Selected ledger '{selected_text}' does not belong to branch "
                f"'{filter_text}'"
            )

    def _select_native_option(
        self, select_locator, ledger_name: str, branch: str = ""
    ) -> None:
        """Select an exact ledger and fail instead of silently retaining a default."""
        assert select_locator.is_enabled(), (
            f"Ledger selector is disabled while selecting '{ledger_name}'"
        )
        value = select_locator.evaluate(
            """(el, args) => {
                const options = Array.from(el.options);
                const wanted = args.ledger.toLowerCase();
                const branch = args.branch.toLowerCase();
                const candidates = options.filter(o =>
                    o.value && o.text.toLowerCase().includes(wanted)
                );
                if (branch) {
                    const scoped = candidates.find(o =>
                        o.text.toLowerCase().includes(branch)
                    );
                    if (scoped) return scoped.value;
                }
                const exact = candidates.find(o =>
                    o.text.trim().toLowerCase() === wanted
                );
                return exact ? exact.value : (candidates[0]?.value ?? null);
            }""",
            {"ledger": ledger_name, "branch": branch},
        )
        assert value is not None, (
            f"Ledger '{ledger_name}' was not available in the selector"
        )
        select_locator.select_option(value=value)

    def _fill_journal_line(
        self, index: int, ledger: str, dr_cr: str, amount: str
    ) -> None:
        row = self._journal_rows().nth(index)
        row.wait_for(state="visible", timeout=5000)
        ledger_select = row.locator("select").first
        value = ledger_select.evaluate(
            """(el, name) => {
                const wanted = name.toLowerCase();
                const option = Array.from(el.options).find(o =>
                    o.value && o.text.toLowerCase().includes(wanted)
                );
                return option ? option.value : null;
            }""",
            ledger,
        )
        assert value is not None, f"Journal ledger '{ledger}' is unavailable"
        ledger_select.select_option(value=value)

        entry_type = "dr" if dr_cr.lower() in {"dr", "debit"} else "cr"
        row.locator("select").nth(1).select_option(value=entry_type)
        row.locator("input[type='number']").first.fill(str(amount))

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
        self.navigate_receipt_voucher()
        target_branch = branch or "Branch-neutral"
        self._select_field("branchId", target_branch, fallback_index=0)
        self._select_field(
            "debitId", cash_bank_ledger, fallback_index=1, filter_text=branch
        )
        self._select_field("creditId", customer_ledger, fallback_index=2)
        self.fill_amount(amount)
        self._set_allocation(allocation)
        if remarks:
            self.fill_remarks(remarks)

        submit = self.submit_button().first
        expect(submit).to_be_enabled(timeout=15000)
        with self.page.expect_response(
            lambda response: self._matches_post(response, "/vouchers/receipt"),
            timeout=15000,
        ) as response_info:
            submit.click()
        voucher = self._voucher_payload(response_info.value, "Receipt Voucher")
        self.page.wait_for_url("**/vouchers/history", timeout=10000)
        return VoucherResult(
            voucher_no=str(voucher["voucher_no"]),
            voucher_type="Receipt Voucher",
            amount=Decimal(str(amount)),
            debit_ledger=cash_bank_ledger,
            credit_ledger=customer_ledger,
            branch_name=target_branch,
            voucher_id=str(voucher["id"]),
        )

    def create_contra_voucher(
        self,
        debit_ledger: str = "",
        credit_ledger: str = "",
        amount: str = "",
        *,
        preset: str = "custom",
        branch: str = "",
        remarks: str = "",
    ) -> VoucherResult:
        self.navigate_contra()
        self._preset_select.select_option(preset)
        if debit_ledger:
            self._select_native_option(
                self._debit_ledger_select, debit_ledger, branch
            )
        if credit_ledger:
            self._select_native_option(
                self._credit_ledger_select, credit_ledger, branch
            )

        selected_debit = self._debit_ledger_select.locator(
            "option:checked"
        ).inner_text().strip()
        selected_credit = self._credit_ledger_select.locator(
            "option:checked"
        ).inner_text().strip()
        assert selected_debit and selected_credit, "Contra ledgers were not selected"
        assert selected_debit != selected_credit, "Contra ledgers must be different"

        self._amount_input.fill(amount)
        if remarks:
            self._remarks_textarea.fill(remarks)
        expect(self._contra_submit_button).to_be_enabled(timeout=10000)
        with self.page.expect_response(
            lambda response: self._matches_post(response, "/vouchers/contra"),
            timeout=15000,
        ) as response_info:
            self._contra_submit_button.click()
        voucher = self._voucher_payload(response_info.value, "Contra Voucher")
        self.page.wait_for_url("**/vouchers/history", timeout=10000)
        return VoucherResult(
            voucher_no=str(voucher["voucher_no"]),
            voucher_type="Contra Voucher",
            amount=Decimal(str(amount)),
            debit_ledger=selected_debit,
            credit_ledger=selected_credit,
            branch_name=branch or None,
            voucher_id=str(voucher["id"]),
        )

    def create_journal_voucher(
        self, entries: list[dict], *, remarks: str = "", reference: str = ""
    ) -> VoucherResult:
        self.navigate_journal()
        for index, entry in enumerate(entries):
            if index >= self._journal_rows().count():
                self._add_journal_line()
            self._fill_journal_line(
                index, entry["ledger"], entry["type"], entry["amount"]
            )
        if remarks:
            self.fill_remarks(remarks)

        submit = self.submit_button().first
        expect(submit).to_be_enabled(timeout=10000)
        with self.page.expect_response(
            lambda response: self._matches_post(response, "/vouchers/journal"),
            timeout=15000,
        ) as response_info:
            submit.click()
        voucher = self._voucher_payload(response_info.value, "Journal Voucher")
        self.page.wait_for_url("**/vouchers/history", timeout=10000)
        debit_total = sum(
            Decimal(str(entry["amount"]))
            for entry in entries
            if entry["type"].lower() in {"dr", "debit"}
        )
        return VoucherResult(
            voucher_no=str(voucher["voucher_no"]),
            voucher_type="Journal Voucher",
            amount=debit_total,
            debit_ledger=", ".join(
                entry["ledger"]
                for entry in entries
                if entry["type"].lower() in {"dr", "debit"}
            ),
            credit_ledger=", ".join(
                entry["ledger"]
                for entry in entries
                if entry["type"].lower() in {"cr", "credit"}
            ),
            voucher_id=str(voucher["id"]),
        )

    def create_mdr_settlement_voucher(
        self,
        bank_ledger: str,
        mdr_amount: str,
        *,
        settlement_date: str,
        expected_gross: str,
        remarks: str = "",
    ) -> VoucherResult:
        """Create a strict Restaurant MDR settlement from prior-day bank sales."""
        self.page.goto(self.mdr_settlement_url)
        self.page.wait_for_load_state("networkidle")
        form = self._form()
        form.wait_for(state="visible", timeout=10000)

        bank_select = form.locator("select").first
        bank_select.wait_for(state="visible", timeout=10000)
        bank_value = bank_select.evaluate(
            """(select, wanted) => {
                const option = Array.from(select.options).find(
                    item => item.text.trim() === wanted
                );
                return option ? option.value : null;
            }""",
            bank_ledger,
        )
        assert bank_value is not None, (
            f"Bank '{bank_ledger}' was unavailable for MDR settlement"
        )

        date_input = form.locator("input[type='date']")
        date_input.fill(settlement_date)
        with self.page.expect_response(
            lambda response: (
                response.request.method == "GET"
                and "/accounting/mdr-settlement/preview" in response.url
                and f"bank_account_id={bank_value}" in response.url
            ),
            timeout=15000,
        ) as preview_info:
            bank_select.select_option(value=bank_value)

        preview_response = preview_info.value
        preview_payload = preview_response.json()
        assert preview_response.ok, (
            f"MDR preview returned HTTP {preview_response.status}: {preview_payload}"
        )
        preview = preview_payload.get("data") or {}
        assert Decimal(str(preview.get("gross_amount"))) == Decimal(expected_gross)

        number_input = form.locator("input[type='number']").first
        number_input.fill(mdr_amount)
        if remarks:
            form.locator("textarea").fill(remarks)

        submit = form.get_by_role("button", name="Create MDR settlement", exact=True)
        expect(submit).to_be_enabled(timeout=10000)
        with self.page.expect_response(
            lambda response: self._matches_post(response, "/vouchers"),
            timeout=15000,
        ) as response_info:
            submit.click()
        voucher = self._voucher_payload(response_info.value, "MDR Settlement")
        self.page.wait_for_url("**/vouchers/history", timeout=10000)

        gross = Decimal(expected_gross)
        charge = Decimal(mdr_amount)
        return VoucherResult(
            voucher_no=str(voucher["voucher_no"]),
            voucher_type="MDR Settlement",
            amount=gross - charge,
            debit_ledger="Bank Charges Ledger",
            credit_ledger=bank_ledger,
            voucher_id=str(voucher["id"]),
        )
