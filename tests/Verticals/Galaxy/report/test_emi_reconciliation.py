"""Galaxy EMI reconciliation: a new EMI sale shows as financed and fully outstanding for its provider."""
from decimal import Decimal

from pages.main_menu.sales_page import SalesPage
from pages.report.emi_reconciliation_page import EmiReconciliationPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH

PRICE = "15000"
DOWN_PAYMENT = "5000"
FINANCED = Decimal("10000")


def test_emi_sale_appears_as_outstanding_for_provider(galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer, galaxy_emi_provider):
    product, serials, _ = galaxy_stock
    sales_page = SalesPage(galaxy_logged_in_page, tenant)
    sales_page.add_sale(
        galaxy_customer, GALAXY_BRANCH, DOWN_PAYMENT, PRICE, product_name=product, serials=[serials[0]],
        is_emi=True, emi_provider_name=galaxy_emi_provider, emi_financed_amount=str(FINANCED),
    )
    assert sales_page.last_sale_response.get("status") in (200, 201), f"EMI sale failed: {sales_page.last_sale_response}"

    recon_page = EmiReconciliationPage(galaxy_logged_in_page, tenant)
    recon_page.navigate()
    assert recon_page.search_provider(galaxy_emi_provider), f"{galaxy_emi_provider} is not listed in EMI reconciliation"

    row = recon_page.get_provider_reconciliation_row(galaxy_emi_provider)
    assert row["total_financed"] == FINANCED, row
    assert row["total_settled"] == Decimal("0"), row
    assert row["total_outstanding"] == FINANCED, row
