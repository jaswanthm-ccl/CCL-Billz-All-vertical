"""Restaurant Food Category lifecycle and validation tests."""

import pytest

from pages.Verticals.Restaurant.master_menu.food_categories_page import (
    FoodCategoriesPage,
)
from utils.random_data import generate_random_description, generate_random_name


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_category_cleanup(res_logged_in_page):
    created_categories: list[str] = []
    yield created_categories

    categories_page = FoodCategoriesPage(res_logged_in_page)
    for name in reversed(created_categories):
        try:
            categories_page.navigate()
            if categories_page.is_category_active(name):
                categories_page.delete_category(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant category {name}: {exc}")


def test_restaurant_food_category_crud_lifecycle(
    res_logged_in_page, restaurant_category_cleanup
):
    categories_page = FoodCategoriesPage(res_logged_in_page)
    categories_page.navigate()

    category_name = generate_random_name("res_auto_cat")
    description = generate_random_description("restaurant_category")
    sort_order = "5"
    categories_page.add_category(
        name=category_name,
        sort_order=sort_order,
        description=description,
    )
    restaurant_category_cleanup.append(category_name)

    assert categories_page.search_category(category_name)
    assert categories_page.view_category(
        category_name,
        expected_description=description,
        expected_sort_order=sort_order,
    )

    updated_name = generate_random_name("res_updated_cat")
    updated_description = generate_random_description("restaurant_updated_category")
    updated_sort_order = "9"
    assert categories_page.edit_category(
        category_name,
        updated_name,
        new_sort_order=updated_sort_order,
        new_description=updated_description,
    )
    restaurant_category_cleanup.remove(category_name)
    restaurant_category_cleanup.append(updated_name)

    assert categories_page.search_category(updated_name)
    assert categories_page.view_category(
        updated_name,
        expected_description=updated_description,
        expected_sort_order=updated_sort_order,
    )

    assert categories_page.delete_category(updated_name)
    assert categories_page.retrieve_category(updated_name)
    assert categories_page.search_category(updated_name)


def test_restaurant_food_category_required_fields(res_logged_in_page):
    categories_page = FoodCategoriesPage(res_logged_in_page)
    categories_page.navigate()

    assert categories_page.validate_required_fields(), (
        "Category Name must be required without submitting the create request"
    )


def test_restaurant_food_category_rejects_duplicate_name(
    res_logged_in_page, restaurant_category_cleanup
):
    categories_page = FoodCategoriesPage(res_logged_in_page)
    categories_page.navigate()

    category_name = generate_random_name("res_dup_cat")
    categories_page.add_category(name=category_name)
    restaurant_category_cleanup.append(category_name)

    assert categories_page.validate_duplicate_category(category_name), (
        "A duplicate Restaurant category name must be rejected"
    )
