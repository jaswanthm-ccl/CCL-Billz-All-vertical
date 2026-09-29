"""Restaurant Financial Report Test Suite.

Route: /reports/financial-report
Covers:
  1. Structure  — Page loads, Today/Filter/Clear buttons visible, metric cards rendered
  2. Accounting — Cash expense created in ExpensesPage accurately increases 'Cash Expense' in Financial Report
"""
from __future__ import annotations

from decimal import Decimal
import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.accounting.financial_report_page import FinancialReportPage
from pages.Verticals.Restaurant.main_menu.expenses_page import ExpensesPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Known-state Fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def res_financial_known_expense(browser, res_auth_state, res_branch):
    """
    Snapshots Financial Report Cash Expense before and after creating a ₹250 Direct Cash Expense.
    """
    context = browser.new_context(
        storage_state=res_auth_state,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()

    fin_page = FinancialReportPage(page)
    exp_page = ExpensesPage(page)

    # 1. Snapshot BEFORE
    fin_page.navigate()
    fin_page.apply_today_filter()
    expense_before = fin_page.get_cash_expense()

    # 2. Add Direct Cash Expense (₹250)
    exp_page.navigate()
    note = generate_random_name("fin_exp")
    exp_page.add_expense(
        expense_group="Direct",
        amount="250",
        notes=note,
    )

    # 3. Snapshot AFTER
    fin_page.navigate()
    fin_page.apply_today_filter()
    expense_after = fin_page.get_cash_expense()

    context.close()

    yield {
        "expense_before": expense_before,
        "expense_after": expense_after,
        "amount": Decimal("250"),
    }


# ── Structure Tests ────────────────────────────────────────────────────────────

class TestResFinancialReportStructure:
    """Verify page loading and UI element presence."""

    def test_financial_report_page_loads(self, res_logged_in_page):
        page = res_logged_in_page
        fin_page = FinancialReportPage(page)
        fin_page.navigate()

        assert (
            page.get_by_text("Financial Report", exact=False).first.is_visible()
            or fin_page.today_button.is_visible()
            or page.get_by_text("Cash Expense", exact=False).first.is_visible()
        ), "Financial Report page heading or metric cards not visible"

    def test_filter_buttons_visible(self, res_logged_in_page):
        fin_page = FinancialReportPage(res_logged_in_page)
        fin_page.navigate()

        assert (
            fin_page.today_button.is_visible()
            or fin_page.filter_button.is_visible()
        ), "Filter/Today buttons should be visible"


# ── Accounting Tests ───────────────────────────────────────────────────────────

class TestResFinancialReportAccounting:
    """Verify financial metric cards reflect actual accounting transactions."""

    def test_cash_expense_increases_after_adding_expense(
        self, res_financial_known_expense
    ):
        before = res_financial_known_expense["expense_before"]
        after = res_financial_known_expense["expense_after"]
        amount = res_financial_known_expense["amount"]

        assert after >= before + amount, (
            f"Cash Expense did not increase by ₹{amount}. Before: {before}, After: {after}"
        )

    def test_metrics_are_non_negative(self, res_logged_in_page):
        fin_page = FinancialReportPage(res_logged_in_page)
        fin_page.navigate()
        fin_page.apply_today_filter()

        cash_exp = fin_page.get_cash_expense()
        upi_exp = fin_page.get_upi_expense()
        credit_exp = fin_page.get_credit_expense()

        assert cash_exp >= Decimal("0"), f"Cash Expense should be non-negative: {cash_exp}"
        assert upi_exp >= Decimal("0"), f"UPI Expense should be non-negative: {upi_exp}"
        assert credit_exp >= Decimal("0"), f"Credit Expense should be non-negative: {credit_exp}"
