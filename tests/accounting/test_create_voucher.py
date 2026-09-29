"""Tests for Create Voucher — all 6 voucher types.

Sections:
1. Contra Voucher (native selects, /vouchers/contra/create)
2. Journal Voucher (multi-line DR/CR)
3. Payment Voucher (supplier allocation)
4. Receipt Voucher (customer allocation)
5. Chit Entry & MDR Settlement
6. Manual Numbering defect (skipped)
"""
import pytest

from pages.accounting.create_voucher_page import CreateVoucherPage


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONTRA VOUCHER
# ══════════════════════════════════════════════════════════════════════════════


class TestContraVoucher:
    """Contra Voucher: internal cash/bank transfers."""

    def test_contra_cash_to_bank_preset(self, logged_in_page, voucher_funded_state):
        """Create a contra voucher using cash_to_bank preset."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        page.create_contra_preset("cash_to_bank", "10", remarks="Cash to bank test")

        assert page.wait_for_redirect_to_history(), (
            "Contra voucher (cash_to_bank) did not redirect to history"
        )

    def test_contra_bank_to_cash_preset(self, logged_in_page, voucher_funded_state):
        """Create a contra voucher using bank_to_cash preset."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        page.create_contra_preset(
            "bank_to_cash",
            "50",
            remarks="Bank to cash test",
            credit_ledger=voucher_funded_state["bank"],
            debit_ledger="Cash Ledger",
            branch=voucher_funded_state["branch"],
        )

        assert page.wait_for_redirect_to_history(), (
            "Contra voucher (bank_to_cash) did not redirect to history"
        )

    def test_contra_bank_to_bank_preset(self, logged_in_page, voucher_funded_state):
        """Create a contra voucher using bank_to_bank preset (if two banks exist)."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        # bank_to_bank requires at least 2 bank accounts
        page._preset_select.select_option("bank_to_bank")
        page.page.wait_for_timeout(500)

        # Check if debit ledger has options (needs 2+ banks)
        options_count = page._debit_ledger_select.locator("option").count()
        if options_count <= 1:
            pytest.skip("Only one bank account exists — cannot test bank_to_bank preset")

        page._amount_input.fill("25")
        page._remarks_textarea.fill("Bank to bank transfer test")
        page._contra_submit_button.click()

        assert page.wait_for_redirect_to_history(), (
            "Contra voucher (bank_to_bank) did not redirect to history"
        )

    def test_contra_custom_transfer(self, logged_in_page, voucher_funded_state):
        """Create a contra voucher with custom ledger selection."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        bank_name = voucher_funded_state["bank"]
        page.create_contra_custom(
            debit_ledger=bank_name,
            credit_ledger="Cash Ledger",
            amount="30",
            remarks="Custom contra transfer",
            branch=voucher_funded_state["branch"],
        )

        assert page.wait_for_redirect_to_history(), (
            "Custom contra voucher did not redirect to history"
        )

    def test_contra_same_ledger_rejected(self, logged_in_page, voucher_funded_state):
        """Selecting the same debit and credit ledger should show an error."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        page._preset_select.select_option("custom")
        page.page.wait_for_timeout(500)

        # Select same ledger for both debit and credit
        page._debit_ledger_select.select_option(label="Cash Ledger")
        page._credit_ledger_select.select_option(label="Cash Ledger")
        page._amount_input.fill("100")

        page.submit_contra_without_redirect()

        # Should show error or stay on the page
        current_url = page.page.url
        assert "/vouchers/contra/create" in current_url or page.is_same_ledger_error_visible(), (
            "Same ledger selection should be rejected but form appeared to submit"
        )

    def test_contra_zero_amount_rejected(self, logged_in_page, voucher_funded_state):
        """Zero amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        page._preset_select.select_option("cash_to_bank")
        page.page.wait_for_timeout(500)
        page._amount_input.fill("0")
        page.submit_contra_without_redirect()

        # Should stay on form
        assert "/vouchers/contra/create" in page.page.url, (
            "Zero amount should not allow form submission"
        )

    def test_contra_negative_amount_rejected(self, logged_in_page, voucher_funded_state):
        """Negative amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        page._preset_select.select_option("cash_to_bank")
        page.page.wait_for_timeout(500)
        page._amount_input.fill("-50")
        page.submit_contra_without_redirect()

        # Should stay on form
        assert "/vouchers/contra/create" in page.page.url, (
            "Negative amount should not allow form submission"
        )

    def test_contra_empty_amount_rejected(self, logged_in_page, voucher_funded_state):
        """Empty amount field should prevent submission."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate_contra()

        page._preset_select.select_option("cash_to_bank")
        page.page.wait_for_timeout(500)
        page._amount_input.fill("")
        page.submit_contra_without_redirect()

        assert "/vouchers/contra/create" in page.page.url, (
            "Empty amount should not allow form submission"
        )



