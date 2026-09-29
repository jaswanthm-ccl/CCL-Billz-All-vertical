"""End-to-end coverage for cash and bank branch fund transfers."""
import time

import pytest
from playwright.sync_api import expect

from pages.accounting.branch_fund_transfers_page import BranchFundTransfersPage


@pytest.fixture(scope="module")
def cash_transfer(module_page, voucher_funded_state, transfer_destination_branch):
    marker = f"cash transfer {time.time_ns()}"
    transfer = BranchFundTransfersPage(module_page)
    balance_before = transfer.create_transfer(
        source=voucher_funded_state["branch"],
        destination=transfer_destination_branch,
        amount="40",
        remarks=marker,
    )
    balance_after = transfer.current_balance_for(
        voucher_funded_state["branch"], transfer_destination_branch
    )
    return {
        "marker": marker,
        "amount": "40.00",
        "balance_before": balance_before,
        "balance_after": balance_after,
    }


@pytest.fixture(scope="module")
def bank_transfer(
    module_page,
    voucher_funded_state,
    transfer_destination_branch,
    transfer_destination_bank,
):
    marker = f"bank transfer {time.time_ns()}"
    transfer = BranchFundTransfersPage(module_page)
    balance_before = transfer.create_transfer(
        source=voucher_funded_state["branch"],
        destination=transfer_destination_branch,
        amount="35",
        remarks=marker,
        transfer_type="bank",
        source_bank=voucher_funded_state["bank"],
        destination_bank=transfer_destination_bank,
    )
    balance_after = transfer.current_balance_for(
        voucher_funded_state["branch"],
        transfer_destination_branch,
        transfer_type="bank",
        source_bank=voucher_funded_state["bank"],
        destination_bank=transfer_destination_bank,
    )
    return {
        "marker": marker,
        "amount": "35.00",
        "balance_before": balance_before,
        "balance_after": balance_after,
    }


class TestBranchFundTransferForm:
    def test_page_loads(self, logged_in_page):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        assert transfer.is_branch_fund_transfers_visible()

    def test_required_fields_keep_submit_disabled(self, logged_in_page):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate_create()
        expect(transfer.submit_button).to_be_disabled()

    def test_same_branch_is_rejected(self, logged_in_page, voucher_funded_state):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate_create()
        transfer.select_branches(
            voucher_funded_state["branch"], voucher_funded_state["branch"]
        )
        expect(transfer.same_branch_error()).to_be_visible()
        expect(transfer.submit_button).to_be_disabled()

    @pytest.mark.parametrize("invalid_amount", ["0", "-1"])
    def test_non_positive_amount_is_rejected(
        self,
        logged_in_page,
        voucher_funded_state,
        transfer_destination_branch,
        invalid_amount,
    ):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate_create()
        transfer.select_branches(voucher_funded_state["branch"], transfer_destination_branch)
        transfer.wait_for_available_balance()
        transfer.amount.fill(invalid_amount)
        expect(transfer.submit_button).to_be_disabled()

    def test_amount_above_available_balance_is_rejected(
        self, logged_in_page, voucher_funded_state, transfer_destination_branch
    ):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate_create()
        transfer.select_branches(voucher_funded_state["branch"], transfer_destination_branch)
        balance = transfer.wait_for_available_balance()
        transfer.amount.fill(str(balance + 0.01))
        expect(transfer.exceeds_balance_error()).to_be_visible()
        expect(transfer.submit_button).to_be_disabled()

    def test_cash_transfer_can_be_created(self, logged_in_page, cash_transfer):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        transfer.search(cash_transfer["marker"])
        row = transfer.row_with_text(cash_transfer["marker"])
        expect(row).to_contain_text("Cash")
        expect(row).to_contain_text(cash_transfer["amount"])

    def test_bank_transfer_can_be_created(self, logged_in_page, bank_transfer):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        transfer.search(bank_transfer["marker"])
        row = transfer.row_with_text(bank_transfer["marker"])
        expect(row).to_contain_text("Bank")
        expect(row).to_contain_text(bank_transfer["amount"])

    @pytest.mark.parametrize(
        ("fixture_name", "amount"),
        [("cash_transfer", 40.0), ("bank_transfer", 35.0)],
    )
    def test_source_balance_decreases_by_transfer_amount(
        self, request, fixture_name, amount
    ):
        transfer_data = request.getfixturevalue(fixture_name)
        assert transfer_data["balance_before"] - transfer_data["balance_after"] == pytest.approx(
            amount
        )


class TestBranchFundTransferHistory:
    def test_search_unknown_transfer_shows_empty_state(self, logged_in_page):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        transfer.search(f"missing-transfer-{time.time_ns()}")
        expect(logged_in_page.get_by_text("No branch fund transfers found.")).to_be_visible()

    def test_source_destination_and_type_filters(
        self,
        logged_in_page,
        cash_transfer,
        voucher_funded_state,
        transfer_destination_branch,
    ):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        transfer.search(cash_transfer["marker"])
        transfer.apply_filters(
            voucher_funded_state["branch"], transfer_destination_branch, "Cash"
        )
        row = transfer.row_with_text(cash_transfer["marker"])
        expect(row).to_contain_text(voucher_funded_state["branch"])
        expect(row).to_contain_text(transfer_destination_branch)
        expect(row).to_contain_text("Cash")

    def test_cash_transfer_details_match_form_data(
        self,
        logged_in_page,
        cash_transfer,
        voucher_funded_state,
        transfer_destination_branch,
    ):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        transfer.search(cash_transfer["marker"])
        drawer = transfer.open_details(cash_transfer["marker"])
        expect(drawer).to_contain_text(voucher_funded_state["branch"])
        expect(drawer).to_contain_text(transfer_destination_branch)
        expect(drawer).to_contain_text(cash_transfer["marker"])
        expect(drawer).to_contain_text(cash_transfer["amount"])

    @pytest.mark.parametrize("voucher_heading", ["Source voucher", "Destination voucher"])
    def test_each_cash_transfer_voucher_is_balanced(
        self, logged_in_page, cash_transfer, voucher_heading
    ):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        transfer.search(cash_transfer["marker"])
        drawer = transfer.open_details(cash_transfer["marker"])
        debit, credit = transfer.voucher_totals(drawer, voucher_heading)
        assert debit == credit == 40.0, (
            f"{voucher_heading} should contain equal 40.00 debit and credit entries; "
            f"got debit={debit}, credit={credit}"
        )

    def test_bank_transfer_creates_paired_vouchers(self, logged_in_page, bank_transfer):
        transfer = BranchFundTransfersPage(logged_in_page)
        transfer.navigate()
        transfer.search(bank_transfer["marker"])
        drawer = transfer.open_details(bank_transfer["marker"])
        expect(drawer.get_by_text("Source voucher", exact=True)).to_be_visible()
        expect(drawer.get_by_text("Destination voucher", exact=True)).to_be_visible()
        source_debit, source_credit = transfer.voucher_totals(drawer, "Source voucher")
        destination_debit, destination_credit = transfer.voucher_totals(
            drawer, "Destination voucher"
        )
        assert source_debit == source_credit == 35.0
        assert destination_debit == destination_credit == 35.0
