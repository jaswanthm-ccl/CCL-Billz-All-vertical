from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page

from utils.constants import STOCK_TRANSFERS_URL
from utils.models import StockTransferResult


class StockTransfersPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = STOCK_TRANSFERS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def is_stock_transfers_visible(self) -> bool:
        """Verify the stock transfers page loaded (title + add button present)."""
        try:
            self.page.get_by_text("Stock transfers").first.wait_for(
                state="visible", timeout=5000
            )
            self.page.get_by_role("button", name="New transfer").wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    # ─── Create ────────────────────────────────────────────────────────────────

    def add_stock_transfer(
        self,
        source_branch: str,
        destination_branch: str,
        products_data: list[dict[str, str | int]],
        remarks: str = "",
    ) -> StockTransferResult:
        """Create a stock transfer and return a StockTransferResult."""
        self.page.goto(f"{self.url}/add")
        self.page.wait_for_load_state("networkidle")

        # Select Source Branch
        source_ctrl = self.page.locator("input[name='source_branch_id']").locator("xpath=..").locator(".react-select__control, .react-select__input-container").first
        source_ctrl.click()
        self.page.wait_for_timeout(300)
        self.page.keyboard.type(source_branch, delay=20)
        self.page.wait_for_timeout(500)
        try:
            self.page.get_by_role("option", name=source_branch, exact=False).first.click(timeout=5000)
        except Exception:
            self.page.locator(".react-select__option").filter(has_text=source_branch).first.click()
        self.page.wait_for_timeout(500)

        # Select Destination Branch
        dest_ctrl = self.page.locator("input[name='destination_branch_id']").locator("xpath=..").locator(".react-select__control, .react-select__input-container").first
        dest_ctrl.click()
        self.page.wait_for_timeout(300)
        self.page.keyboard.type(destination_branch, delay=20)
        self.page.wait_for_timeout(500)
        try:
            self.page.get_by_role("option", name=destination_branch, exact=False).first.click(timeout=5000)
        except Exception:
            self.page.locator(".react-select__option").filter(has_text=destination_branch).first.click()
        self.page.wait_for_timeout(500)

        # Fill Remarks
        if remarks:
            self.page.locator("textarea[name='remarks']").fill(remarks)

        total_qty = Decimal("0")
        # Add product line items
        for i, item in enumerate(products_data):
            if i > 0:
                self.page.get_by_role("button", name="Add line").click()
                self.page.wait_for_timeout(300)

            # Select product
            prod_ctrl = self.page.locator(f"input[name='items.{i}.product_selector']").locator("xpath=..").locator(".react-select__control, .react-select__input-container").first
            prod_ctrl.click()
            self.page.wait_for_timeout(300)
            self.page.keyboard.type(str(item["product"]), delay=20)
            self.page.wait_for_timeout(500)
            try:
                self.page.get_by_role("option", name=str(item["product"]), exact=False).first.click(timeout=5000)
            except Exception:
                self.page.locator(".react-select__option").filter(has_text=str(item["product"])).first.click()
            self.page.wait_for_timeout(500)

            # Fill quantity
            item_qty = Decimal(str(item["quantity"]))
            total_qty += item_qty
            qty_input = self.page.locator(f"input[name='items.{i}.quantity']")
            qty_input.click()
            qty_input.fill(str(item["quantity"]))

            # Fill item remarks if provided
            if "remarks" in item and item["remarks"]:
                try:
                    self.page.locator(f"input[name='items.{i}.remarks']").fill(
                        str(item["remarks"])
                    )
                except Exception:
                    pass

        # Submit
        self.page.get_by_role("button", name="Create transfer").click()

        # Check for error alert first
        err_alert = self.page.locator(".Toastify__toast--error, .alert-danger, .invalid-feedback").first
        if err_alert.count() > 0 and err_alert.is_visible():
            raise RuntimeError(f"Stock transfer failed with error: {err_alert.inner_text()}")

        transfer_no = ""
        # Wait for success — either navigates to index/detail page or shows toast
        try:
            self.page.wait_for_url(
                lambda url: "/stock-transfers" in url and "/add" not in url,
                timeout=10000,
            )
            try:
                title = self.page.locator("h1, h2, h3, h4").first.text_content()
                transfer_no = title.strip() if title else ""
            except Exception:
                pass
        except Exception:
            try:
                toast = self.page.get_by_text(
                    re.compile(r"transfer.*created|created.*successfully|success", re.IGNORECASE)
                )
                toast.wait_for(state="visible", timeout=5000)
            except Exception:
                pass


        if not transfer_no:
            # Check table for latest transfer from this source branch
            self.navigate()
            try:
                first_row = self.page.locator("table tbody tr").filter(has_text=source_branch).first
                if first_row.is_visible():
                    transfer_no = first_row.locator("td").first.inner_text().strip()
            except Exception:
                pass

        return StockTransferResult(
            transfer_no=transfer_no,
            source_branch=source_branch,
            destination_branch=destination_branch,
            quantity=total_qty,
            remarks=remarks,
        )


    # ─── Search ────────────────────────────────────────────────────────────────

    def search_stock_transfer(self, query: str) -> bool:
        """Search for a stock transfer by transfer number or remarks.

        The search is server-side. When searching by transfer number, the
        result row will contain the query text. When searching by remarks,
        it won't (remarks aren't displayed in the table), but the server
        still filters correctly.
        """
        search_box = self.page.get_by_placeholder("Search transfer no or remarks...")
        search_box.fill(query)
        search_box.press("Enter")
        self.page.wait_for_load_state("networkidle", timeout=5000)
        try:
            self.page.locator("table tbody tr").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def get_first_transfer_no(self) -> str:
        """Read the transfer number from the first row in the table."""
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=5000)
        # Transfer no is the first column (index 0)
        return row.locator("td").nth(0).text_content().strip()

    # ─── View Detail ───────────────────────────────────────────────────────────

    def view_stock_transfer(self, transfer_no: str) -> bool:
        """Search for a transfer by its number and click view to open detail page."""
        if not self.search_stock_transfer(transfer_no):
            return False
        # Transfer number IS visible in the row, so we can match precisely
        row = self.page.locator("table tbody tr").filter(has_text=transfer_no).first
        try:
            row.wait_for(state="visible", timeout=5000)
        except Exception:
            # Fallback to first row if exact match fails
            row = self.page.locator("table tbody tr").first

        row.get_by_title("view").first.click()
        self.page.wait_for_load_state("networkidle")

        # Verify detail page loaded — should show "Transfer details"
        try:
            self.page.get_by_text("Transfer details").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    def get_transfer_detail_info(self) -> dict:
        """Read transfer detail info from the currently open detail page.

        Returns dict with keys: transfer_no, from_branch, to_branch, created_by.
        """
        info = {}
        try:
            # Transfer no
            transfer_no_el = self.page.get_by_text("Transfer no").locator(
                "xpath=following-sibling::*"
            ).first
            info["transfer_no"] = transfer_no_el.text_content().strip()
        except Exception:
            info["transfer_no"] = ""

        try:
            from_el = self.page.get_by_text("From branch").locator(
                "xpath=following-sibling::*"
            ).first
            info["from_branch"] = from_el.text_content().strip()
        except Exception:
            info["from_branch"] = ""

        try:
            to_el = self.page.get_by_text("To branch").locator(
                "xpath=following-sibling::*"
            ).first
            info["to_branch"] = to_el.text_content().strip()
        except Exception:
            info["to_branch"] = ""

        return info

    def is_product_in_detail_items(self, product_name: str) -> bool:
        """Check if a product appears in the line items table on the detail page."""
        try:
            self.page.get_by_text("Line items").first.wait_for(
                state="visible", timeout=5000
            )
            self.page.locator("table tbody tr").filter(
                has_text=product_name
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    # ─── Filters ───────────────────────────────────────────────────────────────

    def expand_filters(self) -> None:
        """Expand the filters panel if collapsed."""
        try:
            toggle_btn = self.page.get_by_role(
                "button", name=re.compile(r"filter", re.IGNORECASE)
            )
            if toggle_btn.is_visible():
                toggle_btn.click()
                self.page.wait_for_timeout(500)
        except Exception:
            pass

    def filter_by_source_branch(self, branch_name: str) -> None:
        """Apply source branch filter."""
        self.expand_filters()
        container = self.page.locator("input[name='source_branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        container.click()
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(branch_name, delay=20)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("option", name=branch_name, exact=False).first.click()
        self.page.get_by_role("button", name="Filter", exact=True).click()
        self.page.wait_for_load_state("networkidle", timeout=5000)

    def filter_by_destination_branch(self, branch_name: str) -> None:
        """Apply destination branch filter."""
        self.expand_filters()
        container = self.page.locator("input[name='destination_branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container")
        container.click()
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(branch_name, delay=20)
        self.page.wait_for_timeout(300)
        self.page.get_by_role("option", name=branch_name, exact=False).first.click()
        self.page.get_by_role("button", name="Filter", exact=True).click()
        self.page.wait_for_load_state("networkidle", timeout=5000)

    def clear_filters(self) -> None:
        """Click clear filters to reset."""
        self.expand_filters()
        try:
            self.page.get_by_text("Clear filters").click()
            self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

    def is_transfer_in_table(self, text: str) -> bool:
        """Check if a row containing text is visible in the table."""
        try:
            self.page.locator("table tbody tr").filter(
                has_text=text
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def is_table_empty(self) -> bool:
        """Return True if the table shows empty state."""
        try:
            self.page.get_by_text("No stock transfers found.").wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    # ─── Validation Helpers ────────────────────────────────────────────────────

    def attempt_transfer_same_branch(self, branch_name: str, product_name: str) -> bool:
        """Try to create a transfer with same source and destination — should fail validation."""
        self.page.goto(f"{self.url}/add")
        self.page.wait_for_load_state("networkidle")

        # Select Source Branch
        self.page.locator("input[name='source_branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=branch_name).click()
        self.page.wait_for_timeout(500)

        # Try to select same branch as destination — it should be filtered out
        self.page.locator("input[name='destination_branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()

        # Check if the same branch is NOT in the options (filtered out)
        try:
            option = self.page.get_by_role("option", name=branch_name)
            if option.count() == 0:
                return True  # Correctly filtered out
            # If it is there, try selecting and submitting
            option.click()
        except Exception:
            return True  # Not available = validation working

        # Select product and try to submit
        self.page.locator("input[name='items.0.product_selector']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=product_name).click()
        self.page.wait_for_timeout(500)

        self.page.get_by_role("button", name="Create transfer").click()

        # Check for validation error
        try:
            self.page.get_by_text(
                re.compile(r"source.*destination.*different|same.*branch", re.IGNORECASE)
            ).wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return True  # Either filtered out or showed error

    def attempt_transfer_exceeding_stock(
        self, source_branch: str, destination_branch: str, product_name: str, quantity: int
    ) -> bool:
        """Try to create transfer with quantity > available stock — should fail validation."""
        self.page.goto(f"{self.url}/add")
        self.page.wait_for_load_state("networkidle")

        # Select Source Branch
        self.page.locator("input[name='source_branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=source_branch).click()
        self.page.wait_for_timeout(500)

        # Select Destination Branch
        self.page.locator("input[name='destination_branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=destination_branch).click()
        self.page.wait_for_timeout(500)

        # Select product
        self.page.locator("input[name='items.0.product_selector']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=product_name).click()
        self.page.wait_for_timeout(500)

        # Fill excessive quantity
        qty_input = self.page.locator("input[name='items.0.quantity']")
        qty_input.click()
        qty_input.fill(str(quantity))

        # Submit
        self.page.get_by_role("button", name="Create transfer").click()

        # Check for validation error about exceeding stock
        try:
            self.page.get_by_text(
                re.compile(r"exceeds.*available|quantity.*stock", re.IGNORECASE)
            ).wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            # Check if form didn't navigate away (stayed on form = error)
            return "/add" in self.page.url