# ══════════════════════════════════════════════════════════════════════════════
# 2. JOURNAL VOUCHER
# ══════════════════════════════════════════════════════════════════════════════


class TestJournalVoucher:
    """Journal Voucher: multi-line debit/credit adjustment entries."""

    def test_journal_balanced_entry(self, logged_in_page, voucher_funded_state):
        """Create a balanced journal voucher (total DR == total CR)."""
        page = CreateVoucherPage(logged_in_page)

        customer_name = voucher_funded_state.get("customer", "")
        page.create_journal_voucher(
            entries=[
                {"ledger": "Sales Account", "type": "debit", "amount": "100"},
                {"ledger": customer_name or "Discount", "type": "credit", "amount": "100"},
            ],
            remarks="Balanced journal entry test",
        )

        # Should redirect to history or show success
        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, (
            "Balanced journal voucher was not created successfully"
        )

    def test_journal_unbalanced_entry_rejected(self, logged_in_page, voucher_funded_state):
        """An unbalanced journal (DR != CR) should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Journal")
        page.page.wait_for_timeout(500)

        customer_name = voucher_funded_state.get("customer", "")

        # Fill first line: DR 200
        page._fill_journal_line(0, "Sales Account", "debit", "200")

        # Fill the second default line: CR 100 (unbalanced - 200 != 100)
        page._fill_journal_line(1, customer_name or "Discount", "credit", "100")

        assert page.is_unbalanced_error_visible()
        assert not page.is_submit_enabled(), "Unbalanced journal must disable submit"

    def test_journal_add_and_remove_lines(self, logged_in_page, voucher_funded_state):
        """Verify adding and removing journal entry lines works."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Journal")
        page.page.wait_for_timeout(500)

        # Start with the initial row(s), add two more
        page._add_journal_line()
        page.page.wait_for_timeout(300)
        page._add_journal_line()
        page.page.wait_for_timeout(300)

        # Count rows — should have at least 3
        initial_count = page._journal_rows().count()
        assert initial_count == 4, (
            f"Expected at least 3 entry lines after adding 2, got {initial_count}"
        )

        # Remove the last line
        page._remove_journal_line(initial_count - 1)
        page.page.wait_for_timeout(300)

        # Count again — should be one fewer
        rows_after = page._journal_rows().count()
        assert rows_after == initial_count - 1, (
            f"Expected one fewer row after removal, got {rows_after} (was {initial_count})"
        )

    def test_journal_zero_amount_rejected(self, logged_in_page, voucher_funded_state):
        """Journal entry with zero amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Journal")
        page.page.wait_for_timeout(500)

        bank_name = voucher_funded_state["bank"]
        page._fill_journal_line(0, "Cash Ledger", "debit", "0")

        page._fill_journal_line(1, bank_name, "credit", "0")

        assert not page.is_submit_enabled(), "Zero-value journal must disable submit"

    def test_journal_empty_ledger_rejected(self, logged_in_page, voucher_funded_state):
        """Journal entry without selecting a ledger should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Journal")
        page.page.wait_for_timeout(500)

        # Fill amount but don't select ledger
        amount_inputs = page._form().locator("input[type='number']").all()
        if amount_inputs:
            amount_inputs[0].fill("100")

        assert not page.is_submit_enabled(), "Journal without ledgers must disable submit"



# ══════════════════════════════════════════════════════════════════════════════
# 3. PAYMENT VOUCHER
# ══════════════════════════════════════════════════════════════════════════════


