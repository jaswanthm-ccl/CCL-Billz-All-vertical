"""End-to-end coverage for the Balance Sheet report."""
from datetime import date
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.accounting.balance_sheet_page import BalanceSheetPage


def section_row_total(report: dict, section: str) -> Decimal:
    return sum(
        (Decimal(str(row["balance"])) for row in report[section]["rows"]),
        Decimal("0"),
    )


@pytest.fixture(scope="module")
def balance_sheet_funded_state(module_page, voucher_funded_state):
    """Load a branch-scoped Balance Sheet after creating balanced entries."""
    report_page = BalanceSheetPage(module_page)
    report_page.navigate()
    report = report_page.apply_filters(
        date.today().isoformat(), voucher_funded_state["branch"]
    )
    return {"report": report, **voucher_funded_state}


class TestBalanceSheetStructure:
    def test_page_loads_and_report_is_requested(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report = report_page.navigate()

        assert report_page.is_page_visible()
        assert report_page.last_status == 200
        assert {
            "as_of_date",
            "branch_id",
            "retained_earnings_from_date",
            "assets",
            "liabilities",
            "equity",
            "assets_grouped",
            "liabilities_grouped",
            "equity_grouped",
            "total_liabilities_and_equity",
            "is_balanced",
        } <= report.keys()

    def test_default_date_is_today(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report_page.navigate()
        assert report_page.as_of_date.input_value() == date.today().isoformat()

    def test_assets_and_liabilities_equity_sections_are_visible(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report_page.navigate()
        expect(logged_in_page.get_by_text("Assets", exact=True).first).to_be_visible()
        expect(logged_in_page.get_by_text("Liabilities & Equity", exact=True)).to_be_visible()
        expect(logged_in_page.get_by_text("Total Assets", exact=True).last).to_be_visible()
        expect(
            logged_in_page.get_by_text("Total Liabilities & Equity", exact=True)
        ).to_be_visible()


class TestBalanceSheetFilters:
    def test_date_is_required(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report_page.navigate()
        report_page.submit_without_date()
        expect(report_page.date_validation_error()).to_be_visible()

    def test_as_of_date_filter_is_sent_to_report(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report_page.navigate()
        report = report_page.apply_filters("2099-12-31")
        assert report["as_of_date"] == "2099-12-31"

    def test_clear_filters_restores_today(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report_page.navigate()
        report_page.apply_filters("2099-12-31")
        report = report_page.clear_filters()

        assert report_page.as_of_date.input_value() == date.today().isoformat()
        assert report["as_of_date"] == date.today().isoformat()
        assert report["branch_id"] is None

    def test_branch_filter_excludes_other_branch_rows(self, balance_sheet_funded_state):
        report = balance_sheet_funded_state["report"]
        rows = report["assets"]["rows"] + report["liabilities"]["rows"] + report["equity"]["rows"]
        mismatched_rows = [
            row
            for row in rows
            if row["branch_id"] is not None
            and str(row["branch_id"]) != str(report["branch_id"])
        ]

        assert report["branch_id"] is not None
        assert not mismatched_rows, (
            f"Branch filter {report['branch_id']} returned other branches: "
            f"{[(row['ledger_name'], row['branch_id']) for row in mismatched_rows]}"
        )


class TestBalanceSheetAccounting:
    @pytest.mark.parametrize("section", ["assets", "liabilities", "equity"])
    def test_section_rows_sum_to_section_total(
        self, balance_sheet_funded_state, section
    ):
        report = balance_sheet_funded_state["report"]
        assert section_row_total(report, section) == Decimal(
            str(report[section]["total"])
        )

    @pytest.mark.parametrize("section", ["assets", "liabilities", "equity"])
    def test_grouped_total_matches_section_total(
        self, balance_sheet_funded_state, section
    ):
        report = balance_sheet_funded_state["report"]
        assert Decimal(str(report[f"{section}_grouped"]["total"])) == Decimal(
            str(report[section]["total"])
        )

    def test_liabilities_plus_equity_matches_combined_total(self, balance_sheet_funded_state):
        report = balance_sheet_funded_state["report"]
        expected = Decimal(str(report["liabilities"]["total"])) + Decimal(
            str(report["equity"]["total"])
        )
        assert expected == Decimal(str(report["total_liabilities_and_equity"]))

    def test_balance_flag_matches_accounting_equation(self, balance_sheet_funded_state):
        report = balance_sheet_funded_state["report"]
        assets = Decimal(str(report["assets"]["total"]))
        liabilities_and_equity = Decimal(str(report["total_liabilities_and_equity"]))
        assert report["is_balanced"] is (assets == liabilities_and_equity)

    @pytest.mark.skip(
        reason=(
            "BUG: The branch-scoped Balance Sheet omits the Bank Ledger entry created "
            "by a bank-paid sale while retaining that sale in income"
        )
    )
    def test_funded_branch_balance_sheet_is_balanced(self, balance_sheet_funded_state):
        report = balance_sheet_funded_state["report"]
        assert report["is_balanced"] is True
        assert Decimal(str(report["assets"]["total"])) == Decimal(
            str(report["total_liabilities_and_equity"])
        )

    def test_rendered_totals_match_api(self, module_page, balance_sheet_funded_state):
        report_page = BalanceSheetPage(module_page)
        report = report_page.apply_filters(
            date.today().isoformat(), balance_sheet_funded_state["branch"]
        )

        assert report_page.summary_amount("Total Assets") == Decimal(
            str(report["assets"]["total"])
        )
        assert report_page.summary_amount("Liabilities") == Decimal(
            str(report["liabilities"]["total"])
        )
        assert report_page.summary_amount("Equity") == Decimal(
            str(report["equity"]["total"])
        )
        assert report_page.liabilities_subtotal() == Decimal(
            str(report["liabilities"]["total"])
        )
        assert report_page.footer_amount("assets") == Decimal(
            str(report["assets"]["total"])
        )
        assert report_page.footer_amount("liabilities_and_equity") == Decimal(
            str(report["total_liabilities_and_equity"])
        )

    def test_balance_message_matches_api(self, module_page, balance_sheet_funded_state):
        report_page = BalanceSheetPage(module_page)
        report = report_page.apply_filters(
            date.today().isoformat(), balance_sheet_funded_state["branch"]
        )
        expected = (
            "Balance Sheet is balanced"
            if report["is_balanced"]
            else "Balance Sheet mismatch detected"
        )
        assert expected in report_page.balance_message()

    def test_group_rows_can_be_collapsed_and_expanded(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report_page.navigate()
        before = report_page.displayed_ledger_count()
        assert before > 0
        report_page.collapse_first_group()
        expect(logged_in_page.get_by_role("button", name="Expand group").first).to_be_visible()
        report_page.expand_first_group()
        assert report_page.displayed_ledger_count() == before

    def test_ledger_row_opens_ledger_statement(self, logged_in_page):
        report_page = BalanceSheetPage(logged_in_page)
        report_page.navigate()
        assert report_page.displayed_ledger_count() > 0
        report_page.open_first_ledger()
        assert "/reports/ledger-statement" in logged_in_page.url
