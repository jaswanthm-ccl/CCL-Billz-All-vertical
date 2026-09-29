"""Restaurant Departments Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.departments_page import DepartmentsPage


@pytest.fixture
def dept_cleanup(res_logged_in_page):
    created_depts = []
    yield created_depts

    page = res_logged_in_page
    dept_page = DepartmentsPage(page)
    dept_page.navigate()
    for name in list(created_depts):
        try:
            if dept_page.delete_department(name):
                created_depts.remove(name)
        except Exception as e:
            print(f"Teardown: could not delete department {name}: {e}")


@pytest.mark.restaurant
def test_department_crud_lifecycle(res_logged_in_page, dept_cleanup):
    """Test creating, searching, editing, and soft-deleting a restaurant department."""
    page = res_logged_in_page
    dept_page = DepartmentsPage(page)
    dept_page.navigate()

    name = generate_random_name("auto_dept")
    new_name = generate_random_name("auto_dept_edit")
    dept_cleanup.append(name)

    assert dept_page.add_department(name, "Automated test department"), "Failed to add department"
    assert dept_page.search_department(name), f"Department '{name}' was not found in table"

    assert dept_page.edit_department(name, new_name), f"Failed to edit department '{name}'"
    dept_cleanup.remove(name)
    dept_cleanup.append(new_name)
    assert dept_page.search_department(new_name), f"Edited department '{new_name}' was not found in table"

    assert dept_page.delete_department(new_name), f"Failed to delete department '{new_name}'"
    dept_cleanup.remove(new_name)