class TestPaymentVoucher:
    """Payment Voucher: outflow from cash/bank to supplier/expense ledger."""

    def test_payment_auto_allocation(self, logged_in_page, voucher_funded_state, module_outstanding_purchase):
        """Create a payment voucher with automatic bill allocation."""
        page = CreateVoucherPage(logged_in_page)

        supplier = module_outstanding_purchase["supplier"]
        branch_name = module_outstanding_purchase.get("branch", voucher_funded_state["branch"])
        page.create_payment_voucher(
            supplier_ledger=supplier,
            cash_bank_ledger=voucher_funded_state["bank"],
            amount="100",
            branch=branch_name,
            allocation="auto",
            remarks="Auto allocation payment",
        )

        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, (
            "Payment voucher (auto allocation) was not created successfully"
        )

    def test_payment_amount_exceeding_outstanding(self, logged_in_page, voucher_funded_state, module_outstanding_purchase):
        """Payment amount exceeding supplier outstanding should warn or restrict."""
        page = CreateVoucherPage(logged_in_page)
        supplier = module_outstanding_purchase["supplier"]
        branch_name = module_outstanding_purchase.get("branch", voucher_funded_state["branch"])
        page.prepare_payment(supplier, "Cash Ledger", "99999", branch=branch_name)
        page.submit_payment_without_redirect()

        assert (
            page.is_amount_exceeds_outstanding_error()
            or not page.is_submit_enabled()
            or "/vouchers/create" in logged_in_page.url
            or page.wait_for_error_toast(timeout=2000)
        )

    def test_payment_zero_amount_rejected(self, logged_in_page, voucher_funded_state, module_outstanding_purchase):
        """Payment with zero amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        supplier = module_outstanding_purchase["supplier"]
        branch_name = module_outstanding_purchase.get("branch", voucher_funded_state["branch"])
        page.prepare_payment(supplier, "Cash Ledger", "0", branch=branch_name)
        assert not page.is_submit_enabled(), "Zero payment must disable submit"

    def test_payment_negative_amount_rejected(self, logged_in_page, voucher_funded_state, module_outstanding_purchase):
        """Payment with negative amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        supplier = module_outstanding_purchase["supplier"]
        branch_name = module_outstanding_purchase.get("branch", voucher_funded_state["branch"])
        page.prepare_payment(supplier, "Cash Ledger", "-100", branch=branch_name)
        assert not page.is_submit_enabled(), "Negative payment must disable submit"

    def test_payment_required_fields(self, logged_in_page, voucher_funded_state):
        """Submitting payment with no fields filled should show validation errors."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Payment")
        page.page.wait_for_timeout(500)

        assert not page.is_submit_enabled(), "Empty payment must disable submit"

    def test_payment_via_bank_account(self, logged_in_page, voucher_funded_state, module_outstanding_purchase):
        """Create a payment voucher paid via bank account (not cash)."""
        page = CreateVoucherPage(logged_in_page)

        supplier = module_outstanding_purchase["supplier"]
        bank_name = voucher_funded_state["bank"]
        branch_name = module_outstanding_purchase.get("branch", voucher_funded_state["branch"])

        page.create_payment_voucher(
            supplier_ledger=supplier,
            cash_bank_ledger=bank_name,
            amount="50",
            branch=branch_name,
            allocation="auto",
            remarks="Payment via bank",
        )

        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, (
            "Payment voucher via bank was not created successfully"
        )



# ══════════════════════════════════════════════════════════════════════════════
# 4. RECEIPT VOUCHER
# ══════════════════════════════════════════════════════════════════════════════


class TestReceiptVoucher:
    """Receipt Voucher: inflow from customer to cash/bank ledger."""

    def test_receipt_auto_allocation(self, logged_in_page, voucher_funded_state, module_outstanding_sale):
        """Create a receipt voucher with automatic bill allocation."""
        page = CreateVoucherPage(logged_in_page)

        customer = module_outstanding_sale["customer"]
        branch_name = module_outstanding_sale.get("branch", voucher_funded_state["branch"])
        page.create_receipt_voucher(
            customer_ledger=customer,
            cash_bank_ledger="Cash Ledger",
            amount="100",
            branch=branch_name,
            allocation="auto",
            remarks="Auto allocation receipt",
        )

        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, (
            "Receipt voucher (auto allocation) was not created successfully"
        )

    def test_receipt_manual_allocation(self, logged_in_page, voucher_funded_state, module_outstanding_sale):
        """Create a receipt voucher without auto-allocation."""
        page = CreateVoucherPage(logged_in_page)

        customer = module_outstanding_sale["customer"]
        branch_name = module_outstanding_sale.get("branch", voucher_funded_state["branch"])
        page.create_receipt_voucher(
            customer_ledger=customer,
            cash_bank_ledger="Cash Ledger",
            amount="50",
            branch=branch_name,
            allocation="manual",
            remarks="Manual allocation receipt",
        )

        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, (
            "Receipt voucher (manual allocation) was not created successfully"
        )

    def test_receipt_amount_exceeding_outstanding(self, logged_in_page, voucher_funded_state, module_outstanding_sale):
        """Receipt amount exceeding customer outstanding."""
        page = CreateVoucherPage(logged_in_page)
        customer = module_outstanding_sale["customer"]
        branch_name = module_outstanding_sale.get("branch", voucher_funded_state["branch"])
        page.prepare_receipt(customer, "Cash Ledger", "99999", branch=branch_name)
        page.submit_receipt_without_redirect()

        assert (
            page.is_amount_exceeds_outstanding_error()
            or not page.is_submit_enabled()
            or "/vouchers/create" in logged_in_page.url
            or page.wait_for_error_toast(timeout=2000)
        )

    def test_receipt_zero_amount_rejected(self, logged_in_page, voucher_funded_state, module_outstanding_sale):
        """Receipt with zero amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        customer = module_outstanding_sale["customer"]
        branch_name = module_outstanding_sale.get("branch", voucher_funded_state["branch"])
        page.prepare_receipt(customer, "Cash Ledger", "0", branch=branch_name)
        assert not page.is_submit_enabled(), "Zero receipt must disable submit"

    def test_receipt_negative_amount_rejected(self, logged_in_page, voucher_funded_state, module_outstanding_sale):
        """Receipt with negative amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        customer = module_outstanding_sale["customer"]
        branch_name = module_outstanding_sale.get("branch", voucher_funded_state["branch"])
        page.prepare_receipt(customer, "Cash Ledger", "-100", branch=branch_name)
        assert not page.is_submit_enabled(), "Negative receipt must disable submit"

    def test_receipt_required_fields(self, logged_in_page, voucher_funded_state):
        """Submitting receipt with no fields filled should show validation errors."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Receipt")
        page.page.wait_for_timeout(500)

        assert not page.is_submit_enabled(), "Empty receipt must disable submit"

    def test_receipt_via_bank_account(self, logged_in_page, voucher_funded_state, module_outstanding_sale):
        """Create a receipt voucher received via bank account."""
        page = CreateVoucherPage(logged_in_page)

        customer = module_outstanding_sale["customer"]
        bank_name = voucher_funded_state["bank"]

        page.create_receipt_voucher(
            customer_ledger=customer,
            cash_bank_ledger=bank_name,
            amount="50",
            allocation="auto",
            remarks="Receipt via bank",
        )

        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, (
            "Receipt voucher via bank was not created successfully"
        )



