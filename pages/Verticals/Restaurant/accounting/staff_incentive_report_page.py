"""Restaurant Staff & Waiter Incentive Report Page Object.

Route: RESTAURANT_BASE_URL/reports/waiter-wise-incentive, /reports/daily-incentive
"""
from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from pages.common.base_page import BasePage
from utils.tenants import RESTAURANT, Tenant


class StaffIncentiveReportPage(BasePage):
    def __init__(self, page: Page, tenant: Tenant = RESTAURANT) -> None:
        super().__init__(page, tenant)
        self.waiter_url = tenant.url("/reports/waiter-wise-incentive")
        self.daily_url = tenant.url("/reports/daily-incentive")

    def navigate(self) -> None:
        self.page.goto(self.waiter_url)
        self.page.wait_for_load_state("networkidle")

    @property
    def search_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Search|Filter", re.I)).first

    def search_report(self) -> bool:
        self.navigate()
        if self.search_button.is_visible():
            self.search_button.click()
            self.page.wait_for_load_state("networkidle")
        return True
