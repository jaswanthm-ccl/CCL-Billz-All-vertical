"""Restaurant Purchase Request lifecycle coverage."""

import pytest

from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchase_request_page import PurchaseRequestPage
from pages.Verticals.Restaurant.main_menu.suppliers_page import SuppliersPage
from utils.random_data import generate_random_name, generate_random_phone


@pytest.fixture
def purchase_request_cleanup(res_logged_in_page):
    created = {"supplier": None, "products": []}
    yield created

    request_page = PurchaseRequestPage(res_logged_in_page)
    if created["supplier"]:
        try:
            request_page.ensure_deleted(created["supplier"])
        except Exception:
            pass

    product_page = ProductsPage(res_logged_in_page)
    product_page.navigate()
    for product_name in created["products"]:
        try:
            product_page.delete_product(product_name)
        except Exception:
            pass

    if created["supplier"]:
        supplier_page = SuppliersPage(res_logged_in_page)
        supplier_page.navigate()
        try:
            supplier_page.delete_supplier(created["supplier"])
        except Exception:
            pass


@pytest.mark.restaurant
def test_restaurant_purchase_request_lifecycle(
    res_logged_in_page,
    purchase_request_cleanup,
    res_branch,
    res_category,
    res_department,
    res_unit_type,
):
    """Create, view, edit, delete, restore, and finally delete a request."""
    supplier_page = SuppliersPage(res_logged_in_page)
    product_page = ProductsPage(res_logged_in_page)
    request_page = PurchaseRequestPage(res_logged_in_page)

    supplier_name = generate_random_name("auto_pr_supplier")
    first_product = generate_random_name("auto_pr_raw")
    second_product = generate_random_name("auto_pr_edit_raw")
    purchase_request_cleanup["supplier"] = supplier_name
    purchase_request_cleanup["products"].extend([first_product, second_product])

    supplier_page.navigate()
    assert supplier_page.add_supplier(
        name=supplier_name,
        phone=generate_random_phone(),
        address="Restaurant Purchase Request Automation",
    )

    product_page.navigate()
    for product_name in (first_product, second_product):
        product_page.add_product(
            name=product_name,
            category_name=res_category,
            department_name=res_department,
            unit_type=res_unit_type,
            product_type="Raw material",
        )

    request_page.add_purchase_request(
        branch=res_branch,
        supplier=supplier_name,
        priority="High",
        products_data=[{"product": first_product, "quantity": 5}],
        notes="Restaurant Purchase Request lifecycle",
    )
    assert request_page.search_purchase_request(supplier_name)
    assert request_page.view_purchase_request(
        supplier_name, first_product_name=first_product, priority="Medium"
    )

    assert request_page.edit_purchase_request(
        supplier_name,
        new_product_name=second_product,
        new_quantity=3,
    )
    request_page.navigate()
    res_logged_in_page.wait_for_load_state("networkidle")
    assert request_page.purchase_request_contains_products(
        supplier_name, [first_product, second_product]
    )

    assert request_page.delete_purchase_request(supplier_name)
    assert request_page.retrieve_purchase_request(supplier_name)
    assert request_page.search_purchase_request(supplier_name)
    assert request_page.delete_purchase_request(supplier_name)
