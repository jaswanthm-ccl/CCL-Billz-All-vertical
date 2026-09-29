from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_TABLES_URL


class TablesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_TABLES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Locators (@property) ────────────────────────────────────────────────

    @property
    def create_table_button(self) -> Locator:
        return self.page.get_by_role("button", name="Create Table").first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog")

    @property
    def name_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="name"]')

    @property
    def capacity_input(self) -> Locator:
        return self.modal_dialog.get_by_role("spinbutton")

    @property
    def submit_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name="Create Table", exact=True)

    @property
    def filter_total_tables(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Total Tables", re.I)).first

    @property
    def filter_available(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"^Available", re.I)).first

    @property
    def filter_occupied(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"^Occupied", re.I)).first

    @property
    def filter_reserved(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"^Reserved", re.I)).first

    # ── Helpers & Actions ───────────────────────────────────────────────────

    def _select_branch(self, branch_name: str | None = None) -> None:
        """Selects the branch from the React-Select dropdown."""
        branch_select = self.modal_dialog.locator(".react-select__control, .react-select__input-container, div[class*='-control']").first
        if branch_select.is_visible():
            branch_select.click()
            self.page.wait_for_timeout(300)
            if branch_name:
                self.page.keyboard.type(branch_name)
                self.page.wait_for_timeout(300)
                self.page.keyboard.press("Enter")
            else:
                option = self.page.locator(".react-select__option, [id*='-option-']").first
                try:
                    option.wait_for(state="visible", timeout=3000)
                    option.click()
                except Exception:
                    self.page.keyboard.press("ArrowDown")
                    self.page.keyboard.press("Enter")

    def add_table(self, name: str, capacity: str = "4", branch_name: str | None = None) -> bool:
        """Create a new table layout entry."""
        self.create_table_button.wait_for(state="visible", timeout=5000)
        self.create_table_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        self._select_branch(branch_name)
        self.name_input.fill(name)

        if self.capacity_input.is_visible():
            self.capacity_input.fill(capacity)

        self.submit_button.click()

        toast = self.page.get_by_text(re.compile(r"Table created successfully|successful", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True

    def get_table_card(self, name: str) -> Locator:
        """Locates the card element for a specific table."""
        return self.page.locator("div.card, div[class*='table'], div.border").filter(has_text=name).first

    def is_table_visible(self, name: str) -> bool:
        """Checks if a table with the given name is rendered on the screen."""
        self.page.wait_for_timeout(1000)
        element = self.page.locator("div").filter(has_text=name).first
        try:
            element.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def click_table_seat(self, table_name: str, seat_number: int = 1) -> None:
        """Clicks a specific seat button on a table card to launch the POS/Billing screen."""
        card = self.get_table_card(table_name)
        seat_locator = card.locator("button, [role='button'], span, div").filter(
            has_text=re.compile(rf"^(?:Seat\s*)?{seat_number}$", re.I)
        ).first

        if seat_locator.is_visible():
            seat_locator.click()
        else:
            self.page.get_by_role("button", name=re.compile(rf"Seat\s*{seat_number}", re.I)).first.click()

        self.page.wait_for_load_state("networkidle")
