"""Restaurant Item-Wise Sales Report Test Suite.

Route: /reports/item-wise-sales
Covers:
  1. Structure  — Page loads, heading & search button visible, table headers present
  2. Filters    — Date filter, branch filtering, in-table dish searching
  3. Accounting — Live POS billed dish reflects accurately in item-wise sales report
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import pytest

from pages.Verticals.Restaurant.accounting.item_wise_sales_report_page import ItemWiseSalesReportPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Known-state Fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def res_item_wise_known_sale(
    browser, res_auth_state, res_branch, res_category, res_department, res_unit_type
):
    """
    Creates a dedicated dish, bills 1 unit via POS Billing,
    and provides the dish name & price to verify in the Item-Wise Sales Report.
    """
    context = browser.new_context(
        storage_state=res_auth_state,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()

    prod_page = ProductsPage(page)
    pos_page = POSBillingPage(page)

    dish_name = generate_random_name("item_dish")
    dish_price = "150"

    # 1. Create Dish
    prod_page.navigate()
    dish_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price=dish_price,
        product_type="Finished good",
    )

    # 2. Complete POS Sale
    pos_page.navigate()
    pos_page.select_bill_tab("Bill 1")
    pos_page.select_order_type("Dine In")
    pos_page.select_waiter("Waiter")
    pos_page.enter_dish_by_code(code=dish_code, dish_name=dish_name)

    sale_data = pos_page.settle_and_bill()
    invoice_ref = str(sale_data.get("invoice_no") or sale_data.get("id", ""))
    pos_page.collect_cash_payment(bill_reference=invoice_ref)

    context.close()

    yield {
        "dish_name": dish_name,
        "dish_code": dish_code,
        "price": Decimal(dish_price),
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
        print(f"Teardown warning (item_dish {dish_name}): {e}")


# ── Structure Tests ────────────────────────────────────────────────────────────

class TestResItemWiseSalesStructure:
    """Verify page loading and UI element presence."""

    def test_item_wise_sales_report_page_loads(self, res_logged_in_page):
        page = res_logged_in_page
        report_page = ItemWiseSalesReportPage(page)
        report_page.navigate()

        assert (
            page.get_by_text("Item Wise Sales", exact=False).first.is_visible()
            or report_page.search_button.is_visible()
        ), "Item Wise Sales Report page not visible"

    def test_search_button_is_present(self, res_logged_in_page):
        report_page = ItemWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()
        assert report_page.search_button.is_visible(), "Search button should be visible"

    def test_default_date_ends_today(self, res_logged_in_page):
        report_page = ItemWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()
        if report_page.to_date_input.is_visible():
            assert report_page.to_date_input.input_value() == date.today().isoformat(), (
                "Default to_date should be today"
            )


# ── Filter Tests ───────────────────────────────────────────────────────────────

class TestResItemWiseSalesFilters:
    """Verify date, branch, and search filter operations."""

    def test_filter_by_today(self, res_logged_in_page):
        report_page = ItemWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()
        today = date.today().isoformat()
        report_page.apply_filters(from_date=today, to_date=today)
        assert res_logged_in_page.locator("table").count() > 0, "Report table should be present"

    def test_filter_with_branch(self, res_logged_in_page, res_branch):
        report_page = ItemWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()
        today = date.today().isoformat()
        report_page.apply_filters(from_date=today, to_date=today, branch_name=res_branch)
        assert res_logged_in_page.locator("table").count() > 0, "Table should be rendered with branch filter"

    def test_search_item_by_name(self, res_logged_in_page, res_item_wise_known_sale):
        """Verify the in-table search filter narrows down to the specific dish."""
        dish_name = res_item_wise_known_sale["dish_name"]
        report_page = ItemWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()
        report_page.search_in_table(dish_name)
        assert report_page.find_item_in_report(dish_name), f"Search did not find dish '{dish_name}'"


# ── Accounting & Sales Integrity Tests ─────────────────────────────────────────

class TestResItemWiseSalesAccounting:
    """Verify live billed items reflect in the report."""

    def test_billed_dish_appears_in_item_wise_sales(
        self, res_logged_in_page, res_item_wise_known_sale
    ):
        dish_name = res_item_wise_known_sale["dish_name"]
        branch_name = res_item_wise_known_sale["branch"]

        report_page = ItemWiseSalesReportPage(res_logged_in_page)
        report_page.navigate()

        today = date.today().isoformat()
        report_page.apply_filters(from_date=today, to_date=today, branch_name=branch_name)

        # Search or find the item directly
        report_page.search_in_table(dish_name)
        found = report_page.find_item_in_report(dish_name)

        assert found, f"Billed dish '{dish_name}' was not found in Item-Wise Sales Report"
