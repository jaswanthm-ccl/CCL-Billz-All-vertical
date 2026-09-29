import pytest
from pages.master_menu.users_page import UsersPage
from pages.master_menu.branches_page import BranchesPage 
from pages.master_menu.roles_page import RolesPage
from utils.random_data import generate_random_name, generate_random_email, generate_random_password

@pytest.fixture
def branch_cleanup(logged_in_page):
    created_branches = []
    yield created_branches
    branches_page = BranchesPage(logged_in_page)
    for name in created_branches:
        try:
            branches_page.navigate()
            if branches_page.search_branch(name):
                row = branches_page.page.locator("tr", has=branches_page.page.get_by_text(name, exact=True))
                if row.get_by_title("delete").first.is_visible():
                    branches_page.delete_branch(name)
        except Exception as e:
            print(f"Teardown: Failed to delete branch {name}: {e}")
        branches_page.cleanup_auto_city(name)

@pytest.fixture
def role_cleanup(logged_in_page):
    created_roles = []
    yield created_roles
    roles_page = RolesPage(logged_in_page)
    for name in created_roles:
        try:
            roles_page.navigate()
            if roles_page.search_roles(name):
                row = roles_page.page.locator("tr", has=roles_page.page.get_by_text(name, exact=True))
                if row.get_by_title("delete").first.is_visible():
                    roles_page.delete_role(name)
        except Exception as e:
            print(f"Teardown: Failed to delete role {name}: {e}")

@pytest.fixture
def user_cleanup(logged_in_page):
    created_users = []
    yield created_users
    users_page = UsersPage(logged_in_page)
    for name in created_users:
        try:
            users_page.navigate()
            if users_page.is_user_active(name):
                users_page.delete_user(name)
        except Exception as e:
            print(f"Teardown: Failed to delete user {name}: {e}")

def test_user_crud_lifecycle(
    logged_in_page, branch_cleanup, role_cleanup, user_cleanup
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

    user_name = generate_random_name("auto")
    user_email = generate_random_email("autoemail")
    user_password = generate_random_password()

    users_page.add_user(
        name=user_name,
        email=user_email,
        password=user_password,
        branch_name=branch_name,
        role_name=role_name,
    )
    user_cleanup.append(user_name)
    assert users_page.search_user(user_name)
    assert users_page.view_user(user_name)

    new_name = generate_random_name("edited")
    new_email = generate_random_email("editedemail")
    assert users_page.edit_user(
        user_name,
        new_name,
        new_email=new_email,
    )
    user_cleanup.remove(user_name)
    user_cleanup.append(new_name)
    assert users_page.search_user(new_name)
    assert users_page.view_user(
        new_name,
        expected_email=new_email,
        expected_branch=branch_name,
    ), "Edited User fields should persist in View"
    assert users_page.delete_user(new_name)
    assert users_page.retrieve_user(new_name)
    assert users_page.delete_user(new_name)


def test_validate_user_fields(logged_in_page):
    users_page = UsersPage(logged_in_page)
    users_page.navigate()
    assert users_page.validate_user_required_fields()


@pytest.mark.parametrize(
    ("field", "email", "password"),
    [
        pytest.param("email", "invalid-email", generate_random_password(), id="invalid-email"),
        pytest.param("password", generate_random_email("valid"), "123", id="weak-password"),
    ],
)
def test_validate_user_email_and_password(
    logged_in_page, branch_cleanup, role_cleanup, field, email, password
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
    assert users_page.validate_invalid_user_field(
        name=generate_random_name("invalid_user"),
        email=email,
        password=password,
        branch_name=branch_name,
        role_name=role_name,
        field=field,
    ), f"Expected visible validation feedback for invalid {field}"


@pytest.mark.xfail(
    reason="Known bug: user email without a valid domain suffix is accepted"
)
def test_reject_user_email_without_valid_domain_suffix(
    logged_in_page, branch_cleanup, role_cleanup
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
    assert users_page.validate_invalid_user_field(
        name=generate_random_name("invalid_domain_user"),
        email="autobranchassigned_1783917224@example",
        password=generate_random_password(),
        branch_name=branch_name,
        role_name=role_name,
        field="email",
    ), "Expected email validation for a domain without a suffix"


def test_reject_duplicate_user_email(
    logged_in_page, branch_cleanup, role_cleanup, user_cleanup
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
    first_name = generate_random_name("duplicate_email_user")
    duplicate_email = generate_random_email("duplicate")
    password = generate_random_password()
    users_page.add_user(
        first_name, duplicate_email, password, branch_name, role_name
    )
    user_cleanup.append(first_name)

    assert users_page.validate_duplicate_email(
        name=generate_random_name("second_duplicate_email_user"),
        email=duplicate_email,
        password=password,
        branch_name=branch_name,
        role_name=role_name,
    ), "Expected visible validation feedback for a duplicate user email"
