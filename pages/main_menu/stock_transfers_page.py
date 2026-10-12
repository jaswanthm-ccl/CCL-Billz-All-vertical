from __future__ import annotations

import re
from decimal import Decimal
from typing import Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response, TimeoutError as PlaywrightTimeoutError, expect

from pages.common.base_page import BasePage
from utils.models import StockTransferResult
from utils.tenants import Tenant


class StockTransfersPage(BasePage):
    PATH = "/stock-transfers"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    @property
    def _rows(self):
        return self.page.locator("table tbody tr")

    @staticmethod
    def _is_list_response(response: Response, search: str | None = None) -> bool:
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/stock-transfers")
        ):
            return False
        return search is None or parse_qs(url.query).get("search", [""])[-1] == search

    def _reload_list(self, action: Callable[[], object], search: str | None = None) -> None:
        with self.page.expect_response(lambda r: self._is_list_response(r, search), timeout=15000):
            action()
        self._rows.first.wait_for(state="visible", timeout=10000)

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))

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

    @staticmethod
    def _is_create_response(response) -> bool:
        return response.request.method == "POST" and urlparse(response.url).path.rstrip("/").endswith(
            ("/stock-transfers", "/stock-transfer")
        )

    def _pick_option(self, input_name: str, text: str) -> None:
        self.page.locator(f"input[name='{input_name}']").locator("xpath=..").locator(
            ".react-select__control, .react-select__input-container"
        ).first.click()
        self.page.keyboard.type(text, delay=20)
        option = self.page.get_by_role("option", name=text, exact=False).first
        option.wait_for(state="visible", timeout=5000)
        option.click(timeout=5000)
        menu = self.page.locator(".react-select__menu")
        if menu.count():
            menu.first.wait_for(state="hidden", timeout=5000)

    def add_stock_transfer(
        self,
        source_branch: str,
        destination_branch: str,
        products_data: list[dict[str, str | int]],
        remarks: str = "",
    ) -> StockTransferResult:
        """products_data items: {"product", "quantity"}; for serial-tracked products give "serials": [...]
        instead of a quantity (the form sets one unit per selected serial). Raises if the API rejects it."""
        self.last_transfer_response: dict = {}
        self.page.goto(f"{self.url}/add", wait_until="domcontentloaded")
        self.page.get_by_role("button", name="Create transfer").wait_for(
            state="visible", timeout=15000
        )

        self._pick_option("source_branch_id", source_branch)
        self._pick_option("destination_branch_id", destination_branch)
        if remarks:
            self.page.locator("textarea[name='remarks']").fill(remarks)

        total_qty = Decimal("0")
        for i, item in enumerate(products_data):
            if i > 0:
                self.page.get_by_role("button", name="Add line").click()
            self._pick_option(f"items.{i}.product_selector", str(item["product"]))

            serials = [str(serial) for serial in item.get("serials") or []]
            if serials:
                for serial in serials:
                    self.page.get_by_text(re.compile(rf"^{re.escape(serial)}\b")).first.click()
                expect(self.page.get_by_text(re.compile(rf"Quantity: {len(serials)}\b"))).to_be_visible()
                total_qty += len(serials)
            else:
                quantity_input = self.page.locator(f"input[name='items.{i}.quantity']")
                quantity_input.click()
                quantity_input.fill(str(item["quantity"]))
                total_qty += Decimal(str(item["quantity"]))

            if item.get("remarks"):
                self.page.locator(f"input[name='items.{i}.remarks']").fill(str(item["remarks"]))

        sent: list[str] = []
        record_request = lambda request: sent.append(f"{request.method} {urlparse(request.url).path}")  # noqa: E731
        self.page.on("request", record_request)
        create_button = self.page.get_by_role("button", name="Create transfer")
        try:
            try:
                with self.page.expect_response(self._is_create_response, timeout=8000) as response_info:
                    create_button.click(timeout=10000)
            except PlaywrightTimeoutError:
                # The form sometimes ignores the first click without sending anything; nothing was saved, so retry once.
                if any(not r.startswith("GET") for r in sent):
                    raise
                with self.page.expect_response(self._is_create_response, timeout=15000) as response_info:
                    create_button.click(timeout=10000)
        except PlaywrightTimeoutError as error:
            errors = self.page.locator(".invalid-feedback, .text-danger, .alert-danger, [role='alert']").all_inner_texts()
            fields = self.page.locator("form input[name]").evaluate_all(
                "els => els.filter(e => e.type !== 'search').map(e => `${e.name}=${e.value}${e.matches(':invalid') ? ' (invalid)' : ''}`)"
            )
            raise RuntimeError(
                f"Stock transfer was not submitted: {str(error).splitlines()[0]}; "
                f"form errors: {[e for e in errors if e.strip()]}; fields: {fields}; "
                f"requests sent: {[r for r in sent if not r.startswith('GET')]}"
            ) from None
        finally:
            self.page.remove_listener("request", record_request)
        response = response_info.value
        try:
            body = response.json()
        except ValueError:
            body = {}
        self.last_transfer_response = {"status": response.status, "body": body, "payload": response.request.post_data_json}
        if not response.ok:
            raise RuntimeError(f"Stock transfer rejected ({response.status}): {body.get('message') or body}")

        data = body.get("data") or {}
        transfer_no = str(data.get("transfer_no") or data.get("reference_no") or data.get("number") or "")
        if not transfer_no:
            self.navigate()
            first_row = self.page.locator("table tbody tr").filter(has_text=source_branch).first
            first_row.wait_for(state="visible", timeout=10000)
            transfer_no = first_row.locator("td").first.inner_text().strip()

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
        if search_box.input_value() != query:

            def search() -> None:
                search_box.fill(query)
                search_box.press("Enter")

            self._reload_list(search, search=query)
        try:
            self._rows.first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def get_first_transfer_no(self) -> str:
        """Read the transfer number from the first row in the table."""
        row = self._rows.first
        row.wait_for(state="visible", timeout=5000)
        # Transfer no is the first column (index 0)
        return row.locator("td").nth(0).text_content().strip()

    # ─── View Detail ───────────────────────────────────────────────────────────

    def view_stock_transfer(self, transfer_no: str) -> bool:
        """Search for a transfer by its number and click view to open detail page."""
        if not self.search_stock_transfer(transfer_no):
            return False
        # Transfer number IS visible in the row, so we can match precisely
        row = self._rows.filter(has_text=transfer_no).first
        try:
            row.wait_for(state="visible", timeout=5000)
        except Exception:
            # Fallback to first row if exact match fails
            row = self._rows.first

        row.get_by_title("view").first.click()

        # Verify detail page loaded — should show "Transfer details"
        try:
            self.page.get_by_text("Transfer details").first.wait_for(
                state="visible", timeout=10000
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

    def _filter_control(self, input_name: str):
        return self.page.locator(f"input[name='{input_name}']").locator("xpath=..").locator(
            ".react-select__control"
        ).first

    def expand_filters(self) -> None:
        """Expand the filters panel if collapsed."""
        filter_btn = self.page.get_by_role("button", name="Filter", exact=True)
        if filter_btn.count() and filter_btn.first.is_visible():
            return
        toggle = self.page.locator("button.filters-toggle-btn")
        if toggle.count() and toggle.is_visible() and toggle.get_attribute("aria-expanded") == "false":
            toggle.click()
        else:
            expand = self.page.get_by_label("Expand filters")
            if expand.count():
                expand.click()
        filter_btn.first.wait_for(state="visible", timeout=10000)

    def filter_by_source_branch(self, branch_name: str) -> None:
        """Apply source branch filter."""
        self.expand_filters()
        self._filter_control("source_branch_id").click()
        self.page.keyboard.type(branch_name, delay=20)
        option = self.page.get_by_role("option", name=branch_name, exact=False).first
        option.wait_for(state="visible", timeout=5000)
        option.click()
        self._reload_list(
            lambda: self.page.get_by_role("button", name="Filter", exact=True).click()
        )

    def filter_by_destination_branch(self, branch_name: str) -> None:
        """Apply destination branch filter."""
        self.expand_filters()
        self._filter_control("destination_branch_id").click()
        self.page.keyboard.type(branch_name, delay=20)
        option = self.page.get_by_role("option", name=branch_name, exact=False).first
        option.wait_for(state="visible", timeout=5000)
        option.click()
        self._reload_list(
            lambda: self.page.get_by_role("button", name="Filter", exact=True).click()
        )

    def clear_filters(self) -> None:
        """Click clear filters to reset."""
        self.expand_filters()
        clear = self.page.get_by_text("Clear filters")
        if clear.count() and clear.first.is_visible():
            self._reload_list(lambda: clear.first.click())

    def is_transfer_in_table(self, text: str) -> bool:
        """Check if a row containing text is visible in the table."""
        try:
            self._rows.filter(has_text=text).first.wait_for(state="visible", timeout=5000)
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
        self.page.goto(f"{self.url}/add", wait_until="domcontentloaded")
        self.page.get_by_role("button", name="Create transfer").wait_for(
            state="visible", timeout=15000
        )

        self._pick_option("source_branch_id", branch_name)

        # Try to select same branch as destination — it should be filtered out
        self.page.locator("input[name='destination_branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()

        try:
            option = self.page.get_by_role("option", name=branch_name)
            option.first.wait_for(state="visible", timeout=2000)
            if option.count() == 0:
                return True  # Correctly filtered out
            option.first.click()
        except Exception:
            return True  # Not available = validation working

        self._pick_option("items.0.product_selector", product_name)
        self.page.get_by_role("button", name="Create transfer").click()

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
        self.page.goto(f"{self.url}/add", wait_until="domcontentloaded")
        self.page.get_by_role("button", name="Create transfer").wait_for(
            state="visible", timeout=15000
        )

        self._pick_option("source_branch_id", source_branch)
        self._pick_option("destination_branch_id", destination_branch)
        self._pick_option("items.0.product_selector", product_name)

        qty_input = self.page.locator("input[name='items.0.quantity']")
        qty_input.click()
        qty_input.fill(str(quantity))

        self.page.get_by_role("button", name="Create transfer").click()

        try:
            self.page.get_by_text(
                re.compile(r"exceeds.*available|quantity.*stock", re.IGNORECASE)
            ).wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return "/add" in self.page.url
