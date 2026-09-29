import pytest
from pages.master_menu.account_groups_page import AccountGroupsPage
from utils.random_data import generate_random_name

@pytest.fixture
def account_group_cleanup(logged_in_page):
    created_groups = []
    yield created_groups
    groups_page = AccountGroupsPage(logged_in_page)
    for name in reversed(created_groups):
        try:
            groups_page.navigate()
            if groups_page.search_account_group(name):
                row = groups_page.page.locator("tbody tr").filter(
                    has=groups_page.page.get_by_text(name, exact=True)
                ).first
                if row.locator(
                    'button[title="delete"]:has(i.bi-trash)'
                ).is_visible():
                    groups_page.delete_account_group(name)
        except Exception as e:
            print(f"Teardown: Failed to delete account group {name}: {e}")



def test_account_groups_crud_lifecycle(logged_in_page, account_group_cleanup):
    """Create parent group -> Create child group -> Search -> View -> Edit -> Delete"""

    page_obj = AccountGroupsPage(logged_in_page)
    page_obj.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    
    # 1. Create Parent Group
    parent_name = generate_random_name("parent_grp")
    page_obj.add_account_group(parent_name, parent_group="— Root —")
    account_group_cleanup.append(parent_name)

    assert page_obj.search_account_group(parent_name)

    # 2. Create Child Group assigned to Parent
    child_name = generate_random_name("child_grp")
    page_obj.add_account_group(child_name, parent_group=parent_name)
    account_group_cleanup.append(child_name)

    assert page_obj.search_account_group(child_name)

    # 3. View Child Group and verify parent relationship
    assert page_obj.view_account_group(child_name, expected_parent=parent_name)

    # 4. Edit Child Group
    new_child_name = generate_random_name("child_edited")
    assert page_obj.edit_account_group(child_name, new_child_name)
    account_group_cleanup.remove(child_name)
    account_group_cleanup.append(new_child_name)
    assert page_obj.search_account_group(new_child_name)
    assert page_obj.view_account_group(
        new_child_name,
        expected_parent=parent_name,
    ), "Edited Account Group name and parent should persist in View"

    # 5. Delete Child Group
    assert page_obj.delete_account_group(new_child_name)
    account_group_cleanup.remove(new_child_name)

    # 6. Delete Parent Group
    assert page_obj.delete_account_group(parent_name)
    account_group_cleanup.remove(parent_name)


@pytest.mark.xfail(reason="Restore functionality is not working in the app")
def test_retrieve_account_group(logged_in_page, account_group_cleanup):
    page_obj = AccountGroupsPage(logged_in_page)
    page_obj.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    
    name = generate_random_name("auto_group")
    page_obj.add_account_group(name)
    account_group_cleanup.append(name)
    assert page_obj.search_account_group(name)
    assert page_obj.delete_account_group(name)
    assert page_obj.retrieve_account_group(name)
    assert page_obj.search_account_group(name)

def test_validate_account_group(logged_in_page):
    page_obj = AccountGroupsPage(logged_in_page)
    page_obj.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    assert page_obj.validate_required_fields()
