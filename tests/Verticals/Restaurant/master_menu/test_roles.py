"""Restaurant Role lifecycle and validation tests."""

import pytest

from pages.Verticals.Restaurant.master_menu.roles_page import RolesPage
from utils.random_data import generate_random_description, generate_random_name


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_role_cleanup(res_logged_in_page):
    created_roles: list[str] = []
    yield created_roles
    page_obj = RolesPage(res_logged_in_page)
    for name in reversed(created_roles):
        try:
            page_obj.navigate()
            if page_obj.is_role_active(name):
                page_obj.delete_role(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant role {name}: {exc}")


def test_restaurant_role_crud_lifecycle(
    res_logged_in_page, restaurant_role_cleanup
):
    page_obj = RolesPage(res_logged_in_page)
    page_obj.navigate()
    role_name = page_obj.add_roles()["name"]
    restaurant_role_cleanup.append(role_name)
    assert page_obj.search_roles(role_name)
    assert page_obj.view_roles(role_name)

    updated_name = generate_random_name("res_updated_role")
    updated_description = generate_random_description("res_updated_role")
    assert page_obj.edit_role(
        role_name, updated_name, new_description=updated_description
    )
    restaurant_role_cleanup.remove(role_name)
    restaurant_role_cleanup.append(updated_name)
    assert page_obj.view_roles(
        updated_name, expected_description=updated_description
    )
    assert page_obj.delete_role(updated_name)
    assert page_obj.retrieve_role(updated_name)
    assert page_obj.delete_role(updated_name)


def test_restaurant_role_required_fields(res_logged_in_page):
    page_obj = RolesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_fields()


def test_restaurant_role_rejects_duplicate_name(
    res_logged_in_page, restaurant_role_cleanup
):
    page_obj = RolesPage(res_logged_in_page)
    page_obj.navigate()
    role_name = page_obj.add_roles()["name"]
    restaurant_role_cleanup.append(role_name)
    assert page_obj.validate_duplicate_role(role_name)


@pytest.mark.parametrize("sort_order", ["0", "-1"])
def test_restaurant_role_rejects_invalid_sort_order(
    res_logged_in_page, restaurant_role_cleanup, sort_order
):
    page_obj = RolesPage(res_logged_in_page)
    page_obj.navigate()
    role_name = generate_random_name("res_invalid_sort_role")
    restaurant_role_cleanup.append(role_name)
    assert page_obj.validate_invalid_sort_order(role_name, sort_order)
