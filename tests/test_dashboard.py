from pages.dashboard_page import DashboardPage 
from utils.constants import DASHBOARD_URL

def test_dashboard_visibility(logged_in_page):
    dashboard_page = DashboardPage(logged_in_page)
    dashboard_page.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    assert DASHBOARD_URL in logged_in_page.url 
    assert dashboard_page.is_dashboard_visible()
