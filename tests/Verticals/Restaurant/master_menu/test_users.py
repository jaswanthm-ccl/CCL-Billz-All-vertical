"""Restaurant Branch, Role, and User assignment flow."""

import pytest

from pages.Verticals.Restaurant.master_menu.branches_page import BranchesPage
from pages.Verticals.Restaurant.master_menu.roles_page import RolesPage
from pages.Verticals.Restaurant.master_menu.users_page import UsersPage
from utils.random_data import (
    generate_random_email,
    generate_random_name,
    generate_random_password,
)


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_access_flow_cleanup(res_logged_in_page):
    created = {"users": [], "roles": [], "branches": []}
    yield created

    users_page = UsersPage(res_logged_in_page)
    for user_name in reversed(created["users"]):
        try:
            users_page.navigate()
            if users_page.is_user_active(user_name):
                users_page.delete_user(user_name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant user {user_name}: {exc}")

    roles_page = RolesPage(res_logged_in_page)
    for role_name in reversed(created["roles"]):
        try:
            roles_page.navigate()
            if roles_page.is_role_active(role_name):
                roles_page.delete_role(role_name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant role {role_name}: {exc}")

    branches_page = BranchesPage(res_logged_in_page)
    for branch_name in reversed(created["branches"]):
        try:
            branches_page.navigate()
            if branches_page.search_branch(branch_name):
                row = branches_page.page.locator(
                    "tr",
                    has=branches_page.page.get_by_text(branch_name, exact=True),
                )
                delete_button = row.locator(
                    'button[title="delete"]:has(i.bi-trash)'
                ).first
                if delete_button.is_visible():
                    branches_page.delete_branch(branch_name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant branch {branch_name}: {exc}")


def test_restaurant_branch_role_user_assignment_flow(
    res_logged_in_page, restaurant_access_flow_cleanup
):
    branches_page = BranchesPage(res_logged_in_page)
    branch_name = branches_page.add_branch()
    restaurant_access_flow_cleanup["branches"].append(branch_name)
    assert branches_page.search_branch(branch_name)

    roles_page = RolesPage(res_logged_in_page)
    roles_page.navigate()
    role_name = roles_page.add_roles()["name"]
    restaurant_access_flow_cleanup["roles"].append(role_name)
    assert roles_page.search_roles(role_name)

    users_page = UsersPage(res_logged_in_page)
    users_page.navigate()
    user_name = generate_random_name("res_access_user")
    user_email = generate_random_email("res_access")
    users_page.add_user(
        name=user_name,
        email=user_email,
        password=generate_random_password(),
        branch_name=branch_name,
        role_name=role_name,
    )
    restaurant_access_flow_cleanup["users"].append(user_name)

    assert users_page.row_has_assignments(user_name, branch_name, role_name), (
        "The created User row must show the assigned Restaurant Branch and Role"
    )
    assert users_page.view_user(
        user_name,
        expected_email=user_email,
        expected_branch=branch_name,
    ), "The User view must persist the selected Branch"

    updated_name = generate_random_name("res_updated_access_user")
    updated_email = generate_random_email("res_updated_access")
    assert users_page.edit_user(
        user_name,
        updated_name,
        new_email=updated_email,
    )
    restaurant_access_flow_cleanup["users"].remove(user_name)
    restaurant_access_flow_cleanup["users"].append(updated_name)

    assert users_page.row_has_assignments(updated_name, branch_name, role_name), (
        "Editing the User must retain its Restaurant Branch and Role assignments"
    )
    assert users_page.view_user(
        updated_name,
        expected_email=updated_email,
        expected_branch=branch_name,
    )
    assert users_page.delete_user(updated_name)
    assert users_page.retrieve_user(updated_name)
    assert users_page.delete_user(updated_name)


def test_restaurant_user_required_fields(res_logged_in_page):
    users_page = UsersPage(res_logged_in_page)
    users_page.navigate()
    assert users_page.validate_user_required_fields()
