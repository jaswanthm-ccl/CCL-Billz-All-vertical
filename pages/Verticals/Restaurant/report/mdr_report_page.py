"""Restaurant adapter for the shared MDR Report page object."""

from playwright.sync_api import Page

from pages.report.mdr_report_page import MdrReportPage as DefaultMdrReportPage
from utils.res_constants import RES_MDR_REPORT_URL


class MdrReportPage(DefaultMdrReportPage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = RES_MDR_REPORT_URL
