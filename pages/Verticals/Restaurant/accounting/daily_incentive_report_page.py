"""Restaurant Daily Incentive Report page object."""

from playwright.sync_api import Page

from pages.Verticals.Restaurant.accounting.restaurant_incentive_report_page import (
    RestaurantIncentiveReportPage,
)


class DailyIncentiveReportPage(RestaurantIncentiveReportPage):
    def __init__(self, page: Page) -> None:
        super().__init__(
            page,
            route="/reports/daily-incentive",
            endpoint="/reports/restaurant/incentives/daily",
        )
