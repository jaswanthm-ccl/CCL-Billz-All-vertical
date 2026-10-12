"""Galaxy end-to-end: a sold phone comes back from the customer and the same serial is sold again.

1. Two serial-tracked phones are purchased into the Galaxy branch (galaxy_stock fixture).
2. Serial A is sold for cash.
3. The customer returns serial A: stock goes back to 2.
4. Serial A is sold again; serial B is then the only unit left.
5. Day Book has the first sale, the return and the resale, each balanced at the phone's price.
"""
from datetime import date
from decimal import Decimal

import pytest

from pages.accounting.day_book_page import DayBookPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.sale_returns_page import SaleReturnsPage
from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE

pytestmark = pytest.mark.regression

PRICE = Decimal("15000")


def test_returned_serial_is_resold_and_every_step_is_booked(galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer):
    page = galaxy_logged_in_page
    product, serials, _ = galaxy_stock
    serial_a, serial_b = serials
    today = date.today().isoformat()

    day_book_page = DayBookPage(page, tenant)
    day_book_page.navigate()
    day_book_page.run_report(today, today)
    vouchers_before = {row["voucher_no"] for row in day_book_page.get_all_rows_data()}

    sales_page = SalesPage(page, tenant)
    inventories_page = InventoriesPage(page, tenant)

    # 2. First sale
    first_sale = sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, str(PRICE), str(PRICE), product_name=product, serials=[serial_a])
    assert sales_page.last_sale_response.get("status") in (200, 201), f"First sale failed: {sales_page.last_sale_response}"
    assert first_sale.sale_id and first_sale.invoice_no, "First sale response is missing its identity"

    # 3. Customer returns serial A
    sales_page.navigate()
    sales_page.initiate_sale_return(first_sale.invoice_no)
    response = SaleReturnsPage(page, tenant).submit_return()
    assert response.ok, f"Sale return failed: {response.status} {response.text()[:300]}"
    assert str(response.request.post_data_json["sale_id"]) == first_sale.sale_id
    # Return creation has no data payload; retrieve the return by its exact source sale.
    return_list = page.request.get(
        response.url,
        params={"sale_id": first_sale.sale_id, "per_page": 100},
        headers={
            key: value for key, value in response.request.all_headers().items()
            if key.lower() not in {"content-length", "content-type"}
        },
    )
    assert return_list.ok, (
        f"Could not retrieve the created return: {return_list.status} {return_list.text()[:500]}"
    )
    returns = return_list.json()["data"]["data"]
    assert len(returns) == 1, f"Expected one return for sale {first_sale.sale_id}, got {returns}"
    created_return = returns[0]
    assert str(created_return["sale_id"]) == first_sale.sale_id
    return_id = created_return["id"]
    assert return_id, "Created return is missing its ID"

    inventories_page.navigate()
    assert inventories_page.get_total_stock_number(product) == 2
    inventories_page.navigate()
    assert inventories_page.get_available_stock_number(product) == 2

    # 4. Resell serial A
    resale = sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, str(PRICE), str(PRICE), product_name=product, serials=[serial_a])
    assert sales_page.last_sale_response.get("status") in (200, 201), (
        f"Returned serial {serial_a} could not be sold again: {sales_page.last_sale_response}"
    )
    assert resale.sale_id and resale.invoice_no, "Resale response is missing its identity"
    assert resale.sale_id != first_sale.sale_id and resale.invoice_no != first_sale.invoice_no
    inventories_page.navigate()
    assert inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE) == [serial_b]

    # 5. Day Book
    day_book_page.navigate()
    day_book_page.run_report(today, today)
    rows = day_book_page.get_all_rows_data()
    expected = (
        (f"Sale entry for Sale #{first_sale.sale_id}", "Sales Voucher"),
        (f"Sales Return #{return_id}", "Sales Return Voucher"),
        (f"Sale entry for Sale #{resale.sale_id}", "Sales Voucher"),
    )
    for narration, voucher_type in expected:
        matches = [row for row in rows if row["narration"] == narration]
        assert len(matches) == 1, f"Expected exactly one Day Book entry for {narration}, got {matches}"
        row = matches[0]
        assert row["voucher_no"] not in vouchers_before, f"Historical voucher matched {narration}"
        assert row["type"] == voucher_type, f"Wrong voucher type for {narration}: {row}"
        assert row["debit"] == row["credit"] == PRICE, f"Incorrect accounting for {narration}: {row}"
