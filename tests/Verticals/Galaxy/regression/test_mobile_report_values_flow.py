"""Galaxy end-to-end: stock and outstanding reports show the right numbers for serial-tracked phones.

1. Two phones are bought on credit at 12,000 each, selling price 15,000 (galaxy_stock fixture).
2. Stock Summary: 2 available, average cost 12,000, cost value 24,000, selling value 30,000.
   Supplier Outstanding: 24,000 payable.
3. One phone is sold on credit (nothing paid).
4. Stock Summary: 1 available, cost value 12,000. Customer Outstanding: 15,000 receivable.
"""
from decimal import Decimal

import pytest

from pages.main_menu.sales_page import SalesPage
from pages.report.customer_outstanding_page import CustomerOutstandingPage
from pages.report.stock_summary_page import StockSummaryPage
from pages.report.supplier_outstanding_page import SupplierOutstandingPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH

pytestmark = pytest.mark.regression

COST = Decimal("12000")
PRICE = Decimal("15000")


def _stock_row(page, tenant, product):
    report = StockSummaryPage(page, tenant)
    report.navigate()
    row = report.find_product(report.run_search(product), product_name=product, branch_name=GALAXY_BRANCH)
    assert row is not None, f"{product} missing from Stock Summary"
    return {key: report.amount(row[key]) for key in ("available_qty", "average_cost", "cost_value", "selling_value")}


def _outstanding(report_cls, page, tenant, party):
    report = report_cls(page, tenant)
    report.navigate()
    row = report.find_party(report.search(party), party)
    assert row is not None, f"{party} missing from {report_cls.REPORT_NAME}"
    return row["balance_type"], report.amount(row["outstanding_amount"])


def test_stock_and_outstanding_reports_follow_purchase_and_sale(
    galaxy_logged_in_page, tenant, galaxy_stock, galaxy_supplier, galaxy_customer
):
    page = galaxy_logged_in_page
    product, serials, _ = galaxy_stock

    # 2. After buying two phones
    assert _stock_row(page, tenant, product) == {
        "available_qty": Decimal("2.00"),
        "average_cost": COST.quantize(Decimal("0.01")),
        "cost_value": (2 * COST).quantize(Decimal("0.01")),
        "selling_value": (2 * PRICE).quantize(Decimal("0.01")),
    }
    assert _outstanding(SupplierOutstandingPage, page, tenant, galaxy_supplier) == ("Payable", 2 * COST)

    # 3. Sell one phone on credit
    sales_page = SalesPage(page, tenant)
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, "0", str(PRICE), product_name=product, serials=[serials[0]])
    assert sales_page.last_sale_response.get("status") in (200, 201), f"Credit sale failed: {sales_page.last_sale_response}"

    # 4. After the sale
    after = _stock_row(page, tenant, product)
    assert (after["available_qty"], after["cost_value"]) == (Decimal("1.00"), COST.quantize(Decimal("0.01"))), after
    assert _outstanding(CustomerOutstandingPage, page, tenant, galaxy_customer) == ("Receivable", PRICE)
