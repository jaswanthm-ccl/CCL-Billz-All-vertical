"""Galaxy purchases: every phone bought is recorded against its own serial number.

Purchases have no delete in the UI, so they stay on the tenant (reference prefix GLX-).
"""
import contextlib

import pytest

from pages.main_menu.purchases_page import PurchasesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH, new_serials
from utils.random_data import generate_random_code


@pytest.fixture
def purchases_page(galaxy_logged_in_page, tenant):
    return PurchasesPage(galaxy_logged_in_page, tenant)


def _buy(purchases_page, supplier, product, serials, price="12000"):
    reference = generate_random_code("GLX")
    purchases_page.add_purchase(
        supplier, GALAXY_BRANCH, reference, "0", "Cash",
        products_data=[{"product": product, "price": price, "serials": serials}],
    )
    return reference


def test_purchase_records_each_serial(purchases_page, galaxy_supplier, galaxy_serial_product):
    serials = new_serials(2)
    reference = _buy(purchases_page, galaxy_supplier, galaxy_serial_product, serials)

    record = purchases_page.last_purchase_response
    assert record.get("status") in (200, 201), f"Purchase create failed: {record}"
    item = record["payload"]["items"][0]
    assert item["quantity"] == len(serials)
    assert item["unit_attribute_values"] == serials

    purchases_page.navigate()
    assert purchases_page.search_purchase(reference)
    row_text = purchases_page.page.locator("table tbody tr").filter(has_text=reference).first.inner_text()
    for serial in serials:
        assert serial in row_text, f"Serial {serial} not shown on purchase {reference}"


def test_reject_purchase_of_serial_already_in_stock(purchases_page, galaxy_supplier, galaxy_serial_product):
    serial = new_serials(1)
    _buy(purchases_page, galaxy_supplier, galaxy_serial_product, serial)
    assert purchases_page.last_purchase_response.get("status") in (200, 201)

    with contextlib.suppress(RuntimeError):
        _buy(purchases_page, galaxy_supplier, galaxy_serial_product, serial)

    record = purchases_page.last_purchase_response
    assert record.get("status") == 422, f"Duplicate serial purchase was not rejected: {record}"
    messages = [m for msgs in record["body"].get("errors", {}).values() for m in msgs]
    assert any("must be unique" in m for m in messages), messages
