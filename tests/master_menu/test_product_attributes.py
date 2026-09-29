import pytest
from pages.master_menu.product_attributes_page import ProductAttributesPage
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def product_attr_cleanup(logged_in_page):
    created_attrs = []
    yield created_attrs
    attr_page = ProductAttributesPage(logged_in_page)
    for name in reversed(created_attrs):
        try:
            attr_page.navigate()
            if attr_page.search_product_attribute(name):
                row = attr_page.page.locator("tr", has=attr_page.page.get_by_text(name, exact=True))
                if row.get_by_title("delete").first.is_visible():
                    attr_page.delete_product_attribute(name)
                else:
                    attr_page.delete_attribute_by_api(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete product attribute {name}: {exc}")


def test_product_attribute_crud_lifecycle(logged_in_page, product_attr_cleanup):
    page_obj = ProductAttributesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.is_product_attributes_visible()

    # 1. Create
    attr_name = generate_random_name("auto_attr")
    description = generate_random_description("attr_desc")
    page_obj.add_product_attribute(name=attr_name, unique=True, description=description)
    product_attr_cleanup.append(attr_name)

    # 2. Search
    assert page_obj.search_product_attribute(attr_name)


def test_validate_product_attribute(logged_in_page):
    page_obj = ProductAttributesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_fields()


def test_reject_overlength_product_attribute_name(logged_in_page):
    page_obj = ProductAttributesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_name_too_long("A" * 256), (
        "Expected visible validation feedback for an overlength attribute name"
    )


def test_reject_duplicate_product_attribute_name(logged_in_page, product_attr_cleanup):
    page_obj = ProductAttributesPage(logged_in_page)
    page_obj.navigate()

    attr_name = generate_random_name("dup_attr")
    page_obj.add_product_attribute(name=attr_name)
    product_attr_cleanup.append(attr_name)

    assert page_obj.validate_duplicate_name(attr_name), (
        "Expected HTTP failure (400/409/422) or UI validation feedback for duplicate attribute name"
    )
@pytest.mark.xfail(
    reason="Known UI gap: Product Attribute rows currently have no view, edit, or delete action buttons"
)
def test_product_attribute_row_actions_are_available(
    logged_in_page, product_attr_cleanup
):
    page_obj = ProductAttributesPage(logged_in_page)
    page_obj.navigate()
    attribute_name = generate_random_name("attribute_actions")
    page_obj.add_product_attribute(name=attribute_name)
    product_attr_cleanup.append(attribute_name)
    assert page_obj.has_row_actions(attribute_name), (
        "Expected view, edit, and delete actions for the Product Attribute row"
    )
