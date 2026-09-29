"""Galaxy (Mobile) login smoke tests."""
import pytest

from pages.auth.login_page import LoginPage
from pages.dashboard_page import DashboardPage


@pytest.mark.smoke
def test_galaxy_login_lands_on_dashboard(page, tenant):
    login_page = LoginPage(page, tenant)
    page.goto(tenant.url("/login"), wait_until="domcontentloaded")
    login_page.login(tenant.email, tenant.password)
    page.wait_for_url(lambda url: "/login" not in url, timeout=30000)

    assert page.url.startswith(DashboardPage(page, tenant).url)


@pytest.mark.smoke
def test_galaxy_invalid_login_shows_error(page, tenant):
    login_page = LoginPage(page, tenant)
    page.goto(tenant.url("/login"), wait_until="domcontentloaded")
    login_page.login("invalid@example.com", "invalidpassword")

    login_page.verify_invalid_credentials_message()
    assert "/login" in page.url


@pytest.mark.smoke
def test_galaxy_dashboard_requires_login(page, tenant):
    page.goto(DashboardPage(page, tenant).url)
    page.wait_for_url(lambda url: "/login" in url, timeout=10000)
