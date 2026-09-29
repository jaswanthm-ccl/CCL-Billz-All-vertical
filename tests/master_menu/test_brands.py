import pytest
from pages.master_menu.brands_page import BrandsPage
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def brand_cleanup(logged_in_page):
    created_brands = []
    yield created_brands

    brands_page = BrandsPage(logged_in_page)
    for name in reversed(created_brands):
        try:
            brands_page.navigate()
            if brands_page.is_brand_active(name):
                brands_page.delete_brand(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete brand {name}: {exc}")


def test_brand_crud_lifecycle(logged_in_page, brand_cleanup):
    brands_page = BrandsPage(logged_in_page)
    brands_page.navigate()

    # 1. Create with description
    brand_name = generate_random_name("auto_brand")
    description = generate_random_description("description")
    brands_page.add_brand(brand_name, description)
    brand_cleanup.append(brand_name)
    assert brands_page.search_brand(brand_name)

    # 2. View Original Details
    assert brands_page.view_brand(brand_name, expected_description=description)

    # 3. Edit (Name & Description)
    new_name = generate_random_name("updated_brand")
    new_description = generate_random_description("updated_desc")
    assert brands_page.edit_brand(
        brand_name, new_name, new_description=new_description
    )
    brand_cleanup.remove(brand_name)
    brand_cleanup.append(new_name)
    assert brands_page.search_brand(new_name)

    # 4. View Edited Details
    assert brands_page.view_brand(new_name, expected_description=new_description)

    # 5. Delete (Soft delete)
    assert brands_page.delete_brand(new_name)

    # 6. Retrieve / Restore
    assert brands_page.retrieve_brand(new_name)
    assert brands_page.search_brand(new_name)


def test_validate_required_fields(logged_in_page):
    brands_page = BrandsPage(logged_in_page)
    brands_page.navigate()
    assert brands_page.validate_required_fields(), (
        "Brand Name must be required without submitting the network API"
    )


def test_reject_blank_only_brand_name(logged_in_page):
    brands_page = BrandsPage(logged_in_page)
    brands_page.navigate()
    assert brands_page.validate_blank_only_name(), (
        "Expected visible validation feedback for a blank-only brand name"
    )


def test_duplicate_brand_name(logged_in_page, brand_cleanup):
    brands_page = BrandsPage(logged_in_page)
    brands_page.navigate()

    brand_name = generate_random_name("dup_brand")
    description = generate_random_description("description")
    brands_page.add_brand(brand_name, description)
    brand_cleanup.append(brand_name)

    assert brands_page.validate_duplicate_brand(brand_name, description), (
        "Expected UI validation feedback and HTTP 422 for duplicate brand name"
    )
