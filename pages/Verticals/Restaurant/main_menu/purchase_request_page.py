"""Restaurant Purchase Request page object."""

from pages.main_menu.purchase_request_page import (
    PurchaseRequestPage as DefaultPurchaseRequestPage,
)
from utils.res_constants import RES_PURCHASE_REQUESTS_URL


class PurchaseRequestPage(DefaultPurchaseRequestPage):
    """Use the shared Purchase Request workflow against the Restaurant tenant."""

    def __init__(self, page) -> None:
        super().__init__(page)
        self.url = RES_PURCHASE_REQUESTS_URL

    def _select_named_option(self, field_name: str, option_name: str) -> None:
        control = self.page.locator(f"input[name='{field_name}']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        control.click()
        self.page.get_by_role("option", name=option_name, exact=True).click()

    def _fill_purchase_request_form(
        self,
        branch: str,
        supplier: str,
        priority: str,
        products_data: list[dict[str, str | int]],
        notes: str | None = None,
    ) -> None:
        """Fill the Restaurant minimal Purchase Order form.

        Priority is intentionally omitted by the Restaurant template and is
        supplied by backend defaults.
        """
        self._select_named_option("branch_id", branch)
        self._select_named_option("supplier_id", supplier)

        if notes:
            notes_button = self.page.get_by_role("button", name="Add Notes")
            if notes_button.is_visible():
                notes_button.click()
                self.page.locator('textarea[name="notes"]').fill(notes)

        for index, item in enumerate(products_data):
            row_index = index + 1
            if index > 0:
                self.page.get_by_role("button", name="+ Add Item").click()
            self._select_product_in_row(row_index, str(item["product"]))
            self._fill_quantity_in_row(row_index, item["quantity"])

    def ensure_deleted(self, supplier_name: str) -> None:
        """Delete an active request without restoring an already-deleted request."""
        self.navigate()
        self.page.wait_for_load_state("networkidle")
        if not self.search_purchase_request(supplier_name):
            return

        self.page.get_by_title("delete").first.click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=3000)
        delete_button = dialog.get_by_role(
            "button", name="Delete Purchase Order", exact=True
        )
        if delete_button.is_visible():
            delete_button.click(force=True)
            self.page.get_by_text("Deleted successfully.").wait_for(
                state="visible", timeout=5000
            )
        else:
            close_button = dialog.locator(".btn-close").first
            if close_button.is_visible():
                close_button.click()
            else:
                self.page.keyboard.press("Escape")

    def _change_deleted_state(
        self, supplier_name: str, action_label: str, toast_text: str
    ) -> bool:
        if not self.search_purchase_request(supplier_name):
            return False
        self.page.get_by_title("delete").first.click()
        dialog = self.page.get_by_role("dialog")
        dialog.wait_for(state="visible", timeout=3000)
        dialog.get_by_role("button", name=action_label, exact=True).click(force=True)
        try:
            self.page.get_by_text(toast_text).wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def delete_purchase_request(self, supplier_name: str) -> bool:
        return self._change_deleted_state(
            supplier_name, "Delete Purchase Order", "Deleted successfully."
        )

    def retrieve_purchase_request(self, supplier_name: str) -> bool:
        return self._change_deleted_state(
            supplier_name, "Retrieve Purchase Order", "Retrieved successfully."
        )
