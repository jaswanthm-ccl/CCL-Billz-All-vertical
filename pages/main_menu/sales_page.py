from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import Page, Response, TimeoutError as PlaywrightTimeoutError, expect
from pages.common.base_page import BasePage
from utils.models import SaleResult
from utils.tenants import Tenant

class SalesPage(BasePage):
    PATH = "/sales"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)
        self.last_sale_response: dict = {}

    @staticmethod
    def _is_create_response(response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        return response.request.method == "POST" and (path.endswith("/sales") or path.endswith("/sale"))

    def _record_sale_create(self, response: Response) -> None:
        if self._is_create_response(response):
            try:
                body = response.json()
            except Exception:
                body = {}
            self.last_sale_response = {
                "status": response.status,
                "body": body,
                "payload": response.request.post_data_json,
            }

    def scan_serials(self, row_idx: int, serials: list[str]) -> None:
        """Enter tracked unit values (serials) through the line's scanner box; quantity follows the count."""
        row = self.page.locator(f"table tbody tr:nth-child({row_idx})")
        scanner = row.get_by_placeholder(re.compile(r"^Scan .* here", re.I)).first
        scanner.wait_for(state="visible", timeout=10000)
        for serial in serials:
            scanner.fill(str(serial))
            scanner.press("Enter")
            # The accepted serial is listed on the line before the box takes the next one.
            row.get_by_text(str(serial)).first.wait_for(state="visible", timeout=10000)

    @property
    def _search_box(self):
        return self.page.get_by_role("textbox", name="Search...")

    @staticmethod
    def _is_list_response(response: Response, search: str | None = None) -> bool:
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/sales")
        ):
            return False
        return search is None or parse_qs(url.query).get("search", [""])[-1] == search

    def navigate(self) -> None:
        with self.page.expect_response(self._is_list_response, timeout=15000):
            self.page.goto(self.url)

    def is_sales_visible(self) -> bool:
        try:
            expect(self._search_box).to_be_visible(timeout=5000)
            return True
        except AssertionError:
            return False

    def _pick_option(self, text: str) -> None:
        """Click the open react-select's option containing `text`; fails rather than picking another option."""
        self.page.locator(".react-select__option, div[class*='-option']").filter(has_text=text).first.click()

    def _select_branch(self, branch_name: str) -> None:
        self.page.locator("input[name='branch_id']").locator("..").locator(".react-select__input-container").click()
        self.page.keyboard.type(branch_name)
        self._pick_option(branch_name)

    def _select_customer(self, customer_name: str) -> None:
        wrapper = self.page.locator("input[name='customer_id'], input[name='client_id']").locator("xpath=..")
        input_box = wrapper.locator("input[id^='react-select'], input[type='text']")
        if input_box.count() > 0 and input_box.first.is_visible():
            input_box.first.click()
            input_box.first.fill(customer_name)
        else:
            wrapper.locator(".react-select__input-container").click()
            self.page.keyboard.type(customer_name)
        self._pick_option(customer_name)

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
        self._pick_option(product_name)



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
            self._pick_option(payment_method)

    def add_sale(
        self, customer_name: str, branch_name: str, paid_amount: str, price: str,
        product_name: str | None = None, quantity: int | None = None, address_text: str | None = None, payment_method: str = "Cash",
        salesperson_name: str | None = None, sale_date: str | None = None,
        is_emi: bool = False, emi_provider_name: str | None = None, emi_financed_amount: str | None = None,
        serials: list[str] | None = None,
    ) -> SaleResult:
        """serials: tracked unit values to sell on the first line; replaces quantity."""
        self.last_sale_response = {}
        self.page.goto(f"{self.url}/add")
        self.page.locator("input[name='branch_id']").wait_for(state="attached", timeout=15000)

        self._select_branch(branch_name)
        self._select_customer(customer_name)

        if sale_date:
            self.page.locator("input[name='sale_date']").fill(sale_date)

        if salesperson_name:
            try:
                self.page.locator("input[name='employee_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
            except Exception:
                self.page.locator("div:nth-child(3) > .mb-3 > .css-b62m3t-container > .react-select__control > .react-select__value-container > .react-select__input-container").click()
            self.page.get_by_role("option", name=salesperson_name).click()

        if address_text:
            self._select_address(address_text)

        if product_name:
            self._select_product_in_row(1, product_name)
        if serials:
            self.scan_serials(1, serials)
            quantity = len(serials)
        elif quantity is not None:
            qty_input = self.page.locator("tr:nth-child(1)").get_by_placeholder("Quantity")
            qty_input.wait_for(state="visible", timeout=10000)
            if qty_input.is_editable():
                qty_input.fill(str(quantity))

        price_input = self.page.get_by_placeholder("Price").first
        price_input.fill(str(price))
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
                self._pick_option(emi_provider_name)

            if emi_financed_amount:
                financed_input = self.page.locator('input[name="emi_financed_amount"]')
                if financed_input.is_editable():
                    financed_input.fill(str(emi_financed_amount))
                else:
                    # Read-only when the app derives it as total minus paid amount.
                    shown = financed_input.input_value()
                    assert Decimal(shown or "0") == Decimal(str(emi_financed_amount)), (
                        f"EMI financed amount shows {shown}, expected {emi_financed_amount}"
                    )

        # The product's selling price can land after our fill; make sure the line still has ours.
        if price_input.input_value() != str(price):
            price_input.fill(str(price))

        self.page.on("response", self._record_sale_create)
        try:
            with self.page.expect_response(self._is_create_response, timeout=20000):
                self.page.get_by_role("button", name="Create").click()
                confirm_btn = self.page.locator(
                    "div.modal-footer button, div[role='dialog'] button, .modal-dialog button"
                ).filter(has_text=re.compile(r"^(?:Create|Yes|Confirm)$", re.IGNORECASE))
                if confirm_btn.count() > 0 and confirm_btn.first.is_visible():
                    confirm_btn.first.click()
        except PlaywrightTimeoutError:
            errors = [t.strip() for t in self.page.locator(".invalid-feedback, .text-danger, .alert-danger").all_inner_texts()]
            raise RuntimeError(
                f"Sale was not submitted for {customer_name}; form errors: {[e for e in errors if e and e != '*']}"
            ) from None
        finally:
            self.page.remove_listener("response", self._record_sale_create)

        record = self.last_sale_response
        if record.get("status") not in (200, 201):
            body = record.get("body") or {}
            raise RuntimeError(
                f"Sale rejected ({record.get('status')}) for {customer_name}: {body.get('message')} {body.get('errors') or ''}"
            )
        sale = (record.get("body") or {}).get("data") or {}
        invoice_no = str(sale.get("invoice_id") or "").lstrip("#").strip()

        self.navigate()

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
            sale_id=str(sale["id"]) if sale.get("id") is not None else None,
        )

    def view_sale_by_invoice(self, invoice_no: str) -> dict[str, str | bool]:
        """View sale details by searching strictly for the exact invoice number."""
        self.search_sale(invoice_no)
        row = self.page.locator("table tbody tr").filter(has_text=invoice_no).first
        row.wait_for(state="visible", timeout=10000)
        row.locator('button[title="view"], button[title="View"], a[title="view"]').first.click()
        return self._read_open_sale_dialog()

    def view_sale_details(self, customer_name: str | None = None) -> dict[str, str | bool]:
        if customer_name:
            self.search_sale(customer_name)
        row = self.page.locator("table tbody tr").first
        row.locator('button[title="view"], button[title="View"], a[title="view"]').first.click()
        return self._read_open_sale_dialog()

    def search_sale(self, query: str) -> bool:
        """Search the sales list (live search); True when a row containing `query` is shown."""
        if self._search_box.input_value() != query:
            with self.page.expect_response(lambda r: self._is_list_response(r, query), timeout=15000):
                self._search_box.fill(query)
        try:
            expect(self.page.locator("table tbody tr").filter(has_text=query).first).to_be_visible(timeout=10000)
            return True
        except AssertionError:
            return False

    def _read_open_sale_dialog(self) -> dict[str, str | bool]:
        """Read the open sale-details dialog once its line table has rendered, then close it."""
        dialog = self.page.get_by_role("dialog")
        dialog.locator("table").first.wait_for(state="visible", timeout=10000)
        content = dialog.inner_text()
        details = {
            "has_emi_outstanding": "EMI Outstanding" in content,
            "has_pending_status": "Pending" in content,
            "content": content,
        }
        close_btn = dialog.locator(".btn-close")
        if close_btn.count() > 0 and close_btn.first.is_visible():
            close_btn.first.click()
        else:
            dialog.get_by_role("button", name="Close").first.click()
        dialog.wait_for(state="hidden", timeout=5000)
        return details


    def filter_sales(self, salesperson_name: str | None = None, branch_name: str | None = None) -> None:
        self.navigate()

        expand_btn = self.page.get_by_role("button", name="Expand filters")
        if expand_btn.count() and expand_btn.is_visible():
            expand_btn.click()

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

        if branch_name:
            try:
                self.page.locator("input[name='branch_id']").locator("xpath=..").locator(".react-select__input-container").click(timeout=3000)
            except Exception:
                self.page.locator(".react-select__input-container").first.click()
            self.page.get_by_role("option", name=branch_name).click()

        with self.page.expect_response(self._is_list_response, timeout=15000):
            self.page.get_by_role("button", name="Filter", exact=True).click()

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
        self.navigate()

    def initiate_sale_return(self, query: str) -> None:
        self.search_sale(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        row.get_by_title("Sale Return").first.click()
        self.page.get_by_role("button", name="Return").wait_for(state="visible", timeout=15000)

    def download_invoice(self, query: str) -> str | None:
        self.search_sale(query)
        row = self.page.locator("table tbody tr").filter(has_text=query).first
        
        with self.page.expect_download() as download_info:
            row.get_by_title("Download").first.click()
        download = download_info.value
        return download.path()
