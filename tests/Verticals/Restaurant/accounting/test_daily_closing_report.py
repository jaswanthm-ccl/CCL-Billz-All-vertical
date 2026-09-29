"""End-to-end coverage for the Restaurant Daily Closing Report.

Route: /reports/daily-closing

API response shape (footer):
  total_sales, total_expenses, profit_loss, indent_usage_amount (Material Usage)

What is tested:
  Structure  — page loads, heading visible, search button present
  Filters    — branch filter triggers API, all-branch mode works, metrics non-negative
  Accounting — a completed POS sale raises total_sales;
               a direct expense raises total_expenses
"""

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.accounting.daily_closing_report_page import DailyClosingReportPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.expenses_page import ExpensesPage

pytestmark = pytest.mark.restaurant


# ── Known-state fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def res_daily_closing_known_state(
    browser, res_auth_state, res_branch, res_category, res_department, res_unit_type
):
    """
    Creates a completed POS sale (₹180 dish) and a direct expense (₹250),
    snapshots the Daily Closing footer before and after so accounting
    tests can assert exact deltas.

    Scoped to 'module' — runs once, shared by all tests in this file.
    """
    from utils.random_data import generate_random_name

    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()

    report_page = DailyClosingReportPage(page)
    prod_page = ProductsPage(page)
    pos_page = POSBillingPage(page)
    expenses_page = ExpensesPage(page)

    # ── Snapshot BEFORE ──────────────────────────────────────────────────────
    report_page.navigate()
    before_footer = report_page.filter_by_branch()   # All Branches — captures everything
    sales_before = Decimal(str(before_footer.get("total_sales", 0) or 0))
    expenses_before = Decimal(str(before_footer.get("total_expenses", 0) or 0))

    # ── Create a dish and complete a POS sale ────────────────────────────────
    dish_name = generate_random_name("dc_dish")
    prod_page.navigate()
    dish_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="180",
        product_type="Finished good",
    )

    pos_page.navigate()
    pos_page.select_bill_tab("Bill 1")
    pos_page.select_order_type("Dine In")
    pos_page.select_waiter("Waiter")
    pos_page.enter_dish_by_code(code=dish_code, dish_name=dish_name)

    sale_data = pos_page.settle_and_bill()
    invoice_ref = str(sale_data.get("invoice_no") or sale_data.get("id", ""))
    pos_page.collect_cash_payment(bill_reference=invoice_ref)

    # ── Add a direct expense ─────────────────────────────────────────────────
    expenses_page.navigate()
    expenses_page.add_expense(
        expense_group="Direct",
        amount="250",
        notes="DC known-state expense",
    )

    # ── Snapshot AFTER ───────────────────────────────────────────────────────
    report_page.navigate()
    after_footer = report_page.filter_by_branch()    # All Branches — same scope as before
    sales_after = Decimal(str(after_footer.get("total_sales", 0) or 0))
    expenses_after = Decimal(str(after_footer.get("total_expenses", 0) or 0))

    context.close()

    # ── Cleanup dish ─────────────────────────────────────────────────────────
    try:
        cleanup_ctx = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
        cleanup_page = cleanup_ctx.new_page()
        cp = ProductsPage(cleanup_page)
        cp.navigate()
        cp.delete_product(dish_name)
        cleanup_ctx.close()
    except Exception as e:
        print(f"Teardown warning (dc_dish {dish_name}): {e}")

    yield {
        "sales_before": sales_before,
        "sales_after": sales_after,
        "expenses_before": expenses_before,
        "expenses_after": expenses_after,
        "branch": res_branch,
        "sale_amount": Decimal("180"),
        "expense_amount": Decimal("250"),
    }


# ── Structure tests ────────────────────────────────────────────────────────────

class TestResDailyClosingStructure:
    """Verify the page loads correctly."""

    def test_page_loads_and_heading_is_visible(self, res_logged_in_page):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        assert report_page.is_page_visible(), "Daily Closing Report heading / Search button not visible"

    def test_search_button_is_present(self, res_logged_in_page):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        assert report_page.search_button.is_visible(), "Search button not visible"

    def test_api_returns_footer_on_search(self, res_logged_in_page):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        footer = report_page.filter_by_branch()

        assert "total_sales" in footer, f"API footer missing total_sales: {footer}"
        assert "total_expenses" in footer, f"API footer missing total_expenses: {footer}"
        assert report_page.get_total_sales() >= Decimal("0"), "total_sales should be non-negative"


# ── Filter tests ───────────────────────────────────────────────────────────────

class TestResDailyClosingFilters:
    """Verify branch filter triggers correct API call and metrics are valid."""

    def test_filter_without_branch_returns_all_data(self, res_logged_in_page):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        report_page.filter_by_branch()

        assert report_page.get_total_sales() >= Decimal("0"), "Total Sales should be non-negative"
        assert report_page.get_total_expenses() >= Decimal("0"), "Total Expenses should be non-negative"
        assert report_page.get_material_usage() >= Decimal("0"), "Material Usage should be non-negative"

    def test_filter_with_specific_branch_triggers_api(
        self, res_logged_in_page, res_daily_closing_known_state
    ):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        footer = report_page.filter_by_branch(res_daily_closing_known_state["branch"])

        assert "total_sales" in footer, "Branch-filtered response missing total_sales"
        assert report_page.get_total_sales() >= Decimal("0"), "Branch-filtered Total Sales should be non-negative"

    def test_all_metric_cards_non_negative(self, res_logged_in_page):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        report_page.filter_by_branch()

        for label, value in [
            ("total_sales", report_page.get_total_sales()),
            ("total_expenses", report_page.get_total_expenses()),
            ("material_usage", report_page.get_material_usage()),
            ("profit_loss", report_page.get_profit_loss()),
        ]:
            assert value >= Decimal("0"), f"{label} returned a negative value: {value}"


# ── Accounting integrity tests ─────────────────────────────────────────────────

class TestResDailyClosingAccounting:
    """Verify a POS sale and an expense appear in the report."""

    def test_completed_sale_increases_total_sales(self, res_daily_closing_known_state):
        before = res_daily_closing_known_state["sales_before"]
        after = res_daily_closing_known_state["sales_after"]
        sale_amount = res_daily_closing_known_state["sale_amount"]

        assert after >= before + sale_amount, (
            f"total_sales did not increase by ₹{sale_amount}. Before: {before}, After: {after}"
        )

    def test_direct_expense_increases_total_expenses(self, res_daily_closing_known_state):
        before = res_daily_closing_known_state["expenses_before"]
        after = res_daily_closing_known_state["expenses_after"]
        expense_amount = res_daily_closing_known_state["expense_amount"]

        assert after >= before + expense_amount, (
            f"total_expenses did not increase by ₹{expense_amount}. Before: {before}, After: {after}"
        )

    def test_total_sales_non_negative_after_billing(
        self, res_logged_in_page, res_daily_closing_known_state
    ):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        report_page.filter_by_branch(res_daily_closing_known_state["branch"])

        assert report_page.get_total_sales() >= Decimal("0"), "Total Sales should never be negative"

    def test_material_usage_non_negative(
        self, res_logged_in_page, res_daily_closing_known_state
    ):
        report_page = DailyClosingReportPage(res_logged_in_page)
        report_page.navigate()
        report_page.filter_by_branch(res_daily_closing_known_state["branch"])

        assert report_page.get_material_usage() >= Decimal("0"), "Material Usage should never be negative"
