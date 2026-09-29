"""Restaurant adapter for the shared MDR Report page object."""

from playwright.sync_api import Page

from pages.report.mdr_report_page import MdrReportPage as DefaultMdrReportPage
from utils.tenants import RESTAURANT, Tenant


class MdrReportPage(DefaultMdrReportPage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
