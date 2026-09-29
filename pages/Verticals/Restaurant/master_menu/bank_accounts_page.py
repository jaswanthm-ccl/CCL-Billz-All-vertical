"""Restaurant adapter for the shared Bank Accounts page object."""

from playwright.sync_api import Page

from pages.master_menu.bank_accounts_page import BankAccountPage
from utils.tenants import RESTAURANT, Tenant


class BankAccountsPage(BankAccountPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
