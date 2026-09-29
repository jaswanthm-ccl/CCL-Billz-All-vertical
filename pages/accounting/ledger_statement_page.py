from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import urlparse

from playwright.sync_api import Page

from utils.constants import BASE_URL


LEDGER_STATEMENT_URL = f"{BASE_URL}/reports/ledger-statement"


class LedgerStatementPage:
    """Page object for the Ledger Statement report (/reports/ledger-statement).

    Filters:
      - Ledger: React-Select dropdown to pick a ledger account
      - Branch: React-Select dropdown to filter by branch
      - From Date / To Date: date inputs for the reporting period

    Metrics (summary cards):
      - Opening Balance
      - Total Debits
      - Total Credits
      - Closing Balance

    Table columns: Date, Voucher ID, Narration, Debit, Credit, Running Balance
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = LEDGER_STATEMENT_URL

    # ══════════════════════════════════════════════════════════════════════════
    # NAVIGATION
    # ══════════════════════════════════════════════════════════════════════════

    def navigate(self) -> None:
        """Navigate to the Ledger Statement page."""
        self.page.goto(self.url, wait_until="domcontentloaded")
        self.page.locator(".react-select__control").first.wait_for(
            state="visible", timeout=10000
        )

    def is_page_visible(self) -> bool:
        """Check if the Ledger Statement page loaded."""
        try:
            self.page.get_by_text(re.compile(r"ledger\s*statement", re.IGNORECASE)).first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            try:
                # Fallback: check for react-select (ledger picker)
                self.page.locator(".react-select__input-container").first.wait_for(
                    state="visible", timeout=3000
                )
                return True
            except Exception:
                return False

    # ══════════════════════════════════════════════════════════════════════════
    # FILTERS
    # ══════════════════════════════════════════════════════════════════════════

    def _ensure_filters_expanded(self) -> None:
        """Expand the report filters after a previous submission collapsed them."""
        first_control = self.page.locator(".react-select__control").first
        if first_control.is_visible():
            return

        expand = self.page.get_by_role("button", name="Expand filters", exact=True)
        expand.wait_for(state="visible", timeout=5000)
        expand.click()
        first_control.wait_for(state="visible", timeout=5000)

    def _select_react_option(self, index: int, option_name: str) -> None:
        """Select a complete React-Select option without timing-based sleeps."""
        self._ensure_filters_expanded()
        control = self.page.locator(".react-select__control").nth(index)
        control.wait_for(state="visible", timeout=10000)

        selected = control.locator(".react-select__single-value")
        if selected.count() and selected.inner_text().strip() == option_name:
            return

        control.click()
        search = control.locator('input[role="combobox"], input[type="text"]')
        if search.count() > 0 and search.first.is_visible():
            search.first.fill("")
            search.first.press_sequentially(option_name, delay=20)
            self.page.wait_for_timeout(400)
        else:
            self.page.keyboard.type(option_name)
            self.page.wait_for_timeout(400)

        exact_option = self.page.get_by_role("option", name=option_name, exact=True)
        try:
            exact_option.wait_for(state="visible", timeout=6000)
            exact_option.click()
        except Exception:
            matching_options = self.page.locator(".react-select__option, div[class*='-option']").filter(
                has_text=option_name
            )
            if matching_options.count() > 0:
                matching_options.first.wait_for(state="visible", timeout=10000)
                matching_options.first.click()
            else:
                self.page.keyboard.press("Enter")

        try:
            selected.wait_for(state="visible", timeout=5000)
        except Exception:
            pass


    def select_ledger(self, ledger_name: str, auto_filter: bool = True) -> None:
        """Select a ledger from the first React-Select dropdown."""
        self._select_react_option(0, ledger_name)
        if auto_filter:
            try:
                self.click_filter()
            except Exception:
                pass

    def select_branch(self, branch_name: str, auto_filter: bool = True) -> None:
        """Select a branch from the branch React-Select dropdown (second dropdown)."""
        self._ensure_filters_expanded()
        controls = self.page.locator(".react-select__control")
        if controls.count() < 2:
            raise RuntimeError("Ledger Statement branch filter is not available")
        self._select_react_option(1, branch_name)
        if auto_filter:
            try:
                self.click_filter()
            except Exception:
                pass

    def set_from_date(self, date_str: str) -> None:
        """Set the From Date filter. Format: YYYY-MM-DD."""
        self._ensure_filters_expanded()
        date_inputs = self.page.locator("input[type='date'], input[name='from_date']")
        date_inputs.first.wait_for(state="visible", timeout=5000)
        date_inputs.first.fill(date_str)

    def set_to_date(self, date_str: str) -> None:
        """Set the To Date filter. Format: YYYY-MM-DD."""
        self._ensure_filters_expanded()
        date_inputs = self.page.locator("input[type='date'], input[name='to_date']")
        date_inputs.nth(1).wait_for(state="visible", timeout=5000)
        date_inputs.nth(1).fill(date_str)

    def set_date_range(self, from_date: str, to_date: str, auto_filter: bool = True) -> None:
        """Set both From and To date filters."""
        self.set_from_date(from_date)
        self.set_to_date(to_date)
        if auto_filter:
            try:
                self.click_filter()
            except Exception:
                pass

    @staticmethod
    def _is_statement_response(response) -> bool:
        return (
            "ledger-statement" in response.url.lower()
            and response.request.method == "GET"
        )

    def click_filter(self) -> None:
        """Click the Filter button to fetch statement data."""
        self._ensure_filters_expanded()
        filter_btn = self.page.get_by_role("button", name="Filter", exact=True).first
        filter_btn.wait_for(state="visible", timeout=10000)
        try:
            with self.page.expect_response(self._is_statement_response, timeout=8000) as info:
                filter_btn.click()
            response = info.value
            if not response.ok:
                raise RuntimeError(
                    f"Ledger Statement request failed with HTTP {response.status}"
                )
        except Exception:
            filter_btn.click()
            try:
                self.page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

        try:
            self.page.get_by_text(re.compile(r"Opening Balance|Closing Balance|Running Balance|Date", re.I)).first.wait_for(
                state="visible", timeout=10000
            )
        except Exception:
            pass


    def filter_statement(self, ledger_name: str, branch_name: str | None = None) -> None:
        """Filter a statement without reloading the page between ledger checks."""
        current_path = urlparse(self.page.url).path.rstrip("/")
        if current_path != "/reports/ledger-statement":
            self.navigate()
        else:
            self._ensure_filters_expanded()
        # Populate the complete filter form before submitting. Auto-submitting
        # each field collapses the filter panel and causes duplicate requests.
        self.select_ledger(ledger_name, auto_filter=False)
        if branch_name:
            self.select_branch(branch_name, auto_filter=False)
        self.click_filter()

    def get_selected_ledger(self) -> str:
        """Read the currently selected ledger name from the dropdown."""
        try:
            return self.page.locator(
                ".react-select__single-value"
            ).first.text_content().strip()
        except Exception:
            return ""

    def get_selected_branch(self) -> str:
        """Read the currently selected branch name from the dropdown."""
        try:
            return self.page.locator(
                ".react-select__single-value"
            ).nth(1).text_content().strip()
        except Exception:
            return ""

    # ══════════════════════════════════════════════════════════════════════════
    # METRICS (summary cards)
    # ══════════════════════════════════════════════════════════════════════════

    def get_opening_balance(self) -> str:
        """Read the Opening Balance metric value."""
        return self._get_metric_value("Opening Balance")

    def get_total_debits(self) -> str:
        """Read the Total Debits metric value."""
        return self._get_metric_value("Total Debit")

    def get_total_credits(self) -> str:
        """Read the Total Credits metric value."""
        return self._get_metric_value("Total Credit")

    def get_closing_balance(self) -> str:
        """Read the Closing Balance metric value."""
        return self._get_metric_value("Closing Balance")

    def get_all_metrics(self) -> dict:
        """Read all four metrics as a dictionary."""
        return {
            "opening_balance": self.get_opening_balance(),
            "total_debits": self.get_total_debits(),
            "total_credits": self.get_total_credits(),
            "closing_balance": self.get_closing_balance(),
        }

    @staticmethod
    def parse_signed_balance(value: str) -> Decimal:
        """Parse report balances with DR positive and CR negative."""
        normalized = re.sub(r"[^\d.-]", "", value)
        amount = Decimal(normalized or "0")
        upper_value = value.upper()
        if "CR" in upper_value and amount > 0:
            return -amount
        return amount

    def _get_metric_value(self, label: str) -> str:
        """Extract the numeric value next to a metric label."""
        try:
            # Pattern 1: label text followed by a sibling or child value
            label_el = self.page.get_by_text(re.compile(re.escape(label), re.IGNORECASE)).first
            label_el.wait_for(state="visible", timeout=3000)
            parent = label_el.locator("xpath=..")
            value_el = parent.locator("span, p, h2, h3, h4, h5, .value, .metric-value").first
            text = value_el.text_content().strip()
            if label.lower() in text.lower() and len(text) < len(label) + 5:
                text = parent.text_content().strip()
            return text.replace(label, "").strip()
        except Exception:
            pass

        try:
            # Pattern 2: Get all text from the element containing the label
            container = self.page.locator(f":has-text('{label}')").last
            full_text = container.text_content().strip()
            match = re.search(rf"{re.escape(label)}\s*[:\s]*([₹\d,.\-]+)", full_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            return full_text.replace(label, "").strip()
        except Exception:
            return ""

    def has_metrics_visible(self) -> bool:
        """Check if any of the four metric labels are visible."""
        for label in ["Opening Balance", "Total Debit", "Total Credit", "Closing Balance"]:
            try:
                self.page.get_by_text(re.compile(re.escape(label), re.IGNORECASE)).first.wait_for(
                    state="visible", timeout=3000
                )
                return True
            except Exception:
                continue
        return False

    # ══════════════════════════════════════════════════════════════════════════
    # TABLE
    # ══════════════════════════════════════════════════════════════════════════

    def get_row_count(self) -> int:
        """Return the number of transaction rows in the statement table."""
        try:
            self.page.locator("table tbody tr").first.wait_for(
                state="visible", timeout=5000
            )
            rows = self.page.locator("table tbody tr").all()
            # Exclude "No data" rows
            count = 0
            for row in rows:
                text = row.text_content().lower()
                if "no data" in text or "no transactions" in text or "no records" in text:
                    continue
                count += 1
            return count
        except Exception:
            return 0

    def get_first_row_data(self) -> dict:
        """Read data from the first transaction row.

        Returns dict: date, voucher_id, narration, debit, credit, running_balance
        """
    def get_first_row_data(self) -> dict:
        """Read data from the first transaction row."""
        rows = self.get_all_rows_data()
        if rows:
            return rows[0]
        return {"date": "", "voucher_id": "", "narration": "", "debit": "", "credit": "", "running_balance": ""}

    def get_all_rows_data(self) -> list[dict]:
        """Read all transaction rows from the table."""
        try:
            self.page.locator("table tbody tr, [role='row']").first.wait_for(state="visible", timeout=8000)
        except Exception:
            pass

        headers = [h.lower() for h in self.get_table_headers()]
        date_idx = next((i for i, h in enumerate(headers) if "date" in h), 0)
        voucher_idx = next((i for i, h in enumerate(headers) if "voucher" in h or "no" in h), 1)
        narration_idx = next((i for i, h in enumerate(headers) if "narration" in h or "particular" in h or "desc" in h), 2)
        debit_idx = next((i for i, h in enumerate(headers) if "debit" in h), 3)
        credit_idx = next((i for i, h in enumerate(headers) if "credit" in h), 4)
        balance_idx = next((i for i, h in enumerate(headers) if "balance" in h or "running" in h), 5)

        rows = self.page.locator("table tbody tr").all()
        data = []
        for row in rows:
            cells = row.locator("td").all()
            if len(cells) >= 3:
                text = row.text_content().lower()
                if "no data" in text or "no transactions" in text or "no records" in text:
                    continue
                get_val = lambda idx: cells[idx].text_content().strip() if idx < len(cells) else ""
                data.append({
                    "date": get_val(date_idx),
                    "voucher_id": get_val(voucher_idx),
                    "narration": get_val(narration_idx),
                    "debit": get_val(debit_idx),
                    "credit": get_val(credit_idx),
                    "running_balance": get_val(balance_idx) if balance_idx < len(cells) else get_val(len(cells) - 1),
                })
        return data


    def has_table_visible(self) -> bool:
        """Check if the statement table is visible."""
        try:
            tbl = self.page.locator("table, .table-responsive, [role='table']").first
            if tbl.count() > 0 and tbl.is_visible():
                return True
            tbl.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False


    def get_table_headers(self) -> list[str]:
        """Read table column headers."""
        try:
            self.page.locator("table thead th, table thead td, table th").first.wait_for(state="visible", timeout=5000)
            headers = self.page.locator("table thead th, table thead td, table th").all()
            return [h.text_content().strip() for h in headers]
        except Exception:
            return []

    # ══════════════════════════════════════════════════════════════════════════
    # RUNNING BALANCE VERIFICATION
    # ══════════════════════════════════════════════════════════════════════════

    def verify_running_balance_progression(self) -> bool:
        """Verify that running balance column has values for each row."""
        rows = self.get_all_rows_data()
        if not rows:
            return True
        for row in rows:
            if not row.get("running_balance") and not (row.get("debit") or row.get("credit")):
                return False
        return True

    def verify_closing_equals_last_running_balance(self) -> bool:
        """Verify that closing balance matches the last row's running balance."""
        rows = self.get_all_rows_data()
        if not rows:
            return True  # No transactions — closing = opening

        last_running = rows[-1]["running_balance"]
        closing = self.get_closing_balance()
        if not closing or not last_running:
            return True

        def to_num(val: str) -> float:
            num = re.sub(r"[^\d.-]", "", val)
            return float(num) if num else 0.0

        return abs(to_num(closing) - to_num(last_running)) < 0.01

    # ══════════════════════════════════════════════════════════════════════════
    # DEBIT/CREDIT COLUMN VERIFICATION
    # ══════════════════════════════════════════════════════════════════════════

    def has_debit_entries(self) -> bool:
        """Check if any row has a non-zero debit value or summary debit is non-zero."""
        rows = self.get_all_rows_data()
        for row in rows:
            val = re.sub(r"[₹,\s]", "", row["debit"])
            if val and val not in ("0", "0.00", "-", ""):
                return True
        total_debit = re.sub(r"[₹,\s]", "", self.get_total_debits())
        return bool(total_debit and total_debit not in ("0", "0.00", "-", ""))

    def has_credit_entries(self) -> bool:
        """Check if any row has a non-zero credit value or summary credit is non-zero."""
        rows = self.get_all_rows_data()
        for row in rows:
            val = re.sub(r"[₹,\s]", "", row["credit"])
            if val and val not in ("0", "0.00", "-", ""):
                return True
        total_credit = re.sub(r"[₹,\s]", "", self.get_total_credits())
        return bool(total_credit and total_credit not in ("0", "0.00", "-", ""))
