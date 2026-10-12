"""Galaxy attribute keys and values: phone variants such as RAM, storage and colour."""
import pytest

from pages.master_menu.attribute_keys_page import AttributeKeysPage
from pages.master_menu.attribute_values_page import AttributeValuesPage
from utils.random_data import generate_random_code, generate_random_description, generate_random_name


@pytest.fixture
def keys_page(galaxy_logged_in_page, tenant):
    page_obj = AttributeKeysPage(galaxy_logged_in_page, tenant)
    page_obj.navigate()
    return page_obj


@pytest.fixture
def values_page(galaxy_logged_in_page, tenant):
    return AttributeValuesPage(galaxy_logged_in_page, tenant)


@pytest.fixture
def variant_key(keys_page, cleanup):
    name = generate_random_name("galaxy_storage")
    keys_page.add_attribute_key(name=name)
    cleanup(f"attribute key {name}", lambda: keys_page.ensure_deleted(name))
    return name


def test_attribute_key_lifecycle(keys_page, cleanup):
    name = generate_random_name("galaxy_key")
    description = generate_random_description("galaxy_key_desc")
    keys_page.add_attribute_key(name=name, description=description)
    cleanup(f"attribute key {name}", lambda: keys_page.ensure_deleted(name))
    assert keys_page.view_attribute_key(name, expected_description=description)

    new_name = generate_random_name("galaxy_key_edit")
    assert keys_page.edit_attribute_key(name, new_name)
    cleanup(f"attribute key {new_name}", lambda: keys_page.ensure_deleted(new_name))
    assert keys_page.search_attribute_key(new_name)

    assert keys_page.delete_attribute_key(new_name)
    keys_page.navigate()
    assert keys_page.is_attribute_key_deleted(new_name), "Deleted key should show the retrieve action"


def test_attribute_key_name_is_required(keys_page):
    assert keys_page.validate_required_fields()


def test_create_multiple_values_for_one_key(values_page, variant_key, cleanup):
    suffix = generate_random_code("V")
    values = [f"128GB_{suffix}", f"256GB_{suffix}"]
    values_page.navigate()
    values_page.add_attribute_values(variant_key, values)
    for value in values:
        cleanup(f"attribute value {value}", lambda value=value: values_page.ensure_deleted(value))

    values_page.navigate()
    for value in values:
        assert values_page.search_attribute_value(value), f"Value {value} should be listed"
        assert variant_key in values_page._row(value).inner_text(), f"Value {value} should belong to {variant_key}"


def test_attribute_value_lifecycle(values_page, variant_key, cleanup):
    value = f"8GB_{generate_random_code('R')}"
    values_page.navigate()
    values_page.add_attribute_value(key_name=variant_key, value=value)
    cleanup(f"attribute value {value}", lambda: values_page.ensure_deleted(value))

    new_value = f"12GB_{generate_random_code('R')}"
    assert values_page.edit_attribute_value(value, new_value)
    cleanup(f"attribute value {new_value}", lambda: values_page.ensure_deleted(new_value))
    assert values_page.search_attribute_value(new_value)

    assert values_page.delete_attribute_value(new_value)
    values_page.navigate()
    assert values_page.is_attribute_value_deleted(new_value), "Deleted value should show the retrieve action"


@pytest.fixture
def existing_value(values_page, variant_key, cleanup):
    value = f"512GB_{generate_random_code('D')}"
    values_page.navigate()
    values_page.add_attribute_value(key_name=variant_key, value=value)
    cleanup(f"attribute value {value}", lambda: values_page.ensure_deleted(value))
    values_page.navigate()
    return value


def test_reject_duplicate_value_for_same_key(values_page, variant_key, existing_value):
    response = values_page.submit_attribute_value(variant_key, existing_value)
    values_page.cancel_dialog()

    assert response.status == 422
    errors = response.json().get("errors", {})
    assert any("already exists" in message for messages in errors.values() for message in messages), errors


@pytest.mark.xfail(
    reason="BUG_002: a duplicate value only shows a generic 'Validation failed' toast, not the reason from the API"
)
def test_duplicate_value_error_explains_reason(values_page, variant_key, existing_value):
    values_page.submit_attribute_value(variant_key, existing_value)
    try:
        values_page.page.get_by_text("already exists", exact=False).first.wait_for(state="visible", timeout=5000)
    finally:
        values_page.cancel_dialog()


def test_attribute_value_is_required(values_page):
    values_page.navigate()
    assert values_page.validate_required_fields()
