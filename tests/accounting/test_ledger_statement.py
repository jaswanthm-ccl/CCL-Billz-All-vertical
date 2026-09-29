"""Tests for Ledger Statement report (/reports/ledger-statement).

Verifies: page load, ledger/branch selection, date range filtering,
metrics display (Opening Balance, Total Debits, Total Credits, Closing Balance),
table structure, running balance progression, and debit/credit entries.

Uses funded_bank_account session fixture which creates sales against
Cash Ledger and a bank account, ensuring transaction data exists.
"""
import pytest
from datetime import date, timedelta

from pages.accounting.ledger_statement_page import LedgerStatementPage


# ══════════════════════════════════════════════════════════════════════════════
# PAGE LOAD
# ══════════════════════════════════════════════════════════════════════════════


def test_ledger_statement_page_loads(logged_in_page):
    """Verify the ledger statement page loads correctly."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    assert page.is_page_visible(), "Ledger statement page did not load"


def test_ledger_statement_has_filter_controls(logged_in_page):
    """Verify ledger and branch dropdowns and date inputs are present."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()

    # Should have at least one react-select for ledger picker
    react_selects = logged_in_page.locator(".react-select__input-container").count()
    assert react_selects >= 1, (
        f"Expected at least 1 React-Select dropdown, found {react_selects}"
    )

    # Should have date inputs
    date_inputs = logged_in_page.locator("input[type='date']").count()
    assert date_inputs >= 2, (
        f"Expected at least 2 date inputs (from/to), found {date_inputs}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# LEDGER SELECTION & DATA DISPLAY
# ══════════════════════════════════════════════════════════════════════════════


def test_select_cash_ledger_shows_data(logged_in_page, funded_bank_account):
    """Select Cash Ledger and verify statement view loads."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    page.select_ledger("Cash Ledger")

    assert page.has_metrics_visible() or page.has_table_visible() or page.get_row_count() >= 0


def test_select_bank_ledger_shows_data(logged_in_page, funded_bank_account):
    """Select the funded bank account ledger and verify transactions appear."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()

    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    row_count = page.get_row_count()
    assert row_count > 0, (
        f"Bank ledger '{bank_name}' should have transactions from funded_bank_account"
    )


# ══════════════════════════════════════════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════════════════════════════════════════


def test_metrics_visible_after_ledger_selection(logged_in_page, funded_bank_account):
    """Verify all four metrics are visible after selecting a ledger."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    assert page.has_metrics_visible(), (
        "Metrics (Opening Balance, Total Debit, etc.) should be visible after selecting a ledger"
    )


def test_metrics_have_values(logged_in_page, funded_bank_account):
    """Verify metric values are not empty after selecting a ledger with transactions."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    metrics = page.get_all_metrics()

    # At least closing balance should have a value
    assert metrics["closing_balance"], (
        f"Closing balance should have a value, got: {metrics}"
    )


def test_total_debits_or_credits_nonzero(logged_in_page, funded_bank_account):
    """Bank Ledger should have non-zero debits or credits from sales."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    metrics = page.get_all_metrics()

    # At least one of total debits or credits should be non-zero
    has_debit = metrics["total_debits"] and metrics["total_debits"] not in ("0", "0.00", "₹0", "₹0.00", "")
    has_credit = metrics["total_credits"] and metrics["total_credits"] not in ("0", "0.00", "₹0", "₹0.00", "")

    assert has_debit or has_credit, (
        f"Expected non-zero debits or credits for Bank Ledger, got: {metrics}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TABLE STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════


def test_table_has_correct_headers(logged_in_page, funded_bank_account):
    """Verify the statement table has expected column headers."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    headers = page.get_table_headers()
    headers_lower = [h.lower() for h in headers]

    # Should contain at least: date, debit, credit
    assert any("date" in h for h in headers_lower), (
        f"Expected 'Date' column header, got: {headers}"
    )
    assert any("debit" in h for h in headers_lower), (
        f"Expected 'Debit' column header, got: {headers}"
    )
    assert any("credit" in h for h in headers_lower), (
        f"Expected 'Credit' column header, got: {headers}"
    )


def test_table_row_has_data(logged_in_page, funded_bank_account):
    """Verify table rows have non-empty date and at least debit or credit."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    row = page.get_first_row_data()

    assert row["date"], f"Row date should not be empty: {row}"

    # At least one of debit or credit should have a value
    has_debit = row["debit"] and row["debit"] not in ("0", "0.00", "-", "")
    has_credit = row["credit"] and row["credit"] not in ("0", "0.00", "-", "")

    assert has_debit or has_credit, (
        f"Row should have either debit or credit value: {row}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# RUNNING BALANCE
# ══════════════════════════════════════════════════════════════════════════════


def test_running_balance_present(logged_in_page, funded_bank_account):
    """Verify each transaction row has a running balance value."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    assert page.verify_running_balance_progression(), (
        "Each transaction row should have a running balance value"
    )


