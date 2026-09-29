"""Restaurant adapter for the shared Unit Types page object."""

from playwright.sync_api import Page

from pages.master_menu.unit_types_page import UnitTypesPage as SharedUnitTypesPage
from utils.tenants import RESTAURANT, Tenant


class UnitTypesPage(SharedUnitTypesPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
