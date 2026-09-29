"""Galaxy inventory: purchased serials show up as individually available units."""
from decimal import Decimal

from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.purchases_page import PurchasesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH, new_serials
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE
from utils.random_data import generate_random_code


def test_purchased_serials_are_available_units(galaxy_logged_in_page, tenant, galaxy_supplier, galaxy_serial_product):
    serials = new_serials(2)
    purchases_page = PurchasesPage(galaxy_logged_in_page, tenant)
    purchases_page.add_purchase(
        galaxy_supplier, GALAXY_BRANCH, generate_random_code("GLX"), "0", "Cash",
        products_data=[{"product": galaxy_serial_product, "price": "12000", "serials": serials}],
    )
    assert purchases_page.last_purchase_response.get("status") in (200, 201)

    inventories_page = InventoriesPage(galaxy_logged_in_page, tenant)
    inventories_page.navigate()
    assert inventories_page.get_available_stock_number(galaxy_serial_product) == Decimal(len(serials))
    inventories_page.navigate()
    assert sorted(inventories_page.get_available_units(galaxy_serial_product, GALAXY_TRACKED_ATTRIBUTE)) == sorted(serials)
