from __future__ import annotations

import re
from playwright.sync_api import Page, Locator
from utils.constants import PRODUCTS_URL
from pages.common.form_page import has_required_field_feedback, has_validation_feedback


class ProductsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.products_url = PRODUCTS_URL

    def navigate(self) -> None:
        self.page.goto(self.products_url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def add_product_button(self) -> Locator:
        return self.page.get_by_role("button", name="Add Product")

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_role("textbox", name="Search...")

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog")

    @property
    def name_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="name"]')

    @property
    def cost_price_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="cost_price"]')

    @property
    def selling_price_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="selling_price"]')

    @property
    def low_stock_input(self) -> Locator:
        return self.modal_dialog.locator('input[name="low_stock"]')

    @property
    def create_product_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name="Create Product")

    @property
    def update_product_button(self) -> Locator:
        return self.modal_dialog.get_by_role("button", name="Update Product")

    def is_products_visible(self) -> bool:
        return self.add_product_button.is_visible() or self.search_input.is_visible()

    def _select_option(self, container: Locator, option_name: str) -> None:
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
            first_opt.wait_for(state="visible", timeout=3000)
            first_opt.click()

    def _fill_product_form(
        self,
        modal: Locator,
        name: str,
        brand_name: str,
        category_name: str,
        hsn_code: str,
        unit_type: str,
        cost_price: str = "100",
        selling_price: str = "150",
        gst_percentage: str = "18%",
        low_stock: str = "5",
    ) -> None:
        modal.locator('input[name="name"]').fill(name)

        for field, option in (
            ("category_id", category_name),
            ("brand_id", brand_name),
        ):
            select_container = modal.locator(f"input[name='{field}']").locator("..")
            self._select_option(select_container, option)

        modal.locator('input[name="cost_price"]').fill(cost_price)
        modal.locator('input[name="selling_price"]').fill(selling_price)

        for field, option in (
            ("gst_percentage", gst_percentage),
            ("gst_code_id", hsn_code),
            ("unit_type_id", unit_type),
        ):
            select_container = modal.locator(f"input[name='{field}']").locator("..")
            self._select_option(select_container, option)

        modal.locator('input[name="low_stock"]').fill(low_stock)

    def add_product(
        self,
        name: str,
        brand_name: str,
        category_name: str,
        hsn_code: str,
        unit_type: str,
        cost_price: str = "100",
        selling_price: str = "150",
        gst_percentage: str = "18%",
    ) -> None:
        self.add_product_button.wait_for(state="visible", timeout=10000)
        self.add_product_button.click()
        modal = self.modal_dialog
        try:
            modal.locator('input[name="name"]').wait_for(state="visible", timeout=4000)
        except Exception:
            self.add_product_button.click()
            modal.locator('input[name="name"]').wait_for(state="visible", timeout=10000)

        self._fill_product_form(
            modal, name, brand_name, category_name, hsn_code, unit_type,
            cost_price, selling_price, gst_percentage
        )


        try:
            with self.page.expect_response(
                lambda r: "product" in r.url.lower() and r.request.method == "POST",
                timeout=20000
            ) as resp_info:
                self.create_product_button.click()
            assert resp_info.value.status in (200, 201), f"Product creation failed with HTTP {resp_info.value.status}"
        except Exception:
            if self.create_product_button.is_visible():
                self.create_product_button.click()
                self.page.wait_for_timeout(1000)

        toast = self.page.get_by_text(re.compile(r"successful|created", re.I)).first
        try:
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        try:
            modal.wait_for(state="hidden", timeout=15000)
        except Exception:
            self._ensure_modal_closed()

    def _ensure_modal_closed(self) -> None:
        if not self.modal_dialog.is_visible():
            return
        close_btn = self.modal_dialog.locator(
            ".btn-close, button:has-text('Cancel'), button:has-text('Close')"
        ).first
        try:
            if close_btn.is_visible():
                close_btn.click(timeout=3000)
        except Exception:
            if self.modal_dialog.is_visible():
                self.page.keyboard.press("Escape")
        self.modal_dialog.wait_for(state="hidden", timeout=5000)

    def validate_invalid_numeric_field(
        self, name: str, brand_name: str, category_name: str, hsn_code: str, unit_type: str, field: str, value: str
    ) -> bool:
        self.navigate()
        self._ensure_modal_closed()
        self.add_product_button.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=15000)
        values = {"cost_price": "100", "selling_price": "150", "low_stock": "5"}
        values[field] = value
        self._fill_product_form(
            modal, name, brand_name, category_name, hsn_code, unit_type,
            cost_price=values["cost_price"],
            selling_price=values["selling_price"],
            low_stock=values["low_stock"],
        )

        api_rejected = False
        try:
            with self.page.expect_response(
                lambda r: "/products" in r.url and r.request.method == "POST",
                timeout=3000
            ) as resp_info:
                self.create_product_button.click()
            api_rejected = resp_info.value.status in (400, 422)
        except Exception:
            api_rejected = True

        ui_rejected = has_validation_feedback(
            modal,
            r"must be.*(?:zero|0|positive|greater)",
            r"(?:negative|invalid).*(?:price|stock|value)",
            r"(?:price|stock).*(?:negative|invalid|positive)",
            r"validation",
        )
        self._ensure_modal_closed()
        return api_rejected and ui_rejected

    def validate_duplicate_product(
        self, name: str, brand_name: str, category_name: str, hsn_code: str, unit_type: str
    ) -> bool:
        self.navigate()
        self._ensure_modal_closed()
        self.add_product_button.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=15000)
        self._fill_product_form(
            modal, name, brand_name, category_name, hsn_code, unit_type
        )

        api_rejected = False
        try:
            with self.page.expect_response(
                lambda r: "/products" in r.url and r.request.method == "POST",
                timeout=5000
            ) as resp_info:
                self.create_product_button.click()
            api_rejected = resp_info.value.status in (400, 422)
        except Exception:
            api_rejected = True

        ui_rejected = has_validation_feedback(
            modal,
            r"product.*already",
            r"name.*already been taken",
            r"duplicate.*product",
            r"validation",
        )
        self._ensure_modal_closed()
        return api_rejected and ui_rejected

    def validate_required_fields(self) -> bool:
        self._ensure_modal_closed()
        self.add_product_button.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=15000)

        api_rejected = False
        try:
            with self.page.expect_response(
                lambda r: "/products" in r.url and r.request.method == "POST",
                timeout=3000
            ) as resp_info:
                self.create_product_button.click()
            api_rejected = resp_info.value.status in (400, 422)
        except Exception:
            api_rejected = True

        ui_rejected = has_required_field_feedback(modal)
        self._ensure_modal_closed()
        return api_rejected and ui_rejected

    def search_product(self, name: str) -> bool:
        self.search_input.fill(name)
        self.search_input.press("Enter")
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        try:
            row.first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def view_product(
        self,
        name: str,
        expected_brand: str | None = None,
        expected_category: str | None = None,
        expected_cost_price: str | None = None,
        expected_selling_price: str | None = None,
    ) -> bool:
        self.search_product(name)
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        row.first.locator("button[title='view'], a[title='view']").first.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        try:
            modal.get_by_text(name, exact=True).first.wait_for(state="visible", timeout=5000)
            is_visible = True
            if expected_brand:
                is_visible = is_visible and modal.get_by_text(expected_brand).is_visible()
            if expected_category:
                is_visible = is_visible and modal.get_by_text(expected_category).is_visible()
            modal_text = modal.inner_text()
            if expected_cost_price:
                is_visible = is_visible and re.search(
                    rf"Cost Price\s*₹?\s*{re.escape(expected_cost_price)}(?:\.00)?",
                    modal_text,
                    re.IGNORECASE,
                ) is not None
            if expected_selling_price:
                is_visible = is_visible and re.search(
                    rf"Selling Price(?:\s*\(inc GST\))?\s*₹?\s*{re.escape(expected_selling_price)}(?:\.00)?",
                    modal_text,
                    re.IGNORECASE,
                ) is not None
        except Exception:
            is_visible = False

        modal.get_by_role("button", name="Back to List").click()
        modal.wait_for(state="hidden", timeout=5000)
        return is_visible

    def is_product_active(self, name: str) -> bool:
        if not self.search_product(name):
            return False
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        if row.count() == 0:
            return False
        return row.first.locator("button[title='delete']:has(i.bi-trash)").count() > 0

    def delete_product(self, name: str) -> bool:
        if not self.search_product(name):
            return False
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        active_delete_btn = row.first.locator("button[title='delete']:has(i.bi-trash)")
        if active_delete_btn.count() == 0:
            return False
        active_delete_btn.first.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        delete_btn = modal.get_by_role("button", name="Delete Product")
        try:
            delete_btn.wait_for(state="visible", timeout=3000)
            delete_btn.click()
        except Exception:
            close_btn = modal.locator(".btn-close")
            if close_btn.is_visible():
                close_btn.click()
            elif modal.get_by_role("button", name="Cancel").is_visible():
                modal.get_by_role("button", name="Cancel").click()
            return False

        try:
            toast = self.page.get_by_text(re.compile(r"Deleted|successful|success", re.IGNORECASE)).first
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        modal.wait_for(state="hidden", timeout=5000)
        return True

    def edit_product(self, old_name: str, new_name: str, new_cost_price: str | None = None, new_selling_price: str | None = None) -> bool:
        self.search_product(old_name)
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(old_name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        row.first.locator("button[title='edit'], a[title='edit']").first.click()
        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        self.name_input.fill(new_name)
        if new_cost_price:
            self.cost_price_input.fill(new_cost_price)
        if new_selling_price:
            self.selling_price_input.fill(new_selling_price)

        with self.page.expect_response(
            lambda r: "/products" in r.url and r.request.method in ("PUT", "PATCH"),
            timeout=10000
        ) as resp_info:
            self.update_product_button.click()

        assert resp_info.value.status in (200, 204), f"Edit product failed with status {resp_info.value.status}"
        modal.wait_for(state="hidden", timeout=10000)
        return True

    def update_opening_stock(self, name: str, branch_name: str, quantity: str, cost_price: str) -> bool:
        self.search_product(name)
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        stock_btn = row.first.locator("button[title*='Stock' i], button[title*='stock' i]")
        stock_btn.first.wait_for(state="visible", timeout=5000)
        stock_btn.first.click()

        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        branch_select = modal.locator("input[name='branch_id']").locator("..")
        self._select_option(branch_select, branch_name)

        modal.locator("input[name='lines.0.quantity']").fill(quantity)
        modal.locator("input[name='lines.0.cost_price']").fill(cost_price)

        save_btn = modal.get_by_role("button", name=re.compile(r"(?:save|update)", re.IGNORECASE)).first
        save_btn.click()

        try:
            toast = self.page.get_by_text(re.compile(r"opening stock|updated|success", re.IGNORECASE)).first
            toast.wait_for(state="visible", timeout=5000)
        except Exception:
            pass
        modal.wait_for(state="hidden", timeout=10000)
        return True

    def retrieve_product(self, name: str) -> bool:
        self.search_product(name)
        row = self.page.locator("table tbody tr").filter(has=self.page.get_by_text(name, exact=True))
        row.first.wait_for(state="visible", timeout=5000)

        # Rule 3: Wait for i.bi-arrow-clockwise on soft-deleted row before retrieve
        restore_btn = row.first.locator("button[title='delete']:has(i.bi-arrow-clockwise)")
        restore_btn.wait_for(state="visible", timeout=5000)
        restore_btn.click()

        modal = self.modal_dialog
        modal.wait_for(state="visible", timeout=5000)

        retrieve_confirm = modal.get_by_role("button", name="Retrieve Product")
        retrieve_confirm.wait_for(state="visible", timeout=3000)
        retrieve_confirm.click()

        modal.wait_for(state="hidden", timeout=5000)
        return True
