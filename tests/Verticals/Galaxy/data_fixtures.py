"""Galaxy data fixtures shared by every Galaxy module. Each creates uniquely named data and registers its cleanup.

Transactions (purchases, sales, vouchers) have no delete in the UI and are intentionally left behind.
Registered as fixtures through tests/Verticals/Galaxy/conftest.py.
"""
import random

import pytest

from pages.main_menu.customers_page import CustomersPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.suppliers_page import SuppliersPage
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.emi_providers_page import EmiProvidersPage
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE
from utils.random_data import generate_random_code, generate_random_name

GALAXY_BRANCH = "galaxy Mobile"


def new_serials(count: int) -> list[str]:
    return [f"SN{random.randint(10**12, 10**13 - 1)}" for _ in range(count)]


@pytest.fixture
def galaxy_city(galaxy_logged_in_page, tenant, cleanup):
    cities_page = CitiesPage(galaxy_logged_in_page, tenant)
    cities_page.navigate()
    name = cities_page.add_city(generate_random_name("GalaxyCity"))
    cleanup(f"city {name}", lambda: cities_page.ensure_deleted(name))
    return name


@pytest.fixture
def galaxy_category(galaxy_logged_in_page, tenant, cleanup):
    categories_page = CategoriesPage(galaxy_logged_in_page, tenant)
    categories_page.navigate()
    name = generate_random_name("galaxy_phones")
    categories_page.add_category(name=name)

    def delete_category():
        categories_page.navigate()
        return categories_page.delete_category(name) if categories_page.is_category_active(name) else True

    cleanup(f"category {name}", delete_category)
    return name


@pytest.fixture
def galaxy_supplier(galaxy_logged_in_page, tenant, galaxy_city, cleanup):
    suppliers_page = SuppliersPage(galaxy_logged_in_page, tenant)
    name = generate_random_name("galaxy_supplier")
    suppliers_page.add_supplier(name=name, city_name=galaxy_city)

    def delete_supplier():
        suppliers_page.navigate()
        return suppliers_page.delete_supplier(name) if suppliers_page.search_supplier(name) else True

    cleanup(f"supplier {name}", delete_supplier)
    return name


@pytest.fixture
def galaxy_serial_product(galaxy_logged_in_page, tenant, galaxy_category, cleanup):
    products_page = ProductsPage(galaxy_logged_in_page, tenant)
    products_page.navigate()
    name = generate_random_name("galaxy_phone")
    response = products_page.add_product(
        name, None, galaxy_category, None, None, "12000", "15000", unit_attribute=GALAXY_TRACKED_ATTRIBUTE,
    )
    assert response is not None and response.status in (200, 201), "Serial-tracked product setup failed"
    cleanup(f"product {name}", lambda: products_page.ensure_deleted(name))
    return name


@pytest.fixture
def galaxy_stock(galaxy_logged_in_page, tenant, galaxy_supplier, galaxy_serial_product):
    """(product, serials, purchase_reference): two units of the serial-tracked product bought into the Galaxy branch."""
    serials = new_serials(2)
    reference = generate_random_code("GLX")
    purchases_page = PurchasesPage(galaxy_logged_in_page, tenant)
    purchases_page.add_purchase(
        galaxy_supplier, GALAXY_BRANCH, reference, "0", "Cash",
        products_data=[{"product": galaxy_serial_product, "price": "12000", "serials": serials}],
    )
    assert purchases_page.last_purchase_response.get("status") in (200, 201), "Stock purchase setup failed"
    return galaxy_serial_product, serials, reference


@pytest.fixture
def galaxy_second_branch(galaxy_logged_in_page, tenant, galaxy_city, cleanup):
    branches_page = BranchesPage(galaxy_logged_in_page, tenant)
    branches_page.navigate()
    name = branches_page.add_branch(city_name=galaxy_city, name=generate_random_name("galaxy_branch"))
    cleanup(f"branch {name}", lambda: branches_page.ensure_deleted(name))
    return name


@pytest.fixture
def galaxy_customer(galaxy_logged_in_page, tenant, galaxy_city, cleanup):
    customers_page = CustomersPage(galaxy_logged_in_page, tenant)
    name = generate_random_name("galaxy_customer")
    customers_page.add_customer(name=name, city_name=galaxy_city)

    def delete_customer():
        customers_page.navigate()
        return customers_page.delete_customer(name) if customers_page.search_customer(name) else True

    cleanup(f"customer {name}", delete_customer)
    return name


@pytest.fixture
def galaxy_emi_provider(galaxy_logged_in_page, tenant, cleanup):
    emi_page = EmiProvidersPage(galaxy_logged_in_page, tenant)
    emi_page.navigate()
    name = generate_random_name("galaxy_emi")
    emi_page.add_emi_provider(name)
    cleanup(f"EMI provider {name}", lambda: emi_page.ensure_deleted(name))
    return name
