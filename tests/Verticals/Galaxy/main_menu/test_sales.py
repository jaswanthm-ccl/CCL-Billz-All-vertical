"""Galaxy sales: a phone is sold by its serial number, optionally on EMI.

Sales have no delete in the UI, so they stay on the tenant.
"""
import contextlib

import pytest

from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE

PRICE = "15000"


@pytest.fixture
def sales_page(galaxy_logged_in_page, tenant):
    return SalesPage(galaxy_logged_in_page, tenant)


def _available_serials(page, tenant, product):
    inventories_page = InventoriesPage(page, tenant)
    inventories_page.navigate()
    return sorted(inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE))


def test_sell_one_serial_leaves_the_other_available(sales_page, galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer):
    product, serials, _ = galaxy_stock
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[serials[0]])

    record = sales_page.last_sale_response
    assert record.get("status") in (200, 201), f"Sale create failed: {record}"
    item = record["payload"]["items"][0]
    assert item["quantity"] == 1
    assert len(item["unit_attribute_values"]) == 1

    assert _available_serials(galaxy_logged_in_page, tenant, product) == [serials[1]]


def test_emi_sale_of_a_serial(sales_page, galaxy_stock, galaxy_customer, galaxy_emi_provider):
    product, serials, _ = galaxy_stock
    result = sales_page.add_sale(
        galaxy_customer, GALAXY_BRANCH, "5000", PRICE, product_name=product, serials=[serials[0]],
        is_emi=True, emi_provider_name=galaxy_emi_provider, emi_financed_amount="10000",
    )

    record = sales_page.last_sale_response
    assert record.get("status") in (200, 201), f"EMI sale create failed: {record}"
    details = sales_page.view_sale_by_invoice(result.invoice_no)
    assert details["has_emi_outstanding"], f"EMI outstanding not shown on sale {result.invoice_no}"


def test_sold_serial_cannot_be_sold_again(sales_page, galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer):
    product, serials, _ = galaxy_stock
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[serials[0]])
    assert sales_page.last_sale_response.get("status") in (200, 201)

    with contextlib.suppress(Exception):
        sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[serials[0]])

    second = sales_page.last_sale_response
    assert second.get("status") not in (200, 201), f"Already-sold serial {serials[0]} was sold again: {second}"
    assert _available_serials(galaxy_logged_in_page, tenant, product) == [serials[1]]
