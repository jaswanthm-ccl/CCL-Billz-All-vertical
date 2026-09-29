"""Restaurant Indents Page Object.

Route: RES_INDENTS_URL (/indents)
"""
from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_INDENTS_URL


class IndentsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_INDENTS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def create_indent_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Create Indent|Add Indent", re.I)).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".modal-dialog, div[role='dialog']")).first

    @property
    def template_name_input(self) -> Locator:
        return self.modal_dialog.locator("input[placeholder*='Template Name'], input[placeholder*='template name'], input[name='template_name']").first

    @property
    def save_as_template_checkbox(self) -> Locator:
        return self.modal_dialog.locator("input[type='checkbox']").first

    @property
    def add_menu_items_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Add Menu Item", re.I)).first

    @property
    def add_item_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Add Item", re.I)).first

    @property
    def create_button(self) -> Locator:
        return self.modal_dialog.get_by_role(
            "button", name=re.compile(r"^(Save|Create|Update|Submit)", re.I)
        ).or_(self.modal_dialog.locator("button[type='submit']")).first

    @property
    def create_and_approve_button(self) -> Locator:
        return self.modal_dialog.locator("button:has-text('Save & Approve'), button:has-text('Create & Approve')").first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _select_dropdown(self, container: Locator, option_text: str | None = None) -> None:
        ctrl = container.locator(".react-select__control").first
        ctrl.wait_for(state="visible", timeout=5000)
        ctrl.click()
        self.page.wait_for_timeout(300)

        if option_text:
            opt = self.page.locator(".react-select__option").filter(has_text=re.compile(re.escape(option_text), re.I)).first
            if opt.is_visible():
                opt.click()
            else:
                self.page.keyboard.type(option_text[:8])
                self.page.wait_for_timeout(300)
                opt2 = self.page.locator(".react-select__option").filter(has_text=re.compile(re.escape(option_text), re.I)).first
                if opt2.is_visible():
                    opt2.click()
                else:
                    self.page.locator(".react-select__option").first.click()
        else:
            self.page.locator(".react-select__option").first.click()
        self.page.wait_for_timeout(300)

    # ── Actions ─────────────────────────────────────────────────────────────

    def create_indent(
        self,
        branch_name: str,
        department_name: str,
        mode: str = "Manual",
        template_name: str | None = None,
        save_as_template: bool = False,
        new_template_title: str | None = None,
        items: list[dict[str, str]] | None = None,
        menu_items: list[dict[str, str]] | None = None,
        approve_immediately: bool = False,
    ) -> str:
        """Creates a new restaurant indent and returns the created Indent ID."""
        self.create_indent_button.wait_for(state="visible", timeout=5000)
        self.create_indent_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)
        self.page.wait_for_timeout(600)

        # 1. Select Branch
        b_cont = self.modal_dialog.locator(".col-md-3:has-text('Branch'), .col-md-4:has-text('Branch'), .mb-3:has-text('Branch')")
        self._select_dropdown(b_cont, branch_name)

        # 2. Select Department
        d_cont = self.modal_dialog.locator(".col-md-3:has-text('Department'), .col-md-4:has-text('Department'), .mb-3:has-text('Department')")
        self._select_dropdown(d_cont, department_name)

        # 3. Select Mode (Manual vs Template)
        if mode.lower() == "template":
            m_cont = self.modal_dialog.locator(".col-md-3:has-text('Indent Mode'), .col-md-4:has-text('Indent Mode'), .mb-3:has-text('Indent Mode')")
            self._select_dropdown(m_cont, "Template")
            if template_name:
                t_cont = self.modal_dialog.locator(".col-md-3:has-text('Template'), .col-md-4:has-text('Template'), .mb-3:has-text('Template')").last
                self._select_dropdown(t_cont, template_name)

        # 4. Add Menu Items (dishes)
        if menu_items:
            for m_item in menu_items:
                if self.add_menu_items_button.is_visible():
                    self.add_menu_items_button.click()
                    self.page.wait_for_timeout(500)
                m_select = self.modal_dialog.locator(".react-select__control").filter(has_text=re.compile(r"Select menu item", re.I)).last
                if not m_select.is_visible():
                    m_select = self.modal_dialog.locator(".react-select__control").last
                self._select_dropdown(m_select, m_item["name"])
                if "quantity" in m_item:
                    m_qty = self.modal_dialog.locator("input[name*='menu_items'][type='number'], input[placeholder*='Quantity']").last
                    if m_qty.is_visible():
                        m_qty.fill(str(m_item["quantity"]))

        # 5. Add Raw Material Items
        if items:
            for idx, item in enumerate(items):
                if idx > 0 and self.add_item_button.is_visible():
                    self.add_item_button.click()
                    self.page.wait_for_timeout(300)

                row_ctrl = self.modal_dialog.locator("table tbody tr").nth(idx)
                self._select_dropdown(row_ctrl, item["name"])

                qty_inp = row_ctrl.locator("input[type='number']").first
                if qty_inp.is_visible() and "quantity" in item:
                    qty_inp.fill(str(item["quantity"]))

        # 6. Save as Template Checkbox & Title
        if save_as_template:
            if self.save_as_template_checkbox.is_visible():
                self.save_as_template_checkbox.check()
                self.page.wait_for_timeout(300)
            if new_template_title and self.template_name_input.is_visible():
                self.template_name_input.fill(new_template_title)

        # 7. Submit (Create vs Create & Approve)
        with self.page.expect_response(
            lambda r: "/indents" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            if approve_immediately and self.create_and_approve_button.is_visible():
                self.create_and_approve_button.click()
            else:
                self.create_button.click()

        assert resp_info.value.status in (200, 201), f"Indent API returned HTTP {resp_info.value.status}"
        data = resp_info.value.json()
        indent_id = str(data.get("data", {}).get("id", "") or data.get("id", ""))

        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)
        return indent_id

    def search_indent(self, indent_id: str) -> bool:
        self.search_input.wait_for(state="visible", timeout=5000)
        self.search_input.fill(str(indent_id))
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")
        try:
            self.page.locator("table tbody tr").filter(has_text=str(indent_id)).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def view_indent(self, indent_id: str) -> dict:
        self.search_indent(indent_id)
        row = self.page.locator("table tbody tr").filter(has_text=str(indent_id)).first
        row.locator("button[title='view'], button:has(i.bi-eye)").first.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)
        self.page.wait_for_load_state("networkidle")
        loading = self.modal_dialog.get_by_text(re.compile(r"^Loading", re.I))
        if loading.count() > 0:
            try:
                loading.first.wait_for(state="hidden", timeout=5000)
            except Exception:
                pass
        try:
            self.modal_dialog.get_by_text(str(indent_id)).first.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        content = self.modal_dialog.inner_text()
        close_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"Close|Back", re.I)).first
        if close_btn.is_visible():
            close_btn.click()
        return {"id": indent_id, "content": content}

    def edit_indent(self, indent_id: str, new_quantity: str = "10") -> bool:
        self.search_indent(indent_id)
        row = self.page.locator("table tbody tr").filter(has_text=str(indent_id)).first
        row.locator("button[title='edit'], button:has(i.bi-pencil)").first.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        qty_input = self.modal_dialog.locator("table tbody tr input[type='number']").first
        if qty_input.is_visible():
            qty_input.fill(new_quantity)

        with self.page.expect_response(
            lambda r: f"/indents/{indent_id}" in r.url and r.request.method in ("PUT", "PATCH", "POST"),
            timeout=10000,
        ) as resp_info:
            self.create_button.click()

        assert resp_info.value.status in (200, 201), f"Edit indent returned HTTP {resp_info.value.status}"
        self.page.wait_for_load_state("networkidle")
        return True

    def delete_indent(self, indent_id: str) -> bool:
        if not self.search_indent(indent_id):
            return False
        row = self.page.locator("table tbody tr").filter(has_text=str(indent_id)).first
        del_btn = row.locator("button[title='delete'], button:has(i.bi-trash)").first
        if not del_btn.is_visible() or not del_btn.is_enabled():
            return False
        del_btn.click()

        confirm_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"Delete|Confirm", re.I)).first
        if confirm_btn.is_visible():
            confirm_btn.click()
        self.page.wait_for_load_state("networkidle")
        return True

    def reverse_indent(self, indent_id: str) -> bool:
        if not self.search_indent(indent_id):
            return False
        row = self.page.locator("table tbody tr").filter(has_text=str(indent_id)).first
        rev_btn = row.locator(
            "button[title='Reverse Indent'], button:has(i.bi-arrow-counterclockwise)"
        ).first
        if not rev_btn.is_visible():
            return False
        rev_btn.click()

        confirm_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"Reverse|Confirm", re.I)).first
        if not confirm_btn.is_visible():
            return False
        with self.page.expect_response(
            lambda response: (
                f"/indents/{indent_id}/reverse" in response.url
                and response.request.method == "POST"
            ),
            timeout=10000,
        ) as response_info:
            confirm_btn.click()

        if response_info.value.status not in (200, 201):
            return False
        self.page.get_by_text(re.compile(r"Indent reversed successfully", re.I)).first.wait_for(
            state="visible", timeout=5000
        )
        self.page.reload(wait_until="networkidle")
        return True

    def get_indent_status(self, indent_id: str) -> str:
        self.search_indent(indent_id)
        row = self.page.locator("table tbody tr").filter(has_text=str(indent_id)).first
        return row.inner_text()
