"""Restaurant adapter for the shared Cities page object."""

from playwright.sync_api import Page

from pages.master_menu.cities_page import CitiesPage as SharedCitiesPage
from utils.tenants import RESTAURANT, Tenant


class CitiesPage(SharedCitiesPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
