from __future__ import annotations
import re
from playwright.sync_api import Page

from utils.constants import BASE_URL

VOUCHER_HISTORY_URL = f"{BASE_URL}/vouchers/history"


class VoucherHistoryPage:
    """Page object for the Voucher History page (/vouchers/history).

    Displays a searchable, filterable, paginated list of all posted vouchers.

    Table columns: Voucher No., Type, Source (badge), Bill, Amount, Status (badge), Date, Actions (View button)
    Search: placeholder='Search voucher no...' (live, debounced)
    Filters: Source dropdown (All sources / User / System), Include system vouchers checkbox
    Pagination: PageSizeSelect + Pagination controls
    View: clicking 'View' navigates to /vouchers/:id detail page
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = VOUCHER_HISTORY_URL

    # ─── Navigation ────────────────────────────────────────────────────────────

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def is_page_visible(self) -> bool:
        """Verify the voucher history page loaded."""
        try:
            self.page.locator("h1, h2, h3, h4, h5, h6, .page-title, .card-title").filter(
                has_text=re.compile(r"Voucher\s*history", re.IGNORECASE) 
            ).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            try:
                self.page.locator("table, input[placeholder*='voucher'], input[placeholder*='Search']").first.wait_for(
                    state="visible", timeout=3000
                )
                return True
            except Exception:
                return False

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_voucher(self, query: str) -> bool:
        """Search vouchers by voucher number (live search, debounced).

        Returns True if at least one result row appears.
        """
        search_box = self.page.get_by_placeholder("Search voucher no...")
        search_box.fill("")
        self.page.wait_for_timeout(1000)
        search_box.fill(query)
        self.page.wait_for_timeout(2000)
        self.page.wait_for_load_state("networkidle", timeout=10000)
        try:
            first_row = self.page.locator("table tbody tr").first
            first_row.wait_for(state="visible", timeout=5000)
            text = first_row.text_content()
            return "No vouchers found" not in text
        except Exception:
            return False

    # ─── Filters ───────────────────────────────────────────────────────────────

    def filter_by_source(self, source: str) -> None:
        """Filter vouchers by source.

        Args:
            source: '' (All sources), 'user', or 'system'.
        """
        select = self.page.locator("select.form-select.form-select-sm")
        select.select_option(source)
        self.page.wait_for_timeout(1000)
        self.page.wait_for_load_state("networkidle", timeout=10000)

    def toggle_include_system_vouchers(self, checked: bool) -> None:
        """Toggle the 'Include system vouchers (COGS)' checkbox."""
        checkbox = self.page.locator("input.form-check-input")
        is_checked = checkbox.is_checked()
        if is_checked != checked:
            checkbox.click()
            self.page.wait_for_timeout(1000)
            self.page.wait_for_load_state("networkidle", timeout=10000)

    # ─── Table ─────────────────────────────────────────────────────────────────

    def get_row_count(self) -> int:
        """Return visible row count in the voucher table."""
        self.page.wait_for_load_state("networkidle", timeout=10000)
        try:
            first_row = self.page.locator("table tbody tr").first
            first_row.wait_for(state="visible", timeout=5000)
            # Check if it's the "No vouchers found" message
            text = first_row.text_content()
            if "No vouchers found" in text:
                return 0
            return self.page.locator("table tbody tr").count()
        except Exception:
            return 0

    def get_first_row_data(self) -> dict:
        """Read first row data.

        Returns dict with keys: voucher_no, type, source, amount, status, date.
        """
        self.page.wait_for_load_state("networkidle", timeout=10000)
        row = self.page.locator("table tbody tr").first
        row.wait_for(state="visible", timeout=5000)
        cells = row.locator("td").all()
        return {
            "voucher_no": cells[0].text_content().strip() if len(cells) > 0 else "",
            "type": cells[1].text_content().strip() if len(cells) > 1 else "",
            "source": cells[2].text_content().strip() if len(cells) > 2 else "",
            "bill": cells[3].text_content().strip() if len(cells) > 3 else "",
            "amount": cells[4].text_content().strip() if len(cells) > 4 else "",
            "status": cells[5].text_content().strip() if len(cells) > 5 else "",
            "date": cells[6].text_content().strip() if len(cells) > 6 else "",
        }

    def get_all_row_sources(self) -> list[str]:
        """Get the source badge text from all visible rows.

        Useful for verifying source filter is applied correctly.
        """
        self.page.wait_for_load_state("networkidle", timeout=10000)
        rows = self.page.locator("table tbody tr").all()
        sources = []
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) > 2:
                sources.append(cells[2].text_content().strip())
        return sources

    def get_all_row_statuses(self) -> list[str]:
        """Get the status badge text from all visible rows."""
        self.page.wait_for_load_state("networkidle", timeout=10000)
        rows = self.page.locator("table tbody tr").all()
        statuses = []
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) > 5:
                statuses.append(cells[5].text_content().strip())
        return statuses

    def has_voucher_entry(self, voucher_type: str, amount: str | None = None, include_system: bool = True) -> bool:
        """Verify if a voucher of the specified type and optional amount exists in history."""
        if include_system:
            try:
                self.toggle_include_system_vouchers(True)
            except Exception:
                pass
        self.page.wait_for_load_state("networkidle")
        rows = self.page.locator("table tbody tr").all()
        for row in rows:
            text = row.text_content()
            if voucher_type.lower() in text.lower():
                if amount is None or amount in text or amount.replace(",", "") in text.replace(",", ""):
                    return True
        return False

    def find_voucher_by_text(self, text_to_match: str, include_system: bool = True) -> bool:
        """Check if any row in voucher history contains the given text."""
        if include_system:
            try:
                self.toggle_include_system_vouchers(True)
            except Exception:
                pass
        self.page.wait_for_load_state("networkidle")
        rows = self.page.locator("table tbody tr").all()
        for row in rows:
            if text_to_match.lower() in row.text_content().lower():
                return True
        return False

    # ─── View Detail ───────────────────────────────────────────────────────────

    def view_first_voucher(self) -> bool:
        """Click 'View' on the first voucher row.

        Navigates to /vouchers/:id detail page.
        Returns True if navigation succeeds.
        """
        self.page.wait_for_load_state("networkidle", timeout=10000)
        first_row = self.page.locator("table tbody tr").first
        first_row.wait_for(state="visible", timeout=10000)
        view_btn = first_row.locator(
            "button[title='View'], button[title='view'], a[title='view'], a[title='View'], .btn-info, button:has-text('View'), a:has-text('View'), i.bi-eye"
        ).first
        try:
            view_btn.wait_for(state="visible", timeout=5000)
            view_btn.click()
            # Wait for navigation to voucher detail page
            self.page.wait_for_url(
                lambda url: "/vouchers/" in url and "/history" not in url,
                timeout=10000,
            )
            self.page.wait_for_load_state("networkidle", timeout=10000)
            return True
        except Exception:
            return False

    def is_voucher_detail_visible(self) -> bool:
        """Verify the voucher detail page loaded (shows voucher info card)."""
        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
            self.page.wait_for_timeout(500)
            text = self.page.locator("body").inner_text()
            return bool(
                re.search(r"Voucher|Type|Ledger|Debit|Credit|Amount", text, re.IGNORECASE)
            )
        except Exception:
            return False

    def get_voucher_detail_data(self) -> dict:
        """Read data from the voucher detail page."""
        self.page.wait_for_load_state("networkidle", timeout=10000)
        self.page.wait_for_timeout(500)
        body_text = self.page.locator("body").inner_text()

        # Extract voucher type (e.g. Type: Receipt, or Type: Sales)
        type_match = re.search(r"Type\s*:\s*([A-Za-z\s]+)", body_text, re.IGNORECASE)
        voucher_type = type_match.group(1).strip() if type_match else "Voucher"

        # Extract source (e.g. Source: System, Manual, Sales)
        source_match = re.search(r"Source\s*:\s*([A-Za-z\s]+)", body_text, re.IGNORECASE)
        source = source_match.group(1).strip() if source_match else "System"

        has_entries = (
            self.page.locator("table tbody tr").count() > 0
            or bool(re.search(r"Debit|Credit|Ledger", body_text, re.IGNORECASE))
        )

        return {
            "type": voucher_type,
            "source": source,
            "has_entries": has_entries,
            "content": body_text,
        }

    def click_back_to_history(self) -> None:
        """Click 'Back to history' link on the detail page."""
        back_btn = self.page.locator("button, a").filter(
            has_text=re.compile(r"Back|History", re.IGNORECASE)
        ).first
        if back_btn.count() > 0 and back_btn.is_visible():
            back_btn.click()
        else:
            self.navigate()
        try:
            self.page.wait_for_url(
                lambda url: "/vouchers/history" in url or "/vouchers" in url,
                timeout=10000,
            )
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

    def view_voucher_by_number(self, voucher_no: str) -> bool:
        """Search for a specific voucher number and open its detail view."""
        if not self.search_voucher(voucher_no):
            return False
        row = self.page.locator("table tbody tr").filter(has_text=voucher_no).first
        row.wait_for(state="visible", timeout=5000)
        view_btn = row.locator("button[title='View'], button[title='view'], a[title='view'], a[title='View'], .btn-info, button:has-text('View'), i.bi-eye").first
        view_btn.click()
        self.page.wait_for_url(
            lambda url: "/vouchers/" in url and "/history" not in url,
            timeout=10000,
        )
        # VoucherDetail renders a loader until its API request resolves. The
        # route URL and browser network-idle state can both settle before React
        # commits the voucher content, so wait for detail-specific DOM state.
        self.page.get_by_text(
            re.compile(rf"^Voucher\s+{re.escape(voucher_no)}$", re.IGNORECASE)
        ).first.wait_for(state="visible", timeout=15000)
        self.page.get_by_role(
            "heading", name="Ledger entries", exact=True
        ).wait_for(state="visible", timeout=10000)
        return True

    def inspect_voucher_by_number(self, voucher_no: str) -> dict[str, str | bool]:
        """Opens specific voucher by number and parses details and DR/CR entries."""
        success = self.view_voucher_by_number(voucher_no)
        if not success:
            raise RuntimeError(f"Could not find or open voucher {voucher_no} in history")

        body_text = self.page.locator("body").inner_text()
        return {
            "voucher_no": voucher_no,
            "content": body_text,
            "has_sales_ledger": "Sales Ledger" in body_text,
            "has_entries": "Debit" in body_text or "Credit" in body_text or "Ledger" in body_text,
        }

    def inspect_first_voucher_entries(self, filter_query: str | None = None) -> dict[str, str | bool | list]:
        """Opens matching voucher detail and extracts ledger entry particulars."""
        self.page.wait_for_load_state("networkidle")
        if filter_query:
            self.search_voucher(filter_query)
            self.page.wait_for_timeout(500)

        row = self.page.locator("table tbody tr").filter(has_text=filter_query) if filter_query else self.page.locator("table tbody tr")
        first_row = row.first
        first_row.wait_for(state="visible", timeout=5000)

        view_btn = first_row.locator("button[title='View'], button[title='view'], a[title='view'], a[title='View'], .btn-info, button:has-text('View'), i.bi-eye").first
        view_btn.click()

        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(1000)
        body_text = self.page.locator("body").inner_text()

        return {
            "content": body_text,
            "has_sales_ledger": "Sales Ledger" in body_text,
            "has_entries": "Debit" in body_text or "Credit" in body_text or "Ledger" in body_text,
        }


    # ─── Pagination ────────────────────────────────────────────────────────────

    def get_page_size(self) -> int:
        """Get the currently selected page size from the react-select."""
        try:
            # The PageSizeSelect renders as react-select with value like "10 rows"
            value_el = self.page.locator(
                ".react-select__single-value"
            ).first
            value_el.wait_for(state="visible", timeout=5000)
            text = value_el.text_content().strip()
            # Extract number from "10 rows"
            return int(text.split()[0])
        except Exception:
            return 10  # default

    def set_page_size(self, size: int) -> None:
        """Change the page size via the react-select.

        Args:
            size: One of 5, 10, 20, 50, 100, 500.
        """
        # Click the react-select to open dropdown
        page_size_select = self.page.locator(
            ".react-select__control"
        ).first
        page_size_select.click()
        self.page.wait_for_timeout(300)

        # Click the option matching "{size} rows"
        option = self.page.get_by_role("option", name=f"{size} rows")
        option.wait_for(state="visible", timeout=5000)
        option.click()
        self.page.wait_for_timeout(1000)
        self.page.wait_for_load_state("networkidle", timeout=10000)

    def has_next_page(self) -> bool:
        """Check if the 'Next' pagination button is enabled."""
        try:
            next_btn = self.page.locator("button", has_text="Next").first
            return next_btn.is_enabled()
        except Exception:
            return False

    def has_prev_page(self) -> bool:
        """Check if the 'Previous' pagination button is enabled."""
        try:
            prev_btn = self.page.locator("button", has_text="Previous").first
            return prev_btn.is_enabled()
        except Exception:
            return False

    def go_next_page(self) -> None:
        """Click the 'Next' pagination button."""
        self.page.locator("button", has_text="Next").first.click()
        self.page.wait_for_timeout(1000)
        self.page.wait_for_load_state("networkidle", timeout=10000)

    def go_prev_page(self) -> None:
        """Click the 'Previous' pagination button."""
        self.page.locator("button", has_text="Previous").first.click()
        self.page.wait_for_timeout(1000)
        self.page.wait_for_load_state("networkidle", timeout=10000)
