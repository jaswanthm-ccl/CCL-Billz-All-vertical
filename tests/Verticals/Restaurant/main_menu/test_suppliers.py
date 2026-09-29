"""Restaurant Suppliers Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.suppliers_page import SuppliersPage


@pytest.mark.restaurant
def test_restaurant_supplier_crud_lifecycle(res_logged_in_page):
    """Test creating, searching, and deleting a restaurant supplier."""
    page = res_logged_in_page
    supp_page = SuppliersPage(page)
    supp_page.navigate()

    name = generate_random_name("auto_supp")
    assert supp_page.add_supplier(name=name, mobile="9876543210"), "Failed to add supplier"
    assert supp_page.search_supplier(name), f"Supplier '{name}' was not found in table"
    assert supp_page.delete_supplier(name), f"Failed to delete supplier '{name}'"
