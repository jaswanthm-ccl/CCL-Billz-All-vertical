"""Restaurant Customers Test Suite."""
import pytest
from utils.random_data import generate_random_name, generate_random_phone
from pages.Verticals.Restaurant.main_menu.customers_page import CustomersPage


@pytest.mark.restaurant
def test_restaurant_customers_lifecycle(res_logged_in_page):
    """Test adding and searching customer in restaurant tenant."""
    page = res_logged_in_page
    cust_page = CustomersPage(page)
    cust_page.navigate()

    name = generate_random_name("auto_cust")
    assert cust_page.add_customer(name=name, mobile=generate_random_phone()), "Failed to add customer"
    assert cust_page.search_customer(name), f"Customer '{name}' was not found in table"