# ══════════════════════════════════════════════════════════════════════════════
# 5. CHIT ENTRY & MDR SETTLEMENT
# ══════════════════════════════════════════════════════════════════════════════


class TestChitEntryVoucher:
    """Chit Entry Voucher: records chit fund transactions."""

    def test_chit_entry_creation(self, logged_in_page, voucher_funded_state, module_chit):
        """Create a valid chit entry voucher."""
        page = CreateVoucherPage(logged_in_page)

        page.create_chit_entry_voucher(
            chit_ledger=module_chit,
            cash_bank_ledger="Cash Ledger",
            amount="100",
        )

        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, "Chit entry voucher was not created"

    def test_chit_entry_missing_amount_rejected(self, logged_in_page, voucher_funded_state):
        """Chit entry with no amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Chit Entry")
        page.page.wait_for_timeout(500)

        assert not page.is_submit_enabled(), "Chit entry without amount must be disabled"

    def test_chit_entry_zero_amount_rejected(self, logged_in_page, voucher_funded_state):
        """Chit entry with zero amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("Chit Entry")
        page.page.wait_for_timeout(500)

        page.fill_amount("0")
        assert not page.is_submit_enabled(), "Zero chit amount must disable submit"


class TestMDRSettlementVoucher:
    """MDR Settlement Voucher: reconciles POS card payments against bank charges."""

    def test_mdr_settlement_creation(self, logged_in_page, voucher_funded_state):
        """Create a valid MDR settlement voucher."""
        page = CreateVoucherPage(logged_in_page)

        bank_name = voucher_funded_state["bank"]

        page.create_mdr_settlement_voucher(
            bank_ledger=bank_name,
            mdr_charge_ledger="Cash Ledger",
            settlement_amount="100",
            mdr_amount="2",
            remarks="MDR settlement test",
        )

        redirected = page.wait_for_redirect_to_history()
        success = page.wait_for_success_toast(timeout=3000) if not redirected else True

        assert redirected or success, "MDR settlement voucher was not created"

    def test_mdr_settlement_required_fields(self, logged_in_page, voucher_funded_state):
        """MDR settlement with empty fields should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("MDR Settlement")
        page.page.wait_for_timeout(500)

        assert not page.is_submit_enabled(), "Empty MDR settlement must disable submit"

    def test_mdr_settlement_zero_amount_rejected(self, logged_in_page, voucher_funded_state):
        """MDR settlement with zero settlement amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("MDR Settlement")
        page.page.wait_for_timeout(500)

        page.fill_amount("0")
        assert not page.is_submit_enabled(), "Zero MDR charge must disable submit"

    def test_mdr_settlement_negative_amount_rejected(self, logged_in_page, voucher_funded_state):
        """MDR settlement with negative amount should be rejected."""
        page = CreateVoucherPage(logged_in_page)
        page.navigate()
        page.select_voucher_type("MDR Settlement")
        page.page.wait_for_timeout(500)

        page.fill_amount("-50")
        assert not page.is_submit_enabled(), "Negative MDR charge must disable submit"



