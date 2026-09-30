"""Galaxy end-to-end: a phone bought by serial is sold for cash, and every book reflects it.

1. Two serial-tracked phones are purchased into the Galaxy branch (galaxy_stock fixture).
2. Baselines for today on the Galaxy branch: P&L income, branch cash balance and Day Book vouchers.
3. One serial is sold for cash, fully paid.
4. Inventory no longer lists the sold serial; the other one is still available.
5. Day Book has a new balanced Sales Voucher for the sale amount.
6. The customer ledger closes at zero (fully paid) and branch cash rises by the sale amount.
7. P&L income for the branch rises by exactly the sale amount.

Marked serial (see conftest SERIAL_MODULES): steps 6 and 7 compare branch-wide totals.
"""
from datetime import date
from decimal import Decimal

import pytest

from pages.accounting.day_book_page import DayBookPage
from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.accounting.profit_loss_page import ProfitLossPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE

pytestmark = pytest.mark.regression

PRICE = Decimal("15000")
CASH_LEDGER = f"Cash Ledger — {GALAXY_BRANCH}"


def test_cash_sale_of_a_serial_updates_stock_and_books(galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer):
    page = galaxy_logged_in_page
    product, serials, _ = galaxy_stock
    sold, kept = serials
    today = date.today().isoformat()

    # 2. Baselines
    profit_loss_page = ProfitLossPage(page, tenant)
    profit_loss_page.navigate()
    profit_loss_page.apply_filters(from_date=today, to_date=today, branch=GALAXY_BRANCH)
    income_before = profit_loss_page.summary_amount("Total Income")

    ledger_page = LedgerStatementPage(page, tenant)
    ledger_page.navigate()
    ledger_page.filter_statement(CASH_LEDGER, GALAXY_BRANCH)
    cash_before = LedgerStatementPage.parse_signed_balance(ledger_page.get_closing_balance())

    day_book_page = DayBookPage(page, tenant)
    day_book_page.navigate()
    day_book_page.run_report(today, today)
    vouchers_before = {row["voucher_no"] for row in day_book_page.get_all_rows_data()}

    # 3. Cash sale of one serial, fully paid
    sales_page = SalesPage(page, tenant)
    sale = sales_page.add_sale(
        galaxy_customer, GALAXY_BRANCH, str(PRICE), str(PRICE), product_name=product, serials=[sold],
    )
    assert sales_page.last_sale_response.get("status") in (200, 201), f"Cash sale failed: {sales_page.last_sale_response}"

    # 4. Stock
    inventories_page = InventoriesPage(page, tenant)
    inventories_page.navigate()
    assert inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE) == [kept]

    # 5. Day Book
    day_book_page.navigate()
    day_book_page.run_report(today, today)
    new_sales_vouchers = [
        row for row in day_book_page.get_all_rows_data()
        if row["voucher_no"] not in vouchers_before and row["type"] == "Sales Voucher"
    ]
    assert any(row["debit"] == PRICE and row["credit"] == PRICE for row in new_sales_vouchers), (
        f"Day Book has no new balanced Sales Voucher of {PRICE} for invoice {sale.invoice_no}: {new_sales_vouchers}"
    )

    # 6. Customer and cash ledgers
    ledger_page.navigate()
    ledger_page.filter_statement(galaxy_customer, GALAXY_BRANCH)
    customer_closing = LedgerStatementPage.parse_signed_balance(ledger_page.get_closing_balance())
    assert customer_closing == Decimal("0"), f"Fully paid sale left a customer balance of {customer_closing}"

    ledger_page.navigate()
    ledger_page.filter_statement(CASH_LEDGER, GALAXY_BRANCH)
    cash_after = LedgerStatementPage.parse_signed_balance(ledger_page.get_closing_balance())
    assert cash_after - cash_before == PRICE, f"Branch cash moved by {cash_after - cash_before}, expected {PRICE}"

    # 7. P&L income
    profit_loss_page.navigate()
    profit_loss_page.apply_filters(from_date=today, to_date=today, branch=GALAXY_BRANCH)
    income_after = profit_loss_page.summary_amount("Total Income")
    assert income_after - income_before == PRICE, (
        f"P&L income moved by {income_after - income_before}, expected {PRICE}"
    )