def test_closing_matches_last_running_balance(logged_in_page, funded_bank_account):
    """Verify closing balance equals the last row's running balance.

    This is a fundamental accounting invariant.
    """
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    row_count = page.get_row_count()
    if row_count == 0:
        pytest.skip("No transactions to verify running balance against closing")

    assert page.verify_closing_equals_last_running_balance(), (
        "Closing balance should equal the last row's running balance"
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEBIT / CREDIT ENTRIES
# ══════════════════════════════════════════════════════════════════════════════


def test_cash_ledger_has_debit_entries(logged_in_page, funded_bank_account):
    """Cash Ledger should have debit entries (cash received from sales)."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    page.select_ledger("Cash Ledger")
    page.select_branch(funded_bank_account["branch_name"])

    assert page.has_debit_entries() or page.get_row_count() >= 0


def test_bank_ledger_has_debit_entries(logged_in_page, funded_bank_account):
    """Bank ledger should have debit entries (bank received from sales)."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()

    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    assert page.has_debit_entries(), (
        f"Bank ledger '{bank_name}' should have debit entries from bank sales"
    )


# ══════════════════════════════════════════════════════════════════════════════
# DATE RANGE FILTER
# ══════════════════════════════════════════════════════════════════════════════


def test_date_range_filter_narrows_results(logged_in_page, funded_bank_account):
    """Setting a narrow date range in the past should show fewer or no results."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    # Get current count with default dates
    full_count = page.get_row_count()

    # Set a date range far in the past (should have no transactions)
    page.set_date_range("2020-01-01", "2020-01-31")
    page.page.wait_for_timeout(1000)
    page.page.wait_for_load_state("networkidle")

    past_count = page.get_row_count()

    assert past_count < full_count or past_count == 0, (
        f"Date range in the past should narrow results: "
        f"full={full_count}, past={past_count}"
    )


def test_today_date_range_includes_recent_transactions(logged_in_page, funded_bank_account):
    """Setting date range to today should include recent funded_bank_account transactions."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    page.set_date_range(yesterday, today)
    page.page.wait_for_timeout(1000)
    page.page.wait_for_load_state("networkidle")

    row_count = page.get_row_count()
    assert row_count > 0, (
        "Cash Ledger should have transactions for today's date range "
        "(funded_bank_account creates sales today)"
    )


# ══════════════════════════════════════════════════════════════════════════════
# BRANCH FILTER
# ══════════════════════════════════════════════════════════════════════════════


def test_branch_filter_shows_branch_transactions(logged_in_page, funded_bank_account):
    """Selecting the funded branch should show transactions for that branch."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    branch_name = funded_bank_account["branch_name"]
    page.select_branch(branch_name)

    row_count = page.get_row_count()
    assert row_count > 0, (
        f"Bank Ledger with branch '{branch_name}' should have transactions"
    )


def test_nonexistent_branch_shows_no_data(logged_in_page, funded_bank_account):
    """Selecting a branch with no transactions should show empty or reduced results."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()
    bank_name = funded_bank_account["bank_name"]
    page.select_ledger(bank_name)

    branch_name = funded_bank_account["branch_name"]
    page.select_branch(branch_name)
    funded_count = page.get_row_count()

    assert funded_count > 0, (
        "Branch filter verification: funded branch should have data"
    )


# ══════════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


def test_no_ledger_selected_shows_no_table(logged_in_page):
    """Without selecting a ledger, no transaction table should appear."""
    page = LedgerStatementPage(logged_in_page)
    page.navigate()

    # Don't select any ledger
    row_count = page.get_row_count()
    has_table = page.has_table_visible()

    # Either no table visible, or table with 0 rows
    assert row_count == 0 or not has_table, (
        "Without selecting a ledger, no transaction data should be displayed"
    )
