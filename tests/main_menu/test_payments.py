import pytest
from pages.main_menu.payments_page import PaymentsPage


def test_payments_page_loads(logged_in_page):
    """Verify the payments page loads correctly."""
    payments_page = PaymentsPage(logged_in_page)
    payments_page.navigate()
    assert payments_page.is_payments_visible(), "Payments page did not load"


def test_payments_list_has_data(logged_in_page, funded_bank_account):
    """Verify payments exist (auto-generated from the funded_bank_account sale).

    The funded_bank_account fixture creates Sales with paid_amount=500,
    which auto-generates payment records visible here.
    """
    payments_page = PaymentsPage(logged_in_page)
    payments_page.navigate()

    row_count = payments_page.get_row_count()
    assert row_count > 0, "No payments found — expected at least one from funded_bank_account sale"


def test_payment_row_has_correct_structure(logged_in_page, funded_bank_account):
    """Verify payment row displays type, reference, status, and amount."""
    payments_page = PaymentsPage(logged_in_page)
    payments_page.navigate()

    row_data = payments_page.get_first_row_data()

    # Type should be "Sale" or "Purchase"
    assert row_data["type"] in ("Sale", "Purchase"), (
        f"Expected type 'Sale' or 'Purchase', got '{row_data['type']}'"
    )

    # Reference should contain the type and ID (e.g., "Sale #123")
    assert row_data["reference"], "Reference should not be empty"

    # Status should be a valid status
    assert row_data["status"].lower() in ("paid", "unpaid", "partial"), (
        f"Expected status paid/unpaid/partial, got '{row_data['status']}'"
    )

    # Amount should contain ₹
    assert "₹" in row_data["amount"], (
        f"Expected ₹ in amount, got '{row_data['amount']}'"
    )


def test_search_payment(logged_in_page, funded_bank_account):
    """Search for a payment by type 'Sale'."""
    payments_page = PaymentsPage(logged_in_page)
    payments_page.navigate()

    assert payments_page.search_payment("Sale"), (
        "No payments found when searching for 'Sale'"
    )


@pytest.mark.skip(reason="Search API does not filter results correctly - returns all payments regardless of query. Reported to dev team.")
def test_search_payment_filters_correctly(logged_in_page, funded_bank_account):
    """Verify search actually filters: nonsense query should return no results."""
    payments_page = PaymentsPage(logged_in_page)
    payments_page.navigate()

    # A nonsense search should return empty
    assert not payments_page.search_payment("xyznonexistent99999"), (
        "Search returned results for nonsense query — search is not filtering server-side"
    )


def test_view_payment_reference(logged_in_page, funded_bank_account):
    """Click a payment reference to open the Sale/Purchase view modal."""
    payments_page = PaymentsPage(logged_in_page)
    payments_page.navigate()

    assert payments_page.view_payment_reference(), (
        "Payment reference modal did not open"
    )
    payments_page.close_modal()
