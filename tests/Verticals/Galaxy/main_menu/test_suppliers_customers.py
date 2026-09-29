"""Galaxy suppliers and customers: smoke only, retail covers the deep cases."""
import pytest

from pages.main_menu.customers_page import CustomersPage
from pages.main_menu.suppliers_page import SuppliersPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.smoke

ACTIVE_DELETE_ICON = 'button[title="delete"]:has(i.bi-trash)'


def _ensure_deleted(page_obj, name: str, search: str, delete: str) -> bool:
    page_obj.navigate()
    if not getattr(page_obj, search)(name):
        return True
    row = page_obj.page.locator("table tbody tr").filter(has=page_obj.page.get_by_text(name, exact=True)).first
    if row.locator(ACTIVE_DELETE_ICON).count() == 0:
        return True
    return getattr(page_obj, delete)(name)


def test_supplier_create_search_delete(galaxy_logged_in_page, tenant, galaxy_city, cleanup):
    suppliers_page = SuppliersPage(galaxy_logged_in_page, tenant)
    name = generate_random_name("galaxy_supplier")
    suppliers_page.add_supplier(name=name, city_name=galaxy_city)
    cleanup(f"supplier {name}", lambda: _ensure_deleted(suppliers_page, name, "search_supplier", "delete_supplier"))

    suppliers_page.navigate()
    assert suppliers_page.search_supplier(name)
    assert suppliers_page.delete_supplier(name)


def test_customer_create_search_delete(galaxy_logged_in_page, tenant, galaxy_city, cleanup):
    customers_page = CustomersPage(galaxy_logged_in_page, tenant)
    name = generate_random_name("galaxy_customer")
    customers_page.add_customer(name=name, city_name=galaxy_city)
    cleanup(f"customer {name}", lambda: _ensure_deleted(customers_page, name, "search_customer", "delete_customer"))

    customers_page.navigate()
    assert customers_page.search_customer(name)
    assert customers_page.delete_customer(name)