# ══════════════════════════════════════════════════════════════════════════════
# 6. MANUAL NUMBERING DEFECT (skipped — known defect)
# ══════════════════════════════════════════════════════════════════════════════


class TestManualNumbering:
    """Manual Voucher Numbering — known defect.

    When Payment Voucher is switched to 'Manual Entry' numbering mode,
    the form does not render a Voucher Number input field, making it
    impossible to enter a custom voucher number.

    These tests are skipped until the defect is resolved.
    Future coverage: unique number, blank number rejected, duplicate rejected.
    """

    @pytest.mark.skip(
        reason="DEFECT: Payment Voucher Manual Entry mode does not render "
               "Voucher Number input field. No way to enter custom number. "
               "Reported to dev team — awaiting fix."
    )
    def test_manual_number_entry_field_exists(self, logged_in_page, voucher_funded_state):
        """Verify that switching to Manual Entry shows a Voucher Number field."""
        from pages.master_menu.voucher_types_page import VoucherTypesPage

        vt_page = VoucherTypesPage(logged_in_page)
        vt_page.navigate()

        # Read current prefix to restore later
        original_prefix = vt_page.get_current_prefix("Payment Voucher")

        # Switch to Manual Entry
        vt_page.edit_voucher_type("Payment Voucher", "MANUAL")

        try:
            # Navigate to create payment voucher
            page = CreateVoucherPage(logged_in_page)
            page.navigate()
            page.select_voucher_type("Payment")
            page.page.wait_for_timeout(1000)

            # Check if voucher number input exists
            voucher_no = page.get_voucher_number()
            assert voucher_no is not None, (
                "DEFECT: Manual Entry mode does not show Voucher Number field"
            )
        finally:
            # Rollback: restore original prefix
            vt_page.navigate()
            vt_page.edit_voucher_type("Payment Voucher", original_prefix)

    @pytest.mark.skip(
        reason="DEFECT: Payment Voucher Manual Entry mode does not render "
               "Voucher Number input field. Cannot test unique numbering."
    )
    def test_manual_number_must_be_unique(self, logged_in_page, voucher_funded_state):
        """Duplicate manual voucher numbers should be rejected."""
        pass

    @pytest.mark.skip(
        reason="DEFECT: Payment Voucher Manual Entry mode does not render "
               "Voucher Number input field. Cannot test blank rejection."
    )
    def test_manual_number_blank_rejected(self, logged_in_page, voucher_funded_state):
        """Blank manual voucher number should be rejected."""
        pass
