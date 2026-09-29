"""Restaurant Recipes Page Object.

Route: RES_RECIPES_URL (/recipes)
"""
from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_RECIPES_URL


class RecipesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_RECIPES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Locators (@property) ────────────────────────────────────────────────

    @property
    def add_recipe_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Recipe", re.I)).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".dialog-wrapper, div[role='dialog']")).first

    @property
    def servings_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="number_of_servings"]').first

    @property
    def quantity_input(self) -> Locator:
        return self.modal_dialog.locator('input[name*="quantity"]').first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_role("textbox", name=re.compile(r"Search", re.I)).or_(
            self.page.locator('input[placeholder*="Search"]')
        ).first

    @property
    def create_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Create Recipe", re.I)).first

    @property
    def update_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Update Recipe", re.I)).first

    # ── React-Select Helper ─────────────────────────────────────────────────

    def _select_control(self, control_locator: Locator, option_name: str) -> None:
        """Clicks a react-select control safely and selects the option."""
        control_locator.wait_for(state="visible", timeout=5000)
        input_container = control_locator.locator(".react-select__input-container")
        if input_container.is_visible():
            input_container.click()
        else:
            control_locator.click()

        self.page.wait_for_timeout(300)
        self.page.keyboard.type(option_name)
        self.page.wait_for_timeout(300)
        opt = self.page.locator(".react-select__option, [id*='-option-']").filter(
            has_text=re.compile(re.escape(option_name), re.I)
        ).first
        if opt.is_visible():
            opt.click()
        else:
            self.page.keyboard.press("Enter")

    # ── Actions ─────────────────────────────────────────────────────────────

    def add_recipe(
        self,
        dish_name: str,
        ingredient_name: str,
        servings: str = "1",
        quantity: str = "1",
    ) -> bool:
        """Adds a recipe mapping a dish to its raw ingredient."""
        self.add_recipe_button.wait_for(state="visible", timeout=5000)
        self.add_recipe_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        # 1. Select Finished Dish
        dish_control = self.modal_dialog.locator(".react-select__control").filter(
            has_text=re.compile(r"Select finished good|finished", re.I)
        ).first
        if not dish_control.is_visible():
            dish_control = self.modal_dialog.locator(".react-select__control").first
        self._select_control(dish_control, dish_name)

        # 2. Fill Number of Servings
        if self.servings_input.is_visible():
            self.servings_input.fill(servings)

        # 3. Select Raw Ingredient
        ing_control = self.modal_dialog.locator(".react-select__control").filter(
            has_text=re.compile(r"Select raw material|raw", re.I)
        ).first
        if not ing_control.is_visible():
            ing_control = self.modal_dialog.locator(".react-select__control").nth(1)
        self._select_control(ing_control, ingredient_name)

        # 4. Fill Quantity
        qty_input = self.modal_dialog.locator('input[name="items.0.quantity"], input[name*="quantity"]').first
        if qty_input.is_visible():
            qty_input.fill(quantity)

        # 5. Submit
        self.create_button.click()

        toast = self.page.get_by_text(re.compile(r"Recipe created successfully|created successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True

    def search_recipe(self, dish_name: str) -> bool:
        """Searches for a recipe by dish name."""
        self.search_input.fill(dish_name)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")

        row = self.page.locator("tbody tr, tr").filter(has_text=dish_name).first
        try:
            row.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def view_recipe(self, dish_name: str) -> bool:
        """Opens recipe view modal and closes it."""
        self.search_recipe(dish_name)
        row = self.page.locator("tbody tr, tr").filter(has_text=dish_name).first
        row.wait_for(state="visible", timeout=5000)

        row.locator("button[title='view'], a[title='view'], i.bi-eye").first.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)
        self.page.wait_for_timeout(500)

        # Close View modal
        close_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"Back to List|Close|Cancel", re.I)).first
        if not close_btn.is_visible():
            close_btn = self.modal_dialog.locator("button.btn-close, button[aria-label='Close']").first

        close_btn.click()
        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True

    def edit_recipe(self, dish_name: str, new_quantity: str = "2") -> bool:
        """Edits an existing recipe's ingredient quantity."""
        self.search_recipe(dish_name)
        row = self.page.locator("tbody tr, tr").filter(has_text=dish_name).first
        row.wait_for(state="visible", timeout=5000)

        row.locator("button[title='edit'], a[title='edit'], i.bi-pencil").first.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        qty_input = self.modal_dialog.locator('input[name="items.0.quantity"], input[name*="quantity"]').first
        if qty_input.is_visible():
            qty_input.fill(new_quantity)

        self.update_button.click()

        toast = self.page.get_by_text(re.compile(r"Recipe updated successfully|updated successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True

    def delete_recipe(self, dish_name: str) -> bool:
        """Deletes an existing recipe."""
        self.search_recipe(dish_name)
        row = self.page.locator("tbody tr, tr").filter(has_text=dish_name).first
        if row.count() == 0 or not row.is_visible():
            return False

        del_btn = row.locator("button[title*='delete'], a[title*='delete'], button:has(i.bi-trash), i.bi-trash").first
        del_btn.click()

        # Confirmation modal
        confirm_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"^(?:Delete|Delete Recipe|Confirm)$", re.I)).first
        if confirm_btn.is_visible():
            confirm_btn.click()

        toast = self.page.get_by_text(re.compile(r"Recipe deleted successfully|deleted successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True
