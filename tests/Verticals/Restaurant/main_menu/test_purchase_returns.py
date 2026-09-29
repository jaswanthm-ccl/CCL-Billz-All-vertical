"""Restaurant Purchase Return lifecycle and inventory-impact coverage."""

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.main_menu.inventories_page import InventoriesPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchase_returns_page import PurchaseReturnsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.random_data import generate_random_name


@pytest.fixture
def restaurant_return_product(
    res_logged_in_page, res_category, res_department, res_unit_type
):
    products = ProductsPage(res_logged_in_page)
    product_name = generate_random_name("auto_return_raw")
    products.navigate()
    products.add_product(
        name=product_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        product_type="Raw material",
    )

    yield product_name

    try:
        products.navigate()
        products.delete_product(product_name)
    except Exception as error:
        # Purchase history lifecycle-manages the product in some environments.
        print(f"Teardown warning (return product {product_name}): {error}")


@pytest.mark.restaurant
def test_restaurant_partial_purchase_return_and_inventory_lifecycle(
    res_logged_in_page,
    res_branch,
    res_supplier,
    restaurant_return_product,
):
    """Return part of a Purchase and verify the record and stock reduction."""
    page = res_logged_in_page
    purchases = PurchasesPage(page)
    returns = PurchaseReturnsPage(page)
    inventories = InventoriesPage(page)
    reference = generate_random_name("RES_RET")

    inventories.navigate()
    inventories.search_inventory(restaurant_return_product)
    stock_before = inventories.get_available_stock_number(
        restaurant_return_product, res_branch
    )

    result = purchases.add_purchase(
        supplier=res_supplier,
        branch=res_branch,
        reference_no=reference,
        paid_amount="0",
        purchase_type="Credit",
        products_data=[
            {
                "product": restaurant_return_product,
                "quantity": 3,
                "price": "100",
            }
        ],
    )
    assert result.total_amount == Decimal("300")

    inventories.navigate()
    assert inventories.search_inventory(restaurant_return_product)
    stock_after_purchase = inventories.get_available_stock_number(
        restaurant_return_product, res_branch
    )
    assert stock_after_purchase == stock_before + Decimal("3")

    purchases.navigate()
    purchases.initiate_return(reference)
    created_return = returns.perform_return(quantity="1")
    assert created_return, "Purchase Return API returned no data"

    returns.filter_returns(
        branch_name=res_branch,
        supplier_name=res_supplier,
    )
    assert returns.verify_return_details(
        product_name=restaurant_return_product,
        supplier_name=res_supplier,
        branch_name=res_branch,
        quantity="1",
        price="100",
        total_amount="100.00",
    )

    inventories.navigate()
    assert inventories.search_inventory(restaurant_return_product)
    stock_after_return = inventories.get_available_stock_number(
        restaurant_return_product, res_branch
    )
    assert stock_after_return == stock_after_purchase - Decimal("1"), (
        f"Purchase Return stock mismatch: expected "
        f"{stock_after_purchase - Decimal('1')}, got {stock_after_return}"
    )
