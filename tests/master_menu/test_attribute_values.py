import pytest
from pages.master_menu.attribute_keys_page import AttributeKeysPage
from pages.master_menu.attribute_values_page import AttributeValuesPage
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def attribute_key_cleanup(logged_in_page):
    created_keys = []
    yield created_keys

    keys_page = AttributeKeysPage(logged_in_page)
    for name in reversed(created_keys):
        try:
            keys_page.navigate()
            if keys_page.is_attribute_key_active(name):
                keys_page.delete_attribute_key(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete attribute key {name}: {exc}")


@pytest.fixture
def attribute_value_cleanup(logged_in_page):
    created_values = []
    yield created_values

    value_page = AttributeValuesPage(logged_in_page)
    for name in reversed(created_values):
        try:
            if value_page.is_attribute_value_active(name):
                value_page.delete_attribute_value(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete attribute value {name}: {exc}")


def test_attribute_value_crud_lifecycle(
    logged_in_page, attribute_key_cleanup, attribute_value_cleanup
):
    key_page = AttributeKeysPage(logged_in_page)
    key_page.navigate()
    key_name = generate_random_name("auto_key")
    key_page.add_attribute_key(name=key_name)
    attribute_key_cleanup.append(key_name)

    value_page = AttributeValuesPage(logged_in_page)
    value_page.navigate()

    # 1. Create with description
    value_name = generate_random_name("auto_val")
    description = generate_random_description("val_desc")
    value_page.add_attribute_value(
        key_name=key_name, value=value_name, description=description
    )
    attribute_value_cleanup.append(value_name)
    assert value_page.search_attribute_value(value_name)

    # 2. View Original Details (Feature fixed & active)
    assert value_page.view_attribute_value(
        value_name, expected_description=description
    )

    # 3. Edit (Value & Description)
    new_value = generate_random_name("updated_val")
    new_description = generate_random_description("updated_val_desc")
    assert value_page.edit_attribute_value(
        value_name, new_value, new_description=new_description
    )
    attribute_value_cleanup.remove(value_name)
    attribute_value_cleanup.append(new_value)
    assert value_page.search_attribute_value(new_value)

    # 4. View Edited Details
    assert value_page.view_attribute_value(
        new_value, expected_description=new_description
    )

    # 5. Delete (Soft delete)
    assert value_page.delete_attribute_value(new_value)

    # 6. Retrieve / Restore
    assert value_page.retrieve_attribute_value(new_value)
    assert value_page.search_attribute_value(new_value)


def test_validate_attribute_value(logged_in_page):
    page_obj = AttributeValuesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_fields(), (
        "Attribute value must be required without submitting the network API"
    )


def test_reject_duplicate_attribute_value(
    logged_in_page, attribute_key_cleanup, attribute_value_cleanup
):
    key_page = AttributeKeysPage(logged_in_page)
    key_page.navigate()
    key_name = generate_random_name("duplicate_key")
    key_page.add_attribute_key(name=key_name)
    attribute_key_cleanup.append(key_name)

    value_page = AttributeValuesPage(logged_in_page)
    value_page.navigate()
    value_name = generate_random_name("duplicate_value")
    value_page.add_attribute_value(key_name=key_name, value=value_name)
    attribute_value_cleanup.append(value_name)
    assert value_page.search_attribute_value(value_name)

    assert value_page.validate_duplicate_value(key_name, value_name), (
        "Expected visible validation feedback and API 422 for a duplicate attribute value"
    )
