import pytest
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.cities_page import CitiesPage
from utils.random_data import (
    generate_random_address,
    generate_random_code,
    generate_random_email,
    generate_random_name,
    generate_random_phone,
    generate_random_postal_code,
)

@pytest.fixture
def branch_cleanup(logged_in_page):
    created_branches = []
    yield created_branches
    branches_page = BranchesPage(logged_in_page)
    for name in created_branches:
        try:
            logged_in_page.set_default_timeout(15000)
            branches_page.navigate()
            if branches_page.search_branch(name):
                row = branches_page.page.locator("tr", has=branches_page.page.get_by_text(name, exact=True))
                is_already_deleted = row.locator(".bi-arrow-clockwise").count() > 0
                if not is_already_deleted and row.get_by_title("delete").first.is_visible():
                    branches_page.delete_branch(name)
        except Exception as e:
            print(f"Teardown: Failed to delete branch {name}: {e}")
        finally:
            logged_in_page.set_default_timeout(30000)
        branches_page.cleanup_auto_city(name)

@pytest.fixture(scope="module")
def module_city(module_page):
    cities_page = CitiesPage(module_page)
    cities_page.navigate()
    city_name =  generate_random_name("module_city")
    cities_page.add_city(city_name)
    yield city_name

    try:
        cities_page.navigate()

        if cities_page.search_city(city_name):
            cities_page.delete_city(city_name)
    except Exception as e:
        print(f"Error deleting city {city_name}: {e}")


def test_branch_crud_lifecycle(logged_in_page, module_city, branch_cleanup):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    logged_in_page.wait_for_load_state("networkidle")

    # 1. Add Branch
    branch_name = branches_page.add_branch(module_city)
    branch_cleanup.append(branch_name)

    # 2. Search Branch
    assert branches_page.search_branch(branch_name), f"Branch {branch_name} should be searchable"

    # 3. View Branch
    assert branches_page.view_branch(branch_name), f"Branch {branch_name} details should be viewable"

    # 4. Edit Branch
    edited_fields = {
        "name": branch_name + "_edited",
        "code": generate_random_code("EDIT"),
        "address": generate_random_address(),
        "postal_code": generate_random_postal_code(),
        "phone": generate_random_phone(),
        "email": generate_random_email("editedbranch"),
        "sort_order": "7",
    }
    edited_name = edited_fields["name"]
    assert branches_page.edit_branch(
        branch_name,
        updated_fields=edited_fields,
    ), f"Branch {branch_name} should be editable"
    branch_cleanup.remove(branch_name)
    branch_cleanup.append(edited_name)

    # 5. Reopen View and verify edited fields plus retained City.
    assert branches_page.search_branch(edited_name)
    assert branches_page.view_branch(
        edited_name,
        expected_values={
            **edited_fields,
            "city": module_city,
        },
    ), "Edited Branch fields should persist in View"

    # 6. Delete Branch
    assert branches_page.delete_branch(edited_name), f"Branch {edited_name} should be deleted"

    # 7. Retrieve Soft-Deleted Branch
    assert branches_page.retrieve_branch(edited_name), f"Branch {edited_name} should be retrieved"
    
def test_validate_branch(logged_in_page):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    logged_in_page.wait_for_load_state("networkidle", timeout=10000)
    
    assert branches_page.validate_branch_name()

def test_duplicate_branch(logged_in_page, module_city, branch_cleanup):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    logged_in_page.wait_for_load_state("networkidle", timeout=10000)

    branch_name = branches_page.add_branch(module_city)
    branch_cleanup.append(branch_name)

    assert branches_page.duplicate_branch_name(branch_name)


def test_duplicate_branch_code(logged_in_page, branch_cleanup):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branch_cleanup.append(branch_name)
    duplicate_code = branches_page.get_branch_code(branch_name)
    assert branches_page.duplicate_branch_code(duplicate_code, branch_name), (
        "Expected duplicate Branch Code to be rejected"
    )


