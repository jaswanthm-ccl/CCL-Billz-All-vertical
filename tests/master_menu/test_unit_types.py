import pytest

from pages.master_menu.unit_types_page import UnitTypesPage
from utils.random_data import (
    generate_random_description,
    generate_random_name,
    generate_random_unit,
)


@pytest.fixture
def unit_type_cleanup(logged_in_page):
    created_units = []
    yield created_units

    unit_page = UnitTypesPage(logged_in_page)
    for name in created_units:
        try:
            unit_page.navigate()
            if unit_page.is_unit_type_active(name):
                unit_page.delete_unit_type(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete unit type {name}: {exc}")


def test_unit_type_crud_lifecycle(logged_in_page, unit_type_cleanup):
    unit_types_page = UnitTypesPage(logged_in_page)
    unit_types_page.navigate()

    name = generate_random_name("auto_unit")
    symbol = generate_random_unit()
    description = generate_random_description("unit_description")
    sort_order = "4"
    assert unit_types_page.add_unit_type(
        name,
        symbol,
        description,
        sort_order=sort_order,
    )
    unit_type_cleanup.append(name)
    assert unit_types_page.search_unit_type(name)
    assert unit_types_page.view_unit_type(
        name,
        expected_symbol=symbol,
        expected_description=description,
        expected_sort_order=sort_order,
    )

    new_name = generate_random_name("updated_unit")
    new_symbol = generate_random_unit()
    new_description = generate_random_description(
        "updated_unit_description"
    )
    new_sort_order = "8"
    assert unit_types_page.edit_unit_type(
        name,
        new_name,
        new_symbol,
        new_description,
        new_sort_order,
    )
    unit_type_cleanup.remove(name)
    unit_type_cleanup.append(new_name)
    assert unit_types_page.search_unit_type(new_name)
    assert unit_types_page.view_unit_type(
        new_name,
        expected_symbol=new_symbol,
        expected_description=new_description,
        expected_sort_order=new_sort_order,
    )

    assert unit_types_page.delete_unit_type(new_name)
    assert unit_types_page.retrieve_unit_type(new_name)
    assert unit_types_page.search_unit_type(new_name)


def test_unit_type_required_fields(logged_in_page):
    unit_types_page = UnitTypesPage(logged_in_page)
    unit_types_page.navigate()
    assert unit_types_page.validate_required_fields(), (
        "Name, symbol, and description must be required without an API request"
    )


@pytest.mark.parametrize(
    ("value", "expected_message"),
    [
        ("0", "Sort order must be at least 1"),
        ("1.5", "Sort order must be a number"),
    ],
)
def test_reject_invalid_unit_type_sort_order(
    logged_in_page, value, expected_message
):
    unit_types_page = UnitTypesPage(logged_in_page)
    unit_types_page.navigate()
    assert unit_types_page.validate_invalid_sort_order(
        value, expected_message
    )


def test_reject_duplicate_unit_type(
    logged_in_page, unit_type_cleanup
):
    unit_types_page = UnitTypesPage(logged_in_page)
    unit_types_page.navigate()
    name = generate_random_name("duplicate_unit")
    symbol = generate_random_unit()
    description = generate_random_description(
        "duplicate_unit_description"
    )
    assert unit_types_page.add_unit_type(name, symbol, description)
    unit_type_cleanup.append(name)
    assert unit_types_page.validate_duplicate_unit(
        name, symbol, description
    ), "Expected UI validation and API 422 for a duplicate Unit Type name"
