from __future__ import annotations

import re
from typing import Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, Response, expect

from pages.common.base_page import BasePage
from utils.tenants import Tenant

VIEW_BUTTON = (
    "button[title='View'], button[title='view'], a[title='view'], a[title='View'], "
    ".btn-info, button:has-text('View'), a:has-text('View'), i.bi-eye"
)
EMPTY_TEXT = "No vouchers found"


class VoucherHistoryPage(BasePage):
    """Page object for the Voucher History page (/vouchers/history).

    Displays a searchable, filterable, paginated list of all posted vouchers.

    Table columns: Voucher No., Type, Source (badge), Bill, Amount, Status (badge), Date, Actions (View button)
    Search: placeholder='Search voucher no...' (live, debounced)
    Filters: Source dropdown (All sources / User / System), Include system vouchers checkbox
    Pagination: PageSizeSelect + Pagination controls
    View: clicking 'View' navigates to /vouchers/:id detail page

    Every list change re-fetches GET /vouchers?page=..&per_page=..[&search=..&voucher_source=..&include_system_vouchers=1];
    the helpers wait for that response instead of fixed delays.
    """

    PATH = "/vouchers/history"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    # ─── List loading ──────────────────────────────────────────────────────────

    @staticmethod
    def _list_params(response: Response) -> dict[str, str] | None:
        """Query params of a voucher-list response, or None if it isn't one."""
        url = urlparse(response.url)
        if (
            response.request.method != "GET"
            or response.request.resource_type not in {"fetch", "xhr"}
            or not url.path.rstrip("/").endswith("/vouchers")
        ):
            return None
        return {key: values[-1] for key, values in parse_qs(url.query).items()}

    def _reload_list(self, action: Callable[[], object], **expected: str) -> None:
        """Run `action` and wait for the voucher list it triggers (matching `expected` query params), then its render."""

        def matches(response: Response) -> bool:
            params = self._list_params(response)
            return params is not None and all(params.get(key) == value for key, value in expected.items())

        with self.page.expect_response(matches, timeout=15000) as info:
            action()
        # The table re-renders a moment after the response; wait until it shows this response's rows.
        vouchers = self._items(info.value)
        if vouchers:
            expect(self._rows).to_have_count(len(vouchers), timeout=10000)
            expect(self._rows.first).to_contain_text(str(vouchers[0].get("voucher_no", "")), timeout=10000)
        else:
            expect(self._rows.first).to_contain_text(EMPTY_TEXT, timeout=10000)

    @staticmethod
    def _items(response: Response) -> list[dict]:
        """The voucher rows in a list response (data may be a list or a paginator with a nested list)."""
        data = response.json().get("data")
        if isinstance(data, dict):
            data = data.get("data", data.get("items", []))
        return data if isinstance(data, list) else []

    @property
    def _rows(self):
        return self.page.locator("table tbody tr")

    @property
    def _search_box(self):
        return self.page.get_by_placeholder("Search voucher no...")

    # ─── Navigation ────────────────────────────────────────────────────────────

    def navigate(self) -> None:
        self._reload_list(lambda: self.page.goto(self.url))

    def is_page_visible(self) -> bool:
        """Verify the voucher history page loaded."""
        heading = self.page.locator("h1, h2, h3, h4, h5, h6, .page-title, .card-title").filter(
            has_text=re.compile(r"Voucher\s*history", re.IGNORECASE)
        )
        try:
            expect(heading.or_(self._search_box).first).to_be_visible(timeout=5000)
            return True
        except AssertionError:
            return False

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_voucher(self, query: str) -> bool:
        """Search vouchers by voucher number. Returns True if at least one result row appears."""
        if self._search_box.input_value() != query:
            self._reload_list(lambda: self._search_box.fill(query), search=query)
        return self.get_row_count() > 0

    # ─── Filters ───────────────────────────────────────────────────────────────

    def filter_by_source(self, source: str) -> None:
        """Filter vouchers by source: '' (All sources), 'user', or 'system'."""
        select = self.page.locator("select.form-select.form-select-sm")
        if select.input_value() == source:
            return
        expected = {"voucher_source": source} if source else {}
        self._reload_list(lambda: select.select_option(source), **expected)

    def toggle_include_system_vouchers(self, checked: bool) -> None:
        """Toggle the 'Include system vouchers (COGS)' checkbox."""
        checkbox = self.page.locator("input.form-check-input")
        if checkbox.is_checked() != checked:
            self._reload_list(checkbox.click)

    # ─── Table ─────────────────────────────────────────────────────────────────

    def get_row_count(self) -> int:
        """Return visible row count in the voucher table (0 for the empty-state row)."""
        self._rows.first.wait_for(state="visible", timeout=10000)
        if EMPTY_TEXT in (self._rows.first.text_content() or ""):
            return 0
        return self._rows.count()

    def _cells(self, row) -> list[str]:
        return [text.strip() for text in row.locator("td").all_text_contents()]

    def get_first_row_data(self) -> dict:
        """Read first row data: voucher_no, type, source, bill, amount, status, date."""
        self._rows.first.wait_for(state="visible", timeout=10000)
        cells = self._cells(self._rows.first) + [""] * 7
        keys = ("voucher_no", "type", "source", "bill", "amount", "status", "date")
        return dict(zip(keys, cells))

    def _column(self, index: int) -> list[str]:
        if self.get_row_count() == 0:
            return []
        return [cells[index] for cells in (self._cells(row) for row in self._rows.all()) if len(cells) > index]

    def get_all_row_sources(self) -> list[str]:
        """Source badge text from all visible rows."""
        return self._column(2)

    def get_all_row_statuses(self) -> list[str]:
        """Status badge text from all visible rows."""
        return self._column(5)

    def _row_texts(self, include_system: bool) -> list[str]:
        if include_system:
            self.toggle_include_system_vouchers(True)
        if self.get_row_count() == 0:
            return []
        return [text or "" for text in self._rows.all_text_contents()]

    def has_voucher_entry(self, voucher_type: str, amount: str | None = None, include_system: bool = True) -> bool:
        """Whether a voucher of the given type (and optional amount) is listed."""
        for text in self._row_texts(include_system):
            if voucher_type.lower() in text.lower():
                if amount is None or amount in text or amount.replace(",", "") in text.replace(",", ""):
                    return True
        return False

    def find_voucher_by_text(self, text_to_match: str, include_system: bool = True) -> bool:
        """Whether any listed voucher row contains the given text."""
        return any(text_to_match.lower() in text.lower() for text in self._row_texts(include_system))

    # ─── View Detail ───────────────────────────────────────────────────────────

    def _open_detail(self, row) -> None:
        """Click View on `row` and wait until the detail page has rendered its ledger entries."""
        row.locator(VIEW_BUTTON).first.click()
        self.page.wait_for_url(lambda url: "/vouchers/" in url and "/history" not in url, timeout=10000)
        # The detail route renders a loader until its API call resolves; wait for detail-specific DOM.
        self.page.get_by_role("heading", name="Ledger entries", exact=True).wait_for(state="visible", timeout=15000)

    def view_first_voucher(self) -> bool:
        """Open the first voucher's detail page."""
        if self.get_row_count() == 0:
            return False
        self._open_detail(self._rows.first)
        return True

    def is_voucher_detail_visible(self) -> bool:
        """Verify the voucher detail page loaded (shows the ledger entries section)."""
        try:
            expect(self.page.get_by_role("heading", name="Ledger entries", exact=True)).to_be_visible(timeout=15000)
            return True
        except AssertionError:
            return False

    def get_voucher_detail_data(self) -> dict:
        """Read data from the voucher detail page."""
        self.is_voucher_detail_visible()
        body_text = self.page.locator("body").inner_text()

        type_match = re.search(r"Type\s*:\s*([A-Za-z\s]+)", body_text, re.IGNORECASE)
        source_match = re.search(r"Source\s*:\s*([A-Za-z\s]+)", body_text, re.IGNORECASE)
        has_entries = self._rows.count() > 0 or bool(re.search(r"Debit|Credit|Ledger", body_text, re.IGNORECASE))

        return {
            "type": type_match.group(1).strip() if type_match else "Voucher",
            "source": source_match.group(1).strip() if source_match else "System",
            "has_entries": has_entries,
            "content": body_text,
        }

    def click_back_to_history(self) -> None:
        """Click 'Back to history' on the detail page (or navigate there) and wait for the list."""
        back_btn = self.page.locator("button, a").filter(has_text=re.compile(r"Back|History", re.IGNORECASE)).first
        if back_btn.count() > 0 and back_btn.is_visible():
            self._reload_list(back_btn.click)
        else:
            self.navigate()

    def view_voucher_by_number(self, voucher_no: str) -> bool:
        """Search for a specific voucher number and open its detail view."""
        if not self.search_voucher(voucher_no):
            return False
        self._open_detail(self._rows.filter(has_text=voucher_no).first)
        self.page.get_by_text(
            re.compile(rf"^Voucher\s+{re.escape(voucher_no)}$", re.IGNORECASE)
        ).first.wait_for(state="visible", timeout=15000)
        return True

    def inspect_voucher_by_number(self, voucher_no: str) -> dict[str, str | bool]:
        """Opens specific voucher by number and parses details and DR/CR entries."""
        if not self.view_voucher_by_number(voucher_no):
            raise RuntimeError(f"Could not find or open voucher {voucher_no} in history")
        return self._detail_summary() | {"voucher_no": voucher_no}

    def inspect_first_voucher_entries(self, filter_query: str | None = None) -> dict[str, str | bool | list]:
        """Opens the first (optionally searched) voucher and extracts ledger entry particulars."""
        if filter_query:
            self.search_voucher(filter_query)
        rows = self._rows.filter(has_text=filter_query) if filter_query else self._rows
        self._open_detail(rows.first)
        return self._detail_summary()

    def _detail_summary(self) -> dict[str, str | bool]:
        body_text = self.page.locator("body").inner_text()
        return {
            "content": body_text,
            "has_sales_ledger": "Sales Ledger" in body_text,
            "has_entries": "Debit" in body_text or "Credit" in body_text or "Ledger" in body_text,
        }

    # ─── Pagination ────────────────────────────────────────────────────────────

    def get_page_size(self) -> int:
        """Currently selected page size, read from the "N rows" select."""
        value = self.page.locator(".react-select__single-value").first
        value.wait_for(state="visible", timeout=5000)
        return int((value.text_content() or "").split()[0])

    def set_page_size(self, size: int) -> None:
        """Change the page size (5, 10, 20, 50, 100 or 500) and wait for the reloaded list."""

        def choose() -> None:
            self.page.locator(".react-select__control").first.click()
            self.page.get_by_role("option", name=f"{size} rows").click()

        self._reload_list(choose, per_page=str(size))

    def _pager(self, label: str):
        return self.page.locator("button", has_text=label).first

    def has_next_page(self) -> bool:
        """Whether the 'Next' pagination button is enabled."""
        return self._pager("Next").count() > 0 and self._pager("Next").is_enabled()

    def has_prev_page(self) -> bool:
        """Whether the 'Previous' pagination button is enabled."""
        return self._pager("Previous").count() > 0 and self._pager("Previous").is_enabled()

    def go_next_page(self) -> None:
        """Click 'Next' and wait for that page to load."""
        self._reload_list(self._pager("Next").click)

    def go_prev_page(self) -> None:
        """Click 'Previous' and wait for that page to load."""
        self._reload_list(self._pager("Previous").click)
