from __future__ import annotations

from typing import TypeVar

from playwright.sync_api import Page

from pages.common.components import ReactSelect
from utils.tenants import Tenant, active_tenant

P = TypeVar("P", bound="BasePage")


class BasePage:
    """Tenant-aware base: subclasses set PATH and never import a *_URL constant.

    tenant=None means the run's active tenant (pytest --tenant / BILLZ_TENANT).
    """

    PATH: str = ""

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        self.page = page
        self.tenant = tenant or active_tenant()
        self.url = self.tenant.url(self.PATH)

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("domcontentloaded")

    def open(self, page_cls: type[P]) -> P:
        """Build another page object on the same tenant, so helpers never jump to a different vertical."""
        return page_cls(self.page, self.tenant)

    def select_dropdown_option(self, input_name: str, option_text: str) -> None:
        ReactSelect.by_name(self.page, input_name).select(option_text)