@pytest.mark.parametrize(
    ("field", "error_text"),
    [
        ("code", "Branch Code is required"),
        ("address", "Address is required"),
    ],
)
def test_required_branch_fields(logged_in_page, field, error_text):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    assert branches_page.validate_required_field(field, error_text)


@pytest.mark.parametrize(
    ("field", "value", "patterns"),
    [
        pytest.param(
            "email",
            "test@gmail",
            (r"invalid email", r"email.*format"),
            marks=pytest.mark.xfail(
                reason="Known bug: Branch email without a valid domain suffix is accepted"
            ),
            id="email-without-domain-suffix",
        ),
        ("postal_code", "ABC123", (r"postal.*6-digit", r"postal.*number")),
        ("postal_code", "12345", (r"postal.*6-digit",)),
        ("postal_code", "1234567", (r"postal.*6-digit",)),
    ],
)
def test_branch_field_formats(logged_in_page, field, value, patterns):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    assert branches_page.validate_field_format(field, value, *patterns), (
        f"Expected validation feedback for {field}={value!r}"
    )


@pytest.mark.parametrize("sort_order", ["0", "-1", "1.5"])
def test_branch_sort_order_validation(logged_in_page, sort_order):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    assert branches_page.validate_field_format(
        "sort_order",
        sort_order,
        r"sort order.*greater than 0",
        r"sort_order.*integer",
        r"sort order.*integer",
    ), f"Expected Sort Order validation for {sort_order!r}"


@pytest.mark.xfail(reason="Known bug: clearing Sort Order during Branch edit produces an SQL error")
def test_edit_branch_with_blank_sort_order(logged_in_page, branch_cleanup):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branch_cleanup.append(branch_name)
    assert branches_page.edit_with_blank_sort_order_is_handled(branch_name)


@pytest.mark.xfail(reason="Known bug: the first City is auto-selected without a configured default")
def test_new_branch_has_no_city_selected_by_default(logged_in_page):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    assert branches_page.city_is_unselected_by_default()


@pytest.mark.parametrize("phone", ["123", "abcdefghij"])
def test_validate_branch_phone(logged_in_page, phone):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    logged_in_page.wait_for_load_state("networkidle", timeout=10000)
    assert branches_page.validate_invalid_phone(phone), (
        f"Expected visible phone validation feedback for {phone!r}"
    )


@pytest.mark.xfail(reason="Known bug: phone numbers starting outside 6-9 are accepted")
def test_reject_branch_phone_with_invalid_start_digit(logged_in_page):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    logged_in_page.wait_for_load_state("networkidle", timeout=10000)
    assert branches_page.validate_invalid_phone("1234567890"), (
        "Expected phone validation when the first digit is not 6, 7, 8, or 9"
    )


@pytest.mark.xfail(reason="Known UI gap: Branch Actions column has no sorting option")
def test_branch_actions_column_sorting_is_available(logged_in_page):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    logged_in_page.wait_for_load_state("networkidle", timeout=10000)
    assert branches_page.has_actions_sorting_control(), (
        "Expected a sorting control in the Branch Actions column"
    )


def test_default_city_auto_populates_in_new_branch(logged_in_page):
    from pages.master_menu.cities_page import CitiesPage
    from utils.random_data import generate_random_name

    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()
    previous_default = cities_page.get_default_city_name("Tamil Nadu")
    city_name = generate_random_name("auto_def_city")
    cities_page.add_city(city_name)

    try:
        cities_page.set_city_as_default(city_name)

        branches_page = BranchesPage(logged_in_page)
        branches_page.navigate()
        selected_city = branches_page.get_selected_city_in_new_branch_form()

        assert city_name in selected_city, (
            f"Expected default city {city_name!r} to auto-populate in Add Branch "
            f"form, but got {selected_city!r}"
        )
    finally:
        cities_page.navigate()
        if previous_default:
            cities_page.set_city_as_default(previous_default)
            cities_page.navigate()
        if cities_page.search_city(city_name):
            cities_page.delete_city(city_name)
