from pages.report.customer_outstanding_page import CustomerOutstandingPage
from utils.constants import SUPPLIER_OUTSTANDING_URL


class SupplierOutstandingPage(CustomerOutstandingPage):
    """Supplier Outstanding report using the shared party-report behavior."""

    REPORT_NAME = "Supplier Outstanding"
    API_PATH_SUFFIX = "/accounting/supplier-outstanding"
    SEARCH_PLACEHOLDER = "Search supplier…"
    REPORT_URL = SUPPLIER_OUTSTANDING_URL
    EXPECTED_HEADERS = [
        "SUPPLIER",
        "LEDGER",
        "OUTSTANDING",
        "BALANCE TYPE",
        "BRANCH",
        "LAST TXN",
        "ACTIONS",
    ]
