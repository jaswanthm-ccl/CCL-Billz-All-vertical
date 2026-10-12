"""Galaxy IMEI lookup: staff find a phone, and the invoice that sold it, by its serial number."""
import pytest
from playwright.sync_api import expect

from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH

PRICE = "15000"

pytestmark = pytest.mark.xfail(reason="BUG_025: Inventory and Sales searches don't match serial numbers (IMEI)")


def test_inventory_search_by_serial_finds_the_phone(galaxy_logged_in_page, tenant, galaxy_stock):
    product, serials, _ = galaxy_stock
    inventories_page = InventoriesPage(galaxy_logged_in_page, tenant)
    inventories_page.navigate()

    assert inventories_page.search_inventory(serials[0]), f"Searching serial {serials[0]} found no inventory row"
    rows = galaxy_logged_in_page.locator("table tbody tr").filter(has_text=serials[0])
    expect(rows.first).to_contain_text(product)


def test_sales_search_by_serial_finds_the_invoice(galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer):
    product, serials, _ = galaxy_stock
    sales_page = SalesPage(galaxy_logged_in_page, tenant)
    sale = sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[serials[0]])

    sales_page.search_sale(serials[0])
    invoice_row = galaxy_logged_in_page.locator("table tbody tr").filter(has_text=sale.invoice_no)
    expect(invoice_row.first, f"Searching sold serial {serials[0]} did not list invoice {sale.invoice_no}").to_be_visible(
        timeout=10000
    )
