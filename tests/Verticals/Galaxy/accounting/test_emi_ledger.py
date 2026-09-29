"""Galaxy accounting for EMI sales: the financed part is owed by the EMI provider, not the customer."""
from decimal import Decimal

from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH

PRICE = "15000"
DOWN_PAYMENT = "5000"
FINANCED = "10000"


def test_emi_sale_debits_provider_receivable(galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer, galaxy_emi_provider):
    product, serials, _ = galaxy_stock
    sales_page = SalesPage(galaxy_logged_in_page, tenant)
    sales_page.add_sale(
        galaxy_customer, GALAXY_BRANCH, DOWN_PAYMENT, PRICE, product_name=product, serials=[serials[0]],
        is_emi=True, emi_provider_name=galaxy_emi_provider, emi_financed_amount=FINANCED,
    )
    assert sales_page.last_sale_response.get("status") in (200, 201), f"EMI sale failed: {sales_page.last_sale_response}"

    ledger_page = LedgerStatementPage(galaxy_logged_in_page, tenant)
    ledger_page.navigate()
    ledger_page.filter_statement(f"{galaxy_emi_provider} Receivable", GALAXY_BRANCH)

    assert ledger_page.has_table_visible() or ledger_page.has_metrics_visible(), "Provider receivable ledger did not load"
    total_debits = LedgerStatementPage.parse_signed_balance(ledger_page.get_total_debits())
    assert total_debits == Decimal(FINANCED), f"Provider receivable debits {total_debits}, expected {FINANCED}"
