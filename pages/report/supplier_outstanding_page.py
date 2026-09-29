from pages.report.customer_outstanding_page import CustomerOutstandingPage


class SupplierOutstandingPage(CustomerOutstandingPage):
    """Supplier Outstanding report using the shared party-report behavior."""

    REPORT_NAME = "Supplier Outstanding"
    API_PATH_SUFFIX = "/accounting/supplier-outstanding"
    SEARCH_PLACEHOLDER = "Search supplier…"
    PATH = "/reports/supplier-outstanding"
    EXPECTED_HEADERS = [
        "SUPPLIER",
        "LEDGER",
        "OUTSTANDING",
        "BALANCE TYPE",
        "BRANCH",
        "LAST TXN",
        "ACTIONS",
    ]
