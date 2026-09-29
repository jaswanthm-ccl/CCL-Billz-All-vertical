from __future__ import annotations

from playwright.sync_api import Download, Page
from utils.constants import PURCHASE_REQUESTS_URL
from pages.common.form_page import has_required_field_feedback, has_validation_feedback

class PurchaseRequestPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = PURCHASE_REQUESTS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)

    def is_purchase_requests_visible(self) -> bool:
        try:
            self.page.get_by_role("textbox", name="Search...").wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def _select_product_in_row(self, row_idx: int, product_name: str) -> None:
        # Select product in row row_idx (1-based index)
        # Try to locate the react-select container within column 2 of the specified row
        row_locator = self.page.locator(f"tr:nth-child({row_idx}) > td:nth-child(2)")
        try:
            row_locator.locator(".react-select__input-container").click()
        except Exception:
            self.page.locator(
                f"tr:nth-child({row_idx}) > td:nth-child(2) > .mb-3 > .css-b62m3t-container "
                f"> .react-select__control > .react-select__value-container > .react-select__input-container"
            ).click()
        self.page.get_by_role("option", name=product_name).click()

    def _fill_quantity_in_row(self, row_idx: int, quantity: int | str) -> None:
        # Fill quantity field in row row_idx (1-based index)
        self.page.locator(f"tr:nth-child({row_idx})").get_by_placeholder("Quantity").fill(str(quantity))

    def _fill_purchase_request_form(self, branch: str, supplier: str, priority: str, products_data: list[dict[str, str | int]], notes: str | None = None) -> None:
        # 1. Select Branch
        try:
            self.page.locator("input[name='branch_id']").locator("xpath=..").locator(
                ".react-select__input-container"
            ).click()
        except Exception:
            self.page.locator(".react-select__input-container").first.click()
        self.page.get_by_role("option", name=branch).click()

        # 2. Select Supplier
        try:
            self.page.locator("input[name='supplier_id']").locator("xpath=..").locator(
                ".react-select__input-container"
            ).click()
        except Exception:
            self.page.locator(
                ".react-select__control.css-mgvwv9-control > .react-select__value-container "
                "> .react-select__input-container"
            ).first.click()
        self.page.get_by_role("option", name=supplier).click()

        # 3. Select Priority
        try:
            self.page.locator("input[name='priority']").locator("xpath=..").locator(
                ".react-select__input-container"
            ).click()
        except Exception:
            self.page.locator(
                "div:nth-child(4) > .mb-3 > .css-b62m3t-container > .react-select__control "
                "> .react-select__value-container > .react-select__input-container"
            ).click()
        self.page.get_by_role("option", name=priority).click()

        # 4. Fill Notes
        if notes:
            self.page.get_by_role("button", name="Add Notes").click()
            self.page.locator("textarea[name=\"notes\"]").fill(notes)

        # 5. Add Product Lines
        # products_data is a list of dicts: [{"product": name, "quantity": qty}]
        for i, item in enumerate(products_data):
            row_idx = i + 1
            if i > 0:
                self.page.get_by_role("button", name="+ Add Item").click()
            self._select_product_in_row(row_idx, item["product"])
            self._fill_quantity_in_row(row_idx, item["quantity"])

    def add_purchase_request(self, branch: str, supplier: str, priority: str, products_data: list[dict[str, str | int]], notes: str | None = None) -> None:
        self.page.goto(f"{self.url}/add")
        self.page.wait_for_load_state("networkidle")

        self._fill_purchase_request_form(branch, supplier, priority, products_data, notes)

        # Click Create
        self.page.get_by_role("button", name="Create").first.click()

        toast = self.page.get_by_text("Purchase Request created")
        toast.wait_for(state="visible", timeout=10000)
        try:
            toast.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass
        self.navigate()
        self.page.wait_for_load_state("networkidle")

    def validate_required_fields(self) -> bool:
        self.page.goto(f"{self.url}/add")
        self.page.wait_for_load_state("networkidle")
        create_button = self.page.get_by_role("button", name="Create").first
        if create_button.is_disabled():
            return True
        create_button.click()
        return has_required_field_feedback(self.page)

    def validate_invalid_quantity(self, branch: str, supplier: str, priority: str, product: str, quantity: str | int) -> bool:
        self.page.goto(f"{self.url}/add")
        self.page.wait_for_load_state("networkidle")
        self._fill_purchase_request_form(
            branch,
            supplier,
            priority,
            [{"product": product, "quantity": quantity}],
        )
        quantity_input = self.page.get_by_placeholder("Quantity").first
        if not quantity_input.evaluate("element => element.validity.valid"):
            return True

        self.page.get_by_role("button", name="Create").first.click()
        return has_required_field_feedback(self.page, timeout=2000) or has_validation_feedback(
            self.page,
            r"quantity.*(?:positive|greater|zero|invalid|required)",
            r"(?:positive|valid).*quantity",
            timeout=2000,
        )

    def search_purchase_request(self, supplier_name: str, retries: int = 2) -> bool:
        search_box = self.page.get_by_role("textbox", name="Search...")
        row = self.page.locator("table tbody tr").first

        # Retries absorb the gap between a create/retrieve toast firing and
        # the backend actually finishing the re-index that the list search
        # depends on - networkidle alone doesn't guarantee that has happened.
        for attempt in range(retries + 1):
            search_box.click()
            search_box.fill("")
            search_box.fill(supplier_name)
            search_box.press("Enter")
            self.page.wait_for_load_state("networkidle", timeout=5000)

            try:
                row.wait_for(state="visible", timeout=5000)
                text = row.inner_text().lower()
                if "no data" not in text and "no records" not in text and "no entries" not in text:
                    return True
            except Exception:
                pass

            if attempt < retries:
                self.page.wait_for_timeout(1000)

        return False

    def view_purchase_request(self, supplier_name: str, first_product_name: str, priority: str) -> bool:
        self.search_purchase_request(supplier_name)
        self.page.get_by_title("view").first.click()

        # Verify details anywhere on the page or modal
        try:
            self.page.get_by_text(first_product_name).first.wait_for(state="visible", timeout=5000)
            self.page.get_by_text(priority, exact=False).first.wait_for(state="visible", timeout=5000)
            is_valid = True
        except Exception:
            is_valid = False

        try:
            self.page.locator(".btn-close").click()
        except Exception:
            pass
        return is_valid

    def purchase_request_contains_products(self, supplier_name: str, product_names: list[str]) -> bool:
        self.search_purchase_request(supplier_name)
        self.page.get_by_title("view").first.click()
        try:
            for product_name in product_names:
                self.page.get_by_text(product_name, exact=False).first.wait_for(
                    state="visible", timeout=5000
                )
            return True
        except Exception:
            return False
        finally:
            try:
                self.page.locator(".btn-close").click()
            except Exception:
                pass

    def edit_purchase_request(self, supplier_name: str, new_product_name: str, new_quantity: str | int) -> bool:
        self.search_purchase_request(supplier_name)
        self.page.get_by_title("edit").first.click()
        self.page.wait_for_load_state("networkidle")

        # Add another item
        self.page.get_by_role("button", name="+ Add Item").click()
        # Row 2 (assuming row 1 exists)
        self._select_product_in_row(2, new_product_name)
        self._fill_quantity_in_row(2, new_quantity)

        self.page.get_by_role("button", name="Update").click()

        toast = self.page.get_by_text("Purchase Request updated")
        try:
            toast.wait_for(state="visible", timeout=5000)
            try:
                toast.wait_for(state="hidden", timeout=5000)
            except Exception:
                pass
            return True
        except Exception:
            return False

    def download_purchase_request(self, supplier_name: str) -> Download:
        self.search_purchase_request(supplier_name)
        with self.page.expect_download() as download_info:
            self.page.get_by_title("download").first.click()
        return download_info.value

    def delete_purchase_request(self, supplier_name: str) -> bool:
        self.search_purchase_request(supplier_name)
        self.page.get_by_title("delete").first.click()

        try:
            modal = self.page.get_by_role("dialog")
            modal.wait_for(state="visible", timeout=3000)
            modal.get_by_role("button", name="Delete Purchase Request").click(force=True)
        except Exception:
            self.page.get_by_role("button", name="Delete Purchase Request").click(force=True)

        toast = self.page.get_by_text("Deleted successfully.")
        try:
            toast.wait_for(state="visible", timeout=5000)
            try:
                toast.wait_for(state="hidden", timeout=5000)
            except Exception:
                pass
            return True
        except Exception:
            return False

    def retrieve_purchase_request(self, supplier_name: str) -> bool:
        self.search_purchase_request(supplier_name)
        self.page.get_by_title("delete").first.click() # The delete icon acts as restore when deleted

        try:
            modal = self.page.get_by_role("dialog")
            modal.wait_for(state="visible", timeout=3000)
            modal.get_by_role("button", name="Retrieve Purchase Request").click(force=True)
        except Exception:
            self.page.get_by_role("button", name="Retrieve Purchase Request").click(force=True)

        toast = self.page.get_by_text("Retrieved successfully.")
        try:
            toast.wait_for(state="visible", timeout=5000)
            try:
                toast.wait_for(state="hidden", timeout=5000)
            except Exception:
                pass
            return True
        except Exception:
            return False
