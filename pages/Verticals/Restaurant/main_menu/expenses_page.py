"""Restaurant Expenses Page Object.

Route: RES_EXPENSES_URL (/expenses)

Modal field order (from Playwright recording):
  1. Expense Group  — .col-md-4 first react-select
  2. Category       — 4th child div .mb-3 react-select (loads async after group)
  3. Branch         — 5th child div .mb-3 react-select
  4. Payment Type   — 6th child div .mb-3 react-select
  5. Amount         — spinbutton / input[type=number]
  6. Description    — textarea[name="description"]
"""
from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_EXPENSES_URL


class ExpensesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_EXPENSES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Locators ─────────────────────────────────────────────────────────────

    @property
    def add_expense_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Expense", re.I)).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(
            self.page.locator(".modal-dialog, div[role='dialog']")
        ).first

    @property
    def amount_input(self) -> Locator:
        return self.modal_dialog.locator(
            'input[name="amount"], input[type="number"]'
        ).first

    @property
    def description_input(self) -> Locator:
        return self.modal_dialog.locator(
            'textarea[name="description"], input[name="description"]'
        ).first

    @property
    def submit_button(self) -> Locator:
        return self.modal_dialog.get_by_role(
            "button", name=re.compile(r"^Create$|^Save$", re.I)
        ).first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(
            self.page.locator("input[placeholder*='Search']")
        ).first

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _all_select_inputs(self) -> Locator:
        """All react-select input containers inside the modal."""
        return self.modal_dialog.locator(".react-select__input-container")

    def _wait_enabled(self, nth: int, timeout_ms: int = 8000) -> None:
        """Poll until the nth react-select control is not disabled."""
        elapsed = 0
        while elapsed < timeout_ms:
            try:
                disabled = self._all_select_inputs().nth(nth).evaluate(
                    "el => el.closest('.react-select__control')"
                    "?.classList.contains('react-select__control--is-disabled') ?? false"
                )
                if not disabled:
                    return
            except Exception:
                return
            self.page.wait_for_timeout(300)
            elapsed += 300

    def _select_option(self, nth: int, option_text: str | None = None) -> None:
        """
        Open the nth react-select in the modal and choose an option.
        If option_text is None, picks the first available option.
        """
        self._wait_enabled(nth)

        input_container = self._all_select_inputs().nth(nth)
        input_container.wait_for(state="visible", timeout=8000)
        input_container.click()
        self.page.wait_for_timeout(400)

        # Options list must appear
        opts = self.page.locator(".react-select__option")
        try:
            opts.first.wait_for(state="visible", timeout=8000)
        except Exception:
            # Retry one click in case it didn't register
            input_container.click()
            self.page.wait_for_timeout(400)
            opts.first.wait_for(state="visible", timeout=5000)

        if option_text:
            # Try exact role match first, then partial text match
            target = self.page.get_by_role("option", name=option_text, exact=True)
            if target.count() > 0 and target.first.is_visible():
                target.first.click()
            else:
                target2 = opts.filter(
                    has_text=re.compile(re.escape(option_text), re.I)
                ).first
                if target2.count() > 0 and target2.is_visible():
                    target2.click()
                else:
                    opts.first.click()
        else:
            opts.first.click()

        self.page.wait_for_timeout(300)

    # ── Public actions ────────────────────────────────────────────────────────

    def add_expense(
        self,
        expense_group: str | None = None,
        branch_name: str | None = None,
        amount: str = "250",
        notes: str = "Automated restaurant expense description",
    ) -> bool:
        """
        Fill and submit the Add Expense modal.

        Field order matches the Playwright recording:
          nth(0) Expense Group → nth(1) Category → nth(2) Branch → nth(3) Payment Type
        """
        self.add_expense_button.wait_for(state="visible", timeout=5000)
        self.add_expense_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)
        self.page.wait_for_timeout(500)

        # 1. Expense Group (nth 0)
        self._select_option(0, expense_group)

        # 2. Category (nth 1) — async load after group, pick first available
        self._select_option(1, None)

        # 3. Branch (nth 2) — pick first if branch_name not specified
        self._select_option(2, branch_name)

        # 4. Payment Type (nth 3) — Cash
        self._select_option(3, "Cash")

        # 5. Amount
        self.amount_input.wait_for(state="visible", timeout=5000)
        self.amount_input.click()
        self.amount_input.fill(str(amount))

        # 6. Description
        if self.description_input.is_visible():
            self.description_input.click()
            self.description_input.fill(notes)

        # 7. Submit
        with self.page.expect_response(
            lambda r: "/expenses" in r.url and r.request.method == "POST",
            timeout=10000,
        ) as resp_info:
            self.submit_button.click()

        resp = resp_info.value
        assert resp.status in (200, 201), (
            f"Create expense returned HTTP {resp.status}: {resp.text()}"
        )
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)
        return True

    def search_expense(self, query: str) -> bool:
        self.search_input.wait_for(state="visible", timeout=5000)
        self.search_input.fill(query)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")
        try:
            self.page.locator("table tbody tr").filter(
                has_text=query
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False
