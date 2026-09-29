"""Restaurant Staff & Waiter Incentive Report Test Suite."""
import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.accounting.staff_incentive_report_page import StaffIncentiveReportPage


@pytest.mark.restaurant
def test_restaurant_staff_incentive_report_page_loads(res_logged_in_page):
    """Test staff/waiter incentive report page loads."""
    page = res_logged_in_page
    report_page = StaffIncentiveReportPage(page)
    report_page.navigate()
    expect(page.get_by_text("Waiter-wise Incentive Summary", exact=True)).to_be_visible()
