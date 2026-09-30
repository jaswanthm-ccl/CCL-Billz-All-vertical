"""Galaxy purchases: every phone bought is recorded against its own serial number.

Purchases have no delete in the UI, so they stay on the tenant (reference prefix GLX-).
"""
import contextlib

import pytest

from pages.main_menu.products_page import ProductsPage
from pages.main_menu.purchases_page import PurchasesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH, new_serials
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE
from utils.random_data import generate_random_code, generate_random_name


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

    _assert_rejected_as_duplicate(purchases_page.last_purchase_response)


def test_reject_same_serial_twice_in_one_purchase(purchases_page, galaxy_supplier, galaxy_serial_product):
    serial = new_serials(1)[0]
    reference = generate_random_code("GLX")
    with contextlib.suppress(RuntimeError):
        purchases_page.add_purchase(
            galaxy_supplier, GALAXY_BRANCH, reference, "0", "Cash",
            products_data=[{"product": galaxy_serial_product, "price": "12000", "serials": [serial, serial]}],
        )

    record = purchases_page.last_purchase_response
    if record:
        _assert_rejected_as_duplicate(record)
    purchases_page.navigate()
    assert not purchases_page.search_purchase(reference), f"Purchase {reference} with a repeated serial was created"


def test_reject_serial_already_used_by_another_product(
    purchases_page, galaxy_logged_in_page, tenant, galaxy_supplier, galaxy_serial_product, galaxy_category, cleanup
):
    serial = new_serials(1)
    _buy(purchases_page, galaxy_supplier, galaxy_serial_product, serial)
    assert purchases_page.last_purchase_response.get("status") in (200, 201)

    products_page = ProductsPage(galaxy_logged_in_page, tenant)
    products_page.navigate()
    other_product = generate_random_name("galaxy_phone")
    response = products_page.add_product(
        other_product, None, galaxy_category, None, None, "12000", "15000", unit_attribute=GALAXY_TRACKED_ATTRIBUTE,
    )
    assert response is not None and response.ok, "Second serial-tracked product setup failed"
    cleanup(f"product {other_product}", lambda: products_page.ensure_deleted(other_product))

    with contextlib.suppress(RuntimeError):
        _buy(purchases_page, galaxy_supplier, other_product, serial)

    _assert_rejected_as_duplicate(purchases_page.last_purchase_response)


def _assert_rejected_as_duplicate(record):
    assert record.get("status") == 422, f"Duplicate serial purchase was not rejected: {record}"
    messages = [m for msgs in record["body"].get("errors", {}).values() for m in msgs]
    assert any("unique" in m.lower() or "duplicate" in m.lower() for m in messages), messages
