from __future__ import annotations

from pages.common.base_page import BasePage


class DashboardPage(BasePage):
    PATH = "/dashboard"

    def is_dashboard_visible(self) -> bool:
        return self.page.get_by_role("heading", name="Dashboard").is_visible()
