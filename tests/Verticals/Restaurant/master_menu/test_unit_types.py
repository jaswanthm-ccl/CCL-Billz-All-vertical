"""Restaurant Unit Type lifecycle and validation tests."""

import pytest

from pages.Verticals.Restaurant.master_menu.unit_types_page import UnitTypesPage
from utils.random_data import (
    generate_random_description,
    generate_random_name,
    generate_random_unit,
)


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_unit_type_cleanup(res_logged_in_page):
    created_units: list[str] = []
    yield created_units

    unit_page = UnitTypesPage(res_logged_in_page)
    for name in reversed(created_units):
        try:
            unit_page.navigate()
            if unit_page.is_unit_type_active(name):
                unit_page.delete_unit_type(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant unit type {name}: {exc}")


def test_restaurant_unit_type_crud_lifecycle(
    res_logged_in_page, restaurant_unit_type_cleanup
):
    unit_page = UnitTypesPage(res_logged_in_page)
    unit_page.navigate()

    name = generate_random_name("res_auto_unit")
    symbol = generate_random_unit()
    description = generate_random_description("restaurant_unit")
    sort_order = "4"
    assert unit_page.add_unit_type(name, symbol, description, sort_order=sort_order)
    restaurant_unit_type_cleanup.append(name)

    assert unit_page.search_unit_type(name)
    assert unit_page.view_unit_type(
        name,
        expected_symbol=symbol,
        expected_description=description,
        expected_sort_order=sort_order,
    )

    updated_name = generate_random_name("res_updated_unit")
    updated_symbol = generate_random_unit()
    updated_description = generate_random_description("restaurant_updated_unit")
    updated_sort_order = "8"
    assert unit_page.edit_unit_type(
        name,
        updated_name,
        updated_symbol,
        updated_description,
        updated_sort_order,
    )
    restaurant_unit_type_cleanup.remove(name)
    restaurant_unit_type_cleanup.append(updated_name)

    assert unit_page.search_unit_type(updated_name)
    assert unit_page.view_unit_type(
        updated_name,
        expected_symbol=updated_symbol,
        expected_description=updated_description,
        expected_sort_order=updated_sort_order,
    )

    assert unit_page.delete_unit_type(updated_name)
    assert unit_page.retrieve_unit_type(updated_name)
    assert unit_page.search_unit_type(updated_name)


def test_restaurant_unit_type_required_fields(res_logged_in_page):
    unit_page = UnitTypesPage(res_logged_in_page)
    unit_page.navigate()

    assert unit_page.validate_required_fields(), (
        "Name, symbol, and description must be required without an API request"
    )


@pytest.mark.parametrize(
    ("value", "expected_message"),
    [
        ("0", "Sort order must be at least 1"),
        ("1.5", "Sort order must be a number"),
    ],
)
def test_restaurant_unit_type_rejects_invalid_sort_order(
    res_logged_in_page, value, expected_message
):
    unit_page = UnitTypesPage(res_logged_in_page)
    unit_page.navigate()

    assert unit_page.validate_invalid_sort_order(value, expected_message)


def test_restaurant_unit_type_rejects_duplicate_name(
    res_logged_in_page, restaurant_unit_type_cleanup
):
    unit_page = UnitTypesPage(res_logged_in_page)
    unit_page.navigate()

    name = generate_random_name("res_duplicate_unit")
    symbol = generate_random_unit()
    description = generate_random_description("restaurant_duplicate_unit")
    assert unit_page.add_unit_type(name, symbol, description)
    restaurant_unit_type_cleanup.append(name)

    assert unit_page.validate_duplicate_unit(name, symbol, description), (
        "A duplicate Restaurant unit type name must be rejected"
    )
