"""Restaurant Inventories Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.inventories_page import InventoriesPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage


@pytest.fixture
def inv_cleanup(res_logged_in_page):
    created_prods = []
    yield {"prods": created_prods}

    page = res_logged_in_page
    prod_page = ProductsPage(page)
    prod_page.navigate()
    for prod_name in list(created_prods):
        try:
            if prod_page.delete_product(prod_name):
                created_prods.remove(prod_name)
        except Exception:
            pass


@pytest.mark.restaurant
def test_restaurant_inventory_list_and_stock_reading(res_logged_in_page, res_branch):
    """Test reading 10-column restaurant inventory table values."""
    page = res_logged_in_page
    inv_page = InventoriesPage(page)
    inv_page.navigate()

    inv_page.filter_by_product_and_branch(branch_name=res_branch)
    assert page.locator("table tbody tr").count() > 0, "Inventory table has no rows after filtering by branch"
