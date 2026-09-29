import pytest

from pages.master_menu.expense_categories_page import ExpenseCategoriesPage
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def expense_category_cleanup(logged_in_page):
    created_categories: list[str] = []
    yield created_categories
    page_obj = ExpenseCategoriesPage(logged_in_page)
    for name in reversed(created_categories):
        try:
            page_obj.navigate()
            if page_obj.is_category_active(name):
                page_obj.delete_expense_category(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete expense category {name}: {exc}")


def test_expense_category_crud_lifecycle(
    logged_in_page, expense_category_cleanup
):
    page_obj = ExpenseCategoriesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.is_expense_categories_visible()

    name = generate_random_name("auto_expense")
    description = generate_random_description("expense_description")
    response = page_obj.add_expense_category(
        name, description=description, sort_order=5
    )
    assert response.status in {200, 201}
    expense_category_cleanup.append(name)
    assert page_obj.search_expense_category(name)

    new_name = generate_random_name("updated_expense")
    new_description = generate_random_description("updated_description")
    assert page_obj.edit_expense_category(
        name, new_name, description=new_description, sort_order=9
    )
    expense_category_cleanup.remove(name)
    expense_category_cleanup.append(new_name)

    assert page_obj.get_edit_values(new_name) == {
        "name": new_name,
        "description": new_description,
        "sort_order": "9",
    }
    assert page_obj.delete_expense_category(new_name)
    assert page_obj.retrieve_expense_category(new_name)
    assert page_obj.search_expense_category(new_name)


@pytest.mark.xfail(
    reason="Known defect: Expense Categories has no View action"
)
def test_expense_category_view_action(
    logged_in_page, expense_category_cleanup
):
    page_obj = ExpenseCategoriesPage(logged_in_page)
    page_obj.navigate()
    name = generate_random_name("view_expense")
    response = page_obj.add_expense_category(name)
    assert response.status in {200, 201}
    expense_category_cleanup.append(name)
    assert page_obj.has_view_action(name)


def test_expense_category_required_name(logged_in_page):
    page_obj = ExpenseCategoriesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_name(), (
        "Category Name must be required and client validation must block the API"
    )


def test_reject_duplicate_expense_category(
    logged_in_page, expense_category_cleanup
):
    page_obj = ExpenseCategoriesPage(logged_in_page)
    page_obj.navigate()
    name = generate_random_name("duplicate_expense")
    response = page_obj.add_expense_category(name)
    assert response.status in {200, 201}
    expense_category_cleanup.append(name)
    assert page_obj.validate_duplicate_category(name), (
        "Expected UI feedback and HTTP rejection for a duplicate category"
    )
