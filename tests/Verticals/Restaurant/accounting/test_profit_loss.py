"""End-to-end coverage for the Restaurant-vertical Profit / Loss report."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.accounting.profit_loss_page import ProfitLossPage
from pages.Verticals.Restaurant.main_menu.expenses_page import ExpensesPage

pytestmark = pytest.mark.restaurant


# ── Known-state fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def res_profit_loss_known_state(browser, res_auth_state, res_branch):
    """
    Snapshot the P&L before and after adding a ₹250 expense so accounting
    tests can assert an exact delta without depending on pre-existing data.

    Scoped to 'module' so it runs once and is shared by all accounting tests.
    """
    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()

    today = date.today().isoformat()

    report_page = ProfitLossPage(page)
    report_page.navigate()
    before = report_page.apply_filters(today, today)

    # Add a ₹250 expense so we have a known delta to assert against.
    # expense_group="Direct" is the only combination confirmed working in
    # test_expenses.py — no branch needed, the form auto-assigns one.
    expenses_page = ExpensesPage(page)
    expenses_page.navigate()
    expenses_page.add_expense(
        expense_group="Direct",
        amount="250",
        notes="Res P&L known-state expense",
    )

    report_page.navigate()
    after = report_page.apply_filters(today, today)

    context.close()

    yield {"before": before, "after": after, "branch": res_branch}


# ── Structure tests ────────────────────────────────────────────────────────────

class TestResProfitLossStructure:
    """Verify the page loads correctly and the API returns expected keys."""

    def test_page_loads_and_report_is_requested(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        report = page.navigate()

        assert page.is_page_visible(), "Profit & Loss Reports heading / Filter button not visible"
        assert page.last_status == 200, f"API returned HTTP {page.last_status}"
        assert {"income", "expense", "net_profit", "is_profit"} <= report.keys(), (
            f"Expected keys missing from API response: {report.keys()}"
        )

    def test_default_date_range_ends_today(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()

        assert page.to_date.input_value() == date.today().isoformat(), (
            "Default to_date should be today"
        )
        assert page.from_date.input_value() < page.to_date.input_value(), (
            "Default from_date should be before to_date"
        )

    def test_income_and_expense_tables_have_expected_headers(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()

        assert page.table_headers() == [
            ["Ledger", "Branch", "Amount"],
            ["Ledger", "Branch", "Amount"],
        ], f"Unexpected table headers: {page.table_headers()}"


# ── Filter tests ───────────────────────────────────────────────────────────────

class TestResProfitLossFilters:
    """Verify date and branch filters behave correctly."""

    def test_reversed_date_range_is_rejected_in_form(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        today = date.today()

        page.submit_invalid_range(
            today.isoformat(),
            (today - timedelta(days=1)).isoformat(),
        )
        expect(page.date_validation_error()).to_be_visible()

    def test_future_period_has_zero_totals(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        report = page.apply_filters("2099-12-31", "2099-12-31")

        assert Decimal(str(report["income"]["total"])) == 0, "Income should be 0 for far-future period"
        assert Decimal(str(report["expense"]["total"])) == 0, "Expense should be 0 for far-future period"
        assert Decimal(str(report["net_profit"])) == 0, "Net profit should be 0 for far-future period"

    def test_branch_filter_limits_rows_to_selected_branch(
        self, res_logged_in_page, res_profit_loss_known_state
    ):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        today = date.today()
        branch = res_profit_loss_known_state["branch"]

        report = page.apply_filters(
            (today - timedelta(days=1)).isoformat(),
            today.isoformat(),
            branch,
        )

        assert str(report.get("branch_id", "")) not in {"", "None"}, (
            "branch_id should be set in response when branch filter is active"
        )
        rows = page.section_rows("Income") + page.section_rows("Expense")
        assert all(
            row["branch"] in {branch, ""} for row in rows
        ), "Branch filter returned rows from a different branch"

    def test_single_day_filter_applies_correctly(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        today = date.today().isoformat()
        report = page.apply_filters(today, today)

        assert page.last_status == 200, "Single-day filter should return HTTP 200"
        assert "income" in report and "expense" in report, (
            "Single-day filter response missing income/expense keys"
        )


# ── Accounting integrity tests ─────────────────────────────────────────────────

class TestResProfitLossAccounting:
    """Verify P&L arithmetic and UI summaries match API data."""

    def test_known_expense_increases_total_expense(self, res_profit_loss_known_state):
        before = Decimal(str(res_profit_loss_known_state["before"]["expense"]["total"]))
        after = Decimal(str(res_profit_loss_known_state["after"]["expense"]["total"]))

        assert after - before == Decimal("250.00"), (
            f"Expected expense to increase by 250.00, got delta {after - before}"
        )

    def test_known_expense_does_not_change_income(self, res_profit_loss_known_state):
        before = Decimal(str(res_profit_loss_known_state["before"]["income"]["total"]))
        after = Decimal(str(res_profit_loss_known_state["after"]["income"]["total"]))

        assert after == before, (
            f"Income changed after adding expense: before={before}, after={after}"
        )

    def test_net_profit_equals_income_minus_expense(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        today = date.today().isoformat()
        report = page.apply_filters(today, today)

        income = Decimal(str(report["income"]["total"]))
        expense = Decimal(str(report["expense"]["total"]))
        net = Decimal(str(report["net_profit"]))

        assert net == income - expense, (
            f"net_profit {net} != income {income} - expense {expense}"
        )

    def test_rendered_rows_sum_to_section_totals(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        today = date.today().isoformat()
        report = page.apply_filters(today, today)

        income_sum = sum(
            (row["amount"] for row in page.section_rows("Income")), Decimal("0")
        )
        expense_sum = sum(
            (row["amount"] for row in page.section_rows("Expense")), Decimal("0")
        )

        assert income_sum == Decimal(str(report["income"]["total"])), (
            f"Income rows sum {income_sum} != API total {report['income']['total']}"
        )
        assert expense_sum == Decimal(str(report["expense"]["total"])), (
            f"Expense rows sum {expense_sum} != API total {report['expense']['total']}"
        )

    def test_summary_cards_match_api_totals(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        today = date.today().isoformat()
        report = page.apply_filters(today, today)

        assert page.summary_amount("Total Income") == Decimal(str(report["income"]["total"])), (
            "Total Income card does not match API"
        )
        assert page.summary_amount("Total Expense") == Decimal(str(report["expense"]["total"])), (
            "Total Expense card does not match API"
        )
        assert page.summary_amount(page.net_label()) == Decimal(str(report["net_profit"])), (
            "Net Profit/Loss card does not match API"
        )

    def test_profit_or_loss_label_matches_sign(self, res_logged_in_page):
        page = ProfitLossPage(res_logged_in_page)
        page.navigate()
        today = date.today().isoformat()
        report = page.apply_filters(today, today)

        expected_label = "Net Profit" if report["is_profit"] else "Net Loss"
        assert page.net_label() == expected_label, (
            f"UI label '{page.net_label()}' does not match is_profit={report['is_profit']}"
        )
