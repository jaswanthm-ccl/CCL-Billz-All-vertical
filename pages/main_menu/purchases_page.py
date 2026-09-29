from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from playwright.sync_api import Page, Locator
from utils.constants import PURCHASES_URL
from utils.models import PurchaseResult


class PurchasesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = PURCHASES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("domcontentloaded")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search Purchases...")

    @property
    def add_purchase_button(self) -> Locator:
        return self.page.get_by_role("button", name="Add Purchase")

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog")

    @property
    def supplier_select(self) -> Locator:
        return self.page.locator("input[name='supplier_id']").locator("xpath=..").locator(".react-select__input-container")

    @property
    def branch_select(self) -> Locator:
        return self.page.locator("input[name='branch_id']").locator("xpath=..").locator(".react-select__input-container")

    @property
    def reference_input(self) -> Locator:
        return self.page.locator("input[name='reference_no']")

    @property
    def paid_amount_input(self) -> Locator:
        return self.page.locator("input[name='paid_amount']")

    @property
    def purchase_type_select(self) -> Locator:
        return self.page.locator("input[name='purchase_type']").locator("xpath=..").locator(".react-select__input-container")

    @property
    def bank_account_select(self) -> Locator:
        return self.page.locator("input[name='bank_account_id']").locator("xpath=..").locator(".react-select__input-container")

    @property
    def create_button(self) -> Locator:
        return self.page.get_by_role("button", name="Create", exact=True)

    @property
    def add_item_button(self) -> Locator:
        return self.page.get_by_role("button", name="+ Add Item")

    def is_purchases_visible(self) -> bool:
        try:
            self.search_input.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def add_purchase(
        self,
        supplier: str,
        branch: str,
        reference_no: str,
        paid_amount: str,
        purchase_type: str,
        bank_account: str | None = None,
        products_data: list[dict[str, str | int]] | None = None,
    ) -> PurchaseResult:
        self.page.goto(f"{self.url}/add", wait_until="domcontentloaded")

        # 1. Select Branch first
        branch_wrap = self.page.locator("label:has-text('Branch')").locator("xpath=..")
        branch_input = branch_wrap.locator(".react-select__input-container")
        branch_input.wait_for(state="visible", timeout=15000)
        branch_input.click()
        self.page.keyboard.type(branch)
        self.page.wait_for_timeout(300)
        try:
            self.page.locator(".react-select__option").filter(has_text=branch).first.click(timeout=4000)
        except Exception:
            self.page.get_by_role("option", name=branch, exact=False).first.click(timeout=4000)

        # 2. Select Supplier second
        supp_wrap = self.page.locator("label:has-text('Supplier')").locator("xpath=..")
        supp_wrap.locator(".react-select__input-container").click()
        self.page.keyboard.type(supplier)
        self.page.wait_for_timeout(300)
        try:
            self.page.locator(".react-select__option").filter(has_text=supplier).first.click(timeout=4000)
        except Exception:
            self.page.get_by_role("option", name=supplier, exact=False).first.click(timeout=4000)

        # 3. Fill Reference Number
        if reference_no:
            self.reference_input.fill(reference_no)

        # 4. Add Product Lines
        total_amount = Decimal("0.00")
        if products_data:
            for i, item in enumerate(products_data):
                if i > 0:
                    self.add_item_button.click()

                prod_wrap = self.page.locator(f"table tbody tr:nth-child({i+1}) td:nth-child(2)")
                if prod_wrap.count() == 0:
                    prod_wrap = self.page.locator(f"input[name='items.{i}.product_selector']").locator("xpath=..")
                prod_wrap.locator(".react-select__input-container").click()
                prod_name = str(item["product"])
                self.page.keyboard.type(prod_name)
                self.page.wait_for_timeout(300)
                try:
                    self.page.locator(".react-select__option").filter(has_text=prod_name).first.click(timeout=4000)
                except Exception:
                    self.page.get_by_role("option", name=prod_name, exact=False).first.click(timeout=4000)

                qty = Decimal(str(item["quantity"]))
                self.page.locator(f"input[name='items.{i}.quantity']").fill(str(item["quantity"]))

                if "price" in item:
                    price = Decimal(str(item["price"]))
                    self.page.locator(f"input[name='items.{i}.purchase_price']").fill(str(item["price"]))
                    total_amount += qty * price

        # 5. Enter payment after line totals exist. Purchase forms may
        # recalculate paid_amount when a product is selected.
        self.paid_amount_input.fill(str(paid_amount))
        self.paid_amount_input.blur()
        self.page.wait_for_timeout(200)

        if float(paid_amount) > 0:
            self.purchase_type_select.wait_for(state="visible", timeout=5000)
            self.purchase_type_select.click()
            self.page.get_by_role("option", name=purchase_type).click()

            if purchase_type == "Bank Account" and bank_account:
                self.bank_account_select.wait_for(state="visible", timeout=5000)
                self.bank_account_select.click()
                self.page.get_by_role("option", name=bank_account).click()

        # Click Create
        self.create_button.click()

        # Confirmation dialog check if needed
        try:
            confirm_btn = self.page.locator("div.modal-footer button, div[role='dialog'] button").filter(has_text=re.compile(r"^Create$", re.IGNORECASE))
            if confirm_btn.count() > 0 and confirm_btn.first.is_visible():
                confirm_btn.first.click()
        except Exception:
            pass

        # Check for error toasts / alerts first to fail fast
        err_alert = self.page.locator(".Toastify__toast--error, .alert-danger, .invalid-feedback").first
        if err_alert.count() > 0 and err_alert.is_visible():
            raise RuntimeError(f"Purchase creation failed with error: {err_alert.inner_text()}")

        # Wait for success toast or redirect
        toast_found = False
        try:
            toast = self.page.locator(".Toastify__toast-body, .toast-body, [role='alert'], .ant-message").filter(
                has_text=re.compile(r"Purchase.*(?:created|added|success)", re.IGNORECASE)
            ).first
            toast.wait_for(state="visible", timeout=8000)
            toast_found = True
        except Exception:
            try:
                self.page.get_by_text(re.compile(r"Purchase (?:created|added|success)", re.IGNORECASE)).first.wait_for(
                    state="visible", timeout=3000
                )
                toast_found = True
            except Exception:
                try:
                    self.page.wait_for_url(lambda url: "/purchases" in url and "/add" not in url, timeout=5000)
                    toast_found = True
                except Exception:
                    pass

        if not toast_found:
            # Check if any error text is visible on the page
            page_text = self.page.locator("body").inner_text()
            if "error" in page_text.lower() or "failed" in page_text.lower() or "required" in page_text.lower():
                raise RuntimeError(f"Purchase creation failed: validation or API error on page: {page_text[:300]}")

        self.navigate()
        return PurchaseResult(
            reference_no=reference_no,
            supplier_name=supplier,
            branch_name=branch,
            total_amount=total_amount,
            paid_amount=Decimal(str(paid_amount)),
            purchase_type=purchase_type,
        )


    def search_purchase(self, reference_no: str) -> bool:
        self.search_input.fill(reference_no)
        self.search_input.press("Enter")
        try:
            self.page.locator("table tbody tr").filter(has_text=reference_no).first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def view_purchase(
        self,
        reference_no: str,
        expected_supplier: str | None = None,
        expected_branch: str | None = None,
        expected_product: str | None = None,
        expected_quantity: str | None = None,
        expected_total: str | None = None,
        expected_paid_amount: str | None = None,
        expected_payment_status: str | None = None,
    ) -> bool:
        if not self.search_purchase(reference_no):
            return False
        row = self.page.locator("table tbody tr").filter(has_text=reference_no).first
        row.wait_for(state="visible", timeout=5000)

        view_btn = row.get_by_title("view").first
        if not view_btn.is_visible():
            return False

        view_btn.click()
        dialog = self.page.get_by_role("dialog").filter(has_text="View Purchase").first
        try:
            dialog.wait_for(state="visible", timeout=10000)
            dialog.get_by_text(re.compile(r"Supplier:", re.IGNORECASE)).wait_for(
                state="visible", timeout=10000
            )
            content = dialog.inner_text()
            expected_text = {
                "reference number": reference_no,
                "supplier": expected_supplier,
                "branch": expected_branch,
                "total": expected_total,
                "paid amount": expected_paid_amount,
                "payment status": expected_payment_status,
            }
            missing = [
                label
                for label, value in expected_text.items()
                if value and value.casefold() not in content.casefold()
            ]
            assert not missing, (
                f"Purchase View is missing expected {', '.join(missing)}. "
                f"Visible content: {content}"
            )
            if expected_product:
                item_row = dialog.locator("tbody tr").filter(
                    has_text=expected_product
                ).first
                item_row.wait_for(state="visible", timeout=5000)
                if expected_quantity:
                    quantity_text = item_row.locator("td").nth(2).inner_text().strip()
                    try:
                        quantity = Decimal(quantity_text)
                    except InvalidOperation as error:
                        raise AssertionError(
                            f"Purchase quantity is not numeric: {quantity_text!r}"
                        ) from error
                    assert quantity == Decimal(expected_quantity), (
                        f"Expected purchase quantity {expected_quantity}, got {quantity_text}"
                    )
            return True
        finally:
            close_btn = dialog.locator(".btn-close").first
            if close_btn.count() > 0 and close_btn.is_visible():
                close_btn.click()

    def initiate_return(self, reference_no: str) -> None:
        self.search_purchase(reference_no)
        row = self.page.locator("table tbody tr").filter(has_text=reference_no).first
        row.locator("button[title*='return' i], button:has(i.bi-arrow-repeat)").first.click()
        self.page.wait_for_load_state("networkidle")
