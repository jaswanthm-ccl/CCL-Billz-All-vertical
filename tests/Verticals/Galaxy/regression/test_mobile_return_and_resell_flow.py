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
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, str(PRICE), str(PRICE), product_name=product, serials=[serial_a])
    assert sales_page.last_sale_response.get("status") in (200, 201), f"First sale failed: {sales_page.last_sale_response}"

    # 3. Customer returns serial A
    sales_page.navigate()
    sales_page.initiate_sale_return(galaxy_customer)
    response = SaleReturnsPage(page, tenant).submit_return()
    assert response.ok, f"Sale return failed: {response.status} {response.text()[:300]}"

    inventories_page.navigate()
    assert inventories_page.get_total_stock_number(product) == 2
    inventories_page.navigate()
    assert inventories_page.get_available_stock_number(product) == 2

    # 4. Resell serial A
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, str(PRICE), str(PRICE), product_name=product, serials=[serial_a])
    assert sales_page.last_sale_response.get("status") in (200, 201), (
        f"Returned serial {serial_a} could not be sold again: {sales_page.last_sale_response}"
    )
    inventories_page.navigate()
    assert inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE) == [serial_b]

    # 5. Day Book
    day_book_page.navigate()
    day_book_page.run_report(today, today)
    new_rows = [
        row for row in day_book_page.get_all_rows_data()
        if row["voucher_no"] not in vouchers_before and row["debit"] == PRICE and row["credit"] == PRICE
    ]
    types = [str(row["type"]) for row in new_rows]
    assert types.count("Sales Voucher") >= 2, f"Expected the sale and the resale in Day Book, got {types}"
    assert any("return" in t.lower() for t in types), f"Expected the sale return in Day Book, got {types}"
