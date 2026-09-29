import pytest

from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.racks_page import DELETE_ICON_BUTTON, RacksPage
from utils.random_data import generate_random_code, generate_random_name


@pytest.fixture
def temp_branch(logged_in_page):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()

    yield branch_name

    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            row = branches_page.page.locator(
                "tr",
                has=branches_page.page.get_by_text(branch_name, exact=True),
            )
            if row.locator(DELETE_ICON_BUTTON).is_visible():
                branches_page.delete_branch(branch_name)
    except Exception as exc:
        print(f"Teardown: Failed to delete branch {branch_name}: {exc}")
    branches_page.cleanup_auto_city(branch_name)


@pytest.fixture
def rack_cleanup(logged_in_page):
    created_racks = []
    yield created_racks

    page_obj = RacksPage(logged_in_page)
    for name in created_racks:
        try:
            page_obj.navigate()
            if page_obj.is_rack_active(name):
                page_obj.delete_rack(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete rack {name}: {exc}")


def test_racks_crud_lifecycle(logged_in_page, temp_branch, rack_cleanup):
    page_obj = RacksPage(logged_in_page)
    page_obj.navigate()

    name = generate_random_name("auto_rack")
    code = generate_random_code("RK")
    description = "Rack lifecycle description"
    sort_order = "3"
    page_obj.add_rack(
        name,
        code,
        branch_name=temp_branch,
        description=description,
        sort_order=sort_order,
    )
    rack_cleanup.append(name)
    assert page_obj.search_rack(name)
    assert page_obj.view_rack(
        name,
        expected_code=code,
        expected_branch=temp_branch,
        expected_sort_order=sort_order,
        expected_description=description,
    )

    new_name = generate_random_name("auto_rack_new")
    new_code = generate_random_code("ERK")
    new_description = "Updated rack lifecycle description"
    new_sort_order = "7"
    assert page_obj.edit_rack(
        name,
        new_name,
        new_code=new_code,
        new_description=new_description,
        new_sort_order=new_sort_order,
    )
    rack_cleanup.remove(name)
    rack_cleanup.append(new_name)
    assert page_obj.search_rack(new_name)

    # Reopen View and verify every changed field plus the retained Branch.
    assert page_obj.view_rack(
        new_name,
        expected_code=new_code,
        expected_branch=temp_branch,
        expected_sort_order=new_sort_order,
        expected_description=new_description,
    )

    assert page_obj.delete_rack(new_name)
    assert page_obj.retrieve_rack(new_name)
    assert page_obj.search_rack(new_name)


def test_rack_required_fields(logged_in_page):
    page_obj = RacksPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_fields(), (
        "Rack name, code, and branch must be required without submitting the API"
    )


def test_reject_duplicate_rack_in_branch(
    logged_in_page, temp_branch, rack_cleanup
):
    page_obj = RacksPage(logged_in_page)
    page_obj.navigate()
    name = generate_random_name("duplicate_rack")
    code = generate_random_code("DUP")
    page_obj.add_rack(name, code, branch_name=temp_branch)
    rack_cleanup.append(name)
    assert page_obj.search_rack(name)
    assert page_obj.validate_duplicate_rack(name, code, temp_branch), (
        "Expected UI validation and API rejection for a duplicate rack"
    )


@pytest.mark.xfail(
    reason=(
        "System currently allows deleting a branch that contains an active "
        "rack (missing restriction/bug)"
    )
)
def test_delete_branch_containing_rack(
    logged_in_page, temp_branch, rack_cleanup
):
    racks_page = RacksPage(logged_in_page)
    racks_page.navigate()
    rack_name = generate_random_name("auto_dependency_rack")
    rack_code = generate_random_code("DRK")
    racks_page.add_rack(rack_name, rack_code, branch_name=temp_branch)
    rack_cleanup.append(rack_name)
    assert racks_page.search_rack(rack_name)

    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    assert not branches_page.delete_branch(temp_branch)
