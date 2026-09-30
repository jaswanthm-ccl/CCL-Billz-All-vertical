"""Galaxy end-to-end: a phone is returned to the supplier by serial, and stock and books follow.

1. Two serial-tracked phones are bought on credit into the Galaxy branch (galaxy_stock fixture): supplier is owed 2 x 12,000.
2. One serial is returned to the supplier from the purchase.
3. Inventory lists only the kept serial.
4. The supplier ledger drops to the value of the phone that was kept.
5. Day Book has a new balanced return voucher for the returned phone.
"""
from datetime import date
from decimal import Decimal

import pytest

from pages.accounting.day_book_page import DayBookPage
from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.purchase_returns_page import PurchaseReturnsPage
from pages.main_menu.purchases_page import PurchasesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE

pytestmark = pytest.mark.regression

COST = Decimal("12000")


def test_purchase_return_of_a_serial_updates_stock_supplier_and_day_book(
    galaxy_logged_in_page, tenant, galaxy_stock, galaxy_supplier
):
    page = galaxy_logged_in_page
    product, serials, reference = galaxy_stock
    kept, returned = serials
    today = date.today().isoformat()

    ledger_page = LedgerStatementPage(page, tenant)
    ledger_page.navigate()
    ledger_page.filter_statement(galaxy_supplier, GALAXY_BRANCH)
    owed_before = abs(LedgerStatementPage.parse_signed_balance(ledger_page.get_closing_balance()))
    assert owed_before == 2 * COST, f"Supplier should be owed {2 * COST} after the purchase, got {owed_before}"

    day_book_page = DayBookPage(page, tenant)
    day_book_page.navigate()
    day_book_page.run_report(today, today)
    vouchers_before = {row["voucher_no"] for row in day_book_page.get_all_rows_data()}

    # 2. Return one serial to the supplier
    purchases_page = PurchasesPage(page, tenant)
    purchases_page.navigate()
    purchases_page.initiate_return(reference)
    response = PurchaseReturnsPage(page, tenant).return_serials([returned])
    assert response.ok, f"Purchase return failed: {response.status} {response.text()[:300]}"

    # 3. Stock
    inventories_page = InventoriesPage(page, tenant)
    inventories_page.navigate()
    assert inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE) == [kept]

    # 4. Supplier ledger
    ledger_page.navigate()
    ledger_page.filter_statement(galaxy_supplier, GALAXY_BRANCH)
    owed_after = abs(LedgerStatementPage.parse_signed_balance(ledger_page.get_closing_balance()))
    assert owed_after == COST, f"Supplier should be owed {COST} after returning one phone, got {owed_after}"

    # 5. Day Book
    day_book_page.navigate()
    day_book_page.run_report(today, today)
    new_rows = [row for row in day_book_page.get_all_rows_data() if row["voucher_no"] not in vouchers_before]
    assert any(
        "return" in str(row["type"]).lower() and row["debit"] == COST and row["credit"] == COST for row in new_rows
    ), f"Day Book has no new balanced return voucher of {COST}: {new_rows}"
