from __future__ import annotations

from playwright.sync_api import Locator, expect
from pages.common.base_page import BasePage
import re


class LoginPage(BasePage):

    @property
    def username_input(self) -> Locator:
        return self.page.locator('input[name="email"]')

    @property
    def password_input(self) -> Locator:
        return self.page.locator('input[name="password"]')

    @property
    def login_button(self) -> Locator:
        return self.page.locator('button[type="submit"]')

    def login(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def verify_invalid_credentials_message(self) -> None:
        expect(self.page.locator('div.alert-danger')).to_be_visible()

    def toggle_password_visibility(self) -> None:
        self.page.get_by_role("button").filter(has_text=re.compile(r"^$")).click()
