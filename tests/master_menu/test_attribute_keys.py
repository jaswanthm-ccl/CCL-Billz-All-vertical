import pytest
from pages.master_menu.attribute_keys_page import AttributeKeysPage
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def attribute_key_cleanup(logged_in_page):
    created_keys = []
    yield created_keys

    keys_page = AttributeKeysPage(logged_in_page)
    for name in reversed(created_keys):
        try:
            if keys_page.is_attribute_key_active(name):
                keys_page.delete_attribute_key(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete attribute key {name}: {exc}")


def test_attribute_key_crud_lifecycle(logged_in_page, attribute_key_cleanup):
    page_obj = AttributeKeysPage(logged_in_page)
    page_obj.navigate()

    # 1. Create with description
    name = generate_random_name("auto_key")
    description = generate_random_description("key_desc")
    page_obj.add_attribute_key(name=name, description=description)
    attribute_key_cleanup.append(name)
    assert page_obj.search_attribute_key(name)

    # 2. View Original Details
    assert page_obj.view_attribute_key(name, expected_description=description)

    # 3. Edit Name & Description
    new_name = generate_random_name("updated_key")
    new_description = generate_random_description("updated_key_desc")
    assert page_obj.edit_attribute_key(
        name, new_name, new_description=new_description
    )
    attribute_key_cleanup.remove(name)
    attribute_key_cleanup.append(new_name)
    assert page_obj.search_attribute_key(new_name)

    # 4. View Edited Details
    assert page_obj.view_attribute_key(
        new_name, expected_description=new_description
    )

    # 5. Delete (Soft delete)
    assert page_obj.delete_attribute_key(new_name)

    # 6. Retrieve / Restore
    assert page_obj.retrieve_attribute_key(new_name)
    assert page_obj.search_attribute_key(new_name)


def test_validate_attribute_key(logged_in_page):
    page_obj = AttributeKeysPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_fields(), (
        "Attribute key name must be required without submitting the network API"
    )
