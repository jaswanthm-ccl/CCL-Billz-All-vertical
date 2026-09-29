"""Restaurant Outdoor Billing to Customer Outstanding integration."""

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.accounting.customer_outstanding_page import (
    CustomerOutstandingPage,
)
from pages.Verticals.Restaurant.main_menu.customers_page import CustomersPage
from pages.Verticals.Restaurant.main_menu.outdoor_billing_page import OutdoorBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name


pytestmark = pytest.mark.restaurant


def test_outdoor_booking_balance_appears_and_clears_in_customer_outstanding(
    res_logged_in_page,
    res_branch,
    res_category,
    res_department,
    res_unit_type,
):
    """A partial Outdoor Booking must create and then clear customer debt."""
    page = res_logged_in_page
    customer_name = generate_random_name("outstanding_customer")
    dish_name = generate_random_name("outstanding_dish")
    booking_total = Decimal("1000.00")
    advance = Decimal("200.00")
    expected_outstanding = booking_total - advance

    customers = CustomersPage(page)
    customers.navigate()
    assert customers.add_customer(name=customer_name)

    products = ProductsPage(page)
    products.navigate()
    dish_code = products.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="250",
        product_type="Finished good",
    )

    outdoor = OutdoorBillingPage(page)
    outdoor.navigate()
    booking = outdoor.create_booking(
        branch_name=res_branch,
        customer_name=customer_name,
        dish_name=dish_name,
        dish_code=dish_code,
        quantity="4",
        unit_price="250",
        advance_amount=str(advance),
        advance_payment_mode="cash",
        advance_notes="Customer Outstanding integration advance",
        notes="Customer Outstanding integration booking",
    )
    booking_id = str(booking.get("id") or "")
    booking_ref = str(booking.get("booking_ref") or booking_id)
    assert booking_id and booking_ref, f"Booking response lacked identity: {booking}"

    report = CustomerOutstandingPage(page)
    report.navigate()
    open_data = report.search(customer_name)
    open_party = report.find_party(open_data, customer_name)
    assert open_party is not None, (
        f"Customer {customer_name} was absent from Customer Outstanding"
    )
    assert report.amount(open_party["outstanding_amount"]) == expected_outstanding
    assert open_party["balance_type"] == "Receivable"

    outdoor.navigate()
    outdoor.view_booking(booking_ref)
    outdoor.record_settlement_payment(
        amount=str(expected_outstanding),
        notes="Clear Customer Outstanding integration balance",
    )
    outdoor.close_modal()

    report.navigate()
    cleared_data = report.search(customer_name)
    cleared_party = report.find_party(cleared_data, customer_name)
    if cleared_party is not None:
        assert report.amount(cleared_party["outstanding_amount"]) == Decimal("0.00")
        assert cleared_party["balance_type"] == "Nil"
    else:
        assert cleared_data.get("items", []) == [], (
            f"Unexpected outstanding rows returned for unique customer {customer_name}"
        )
