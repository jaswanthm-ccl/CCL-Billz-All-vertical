"""Restaurant Brand lifecycle and validation tests."""

import pytest

from pages.Verticals.Restaurant.master_menu.brands_page import BrandsPage
from utils.random_data import generate_random_description, generate_random_name


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_brand_cleanup(res_logged_in_page):
    created_brands: list[str] = []
    yield created_brands

    brands_page = BrandsPage(res_logged_in_page)
    for name in reversed(created_brands):
        try:
            brands_page.navigate()
            if brands_page.is_brand_active(name):
                brands_page.delete_brand(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant brand {name}: {exc}")


def test_restaurant_brand_crud_lifecycle(
    res_logged_in_page, restaurant_brand_cleanup
):
    brands_page = BrandsPage(res_logged_in_page)
    brands_page.navigate()

    brand_name = generate_random_name("res_auto_brand")
    description = generate_random_description("restaurant_brand")
    brands_page.add_brand(brand_name, description)
    restaurant_brand_cleanup.append(brand_name)

    assert brands_page.search_brand(brand_name)
    assert brands_page.view_brand(brand_name, expected_description=description)

    updated_name = generate_random_name("res_updated_brand")
    updated_description = generate_random_description("restaurant_updated_brand")
    assert brands_page.edit_brand(
        brand_name,
        updated_name,
        new_description=updated_description,
    )
    restaurant_brand_cleanup.remove(brand_name)
    restaurant_brand_cleanup.append(updated_name)

    assert brands_page.search_brand(updated_name)
    assert brands_page.view_brand(
        updated_name, expected_description=updated_description
    )

    assert brands_page.delete_brand(updated_name)
    assert brands_page.retrieve_brand(updated_name)
    assert brands_page.search_brand(updated_name)


def test_restaurant_brand_required_fields(res_logged_in_page):
    brands_page = BrandsPage(res_logged_in_page)
    brands_page.navigate()

    assert brands_page.validate_required_fields(), (
        "Brand Name must be required without submitting the create request"
    )


def test_restaurant_brand_rejects_blank_name(res_logged_in_page):
    brands_page = BrandsPage(res_logged_in_page)
    brands_page.navigate()

    assert brands_page.validate_blank_only_name(), (
        "A whitespace-only Restaurant brand name must be rejected"
    )


def test_restaurant_brand_rejects_duplicate_name(
    res_logged_in_page, restaurant_brand_cleanup
):
    brands_page = BrandsPage(res_logged_in_page)
    brands_page.navigate()

    brand_name = generate_random_name("res_dup_brand")
    description = generate_random_description("restaurant_brand")
    brands_page.add_brand(brand_name, description)
    restaurant_brand_cleanup.append(brand_name)

    assert brands_page.validate_duplicate_brand(brand_name, description), (
        "A duplicate Restaurant brand name must show validation and be rejected"
    )
