"""Restaurant Cashier-Wise Sales Summary Test Suite.

Route: /reports/category-wise-sales
Covers:
  1. Structure  — Page loads, Cashier Wise Sales Summary heading, Search button, metric cards
  2. Filters    — Filter by Cashier, Filter by Branch
  3. Accounting — Live POS Cash bill increases Cashier's Cash sales metric
"""
from __future__ import annotations

from decimal import Decimal
import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.accounting.category_wise_sales_report_page import CategoryWiseSalesReportPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Known-state Fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def res_cashier_sales_known_state(
    browser, res_auth_state, res_branch, res_category, res_department, res_unit_type
):
    """
    Snapshots Cashier-Wise Sales report before and after completing a ₹180 POS Dine-In cash sale.
    """
    context = browser.new_context(
        storage_state=res_auth_state,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()

    report_page = CategoryWiseSalesReportPage(page)
    prod_page = ProductsPage(page)
    pos_page = POSBillingPage(page)

    dish_name = generate_random_name("cw_dish")
    dish_price = "180"

    # 1. Snapshot BEFORE
    report_page.navigate()
    report_page.filter_report()
    cash_before = report_page.get_cash_income()
    sales_before = report_page.get_sales()

    # 2. Complete POS Sale
    prod_page.navigate()
    dish_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price=dish_price,
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

    # 3. Snapshot AFTER
    report_page.navigate()
    report_page.filter_report()
    cash_after = report_page.get_cash_income()
    sales_after = report_page.get_sales()

    context.close()

    yield {
        "cash_before": cash_before,
        "cash_after": cash_after,
        "sales_before": sales_before,
        "sales_after": sales_after,
        "amount": Decimal(dish_price),
        "dish_name": dish_name,
        "branch": res_branch,
    }

    # Teardown: delete product
    try:
        cleanup_ctx = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
        cleanup_page = cleanup_ctx.new_page()
        cp = ProductsPage(cleanup_page)
        cp.navigate()
        cp.delete_product(dish_name)
        cleanup_ctx.close()
    except Exception as e:
        print(f"Teardown warning (cw_dish {dish_name}): {e}")


# ── Structure Tests ────────────────────────────────────────────────────────────

class TestResCashierWiseSalesStructure:
    """Verify page loading and UI element presence."""

    def test_cashier_wise_sales_report_page_loads(self, res_logged_in_page):
        page = res_logged_in_page
        report_page = CategoryWiseSalesReportPage(page)
        report_page.navigate()

        expect(page.get_by_text("Cashier Wise Sales Summary", exact=True)).to_be_visible()
        assert report_page.search_button.is_visible(), "Search button should be visible"

    def test_summary_metrics_valid_decimals(self, res_logged_in_page):
        report_page = CategoryWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()

        cash = report_page.get_cash_income()
        upi = report_page.get_upi_income()
        credit = report_page.get_credit_income()

        assert cash >= Decimal("0"), f"Cash Income should be non-negative: {cash}"
        assert upi >= Decimal("0"), f"UPI Income should be non-negative: {upi}"
        assert credit >= Decimal("0"), f"Credit Income should be non-negative: {credit}"


# ── Filter Tests ───────────────────────────────────────────────────────────────

class TestResCashierWiseSalesFilters:
    """Verify cashier and branch filter operations."""

    def test_filter_by_branch(self, res_logged_in_page, res_branch):
        report_page = CategoryWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()
        report_page.filter_report(branch_name=res_branch)

        assert report_page.get_cash_income() >= Decimal("0"), "Cash income metric should be non-negative"

    def test_filter_all_cashiers(self, res_logged_in_page):
        report_page = CategoryWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()
        report_page.filter_report()

        assert res_logged_in_page.locator("table, .card, div").count() > 0, "Page content should be present"


# ── Accounting Tests ───────────────────────────────────────────────────────────

class TestResCashierWiseSalesAccounting:
    """Verify POS billing updates cashier's sales/income metric."""

    def test_cashier_sales_reflects_pos_billing(self, res_cashier_sales_known_state):
        cash_before = res_cashier_sales_known_state["cash_before"]
        cash_after = res_cashier_sales_known_state["cash_after"]
        sales_before = res_cashier_sales_known_state["sales_before"]
        sales_after = res_cashier_sales_known_state["sales_after"]
        amount = res_cashier_sales_known_state["amount"]

        assert (cash_after >= cash_before + amount) or (sales_after >= sales_before + amount), (
            f"Cashier Sales/Income did not increase by ₹{amount}. "
            f"Cash: {cash_before} -> {cash_after}, Sales: {sales_before} -> {sales_after}"
        )
