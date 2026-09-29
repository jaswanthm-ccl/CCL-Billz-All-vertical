"""Restaurant Waiter-wise Incentive Report page object."""

from playwright.sync_api import Page

from pages.Verticals.Restaurant.accounting.restaurant_incentive_report_page import (
    RestaurantIncentiveReportPage,
)


class WaiterWiseIncentiveReportPage(RestaurantIncentiveReportPage):
    def __init__(self, page: Page) -> None:
        super().__init__(
            page,
            route="/reports/waiter-wise-incentive",
            endpoint="/reports/restaurant/incentives/waiter-wise",
        )
