"""Restaurant Expense Category lifecycle and validation tests."""

import pytest

from pages.Verticals.Restaurant.master_menu.expense_categories_page import (
    ExpenseCategoriesPage,
)
from utils.random_data import generate_random_description, generate_random_name


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_expense_category_cleanup(res_logged_in_page):
    created_categories: list[str] = []
    yield created_categories

    page_obj = ExpenseCategoriesPage(res_logged_in_page)
    for name in reversed(created_categories):
        try:
            page_obj.navigate()
            if page_obj.is_category_active(name):
                page_obj.delete_expense_category(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant expense category {name}: {exc}")


def test_restaurant_expense_category_crud_lifecycle(
    res_logged_in_page, restaurant_expense_category_cleanup
):
    page_obj = ExpenseCategoriesPage(res_logged_in_page)
    page_obj.navigate()

    name = generate_random_name("res_auto_expense")
    description = generate_random_description("restaurant_expense")
    response = page_obj.add_expense_category(
        name,
        description=description,
        sort_order=5,
    )
    assert response.status in {200, 201}
    restaurant_expense_category_cleanup.append(name)
    assert page_obj.search_expense_category(name)
    assert page_obj.row_has_expense_group(name, page_obj.selected_expense_group)

    updated_name = generate_random_name("res_updated_expense")
    updated_description = generate_random_description("restaurant_updated_expense")
    assert page_obj.edit_expense_category(
        name,
        updated_name,
        description=updated_description,
        sort_order=9,
    )
    restaurant_expense_category_cleanup.remove(name)
    restaurant_expense_category_cleanup.append(updated_name)

    assert page_obj.get_edit_values(updated_name) == {
        "name": updated_name,
        "description": updated_description,
        "sort_order": "9",
    }
    assert page_obj.delete_expense_category(updated_name)
    assert page_obj.retrieve_expense_category(updated_name)
    assert page_obj.search_expense_category(updated_name)


def test_restaurant_expense_category_required_fields(res_logged_in_page):
    page_obj = ExpenseCategoriesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_fields(), (
        "Category Name and Expense Group must be required without an API request"
    )


def test_restaurant_expense_category_excludes_bank_group(res_logged_in_page):
    page_obj = ExpenseCategoriesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_bank_group_excluded(), (
        "Bank must not be available in the Restaurant Expense Group dropdown"
    )


def test_restaurant_expense_category_rejects_duplicate_name(
    res_logged_in_page, restaurant_expense_category_cleanup
):
    page_obj = ExpenseCategoriesPage(res_logged_in_page)
    page_obj.navigate()

    name = generate_random_name("res_duplicate_expense")
    response = page_obj.add_expense_category(name)
    assert response.status in {200, 201}
    restaurant_expense_category_cleanup.append(name)
    assert page_obj.validate_duplicate_category(name), (
        "A duplicate Restaurant expense category name must be rejected"
    )
