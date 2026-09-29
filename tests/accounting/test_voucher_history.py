import pytest
from pages.accounting.voucher_history_page import VoucherHistoryPage


# ══════════════════════════════════════════════════════════════════════════════
# PAGE LOAD
# ══════════════════════════════════════════════════════════════════════════════


def test_voucher_history_page_loads(logged_in_page):
    """Verify the voucher history page loads correctly."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    assert page.is_page_visible(), "Voucher history page did not load"


def test_voucher_history_has_data(logged_in_page, funded_bank_account):
    """Verify vouchers exist (auto-generated from funded_bank_account sales).

    The funded_bank_account fixture creates Sales which generate system
    vouchers visible in the history.
    """
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()

    # Include system vouchers to see sale-generated entries
    page.toggle_include_system_vouchers(True)

    row_count = page.get_row_count()
    assert row_count > 0, (
        "No vouchers found — expected at least one from funded_bank_account sales"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TABLE STRUCTURE
# ══════════════════════════════════════════════════════════════════════════════


def test_voucher_row_has_correct_structure(logged_in_page, funded_bank_account):
    """Verify voucher row displays voucher_no, type, source, amount, status, date."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    row_data = page.get_first_row_data()

    # Voucher number should not be empty
    assert row_data["voucher_no"], (
        f"Voucher number is empty: {row_data}"
    )

    # Type should have a value
    assert row_data["type"], (
        f"Voucher type is empty: {row_data}"
    )

    # Source should be 'user' or 'system'
    assert row_data["source"] in ("user", "system"), (
        f"Expected source 'user' or 'system', got '{row_data['source']}'"
    )

    # Status should be 'active' or 'reversed'
    assert row_data["status"] in ("active", "reversed"), (
        f"Expected status 'active' or 'reversed', got '{row_data['status']}'"
    )

    # Date should not be empty
    assert row_data["date"], (
        f"Date is empty: {row_data}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════════


def test_search_voucher_by_number(logged_in_page, funded_bank_account):
    """Search for a voucher by its voucher number."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    # Get the first voucher number to search for
    row_data = page.get_first_row_data()
    voucher_no = row_data["voucher_no"]
    assert voucher_no, "No voucher number to search for"

    # Search for it
    assert page.search_voucher(voucher_no), (
        f"Voucher '{voucher_no}' not found in search"
    )

    # Verify the result contains the searched voucher number
    result_data = page.get_first_row_data()
    assert voucher_no in result_data["voucher_no"], (
        f"Expected '{voucher_no}' in search result, got '{result_data['voucher_no']}'"
    )


def test_search_nonexistent_voucher(logged_in_page):
    """Search for a non-existent voucher returns no results."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()

    assert not page.search_voucher("NONEXISTENT_XYZ_99999"), (
        "Expected no results for non-existent voucher search"
    )


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE FILTER
# ══════════════════════════════════════════════════════════════════════════════


def test_filter_by_user_source(logged_in_page, funded_bank_account):
    """Filter vouchers by 'User' source and verify all rows are user-sourced."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()

    page.filter_by_source("user")

    row_count = page.get_row_count()
    if row_count == 0:
        pytest.skip("No user-sourced vouchers available to test filter")

    sources = page.get_all_row_sources()
    for source in sources:
        assert source == "user", (
            f"Expected all rows to have source 'user', found '{source}'"
        )


def test_filter_by_system_source(logged_in_page, funded_bank_account):
    """Filter vouchers by 'System' source and verify all rows are system-sourced."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()

    # Must include system vouchers first
    page.toggle_include_system_vouchers(True)
    page.filter_by_source("system")

    row_count = page.get_row_count()
    if row_count == 0:
        pytest.skip("No system-sourced vouchers available to test filter")

    sources = page.get_all_row_sources()
    for source in sources:
        assert source == "system", (
            f"Expected all rows to have source 'system', found '{source}'"
        )


def test_filter_all_sources(logged_in_page, funded_bank_account):
    """Filter by 'All sources' shows vouchers from both user and system."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()

    page.toggle_include_system_vouchers(True)
    page.filter_by_source("")  # All sources

    row_count = page.get_row_count()
    assert row_count > 0, "Expected vouchers when showing all sources"


# ══════════════════════════════════════════════════════════════════════════════
# VIEW DETAIL
# ══════════════════════════════════════════════════════════════════════════════


def test_view_voucher_detail(logged_in_page, funded_bank_account):
    """Click View on first voucher and verify detail page loads."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    assert page.view_first_voucher(), (
        "Failed to navigate to voucher detail page"
    )

    assert page.is_voucher_detail_visible(), (
        "Voucher detail page did not load correctly"
    )


def test_voucher_detail_has_entries(logged_in_page, funded_bank_account):
    """Verify voucher detail page shows ledger entries."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    assert page.view_first_voucher(), "Failed to navigate to voucher detail"

    detail = page.get_voucher_detail_data()
    assert detail["type"], "Voucher type should be displayed"
    assert detail["source"], "Voucher source should be displayed"
    assert detail["has_entries"], "Voucher should have ledger entries"


def test_voucher_detail_back_to_history(logged_in_page, funded_bank_account):
    """Verify 'Back to history' link returns to voucher list."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    assert page.view_first_voucher(), "Failed to navigate to voucher detail"

    page.click_back_to_history()
    assert page.is_page_visible(), (
        "Did not return to voucher history page"
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGINATION
# ══════════════════════════════════════════════════════════════════════════════


def test_pagination_controls_visible(logged_in_page, funded_bank_account):
    """Verify pagination controls are present on the page."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    # Page size selector should be visible
    page_size = page.get_page_size()
    assert page_size in (5, 10, 20, 50, 100, 500), (
        f"Unexpected page size: {page_size}"
    )


def test_change_page_size(logged_in_page, funded_bank_account):
    """Change page size and verify the row count respects it."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    # Set to smallest page size
    page.set_page_size(5)
    row_count = page.get_row_count()
    assert row_count <= 5, (
        f"Expected at most 5 rows with page size 5, got {row_count}"
    )


def test_pagination_next_prev(logged_in_page, funded_bank_account):
    """If multiple pages exist, navigate forward and back."""
    page = VoucherHistoryPage(logged_in_page)
    page.navigate()
    page.toggle_include_system_vouchers(True)

    # Use smallest page size to increase chance of multiple pages
    page.set_page_size(5)

    if not page.has_next_page():
        pytest.skip("Not enough vouchers for multi-page pagination test")

    # Get first row on page 1
    first_page_row = page.get_first_row_data()

    # Go to next page
    page.go_next_page()
    second_page_row = page.get_first_row_data()

    # Rows should differ between pages
    assert first_page_row["voucher_no"] != second_page_row["voucher_no"], (
        "Expected different vouchers on page 2"
    )

    # Go back
    page.go_prev_page()
    back_row = page.get_first_row_data()

    # Should be back to page 1 data
    assert back_row["voucher_no"] == first_page_row["voucher_no"], (
        f"Expected to return to page 1 voucher '{first_page_row['voucher_no']}', "
        f"got '{back_row['voucher_no']}'"
    )
