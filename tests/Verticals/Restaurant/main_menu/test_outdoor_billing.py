"""Restaurant Outdoor Billing Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.outdoor_billing_page import OutdoorBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage


@pytest.fixture
def outdoor_cleanup(res_logged_in_page):
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
def test_restaurant_outdoor_billing_lifecycle(
    res_logged_in_page, outdoor_cleanup, res_branch, res_category, res_department, res_unit_type
):
    """Test outdoor catering booking lifecycle: Create with advance -> View -> Edit -> Settle Payment -> Close Bill."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    outdoor_page = OutdoorBillingPage(page)

    dish_name = generate_random_name("auto_outdoor_dish")
    outdoor_cleanup["prods"].append(dish_name)

    prod_page.navigate()
    dish_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="250",
        product_type="Finished good",
    )

    outdoor_page.navigate()
    booking_data = outdoor_page.create_booking(
        branch_name=res_branch,
        dish_name=dish_name,
        dish_code=dish_code,
        quantity="10",
        unit_price="250",
        advance_amount="1000",
        advance_payment_mode="cash",
        advance_notes="Booking token advance",
        notes="Outdoor catering corporate lunch",
    )
    booking_id = str(booking_data.get("id", ""))
    booking_ref = booking_data.get("booking_ref", "") or booking_id

    # View Details
    view_info = outdoor_page.view_booking(booking_ref=booking_ref)
    assert booking_ref in view_info["content"] or booking_id in view_info["content"], "Booking details missing in view dialog"

    # Edit Booking Quantity
    assert outdoor_page.edit_booking_from_view(new_quantity=12), "Failed to edit outdoor booking quantity"

    # Settle Remaining Payment
    outdoor_page.record_settlement_payment(notes="Full balance settlement")

    # Close Bill
    assert outdoor_page.close_bill(), "Failed to close outdoor catering bill"
    outdoor_page.close_modal()
