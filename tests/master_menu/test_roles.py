import pytest
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.roles_page import RolesPage
from pages.master_menu.users_page import UsersPage
from utils.random_data import (
    generate_random_email,
    generate_random_name,
    generate_random_password,
)

@pytest.fixture
def role_cleanup(logged_in_page):
    created_roles = []
    yield created_roles
    roles_page = RolesPage(logged_in_page)
    for name in created_roles:
        try:
            roles_page.navigate()
            # is_role_active() checks for the trash icon specifically. Delete and
            # Retrieve both render title="delete", so a plain get_by_title check
            # would try to delete an already-deleted role and restore it instead.
            if roles_page.search_roles(name) and roles_page.is_role_active(name):
                roles_page.delete_role(name)
        except Exception as e:
            print(f"Teardown: Failed to delete role {name}: {e}")


@pytest.fixture
def branch_cleanup(logged_in_page):
    created_branches = []
    yield created_branches
    branches_page = BranchesPage(logged_in_page)
    for name in created_branches:
        try:
            branches_page.navigate()
            if branches_page.search_branch(name):
                branches_page.delete_branch(name)
        except Exception as e:
            print(f"Teardown: Failed to delete branch {name}: {e}")
        branches_page.cleanup_auto_city(name)


@pytest.fixture
def user_cleanup(logged_in_page):
    created_users = []
    yield created_users
    users_page = UsersPage(logged_in_page)
    for name in created_users:
        try:
            users_page.navigate()
            if users_page.search_user(name):
                users_page.delete_user(name)
        except Exception as e:
            print(f"Teardown: Failed to delete user {name}: {e}")


def test_role_crud_lifecycle(logged_in_page, role_cleanup):
    from utils.random_data import generate_random_description
    roles_page = RolesPage(logged_in_page)
    roles_page.navigate()

    # 1. Add Role
    role_data = roles_page.add_roles()
    role_name = role_data["name"]
    role_cleanup.append(role_name)

    # 2. Search Role
    assert roles_page.search_roles(role_name), f"Role {role_name} should be searchable"

    # 3. View Role Details
    assert roles_page.view_roles(role_name), f"Role {role_name} details should be viewable in View modal"

    # 4. Edit Role (Update Name & Description)
    new_role_name = generate_random_name("edited_role")
    new_role_desc = generate_random_description("updated_desc")
    assert roles_page.edit_role(role_name, new_role_name, new_description=new_role_desc), (
        f"Role should be updated to {new_role_name}"
    )
    role_cleanup.remove(role_name)
    role_cleanup.append(new_role_name)

    # 5. Re-View Updated Role to confirm updated role is viewable
    assert roles_page.view_roles(
        new_role_name,
        expected_description=new_role_desc,
    ), (
        f"Updated Role {new_role_name} should persist its edited name "
        "and description"
    )

    # 6. Delete Role
    assert roles_page.delete_role(new_role_name), f"Role {new_role_name} should be deleted"

    # 7. Retrieve Soft-Deleted Role
    assert roles_page.retrieve_role(new_role_name), f"Role {new_role_name} should be retrieved"
    assert roles_page.delete_role(new_role_name), f"Role {new_role_name} should be cleaned up"


def test_role_required_fields(logged_in_page):
    roles_page = RolesPage(logged_in_page)
    roles_page.navigate()

    assert roles_page.validate_required_fields(), (
        "Role name, description, and at least one permission must be required"
    )


def test_reject_duplicate_role_name(logged_in_page, role_cleanup):
    roles_page = RolesPage(logged_in_page)
    roles_page.navigate()
    role_name = roles_page.add_roles()["name"]
    role_cleanup.append(role_name)

    assert roles_page.validate_duplicate_role(role_name), (
        f"Duplicate role name {role_name} should be rejected"
    )


@pytest.mark.parametrize(
    "sort_order",
    [
        pytest.param("0", id="zero"),
        pytest.param("-1", id="negative"),
        pytest.param(
            "1.5",
            id="decimal",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Bug #TBD: Role Sort Order accepts decimal values",
            ),
        ),
        pytest.param(
            "1234567",
            id="overlength",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Bug #TBD: Role Sort Order accepts more than 6 digits",
            ),
        ),
    ],
)
def test_reject_invalid_role_sort_order(
    logged_in_page,
    role_cleanup,
    sort_order,
):
    roles_page = RolesPage(logged_in_page)
    roles_page.navigate()
    role_name = generate_random_name("invalid_sort_role")
    role_cleanup.append(role_name)

    assert roles_page.validate_invalid_sort_order(role_name, sort_order), (
        f"Role Sort Order {sort_order!r} should be rejected"
    )


@pytest.mark.xfail(
    strict=True,
    reason="Bug #TBD: A role assigned to an active user can be deleted",
)
def test_role_assigned_to_user_cannot_be_deleted(
    logged_in_page,
    branch_cleanup,
    role_cleanup,
    user_cleanup,
):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branch_cleanup.append(branch_name)

    roles_page = RolesPage(logged_in_page)
    roles_page.navigate()
    role_name = roles_page.add_roles()["name"]
    role_cleanup.append(role_name)

    users_page = UsersPage(logged_in_page)
    users_page.navigate()
    user_name = generate_random_name("role_dependency_user")
    users_page.add_user(
        name=user_name,
        email=generate_random_email("role_dependency"),
        password=generate_random_password(),
        branch_name=branch_name,
        role_name=role_name,
    )
    user_cleanup.append(user_name)

    roles_page.navigate()
    assert roles_page.delete_role_expect_blocked(role_name), (
        f"Role {role_name} should not be deletable while assigned to {user_name}"
    )
