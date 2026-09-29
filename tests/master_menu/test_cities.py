import pytest

from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.branches_page import BranchesPage
from utils.random_data import generate_random_name


@pytest.fixture
def city_cleanup(logged_in_page):
    """Register city names for best-effort teardown deletion."""
    created_cities: list[str] = []
    yield created_cities
    cities_page = CitiesPage(logged_in_page)
    for name in created_cities:
        try:
            cities_page.navigate()
            if cities_page.search_city(name):
                cities_page.delete_city(name)
        except Exception as e:
            print(f"Teardown: Failed to delete city {name}: {e}")


@pytest.fixture
def branch_cleanup(logged_in_page):
    created_branches: list[str] = []
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


# ── Rule 3: Single CRUD lifecycle test ───────────────────────────────────────


def test_city_crud_lifecycle(logged_in_page, city_cleanup):
    """Create -> Search -> Edit -> Delete -> Retrieve in one flow."""
    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()

    # 1. Create
    city_name = cities_page.add_city()
    city_cleanup.append(city_name)

    # 2. Search
    assert cities_page.search_city(city_name), (
        f"City {city_name} should be searchable after creation"
    )

    # 3. Edit
    new_city_name = generate_random_name("edited_city")
    assert cities_page.edit_city(city_name, new_city_name), (
        f"City should be updated from {city_name} to {new_city_name}"
    )
    city_cleanup.remove(city_name)
    city_cleanup.append(new_city_name)
    assert cities_page.search_city(new_city_name)
    assert cities_page.verify_city_name(new_city_name), (
        "Edited City name should persist when Edit is reopened"
    )

    # 4. Delete
    assert cities_page.delete_city(new_city_name), (
        f"City {new_city_name} should be soft-deleted"
    )

    # 5. Retrieve
    assert cities_page.retrieve_city(new_city_name), (
        f"City {new_city_name} should be restored after soft-delete"
    )


# ── Validation tests ─────────────────────────────────────────────────────────


def test_city_name_is_required(logged_in_page):
    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()

    assert cities_page.validate_required_name(), "City Name must be required"


def test_city_name_maximum_length(logged_in_page):
    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()

    assert cities_page.validate_name_too_long("C" * 101), (
        "City Name longer than 100 characters must be rejected"
    )


def test_reject_duplicate_city_in_same_state(logged_in_page, city_cleanup):
    """Duplicate city+state must be rejected with 422 and visible feedback."""
    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()

    city_name = generate_random_name("duplicate_city")
    cities_page.add_city(city_name)
    city_cleanup.append(city_name)

    assert cities_page.validate_duplicate_city(city_name), (
        "Expected visible validation feedback for a duplicate city/state combination"
    )


def test_default_city_selection_persists(logged_in_page, city_cleanup):
    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()
    previous_default = cities_page.get_default_city_name("Tamil Nadu")
    city_name = generate_random_name("default_city")
    city_cleanup.append(city_name)

    try:
        cities_page.add_city(city_name, is_default=True)
        assert cities_page.is_city_default(city_name), (
            f"City {city_name} should remain marked as default after list refresh"
        )
    finally:
        if previous_default:
            cities_page.navigate()
            cities_page.set_city_as_default(previous_default)


@pytest.mark.xfail(
    reason="Bug #TBD: City names containing numbers are accepted"
)
def test_reject_city_name_containing_numbers(logged_in_page):
    """City name with numbers should be rejected by validation."""
    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()

    assert cities_page.validate_invalid_city_name("Coimbatore123"), (
        "Expected city-name validation because numbers are not allowed"
    )


# ── Dependency restriction tests ─────────────────────────────────────────────


@pytest.mark.xfail(
    reason="Bug #TBD: Backend permits deleting a city assigned to an active branch"
)
def test_delete_city_assigned_to_branch_is_blocked(
    logged_in_page,
    city_cleanup,
    branch_cleanup,
):
    """A city in use by a branch must not be deletable."""
    from pages.master_menu.branches_page import BranchesPage
    from utils.random_data import (
        generate_random_code,
        generate_random_address,
        generate_random_phone,
        generate_random_postal_code,
        generate_random_email,
    )

    cities_page = CitiesPage(logged_in_page)
    cities_page.navigate()

    city_name = generate_random_name("city_dep")
    cities_page.add_city(city_name)
    city_cleanup.append(city_name)

    # Create a branch using this city
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()

    branch_name = generate_random_name("branch_dep")
    branch_cleanup.append(branch_name)
    branches_page.page.get_by_role("button", name="Add Branch").click()
    branches_page.page.locator('input[name="name"]').fill(branch_name)
    branches_page.page.locator('input[name="code"]').fill(generate_random_code())
    branches_page.page.locator('input[name="address"]').fill(generate_random_address())

    branches_page.page.locator("input[name='state_id']").locator("xpath=..").locator(
        ".react-select__input-container"
    ).click()
    branches_page.page.get_by_role("option", name="Tamil Nadu").click()

    branches_page.page.locator("input[name='city_id']").locator("xpath=..").locator(
        ".react-select__input-container"
    ).click()
    branches_page.page.get_by_role("option", name=city_name).click()

    branches_page.page.locator('input[name="postal_code"]').fill(generate_random_postal_code())
    branches_page.page.get_by_role("textbox", name="Enter 10-digit phone number").fill(
        generate_random_phone()
    )
    branches_page.page.locator('input[name="email"]').fill(generate_random_email())
    branches_page.page.get_by_role("spinbutton").fill("3")
    branches_page.page.get_by_role("button", name="Create").click()

    branches_page.page.get_by_text("Branch created successfully").wait_for(
        state="visible", timeout=5000
    )

    # Attempt to delete the city — should be blocked
    cities_page.navigate()
    if not cities_page.delete_city_expect_fail(city_name):
        # City was deleted by backend bug — remove from cleanup to prevent teardown timeout
        if city_name in city_cleanup:
            city_cleanup.remove(city_name)
        pytest.fail(f"City {city_name} should NOT be deletable while assigned to a branch")
