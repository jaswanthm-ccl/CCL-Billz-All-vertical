from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_DEPARTMENTS_URL


class DepartmentsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_DEPARTMENTS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Locators (@property) ────────────────────────────────────────────────

    @property
    def add_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Department", re.I)).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".dialog-wrapper, div[role='dialog']")).first

    @property
    def name_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="name"], input[placeholder*="Department Name"]').first

    @property
    def description_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="description"], textarea[name="description"], input[placeholder*="Description"]').first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_role("textbox", name=re.compile(r"Search", re.I)).or_(
            self.page.locator('input[placeholder*="Search"]')
        ).first

    @property
    def submit_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Create Department|Create|Save", re.I)).first

    @property
    def update_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Update Department|Update|Save", re.I)).first

    # ── Actions ─────────────────────────────────────────────────────────────

    def add_department(self, name: str, description: str = "") -> bool:
        self.add_button.wait_for(state="visible", timeout=5000)
        self.add_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        self.name_input.fill(name)
        if description and self.description_input.is_visible():
            self.description_input.fill(description)

        self.submit_button.click()

        toast = self.page.get_by_text(re.compile(r"Department created successfully|created successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True

    def search_department(self, name: str) -> bool:
        self.search_input.fill(name)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")

        row = self.page.locator("table tbody tr, tr").filter(has_text=name).first
        try:
            row.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def edit_department(self, old_name: str, new_name: str) -> bool:
        self.search_department(old_name)
        row = self.page.locator("table tbody tr, tr").filter(has_text=old_name).first
        row.wait_for(state="visible", timeout=5000)

        row.locator("button[title='edit'], a[title='edit'], i.bi-pencil").first.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        self.name_input.fill(new_name)
        self.update_button.click()

        toast = self.page.get_by_text(re.compile(r"Department updated successfully|updated successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True

    def delete_department(self, name: str) -> bool:
        self.search_department(name)
        row = self.page.locator("table tbody tr, tr").filter(has_text=name).first
        if row.count() == 0 or not row.is_visible():
            return False

        row.locator("button[title='delete'], button:has(i.bi-trash), i.bi-trash").first.click()

        confirm_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"^(?:Delete|Delete Department|Confirm)$", re.I)).first
        if confirm_btn.is_visible():
            confirm_btn.click()

        toast = self.page.get_by_text(re.compile(r"Department deleted successfully|deleted successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True
