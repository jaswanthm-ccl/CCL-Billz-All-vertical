"""Galaxy products: phones tracked per unit by the Galaxy tracked attribute (Serial Number)."""
import pytest

from pages.main_menu.products_page import ProductsPage
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE
from utils.random_data import generate_random_name


@pytest.fixture
def products_page(galaxy_logged_in_page, tenant):
    page_obj = ProductsPage(galaxy_logged_in_page, tenant)
    page_obj.navigate()
    return page_obj


def test_create_serial_tracked_product(products_page, galaxy_category, cleanup):
    name = generate_random_name("galaxy_phone")
    products_page.navigate()
    response = products_page.add_product(
        name,
        brand_name=None,
        category_name=galaxy_category,
        hsn_code=None,
        unit_type=None,
        cost_price="12000",
        selling_price="15000",
        unit_attribute=GALAXY_TRACKED_ATTRIBUTE,
    )
    cleanup(f"product {name}", lambda: products_page.ensure_deleted(name))

    assert response is not None and response.status in (200, 201), "Product create API did not succeed"
    submitted = response.request.post_data_json or {}
    assert submitted.get("product_unit_attribute_id"), f"Unit attribute was not sent with the product: {submitted}"

    products_page.navigate()
    assert products_page.search_product(name)
    assert products_page.view_product(name, expected_category=galaxy_category)

    assert products_page.delete_product(name)


def test_create_phone_with_ram_variants(products_page, galaxy_category, cleanup):
    name = generate_random_name("galaxy_variant_phone")
    variants = [
        {"attributes": {"RAM": "8"}, "name": f"{name} 8GB", "cost_price": "12000", "selling_price": "15000"},
        {"attributes": {"RAM": "12"}, "name": f"{name} 12GB", "cost_price": "15000", "selling_price": "18000"},
    ]
    products_page.navigate()
    response = products_page.add_product(
        name,
        brand_name=None,
        category_name=galaxy_category,
        hsn_code=None,
        unit_type=None,
        cost_price="12000",
        selling_price="15000",
        unit_attribute=GALAXY_TRACKED_ATTRIBUTE,
        attribute_keys=["RAM"],
        variants=variants,
    )
    cleanup(f"product {name}", lambda: products_page.ensure_deleted(name))

    assert response is not None and response.status in (200, 201), "Variant product create API did not succeed"
    submitted = response.request.post_data_json or {}
    sent_names = sorted(v.get("name") for v in submitted.get("variants", []))
    assert sent_names == sorted(v["name"] for v in variants), f"Variants sent: {submitted.get('variants')}"

    products_page.navigate()
    assert products_page.search_product(name)
    assert products_page.delete_product(name)


def test_product_required_fields(products_page):
    assert products_page.validate_required_fields()
