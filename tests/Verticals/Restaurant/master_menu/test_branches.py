"""Restaurant Branch lifecycle and validation tests."""

import pytest

from pages.Verticals.Restaurant.master_menu.branches_page import BranchesPage
from utils.random_data import (
    generate_random_address,
    generate_random_code,
    generate_random_email,
    generate_random_name,
    generate_random_phone,
    generate_random_postal_code,
)


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_branch_cleanup(res_logged_in_page):
    created_branches: list[str] = []
    yield created_branches
    page_obj = BranchesPage(res_logged_in_page)
    for name in reversed(created_branches):
        try:
            page_obj.navigate()
            if page_obj.search_branch(name):
                delete_button = page_obj.page.locator(
                    "tr", has=page_obj.page.get_by_text(name, exact=True)
                ).locator('button[title="delete"]:has(i.bi-trash)').first
                if delete_button.is_visible():
                    page_obj.delete_branch(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant branch {name}: {exc}")


def test_restaurant_branch_crud_lifecycle(
    res_logged_in_page, restaurant_branch_cleanup
):
    page_obj = BranchesPage(res_logged_in_page)
    branch_name = page_obj.add_branch()
    restaurant_branch_cleanup.append(branch_name)
    assert page_obj.search_branch(branch_name)
    assert page_obj.view_branch(branch_name)

    updated_name = generate_random_name("res_updated_branch")
    updated_fields = {
        "name": updated_name,
        "code": generate_random_code("RBE"),
        "address": generate_random_address(),
        "postal_code": generate_random_postal_code(),
        "phone": generate_random_phone(),
        "email": generate_random_email(),
        "sort_order": "8",
    }
    assert page_obj.edit_branch(branch_name, updated_fields=updated_fields)
    restaurant_branch_cleanup.remove(branch_name)
    restaurant_branch_cleanup.append(updated_name)
    assert page_obj.view_branch(updated_name, expected_values=updated_fields)
    assert page_obj.delete_branch(updated_name)
    assert page_obj.retrieve_branch(updated_name)


def test_restaurant_branch_name_is_required(res_logged_in_page):
    page_obj = BranchesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_branch_name()


@pytest.mark.parametrize(
    ("field", "error_text"),
    [
        ("code", "Branch Code is required"),
        ("address", "Address is required"),
    ],
)
def test_restaurant_branch_required_fields(
    res_logged_in_page, field, error_text
):
    page_obj = BranchesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_field(field, error_text)


@pytest.mark.parametrize(
    ("field", "value", "patterns"),
    [
        ("postal_code", "ABC123", (r"postal.*6-digit", r"postal.*number")),
        ("postal_code", "12345", (r"postal.*6-digit",)),
        ("sort_order", "0", (r"sort order.*greater than 0",)),
    ],
)
def test_restaurant_branch_rejects_invalid_format(
    res_logged_in_page, field, value, patterns
):
    page_obj = BranchesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_field_format(field, value, *patterns)
