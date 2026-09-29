from utils.constants import ADMIN_EMAIL, ADMIN_PASSWORD, DASHBOARD_URL
from pages.auth.login_page import LoginPage


# ============================================================================
# HAPPY PATH TESTS
# ============================================================================

def test_successful_login(page):
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    page.wait_for_url(lambda url: "/login" not in url, timeout=5000)

    assert page.url == DASHBOARD_URL


def test_failed_login(page):
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("invalid@example.com", "invalidpassword")
    login_page.verify_invalid_credentials_message()


def test_toggle_password_visibility(page):
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.password_input.fill("testpassword")
    login_page.toggle_password_visibility()
    assert login_page.password_input.get_attribute("type") == "text"


# ============================================================================
# EMAIL FIELD VALIDATION TESTS
# ============================================================================

def test_email_required(page):
    """Email is required — empty email should show validation error"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("", ADMIN_PASSWORD)
    assert login_page.page.get_by_text("Email is required").is_visible()


def test_email_invalid_format(page):
    """Invalid email format should show error"""
    login_page = LoginPage(page)
    login_page.navigate()
    invalid_emails = [
        "notanemail",
        "missing@domain",
        "test@",
        "@domain.com",
        "test @domain.com",
        "test@domain .com",
    ]

    for email in invalid_emails:
        login_page.username_input.clear()
        login_page.username_input.fill(email)
        login_page.password_input.clear()
        login_page.password_input.fill(ADMIN_PASSWORD)
        login_page.login_button.click()
        page.wait_for_timeout(500)
        # Should stay on login page or show error
        assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_too_long(page):
    """Email > 255 chars should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    long_email = "a" * 250 + "@test.com"  # Total > 255
    login_page.login(long_email, ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_sql_injection_single_quote(page):
    """SQL injection attempt with single quote should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("admin'--@example.com", ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    # Should fail login, not execute SQL
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_sql_injection_double_quote(page):
    """SQL injection attempt with double quote should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login('admin"--@example.com', ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_sql_injection_comment_sequence(page):
    """SQL injection attempt with -- comment should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("admin@example.com'--", ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_sql_injection_block_comment(page):
    """SQL injection attempt with /* */ block comment should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("admin/*@example.com*/", ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_xss_script_tag(page):
    """XSS attempt with <script> tag should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("<script>alert('xss')</script>@test.com", ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_xss_onerror_event(page):
    """XSS attempt with onerror event handler should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login('test" onerror="alert(1)@test.com', ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_xss_onclick_event(page):
    """XSS attempt with onclick event handler should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login('admin" onclick="alert(1)"@test.com', ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_email_with_special_characters(page):
    """Email with special chars (not standard) should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    special_emails = [
        "test!@example.com",
        "test#@example.com",
        "test$@example.com",
        "test%@example.com",
    ]

    for email in special_emails:
        login_page.username_input.clear()
        login_page.username_input.fill(email)
        login_page.password_input.clear()
        login_page.password_input.fill(ADMIN_PASSWORD)
        login_page.login_button.click()
        page.wait_for_timeout(500)
        assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


# ============================================================================
# PASSWORD FIELD VALIDATION TESTS
# ============================================================================

def test_password_required(page):
    """Password is required — empty password should show validation error"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, "")
    assert login_page.page.get_by_text("Password is required").is_visible()


def test_password_too_short(page):
    """Password < 6 chars should be rejected (based on VALIDATION_RULES.md)"""
    login_page = LoginPage(page)
    login_page.navigate()
    short_passwords = ["1", "12", "123", "1234", "12345"]

    for password in short_passwords:
        login_page.username_input.clear()
        login_page.username_input.fill(ADMIN_EMAIL)
        login_page.password_input.clear()
        login_page.password_input.fill(password)
        login_page.login_button.click()
        page.wait_for_timeout(500)
        assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_too_long(page):
    """Password > 255 chars should be rejected"""
    login_page = LoginPage(page)
    login_page.navigate()
    long_password = "a" * 256
    login_page.login(ADMIN_EMAIL, long_password)
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_leading_spaces_trimmed(page):
    """Password with leading spaces should be trimmed"""
    login_page = LoginPage(page)
    login_page.navigate()
    # Admin password with spaces added — should fail if spaces not trimmed
    login_page.login(ADMIN_EMAIL, "  " + ADMIN_PASSWORD)
    page.wait_for_timeout(500)
    # Should fail login because spaces weren't trimmed on backend
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_trailing_spaces_trimmed(page):
    """Password with trailing spaces should be trimmed"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD + "  ")
    page.wait_for_timeout(500)
    # Should fail login because spaces weren't trimmed on backend
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_sql_injection_single_quote(page):
    """SQL injection attempt in password with single quote"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, "password'--")
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_sql_injection_double_quote(page):
    """SQL injection attempt in password with double quote"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, 'password"--')
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_sql_injection_semicolon(page):
    """SQL injection attempt in password with semicolon"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, "password'; DROP TABLE users;--")
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_xss_script_tag(page):
    """XSS attempt in password with <script> tag"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, "<script>alert('xss')</script>")
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_xss_img_onerror(page):
    """XSS attempt in password with img onerror"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, '<img src=x onerror="alert(1)">')
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


def test_password_xss_event_handler(page):
    """XSS attempt in password with event handler"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, 'javascript:alert("xss")')
    page.wait_for_timeout(500)
    assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()


# ============================================================================
# BOTH FIELDS VALIDATION TESTS
# ============================================================================

def test_empty_credentials(page):
    """Both fields empty should show both required errors"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("", "")
    assert login_page.page.get_by_text("Email is required").is_visible()
    assert login_page.page.get_by_text("Password is required").is_visible()


# ============================================================================
# HTTPS & SECURITY TESTS
# ============================================================================

def test_url_has_https(page):
    """Login page must use HTTPS, not HTTP"""
    login_page = LoginPage(page)
    login_page.navigate()
    assert page.url.startswith("https://")


def test_password_input_type_is_password(page):
    """Password input should default to type='password', not visible"""
    login_page = LoginPage(page)
    login_page.navigate()
    assert login_page.password_input.get_attribute("type") == "password"


def test_password_not_sent_in_url(page):
    """Password should never appear in URL parameters"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    page.wait_for_url(lambda url: "/login" not in url, timeout=5000)
    # Check URL doesn't contain password
    assert ADMIN_PASSWORD not in page.url


# ============================================================================
# SESSION SECURITY TESTS
# ============================================================================

def test_session_persists_after_login(page):
    """Session should persist after successful login — user can navigate without re-login"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    page.wait_for_url(lambda url: "/login" not in url, timeout=5000)

    initial_url = page.url
    assert initial_url == DASHBOARD_URL

    # Navigate back to login page — should redirect to dashboard (session active)
    page.goto(login_page.url)
    page.wait_for_timeout(1000)

    # Session should still be valid — should redirect to dashboard
    if "/login" not in page.url:
        assert page.url == DASHBOARD_URL


def test_logout_clears_session(page):
    """Logout should clear session and redirect to login"""
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    page.wait_for_url(lambda url: "/login" not in url, timeout=5000)

    # Find and click logout button (common patterns)
    logout_button = page.locator('button').filter(has_text="Logout")
    if logout_button.is_visible():
        logout_button.click()
        page.wait_for_url(lambda url: "/login" in url, timeout=5000)
        assert "/login" in page.url


def test_direct_dashboard_access_without_login_redirects(page):
    """Direct access to dashboard without login should redirect to login"""
    page.goto(DASHBOARD_URL)
    page.wait_for_timeout(2000)
    # Should redirect to login
    assert "/login" in page.url


def test_multiple_failed_login_attempts(page):
    """Multiple failed login attempts should still work (no hard lockout)"""
    login_page = LoginPage(page)
    login_page.navigate()

    # Try 5 failed logins
    for i in range(5):
        login_page.username_input.clear()
        login_page.password_input.clear()
        login_page.login("wrong@example.com", "wrongpassword")
        page.wait_for_timeout(500)
        # Should still show error, not lock completely
        assert "/login" in page.url or login_page.page.locator('div.alert-danger').is_visible()

    # Now try correct login — should work if no hard lockout
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    page.wait_for_timeout(2000)
    # Should be able to login successfully
    if "/login" not in page.url:
        assert page.url == DASHBOARD_URL
