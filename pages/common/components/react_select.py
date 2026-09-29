from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from utils.constants import UI_TIMEOUT


class ReactSelect:
    """A react-select control, located by its bound input name or by its field label."""

    def __init__(self, page: Page, control: Locator) -> None:
        self.page = page
        self.control = control

    @classmethod
    def by_name(cls, page: Page, input_name: str, scope: Locator | Page | None = None) -> ReactSelect:
        root = scope or page
        control = (
            root.locator(f"input[name='{input_name}']")
            .locator("xpath=..")
            .locator(".react-select__input-container")
            .first
        )
        return cls(page, control)

    @classmethod
    def by_label(cls, page: Page, label: str, scope: Locator | Page | None = None) -> ReactSelect:
        root = scope or page
        control = (
            root.locator("label")
            .filter(has_text=re.compile(rf"^{re.escape(label)}\s*\*?\s*$", re.I))
            .locator("xpath=..")
            .locator(".react-select__input-container, .react-select__control")
            .first
        )
        return cls(page, control)

    def select(self, option_text: str, *, type_to_filter: bool = True, exact: bool = False) -> None:
        self.control.wait_for(state="visible", timeout=UI_TIMEOUT)
        self.control.click()
        if type_to_filter:
            self.page.keyboard.type(option_text)
        name = option_text if exact else re.compile(re.escape(option_text), re.I)
        option = (
            self.page.locator(".react-select__option, [id*='-option-']")
            .filter(has_text=name)
            .or_(self.page.get_by_role("option", name=name, exact=exact))
            .first
        )
        option.wait_for(state="visible", timeout=UI_TIMEOUT)
        option.click()
