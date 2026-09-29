"""Restaurant adapter for the shared Roles page object."""
from __future__ import annotations

from playwright.sync_api import Page
from pages.master_menu.roles_page import RolesPage as BaseRolesPage
from utils.tenants import RESTAURANT, Tenant


class RolesPage(BaseRolesPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
