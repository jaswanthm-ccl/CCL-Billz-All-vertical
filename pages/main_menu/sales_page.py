from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page
from utils.constants import SALES_URL
from utils.models import SaleResult

class SalesPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = SALES_URL

    def navigate(self) -> None:
        self.page.goto(self.url)

    def is_sales_visible(self) -> bool:
        try:
            self.page.get_by_role("textbox", name="Search...").wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def _select_branch(self, branch_name: str) -> None:
        branch_input = self.page.locator("input[name='branch_id']").locator("..").locator(".react-select__input-container")
        branch_input.click()
        self.page.keyboard.type(branch_name)
        self.page.wait_for_timeout(400)
        try:
            self.page.locator(".react-select__option").filter(has_text=branch_name).first.click(timeout=5000)
        except Exception:
            self.page.get_by_role("option", name=branch_name, exact=False).first.click(timeout=5000)

    def _select_customer(self, customer_name: str) -> None:
        wrapper = self.page.locator("input[name='customer_id'], input[name='client_id']").locator("xpath=..")
        input_box = wrapper.locator("input[id^='react-select'], input[type='text']")
        if input_box.count() > 0 and input_box.first.is_visible():
            input_box.first.click()
            input_box.first.fill(customer_name)
        else:
            cust_input = wrapper.locator(".react-select__input-container")
            cust_input.click()
            self.page.keyboard.type(customer_name)
        self.page.wait_for_timeout(500)
        try:
            self.page.locator(".react-select__option").filter(has_text=customer_name).first.click(timeout=5000)
        except Exception:
            self.page.get_by_role("option", name=customer_name, exact=False).first.click(timeout=5000)

    def _select_address(self, address_text: str) -> None:
        """Select a specific address from the customer's saved addresses."""
        try:
            self.page.locator("input[name='billing_address_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
        except Exception:
            self.page.locator(
                ".react-select__control > .react-select__value-container > .react-select__input-container"
            ).nth(3).click()
        try:
            self.page.get_by_role("option", name=address_text, exact=False).first.click(timeout=3000)
        except Exception:
            self.page.locator(".react-select__option").filter(has_text=address_text).first.click()

    def _select_product_in_row(self, row_idx: int, product_name: str) -> None:
        row_locator = self.page.locator(f"table tbody tr:nth-child({row_idx}) td:nth-child(2)")
        if row_locator.count() == 0:
            row_locator = self.page.locator(f"input[name='items.{row_idx-1}.product_selector']").locator("xpath=..")
        
        input_container = row_locator.locator(".react-select__control, .react-select__input-container").first
        input_container.wait_for(state="visible", timeout=10000)
        input_container.click()
        
        search = row_locator.locator('input[role="combobox"], input[type="text"], input[id^="react-select"]')
        if search.count() > 0 and search.first.is_visible():
            search.first.press_sequentially(product_name, delay=20)
        else:
            self.page.keyboard.type(product_name)
        self.page.wait_for_timeout(500)

        try:
            opt = self.page.get_by_role("option", name=product_name, exact=False).first
            opt.wait_for(state="visible", timeout=6000)
            opt.click()
        except Exception:
            matching = self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=product_name)
            if matching.count() > 0:
                matching.first.wait_for(state="visible", timeout=6000)
                matching.first.click()
            else:
                self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(400)




    def _select_payment_method(self, payment_method: str) -> None:
        """payment_method is either "Cash" or the exact name of a Bank Account."""
        self.page.get_by_text(re.compile(r"^Sale type \*")).wait_for(state="visible", timeout=5000)

        target_sale_type = "Cash" if payment_method == "Cash" else "Bank Account"
        self.page.locator("input[name='sale_type']").locator("xpath=..").locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=target_sale_type).click()

        if target_sale_type == "Bank Account":
            self.page.get_by_text(re.compile(r"^Bank Account \*")).wait_for(state="visible", timeout=5000)
            self.page.locator("input[name='bank_account_id']").locator("xpath=..").locator(".react-select__input-container").click()
            self.page.keyboard.type(payment_method)
            self.page.wait_for_timeout(300)
            try:
                self.page.locator(".react-select__option").filter(has_text=payment_method).first.click(timeout=4000)
            except Exception:
                self.page.get_by_role("option", name=payment_method, exact=False).click(timeout=4000)

    def add_sale(
        self, customer_name: str, branch_name: str, paid_amount: str, price: str,
        product_name: str | None = None, quantity: int | None = None, address_text: str | None = None, payment_method: str = "Cash",
        salesperson_name: str | None = None, sale_date: str | None = None,
        is_emi: bool = False, emi_provider_name: str | None = None, emi_financed_amount: str | None = None
    ) -> SaleResult:
        self.page.goto(f"{self.url}/add")
        try:
            self.page.wait_for_load_state("domcontentloaded")
            self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        self._select_branch(branch_name)
        self.page.wait_for_timeout(800)
        self._select_customer(customer_name)
        self.page.wait_for_timeout(800)

        if sale_date:
            self.page.locator("input[name='sale_date']").fill(sale_date)

        if salesperson_name:
            try:
                self.page.locator("input[name='employee_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
            except Exception:
                self.page.locator("div:nth-child(3) > .mb-3 > .css-b62m3t-container > .react-select__control > .react-select__value-container > .react-select__input-container").click()
            self.page.get_by_role("option", name=salesperson_name).click()
            self.page.wait_for_timeout(500)

        if address_text:
            self._select_address(address_text)

        if product_name:
            self._select_product_in_row(1, product_name)
        if quantity is not None:
            qty_input = self.page.locator("tr:nth-child(1)").get_by_placeholder("Quantity")
            try:
                qty_input.wait_for(state="visible", timeout=5000)
                if qty_input.is_editable():
                    qty_input.fill(str(quantity))
            except Exception:
                pass

        self.page.get_by_placeholder("Price").first.fill(str(price))
        self.page.locator('input[name="paid_amount"]').fill(str(paid_amount))


        # Only select payment method if paid_amount > 0
        if float(paid_amount) > 0:
            self._select_payment_method(payment_method)

        # Handle EMI Sale checkbox & Provider
        if is_emi:
            emi_checkbox = self.page.get_by_role("checkbox", name=re.compile(r"EMI Sale", re.I))
            emi_checkbox.wait_for(state="visible", timeout=5000)
            emi_checkbox.check()

            if emi_provider_name:
                provider_wrap = self.page.locator("label:has-text('EMI Provider'), label:has-text('Provider')").locator("xpath=..")
                if provider_wrap.count() > 0:
                    provider_wrap.locator(".react-select__input-container").click()
                else:
                    self.page.locator(".react-select__input-container").last.click()
                self.page.keyboard.type(emi_provider_name)
                self.page.wait_for_timeout(400)
                try:
                    self.page.locator(".react-select__option").filter(has_text=emi_provider_name).first.click(timeout=4000)
                except Exception:
                    self.page.get_by_role("option", name=emi_provider_name, exact=False).first.click(timeout=4000)

            if emi_financed_amount:
                self.page.locator('input[name="emi_financed_amount"]').fill(str(emi_financed_amount))

        self.page.get_by_role("button", name="Create").click()
        try:
            confirm_btn = self.page.locator("div.modal-footer button, div[role='dialog'] button, .modal-dialog button").filter(has_text=re.compile(r"^(?:Create|Yes|Confirm)$", re.IGNORECASE))
            if confirm_btn.count() > 0 and confirm_btn.first.is_visible():
                confirm_btn.first.click()
        except Exception:
            pass

        # Check for error toasts / alerts first to fail fast
        err_alert = self.page.locator(".Toastify__toast--error, .alert-danger, .invalid-feedback").first
        if err_alert.count() > 0 and err_alert.is_visible():
            raise RuntimeError(f"Sale creation failed with error: {err_alert.inner_text()}")

        # Wait for toast or redirect
        toast_found = False
        try:
            toast = self.page.locator(".Toastify__toast-body, .toast-body, [role='alert'], .ant-message").filter(
                has_text=re.compile(r"Sale.*(?:created|added|success)", re.IGNORECASE)
            ).first
            toast.wait_for(state="visible", timeout=10000)
            toast_found = True
        except Exception:
            try:
                self.page.get_by_text(re.compile(r"Sale (?:created|added)", re.IGNORECASE)).first.wait_for(state="visible", timeout=5000)
                toast_found = True
            except Exception:
                pass
        
        # Navigate to Sales List to retrieve invoice number
        try:
            self.page.get_by_role("button", name="Sales List").click(timeout=3000)
        except Exception:
            self.navigate()
        self.page.wait_for_load_state("networkidle")

        # Search for customer to find the created invoice number
        self.search_sale(customer_name)
        first_row = self.page.locator("table tbody tr").filter(has_text=customer_name).first
        first_row.wait_for(state="visible", timeout=10000)
        
        cells = first_row.locator("td").all()
        # Invoice number is usually first or second column
        invoice_no = cells[0].inner_text().strip() if len(cells) > 0 else ""
        if not invoice_no or invoice_no == customer_name:
            invoice_no = cells[1].inner_text().strip() if len(cells) > 1 else ""
        invoice_no = invoice_no.lstrip("#").strip()

        qty_val = Decimal(str(quantity if quantity is not None else 1))
        unit_price = Decimal(str(price))
        total_amount = qty_val * unit_price

        return SaleResult(
            invoice_no=invoice_no,
            customer_name=customer_name,
            branch_name=branch_name,
            total_amount=total_amount,
            paid_amount=Decimal(str(paid_amount)),
            payment_method=payment_method,
        )

    def view_sale_by_invoice(self, invoice_no: str) -> dict[str, str | bool]:
        """View sale details by searching strictly for the exact invoice number."""
        self.search_sale(invoice_no)
        row = self.page.locator("table tbody tr").filter(has_text=invoice_no).first
        row.wait_for(state="visible", timeout=10000)
        row.locator('button[title="view"], button[title="View"], a[title="view"]').first.click()

        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=10000)
        self.page.wait_for_timeout(1000)

        details = {
            "has_emi_outstanding": dialog.locator(":has-text('EMI Outstanding')").count() > 0 or dialog.get_by_role("cell", name="EMI Outstanding").count() > 0 or "EMI Outstanding" in dialog.inner_text(),
            "has_pending_status": dialog.locator(":has-text('Pending')").count() > 0 or dialog.get_by_role("cell", name="Pending").count() > 0 or "Pending" in dialog.inner_text(),
            "content": dialog.inner_text(),
        }

        close_btn = dialog.locator(".btn-close")
        if close_btn.count() > 0 and close_btn.first.is_visible():
            close_btn.first.click()
        else:
            dialog.get_by_role("button", name="Close").first.click()
        dialog.wait_for(state="hidden", timeout=5000)
        return details

    def view_sale_details(self, customer_name: str | None = None) -> dict[str, str | bool]:
        if customer_name:
            self.search_sale(customer_name)
        row = self.page.locator("table tbody tr").first
        row.locator('button[title="view"], button[title="View"], a[title="view"]').first.click()

        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=10000)

        # Allow modal body to populate data
        self.page.wait_for_timeout(1000)

        details = {
            "has_emi_outstanding": dialog.locator(":has-text('EMI Outstanding')").count() > 0 or dialog.get_by_role("cell", name="EMI Outstanding").count() > 0 or "EMI Outstanding" in dialog.inner_text(),
            "has_pending_status": dialog.locator(":has-text('Pending')").count() > 0 or dialog.get_by_role("cell", name="Pending").count() > 0 or "Pending" in dialog.inner_text(),
            "content": dialog.inner_text(),
        }

        close_btn = dialog.locator(".btn-close")
        if close_btn.count() > 0:
            close_btn.click()
        else:
            dialog.get_by_role("button", name="Close").click()
        dialog.wait_for(state="hidden", timeout=5000)
        return details

    def search_sale(self, query: str) -> bool:
        search_box = self.page.get_by_role("textbox", name="Search...")
        search_box.fill(query)
        search_box.press("Enter")
        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        try:
            self.page.locator("table tbody tr").filter(has_text=query).first.wait_for(
                state="visible", timeout=10000
            )
            return True
        except Exception:
            return False



    def filter_sales(self, salesperson_name: str | None = None, branch_name: str | None = None) -> None:
        self.navigate()
        self.page.wait_for_load_state("networkidle")

        try:
            expand_btn = self.page.get_by_role("button", name="Expand filters")
            if expand_btn.is_visible():
                expand_btn.click()
        except Exception:
            pass

        if salesperson_name:
            try:
                self.page.locator("input[name='employee_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
            except Exception:
                try:
                    self.page.locator("input[name='user_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
                except Exception:
                    try:
                        self.page.locator("div").filter(has_text=re.compile(r"^Select\.\.\.$")).nth(2).click()
                    except Exception:
                        self.page.locator(".react-select__input-container").last.click()
            self.page.get_by_role("option", name=salesperson_name).click()
            self.page.wait_for_timeout(500)

        if branch_name:
            try:
                self.page.locator("input[name='branch_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
            except Exception:
                self.page.locator(".react-select__input-container").first.click()
            self.page.get_by_role("option", name=branch_name).click()
            self.page.wait_for_timeout(500)

        self.page.get_by_role("button", name="Filter", exact=True).click()
        self.page.wait_for_load_state("networkidle")

    def view_sale(self, query: str, branch_name: str, salesperson_name: str) -> bool:
        self.search_sale(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.click()
        row.get_by_title("view").first.click()

        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=5000)

        # Verify details
        dialog.get_by_text(query).first.wait_for(state="visible", timeout=5000)
        dialog.get_by_text(branch_name).first.wait_for(state="visible", timeout=5000)
        dialog.get_by_text(salesperson_name).first.wait_for(state="visible", timeout=5000)

        # Close dialog
        try:
            self.page.locator(".btn-close").click()
        except Exception:
            dialog.get_by_role("button").filter(has_text=re.compile(r"^$")).first.click()
        dialog.wait_for(state="hidden", timeout=5000)
        return True

    def edit_sale(self, query: str, new_quantity: str | int) -> None:
        self.search_sale(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("Edit").first.click()

        # Update Quantity
        qty_input = self.page.get_by_placeholder("Quantity").first
        qty_input.click()
        qty_input.fill(str(new_quantity))

        # Click Update
        self.page.get_by_role("button", name="Update").click()
        
        toast = self.page.get_by_text("Sale updated successfully.")
        toast.wait_for(state="visible", timeout=10000)
        
        # Click Sales List or navigate
        try:
            self.page.get_by_role("button", name="Sales List").click(timeout=3000)
        except Exception:
            self.navigate()
        self.page.wait_for_load_state("networkidle")

    def initiate_sale_return(self, query: str) -> None:
        self.search_sale(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("Sale Return").first.click()
        self.page.wait_for_load_state("networkidle")

    def download_invoice(self, query: str) -> str | None:
        self.search_sale(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        
        with self.page.expect_download() as download_info:
            row.get_by_title("Download").first.click()
        download = download_info.value
        return download.path()
