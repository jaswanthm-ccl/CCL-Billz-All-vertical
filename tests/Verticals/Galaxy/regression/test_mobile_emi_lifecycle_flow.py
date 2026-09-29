"""Galaxy end-to-end: buy phones by serial, sell one on EMI, then settle the EMI with the provider.

1. Two serial-tracked phones are purchased into the Galaxy branch (galaxy_stock fixture).
2. One serial is sold on EMI: cash down payment, the rest financed by the EMI provider.
3. Inventory no longer lists the sold serial.
4. The provider's Receivable ledger is debited with the financed amount.
5. EMI reconciliation shows the financed amount as fully outstanding.
6. A Receipt Voucher settles the financed amount from the provider.
7. EMI reconciliation shows it settled with nothing outstanding; the receivable closes at zero.
"""
from decimal import Decimal

import pytest

from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.sales_page import SalesPage
from pages.report.emi_reconciliation_page import EmiReconciliationPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE

pytestmark = pytest.mark.regression

PRICE = "15000"
DOWN_PAYMENT = "5000"
FINANCED = Decimal("10000")


def test_buy_sell_on_emi_and_settle_with_provider(
    galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer, galaxy_emi_provider
):
    page = galaxy_logged_in_page
    product, serials, _ = galaxy_stock
    sold, kept = serials
    receivable = f"{galaxy_emi_provider} Receivable"

    # 2. Sell one serial on EMI
    sales_page = SalesPage(page, tenant)
    sales_page.add_sale(
        galaxy_customer, GALAXY_BRANCH, DOWN_PAYMENT, PRICE, product_name=product, serials=[sold],
        is_emi=True, emi_provider_name=galaxy_emi_provider, emi_financed_amount=str(FINANCED),
    )
    assert sales_page.last_sale_response.get("status") in (200, 201), f"EMI sale failed: {sales_page.last_sale_response}"

    # 3. Sold serial leaves stock
    inventories_page = InventoriesPage(page, tenant)
    inventories_page.navigate()
    assert inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE) == [kept]

    # 4. Provider receivable is debited with the financed amount
    ledger_page = LedgerStatementPage(page, tenant)
    ledger_page.navigate()
    ledger_page.filter_statement(receivable, GALAXY_BRANCH)
    assert LedgerStatementPage.parse_signed_balance(ledger_page.get_total_debits()) == FINANCED

    # 5. Reconciliation: financed and fully outstanding
    recon_page = EmiReconciliationPage(page, tenant)
    recon_page.navigate()
    assert recon_page.search_provider(galaxy_emi_provider)
    before = recon_page.get_provider_reconciliation_row(galaxy_emi_provider)
    assert (before["total_financed"], before["total_settled"], before["total_outstanding"]) == (
        FINANCED, Decimal("0"), FINANCED,
    ), before

    # 6. Settle the financed amount with a Receipt Voucher from the provider
    receipt = CreateVoucherPage(page, tenant).create_receipt_voucher(
        customer_ledger=receivable,
        cash_bank_ledger=f"Cash Ledger — {GALAXY_BRANCH}",
        amount=str(FINANCED),
        branch=GALAXY_BRANCH,
        remarks=f"EMI settlement for {galaxy_emi_provider}",
    )
    assert receipt.amount == FINANCED, f"Receipt voucher amount {receipt.amount}, expected {FINANCED}"

    # 7. Reconciliation: settled, nothing outstanding; receivable closes at zero
    recon_page.navigate()
    assert recon_page.search_provider(galaxy_emi_provider)
    after = recon_page.get_provider_reconciliation_row(galaxy_emi_provider)
    assert (after["total_settled"], after["total_outstanding"]) == (FINANCED, Decimal("0")), after

    ledger_page.navigate()
    ledger_page.filter_statement(receivable, GALAXY_BRANCH)
    assert LedgerStatementPage.parse_signed_balance(ledger_page.get_closing_balance()) == Decimal("0")
