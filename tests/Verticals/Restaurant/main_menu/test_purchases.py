"""Restaurant Purchase creation and inventory-impact coverage."""

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.main_menu.inventories_page import InventoriesPage
from pages.Verticals.Restaurant.main_menu.outdoor_billing_page import OutdoorBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.random_data import generate_random_name


@pytest.fixture
def restaurant_purchase_products(
    res_logged_in_page, res_category, res_department, res_unit_type
):
    products = ProductsPage(res_logged_in_page)
    raw_material = generate_random_name("auto_purchase_raw")
    funding_dish = generate_random_name("auto_purchase_dish")
    products.navigate()
    products.add_product(
        name=raw_material,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        product_type="Raw material",
    )
    products.navigate()
    products.add_product(
        name=funding_dish,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="300",
        product_type="Finished good",
    )

    yield {"raw_material": raw_material, "funding_dish": funding_dish}

    for product_name in (raw_material, funding_dish):
        try:
            products.navigate()
            products.delete_product(product_name)
        except Exception as error:
            print(f"Teardown warning (purchase product {product_name}): {error}")


@pytest.mark.restaurant
def test_restaurant_purchase_create_view_and_inventory_lifecycle(
    res_logged_in_page,
    res_branch,
    res_supplier,
    restaurant_purchase_products,
):
    """Create a partially paid Purchase and verify payment and inventory impact."""
    purchases = PurchasesPage(res_logged_in_page)
    inventories = InventoriesPage(res_logged_in_page)
    outdoor = OutdoorBillingPage(res_logged_in_page)
    reference = generate_random_name("RES_PUR")
    raw_material = restaurant_purchase_products["raw_material"]
    funding_dish = restaurant_purchase_products["funding_dish"]

    outdoor.navigate()
    funding_booking = outdoor.create_booking(
        branch_name=res_branch,
        dish_name=funding_dish,
        quantity="1",
        unit_price="300",
        advance_amount="300",
        advance_notes=f"Fund Purchase test {reference}",
        notes=f"Automation funding booking for {reference}",
    )
    assert funding_booking.get("id"), "Cash-funding Outdoor Booking was not created"

    inventories.navigate()
    inventories.search_inventory(raw_material)
    stock_before = inventories.get_available_stock_number(
        raw_material, res_branch
    )

    result = purchases.add_purchase(
        supplier=res_supplier,
        branch=res_branch,
        reference_no=reference,
        paid_amount="40",
        purchase_type="Cash",
        products_data=[
            {
                "product": raw_material,
                "quantity": 3,
                "price": "300",
            }
        ],
    )

    assert result.reference_no == reference
    assert result.total_amount == Decimal("900")
    assert result.paid_amount == Decimal("40")
    created = purchases.last_created_purchase
    if created:
        created_purchase = created.get("purchase") or created
        assert created_purchase.get("reference_no") == reference, created
    assert purchases.view_purchase(
        reference,
        expected_supplier=res_supplier,
        expected_branch=res_branch,
        expected_product=raw_material,
        expected_quantity="3",
        expected_total="900.00",
        expected_paid_amount="40.00",
        expected_payment_status="Partial",
    )

    inventories.navigate()
    assert inventories.search_inventory(raw_material), (
        f"Purchased product {raw_material} is missing from Inventory"
    )
    stock_after = inventories.get_available_stock_number(
        raw_material, res_branch
    )
    assert stock_after == stock_before + Decimal("3"), (
        f"Purchase stock impact mismatch: expected {stock_before + Decimal('3')}, "
        f"got {stock_after}"
    )
