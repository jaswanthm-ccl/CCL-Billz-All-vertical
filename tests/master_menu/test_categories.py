import pytest
from pages.master_menu.categories_page import DELETE_ICON_BUTTON, CategoriesPage
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def category_cleanup(logged_in_page):
    created_categories = []
    yield created_categories

    categories_page = CategoriesPage(logged_in_page)
    for name in created_categories:
        try:
            categories_page.navigate()
            if categories_page.is_category_active(name):
                categories_page.delete_category(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete category {name}: {exc}")


def test_category_crud_lifecycle(logged_in_page, category_cleanup):
    categories_page = CategoriesPage(logged_in_page)
    categories_page.navigate()

    # 1. Create with description and sort order
    category_name = generate_random_name("auto_cat")
    description = generate_random_description("description")
    sort_order = "5"
    categories_page.add_category(
        name=category_name, sort_order=sort_order, description=description
    )
    category_cleanup.append(category_name)
    assert categories_page.search_category(category_name)

    # 2. View Original Details
    assert categories_page.view_category(
        category_name,
        expected_description=description,
        expected_sort_order=sort_order,
    )

    # 3. Edit (Name, Description, Sort Order)
    new_name = generate_random_name("updated_cat")
    new_description = generate_random_description("updated_desc")
    new_sort_order = "9"
    assert categories_page.edit_category(
        category_name,
        new_name,
        new_sort_order=new_sort_order,
        new_description=new_description,
    )
    category_cleanup.remove(category_name)
    category_cleanup.append(new_name)
    assert categories_page.search_category(new_name)

    # 4. View Edited Details
    assert categories_page.view_category(
        new_name,
        expected_description=new_description,
        expected_sort_order=new_sort_order,
    )

    # 5. Delete (Soft delete)
    assert categories_page.delete_category(new_name)

    # 6. Retrieve / Restore
    assert categories_page.retrieve_category(new_name)
    assert categories_page.search_category(new_name)


def test_validate_required_fields(logged_in_page):
    categories_page = CategoriesPage(logged_in_page)
    categories_page.navigate()
    assert categories_page.validate_required_fields(), (
        "Category Name must be required without submitting the network API"
    )


def test_duplicate_category_name(logged_in_page, category_cleanup):
    categories_page = CategoriesPage(logged_in_page)
    categories_page.navigate()

    category_name = generate_random_name("dup_cat")
    categories_page.add_category(name=category_name)
    category_cleanup.append(category_name)

    assert categories_page.validate_duplicate_category(category_name), (
        "Expected UI validation feedback and HTTP 422 for duplicate category name"
    )
