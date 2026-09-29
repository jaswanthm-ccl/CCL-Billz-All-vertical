"""Restaurant adapter for the shared SAC/HSN Code page object."""

from playwright.sync_api import Page

from pages.master_menu.sac_hsn_code_page import (
    SacHsnCodePage as SharedSacHsnCodePage,
)
from utils.tenants import RESTAURANT, Tenant


class SacHsnCodePage(SharedSacHsnCodePage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
