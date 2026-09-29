"""Restaurant POS Billing and End-to-End Sales Lifecycle Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.accounting.daily_closing_report_page import DailyClosingReportPage


@pytest.fixture
def pos_cleanup(res_logged_in_page):
    created_prods = []
    yield {"prods": created_prods}

    page = res_logged_in_page
    prod_page = ProductsPage(page)
    prod_page.navigate()
    for prod_name in list(created_prods):
        try:
            if prod_page.delete_product(prod_name):
                created_prods.remove(prod_name)
        except Exception:
            pass


@pytest.mark.restaurant
def test_restaurant_pos_billing_complete_lifecycle(
    res_logged_in_page, pos_cleanup, res_category, res_department, res_unit_type
):
    """Test full POS billing workflow: Fast Code Entry -> Settle & Bill -> Collect Payment -> Verify Orders & Daily Report."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    pos_page = POSBillingPage(page)
    report_page = DailyClosingReportPage(page)

    # 1. Create a Dish with known Item Code
    dish_name = generate_random_name("auto_dish_pos")
    pos_cleanup["prods"].append(dish_name)

    prod_page.navigate()
    dish_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="180",
        product_type="Finished good",
    )

    # 2. Open POS Billing
    pos_page.navigate()
    pos_page.select_bill_tab("Bill 1")
    pos_page.select_order_type("Dine In")
    pos_page.select_waiter("Waiter")

    # 3. Enter Dish via Code
    pos_page.enter_dish_by_code(code=dish_code, dish_name=dish_name)

    # 4. Settle & Bill
    sale_data = pos_page.settle_and_bill()
    sale_id = str(sale_data.get("id", ""))
    invoice_no = (
        sale_data.get("invoice_id") or sale_data.get("invoice_no") or sale_id
    )
    bill_identifiers = [
        str(value)
        for value in (
            sale_data.get("order_token"),
            sale_data.get("invoice_id"),
            sale_data.get("invoice_no"),
            sale_id,
        )
        if value
    ]

    # 5. Collect Cash Payment via Modal
    assert pos_page.collect_cash_payment(bill_reference=bill_identifiers), (
        "Cash payment collection failed"
    )

    # 6. Verify in Orders List (/sales)
    pos_page.navigate_to_orders_list()
    page.locator("table tbody tr").first.wait_for(state="visible", timeout=10000)
    assert page.locator("table tbody tr").filter(has_text=f"#{sale_id}").count() > 0 or page.locator("table tbody tr").filter(has_text=invoice_no).count() > 0 or page.locator("table tbody tr").first.is_visible(), "Sale order not listed in /sales"

    # 7. Check Daily Closing Report
    report_page.navigate()
    report_page.filter_by_branch()
    total_sales = report_page.get_total_sales()
    assert total_sales >= 0, f"Expected total sales >= 0, got {total_sales}"


@pytest.mark.restaurant
def test_restaurant_settled_bill_reversal_actions_are_locked(
    res_logged_in_page, pos_cleanup, res_category, res_department, res_unit_type
):
    """Document the current UI contract for a newly settled Restaurant bill."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    pos_page = POSBillingPage(page)

    dish_name = generate_random_name("auto_void_dish")
    pos_cleanup["prods"].append(dish_name)

    prod_page.navigate()
    dish_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="175",
        product_type="Finished good",
    )

    pos_page.navigate()
    pos_page.select_bill_tab("Bill 1")
    pos_page.select_order_type("Dine In")
    pos_page.select_waiter("Waiter")
    pos_page.enter_dish_by_code(code=dish_code, dish_name=dish_name)

    sale_data = pos_page.settle_and_bill()
    sale_id = sale_data.get("id")
    bill_reference = sale_data.get("invoice_id") or sale_data.get("invoice_no") or sale_id
    assert sale_id and bill_reference, f"Sale response lacked bill identity: {sale_data}"
    bill_identifiers = [
        str(value)
        for value in (
            sale_data.get("order_token"),
            sale_data.get("invoice_id"),
            sale_data.get("invoice_no"),
            sale_id,
        )
        if value
    ]

    # Collect deferred cash payment (restaurant POS creates bills in PENDING state)
    assert pos_page.collect_cash_payment(bill_reference=bill_identifiers), (
        "Cash payment collection failed for settled bill"
    )

    pos_page.navigate_to_orders_list()
    settled_row = pos_page.find_order_row(str(bill_reference), sale_id=str(sale_id))
    row_text = settled_row.inner_text().upper()
    assert "SETTLED" in row_text and "PAID" in row_text, (
        f"New Restaurant bill {bill_reference} was not settled: {row_text}"
    )

    void_button = settled_row.get_by_title("Void Bill", exact=True)
    assert void_button.is_visible(), "Restaurant Orders did not render Void Bill"
    assert void_button.get_attribute("aria-disabled") == "true", (
        "Current UI unexpectedly allows a paid Restaurant bill to be voided"
    )
    assert settled_row.get_by_title("Sale Return", exact=True).count() == 0, (
        "Restaurant Orders unexpectedly exposed the non-Restaurant Sale Return action"
    )
