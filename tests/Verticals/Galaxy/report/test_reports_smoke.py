"""Galaxy smoke for reports: each report page loads and renders its table on the Galaxy tenant."""
import pytest

from pages.report.customer_outstanding_page import CustomerOutstandingPage
from pages.report.emi_reconciliation_page import EmiReconciliationPage
from pages.report.gstr_1_b2b_page import Gstr1B2bPage
from pages.report.gstr_1_b2c_page import Gstr1B2cPage
from pages.report.mdr_report_page import MdrReportPage
from pages.report.outstanding_bills_page import OutstandingBillsPage
from pages.report.stock_summary_page import StockSummaryPage
from pages.report.supplier_outstanding_page import SupplierOutstandingPage

pytestmark = pytest.mark.smoke

REPORTS = {
    "outstanding_bills": OutstandingBillsPage,
    "customer_outstanding": CustomerOutstandingPage,
    "supplier_outstanding": SupplierOutstandingPage,
    "mdr_report": MdrReportPage,
    "emi_reconciliation": EmiReconciliationPage,
    "stock_summary": StockSummaryPage,
    "gstr1_b2b": Gstr1B2bPage,
    "gstr1_b2c": Gstr1B2cPage,
}


EMPTY_STATES = {
    "mdr_report": "No MDR settlements for the selected period.",
}


@pytest.mark.parametrize("report", list(REPORTS))
def test_report_loads(report, galaxy_logged_in_page, tenant):
    page_obj = REPORTS[report](galaxy_logged_in_page, tenant)
    page_obj.navigate()
    if report == "stock_summary":
        page_obj.run_report()

    assert galaxy_logged_in_page.url.startswith(page_obj.url), f"{report}: redirected to {galaxy_logged_in_page.url}"
    rendered = galaxy_logged_in_page.locator("table").first
    if report in EMPTY_STATES:
        rendered = rendered.or_(galaxy_logged_in_page.get_by_text(EMPTY_STATES[report]))
    rendered.wait_for(state="visible", timeout=15000)
