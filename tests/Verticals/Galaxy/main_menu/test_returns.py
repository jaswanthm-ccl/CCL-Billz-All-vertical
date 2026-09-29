"""Galaxy returns: a returned serial goes back into stock; a serial returned to the supplier leaves it."""
import pytest

from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.purchase_returns_page import PurchaseReturnsPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.sale_returns_page import SaleReturnsPage
from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE

PRICE = "15000"


def _available_serials(page, tenant, product):
    inventories_page = InventoriesPage(page, tenant)
    inventories_page.navigate()
    return sorted(inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE))


@pytest.fixture
def returned_serial(galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer):
    """Sell the first serial, then return it. Yields (product, serials)."""
    product, serials, _ = galaxy_stock
    sales_page = SalesPage(galaxy_logged_in_page, tenant)
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[serials[0]])
    assert sales_page.last_sale_response.get("status") in (200, 201)
    assert _available_serials(galaxy_logged_in_page, tenant, product) == [serials[1]]

    sales_page.navigate()
    sales_page.initiate_sale_return(galaxy_customer)
    response = SaleReturnsPage(galaxy_logged_in_page, tenant).submit_return()
    assert response.status in (200, 201), f"Sale return failed: {response.status} {response.text()[:300]}"
    return product, serials


def test_sale_return_restores_stock_and_serial_can_be_resold(galaxy_logged_in_page, tenant, returned_serial, galaxy_customer):
    product, serials = returned_serial
    inventories_page = InventoriesPage(galaxy_logged_in_page, tenant)
    inventories_page.navigate()
    assert inventories_page.get_total_stock_number(product) == 2
    inventories_page.navigate()
    assert inventories_page.get_available_stock_number(product) == 2

    sales_page = SalesPage(galaxy_logged_in_page, tenant)
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[serials[0]])
    assert sales_page.last_sale_response.get("status") in (200, 201), (
        f"Returned serial {serials[0]} could not be sold again: {sales_page.last_sale_response}"
    )


@pytest.mark.xfail(reason="BUG_011: returned serial is back in stock but not listed under AVAILABLE UNITS")
def test_returned_serial_is_listed_as_available_unit(galaxy_logged_in_page, tenant, returned_serial):
    product, serials = returned_serial
    assert _available_serials(galaxy_logged_in_page, tenant, product) == sorted(serials)


def test_purchase_return_removes_serial_from_stock(galaxy_logged_in_page, tenant, galaxy_stock):
    product, serials, reference = galaxy_stock
    purchases_page = PurchasesPage(galaxy_logged_in_page, tenant)
    purchases_page.navigate()
    purchases_page.initiate_return(reference)
    response = PurchaseReturnsPage(galaxy_logged_in_page, tenant).return_serials([serials[1]])

    assert response.status in (200, 201), f"Purchase return failed: {response.status} {response.text()[:300]}"
    returned_items = (response.request.post_data_json or {}).get("items", [])
    assert returned_items and len(returned_items[0].get("unit_attribute_values") or []) == 1, returned_items
    assert _available_serials(galaxy_logged_in_page, tenant, product) == [serials[0]]
