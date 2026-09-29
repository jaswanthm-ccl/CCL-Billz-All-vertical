"""Restaurant adapter for the shared Categories page object."""

from playwright.sync_api import Page

from pages.master_menu.categories_page import CategoriesPage
from utils.tenants import RESTAURANT, Tenant


class FoodCategoriesPage(CategoriesPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
