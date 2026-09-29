"""Restaurant Customer Outstanding report adapter."""

from playwright.sync_api import Page

from pages.report.customer_outstanding_page import (
    CustomerOutstandingPage as SharedCustomerOutstandingPage,
)
from utils.tenants import RESTAURANT, Tenant


class CustomerOutstandingPage(SharedCustomerOutstandingPage):
    """Use the shared API-backed report contract against the Restaurant tenant."""

    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
