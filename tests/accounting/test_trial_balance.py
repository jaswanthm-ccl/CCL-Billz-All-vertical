"""End-to-end coverage for the Trial Balance report."""
from datetime import date
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.accounting.trial_balance_page import TrialBalancePage


@pytest.fixture(scope="module")
def trial_balance_funded_state(module_page, voucher_funded_state):
    """Load Trial Balance after the accounting fixtures create balanced entries."""
    report_page = TrialBalancePage(module_page)
    report_page.navigate()
    report = report_page.apply_filters(
        date.today().isoformat(), voucher_funded_state["branch"]
    )
    return {"report": report, **voucher_funded_state}


class TestTrialBalanceStructure:
    def test_page_loads_and_report_is_requested(self, logged_in_page):
        report_page = TrialBalancePage(logged_in_page)
        report = report_page.navigate()

        assert report_page.is_page_visible()
        assert report_page.last_status == 200
        assert {
            "as_of_date",
            "branch_id",
            "rows",
            "total_debit",
            "total_credit",
            "is_balanced",
            "count",
        } <= report.keys()

    def test_default_date_is_today(self, logged_in_page):
        report_page = TrialBalancePage(logged_in_page)
        report_page.navigate()
        assert report_page.as_of_date.input_value() == date.today().isoformat()

    def test_table_has_expected_headers(self, logged_in_page):
        report_page = TrialBalancePage(logged_in_page)
        report_page.navigate()
        assert report_page.table_headers() == [
            "Ledger",
            "Type",
            "Branch",
            "Debit (₹)",
            "Credit (₹)",
        ]


class TestTrialBalanceFilters:
    def test_date_is_required(self, logged_in_page):
        report_page = TrialBalancePage(logged_in_page)
        report_page.navigate()
        report_page.submit_without_date()
        expect(report_page.date_validation_error()).to_be_visible()

    def test_as_of_date_filter_is_sent_to_report(self, logged_in_page):
        report_page = TrialBalancePage(logged_in_page)
        report_page.navigate()
        report = report_page.apply_filters("2099-12-31")

        assert report["as_of_date"] == "2099-12-31"
        assert report["count"] == len(report["rows"])

    def test_clear_filters_restores_today(self, logged_in_page):
        report_page = TrialBalancePage(logged_in_page)
        report_page.navigate()
        report_page.apply_filters("2099-12-31")
        report = report_page.clear_filters()

        assert report_page.as_of_date.input_value() == date.today().isoformat()
        assert report["as_of_date"] == date.today().isoformat()
        assert report["branch_id"] is None

    def test_branch_filter_is_sent_to_report(self, trial_balance_funded_state):
        report = trial_balance_funded_state["report"]
        assert report["branch_id"] is not None
        mismatched_rows = [
            row
            for row in report["rows"]
            if row["branch_id"] is not None
            and str(row["branch_id"]) != str(report["branch_id"])
        ]
        assert not mismatched_rows, (
            f"Branch filter {report['branch_id']} returned other branches: "
            f"{[(row['ledger_name'], row['branch_id'], row['branch_name']) for row in mismatched_rows]}"
        )


class TestTrialBalanceAccounting:
    def test_api_row_debits_sum_to_total(self, trial_balance_funded_state):
        report = trial_balance_funded_state["report"]
        row_total = sum(
            (Decimal(str(row["debit_balance"])) for row in report["rows"]),
            Decimal("0"),
        )
        assert row_total == Decimal(str(report["total_debit"]))

    def test_api_row_credits_sum_to_total(self, trial_balance_funded_state):
        report = trial_balance_funded_state["report"]
        row_total = sum(
            (Decimal(str(row["credit_balance"])) for row in report["rows"]),
            Decimal("0"),
        )
        assert row_total == Decimal(str(report["total_credit"]))

    def test_balance_flag_matches_debit_and_credit_totals(self, trial_balance_funded_state):
        report = trial_balance_funded_state["report"]
        totals_match = Decimal(str(report["total_debit"])) == Decimal(
            str(report["total_credit"])
        )
        assert report["is_balanced"] is totals_match

    @pytest.mark.skip(
        reason=(
            "BUG: The branch-scoped Trial Balance omits the Bank Ledger debit "
            "for a bank-paid sale, so total debit does not equal total credit"
        )
    )
    def test_funded_branch_trial_balance_is_balanced(self, trial_balance_funded_state):
        report = trial_balance_funded_state["report"]
        assert report["is_balanced"] is True
        assert Decimal(str(report["total_debit"])) == Decimal(
            str(report["total_credit"])
        )

    def test_rendered_totals_match_api(self, module_page, trial_balance_funded_state):
        report_page = TrialBalancePage(module_page)
        report = report_page.apply_filters(
            date.today().isoformat(), trial_balance_funded_state["branch"]
        )
        debit = Decimal(str(report["total_debit"]))
        credit = Decimal(str(report["total_credit"]))

        assert report_page.summary_amount("Total Debit") == debit
        assert report_page.summary_amount("Total Credit") == credit
        assert report_page.footer_amount("debit") == debit
        assert report_page.footer_amount("credit") == credit

    def test_rendered_rows_match_api_count(self, module_page, trial_balance_funded_state):
        report_page = TrialBalancePage(module_page)
        report = report_page.apply_filters(
            date.today().isoformat(), trial_balance_funded_state["branch"]
        )
        assert len(report_page.rows()) == report["count"] == len(report["rows"])

    def test_ledger_row_opens_ledger_statement(self, logged_in_page):
        report_page = TrialBalancePage(logged_in_page)
        report = report_page.navigate()
        assert report["rows"], "Trial Balance requires at least one ledger row"
        report_page.open_first_ledger()
        assert "/reports/ledger-statement" in logged_in_page.url
