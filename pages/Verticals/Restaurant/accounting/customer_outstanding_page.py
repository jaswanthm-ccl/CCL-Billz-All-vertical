"""Restaurant Customer Outstanding report adapter."""

from playwright.sync_api import Page

from pages.report.customer_outstanding_page import (
    CustomerOutstandingPage as SharedCustomerOutstandingPage,
)
from utils.res_constants import RES_CUSTOMER_OUTSTANDING_URL


class CustomerOutstandingPage(SharedCustomerOutstandingPage):
    """Use the shared API-backed report contract against the Restaurant tenant."""

    REPORT_URL = RES_CUSTOMER_OUTSTANDING_URL

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = self.REPORT_URL
