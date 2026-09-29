"""Galaxy (Mobile) dashboard smoke test."""
import pytest

from pages.dashboard_page import DashboardPage


@pytest.mark.smoke
def test_galaxy_dashboard_visible(galaxy_logged_in_page, tenant):
    dashboard_page = DashboardPage(galaxy_logged_in_page, tenant)
    dashboard_page.navigate()
    galaxy_logged_in_page.wait_for_load_state("networkidle")

    assert galaxy_logged_in_page.url.startswith(dashboard_page.url)
    assert dashboard_page.is_dashboard_visible()
