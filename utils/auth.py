from __future__ import annotations

from playwright.sync_api import Browser

from pages.auth.login_page import LoginPage
from utils.tenants import Tenant


def login_storage_state(browser: Browser, tenant: Tenant) -> dict:
    """Log in to the tenant once and return its storage state for reuse across contexts."""
    assert tenant.email and tenant.password, f"Missing login credentials for tenant '{tenant.name}' in .env"
    context = browser.new_context(ignore_https_errors=True)
    try:
        page = context.new_page()
        page.goto(tenant.url("/login"), wait_until="domcontentloaded")
        LoginPage(page, tenant).login(tenant.email, tenant.password)
        page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
        page.wait_for_load_state("networkidle")
        return context.storage_state()
    finally:
        context.close()
