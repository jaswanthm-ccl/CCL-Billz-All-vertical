"""Restaurant Products (Menu Items / Dishes / Raw Materials) Page Object.

Route: RES_PRODUCTS_URL (/products)
"""
from __future__ import annotations

import re
from pathlib import Path
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_PRODUCTS_URL
from utils.random_data import generate_random_code


class ProductsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_PRODUCTS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Locators (@property) ────────────────────────────────────────────────

    @property
    def add_product_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Add Product", re.I)).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".dialog-wrapper, div[role='dialog']")).first

    @property
    def name_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="name"]')

    @property
    def code_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="code"], input[placeholder*="item code"], input[placeholder*="Code"]').first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_role("textbox", name=re.compile(r"Search", re.I)).or_(
            self.page.locator('input[placeholder*="Search"]')
        ).first

    @property
    def submit_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Create Product|Create|Save", re.I)).first

    @property
    def update_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name=re.compile(r"Update Product|Update|Save", re.I)).first

    # ── Dropdown Select Helper ──────────────────────────────────────────────

    def _select_option(self, container: Locator, option_name: str) -> None:
        """Selects an option from a React-Select container."""
        container.wait_for(state="visible", timeout=5000)
        container.click()

        search_input = container.locator("input[id^='react-select'], input[type='text']")
        if search_input.count() > 0 and search_input.first.is_visible():
            search_input.first.fill(option_name)

        opt = self.page.get_by_role("option", name=option_name)
        if opt.count() > 0:
            try:
                opt.first.wait_for(state="visible", timeout=3000)
                opt.first.click()
                return
            except Exception:
                pass

        fallback = self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=option_name)
        if fallback.count() > 0:
            fallback.first.wait_for(state="visible", timeout=3000)
            fallback.first.click()
        else:
            first_opt = self.page.locator(".react-select__option, div[class*='-option']").first
            if first_opt.is_visible():
                first_opt.click()

    def _select_field_dropdown(self, field_name: str, placeholder: str, option_name: str) -> None:
        """Finds dropdown by hidden input name or placeholder text and selects the option."""
        # 1. Try finding via hidden input name
        container = self.modal_dialog.locator(f"input[name='{field_name}']").locator("..").locator(".react-select__control")
        if container.count() > 0 and container.first.is_visible():
            self._select_option(container.first, option_name)
            return

        # 2. Try finding via placeholder or label text on control
        container = self.modal_dialog.locator(".react-select__control").filter(has_text=re.compile(rf"{placeholder}", re.I)).first
        if container.is_visible():
            self._select_option(container, option_name)
            return

        # 3. Fallback to any react-select control
        container = self.modal_dialog.locator(".react-select__control").first
        if container.is_visible():
            self._select_option(container, option_name)

    # ── Actions ─────────────────────────────────────────────────────────────

    def add_product(
        self,
        name: str,
        code: str | None = None,
        category_name: str | None = None,
        department_name: str | None = None,
        unit_type: str | None = "Kg",
        price: str = "150",
        product_type: str = "Finished good",
        incentive_percentage: str | None = None,
    ) -> str:
        """Adds a new finished dish or raw product and returns its unique code."""
        item_code = code or generate_random_code("ITM")

        self.add_product_button.wait_for(state="visible", timeout=5000)
        self.add_product_button.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        # 1. Select Product Type (Finished good vs Raw material)
        if product_type and "finished" not in product_type.lower():
            type_control = self.modal_dialog.locator(".react-select__control").filter(
                has_text=re.compile(r"Finished good|Raw material", re.I)
            ).first
            if not type_control.is_visible():
                type_control = self.modal_dialog.locator(".react-select__control").first

            if type_control.is_visible():
                type_control.click()
                self.page.wait_for_timeout(300)
                opt = self.page.locator(".react-select__option, [id*='-option-']").filter(
                    has_text=re.compile(re.escape(product_type), re.I)
                ).first
                if opt.is_visible():
                    opt.click()
                else:
                    self.page.keyboard.type(product_type)
                    self.page.keyboard.press("Enter")

        # 2. Fill Product Name & Code
        self.name_input.fill(name)
        if self.code_input.is_visible():
            self.code_input.fill(item_code)

        # 3. Select Category
        if category_name:
            self._select_field_dropdown("category_id", "Select Category", category_name)

        # 4. Select Department
        if department_name:
            self._select_field_dropdown("department_id", "Select Department", department_name)

        # 5. Select Unit Type (e.g. Kg)
        if unit_type:
            self._select_field_dropdown("unit_type_id", "Select Unit", unit_type)

        # 6. Fill Price (if visible)
        price_input = self.modal_dialog.locator('input[name="selling_price"], input[name="price"], input[name="cost_price"]')
        if price_input.count() > 0 and price_input.first.is_visible():
            price_input.first.fill(price)

        # 6b. Fill Incentive Percentage (if provided)
        if incentive_percentage is not None:
            inc_input = self.modal_dialog.locator('input[name="incentive_percentage"]')
            if inc_input.count() > 0 and inc_input.first.is_visible():
                inc_input.first.fill(str(incentive_percentage))

        # 7. Submit
        self.submit_button.click()

        toast = self.page.get_by_text(re.compile(r"Product created successfully|created successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return item_code

    def search_product(self, name: str) -> bool:
        """Searches for a product and checks if it appears in the table."""
        self.search_input.fill(name)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")

        row = self.page.locator("tbody tr, div.card, tr").filter(has_text=name).first
        try:
            row.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def import_products(self, workbook_path: Path) -> None:
        """Upload a Restaurant product workbook and wait for the import API."""
        self.page.get_by_role("button", name="Import", exact=True).click()
        dialog = self.page.get_by_role("dialog").first
        dialog.wait_for(state="visible", timeout=5000)

        product_form = dialog.locator("form").first
        product_form.locator('input[type="file"]').set_input_files(str(workbook_path))
        with self.page.expect_response(
            lambda response: (
                "products/bulk-upload" in response.url
                and response.request.method == "POST"
            ),
            timeout=20000,
        ) as response_info:
            product_form.get_by_role("button", name="Upload", exact=True).click()

        response = response_info.value
        assert response.status in (200, 201), (
            f"Restaurant product import failed with HTTP {response.status}: "
            f"{response.text()}"
        )
        dialog.wait_for(state="hidden", timeout=10000)
        self.page.wait_for_load_state("networkidle")

    def edit_product(self, old_name: str, new_name: str) -> bool:
        """Edits an existing product's name."""
        self.search_product(old_name)
        row = self.page.locator("tbody tr, tr").filter(has_text=old_name).first
        row.wait_for(state="visible", timeout=5000)

        edit_btn = row.locator("button[title='edit'], button:has(i.bi-pencil), a[title='edit'], i.bi-pencil").first
        edit_btn.click()
        self.modal_dialog.wait_for(state="visible", timeout=5000)

        self.name_input.fill(new_name)
        self.update_button.click()

        toast = self.page.get_by_text(re.compile(r"Product updated successfully|updated successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        try:
            self.modal_dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        return True

    def delete_product(self, name: str) -> bool:
        """Soft-deletes an existing product."""
        self.search_product(name)
        row = self.page.locator("tbody tr, tr").filter(has_text=name).first
        if row.count() == 0 or not row.is_visible():
            return False

        del_btn = row.locator("button[title='delete'], button:has(i.bi-trash), i.bi-trash").first
        del_btn.click()

        # Confirmation modal if present
        confirm_btn = self.modal_dialog.get_by_role("button", name=re.compile(r"^(?:Delete|Confirm|Delete Product)$", re.I)).first
        if confirm_btn.is_visible():
            confirm_btn.click()

        toast = self.page.get_by_text(re.compile(r"Product deleted successfully|deleted successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass

        return True

    def update_opening_stock(
        self,
        product_name: str,
        branch_name: str,
        quantity: str = "10",
        cost_price: str = "10",
    ) -> bool:
        """Opens Opening Stock Update dialog on the product row, fills branch, quantity, and cost price, and saves."""
        self.search_product(product_name)
        row = self.page.locator("tbody tr, tr").filter(has_text=product_name).first
        row.wait_for(state="visible", timeout=5000)

        op_btn = row.locator(
            "button[title='Opening Stock Update'], button:has(i.bi-box-seam), i.bi-box-seam"
        ).first
        op_btn.click()

        dialog = self.page.get_by_role("dialog").or_(self.page.locator(".modal-dialog, div[role='dialog']")).first
        dialog.wait_for(state="visible", timeout=5000)

        # Select Branch
        branch_select = dialog.locator(".col-md-6, .mb-3, div").filter(
            has_text=re.compile(r"Branch", re.I)
        ).locator(".react-select__control, .react-select__input-container").first
        if branch_select.is_visible():
            branch_select.click()
            self.page.wait_for_timeout(300)
            self.page.keyboard.type(branch_name[:12])
            self.page.wait_for_timeout(400)
            opt = self.page.locator(".react-select__option").filter(has_text=branch_name).first
            if opt.is_visible():
                opt.click()
            else:
                self.page.keyboard.press("Enter")

        # Fill Quantity
        qty_input = dialog.locator("input[name='lines.0.quantity'], input[name*='quantity'], input[placeholder*='Quantity']").first
        if qty_input.is_visible():
            qty_input.fill(str(quantity))

        # Fill Cost Price
        cost_input = dialog.locator("input[name='lines.0.cost_price'], input[name*='cost_price'], input[placeholder*='Cost']").first
        if cost_input.is_visible():
            cost_input.fill(str(cost_price))

        # Click Save Opening Stock
        save_btn = dialog.get_by_role("button", name=re.compile(r"Save Opening Stock|Save", re.I)).first
        save_btn.click()

        toast = self.page.get_by_text(re.compile(r"Opening stock updated|updated successfully", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=6000)
        except Exception:
            pass

        try:
            dialog.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

        self.page.wait_for_load_state("networkidle")
        return True
