import random
import pytest
from pages.main_menu.ledgers_page import LedgersPage
from pages.master_menu.bank_accounts_page import BankAccountPage
from utils.random_data import generate_random_name


def test_ledgers_page_loads(logged_in_page):
    """Verify the ledgers page loads correctly."""
    ledgers_page = LedgersPage(logged_in_page)
    ledgers_page.navigate()
    assert ledgers_page.is_ledgers_visible(), "Ledgers page did not load"


def test_ledgers_has_data(logged_in_page):
    """Verify ledgers exist (auto-created from system entities)."""
    ledgers_page = LedgersPage(logged_in_page)
    ledgers_page.navigate()

    row_count = ledgers_page.get_row_count()
    assert row_count > 0, "No ledgers found — expected auto-created ledgers (Cash, Bank, etc.)"


def test_search_ledger_by_name(logged_in_page):
    """Search for 'Cash Ledger' which is always auto-created per branch."""
    ledgers_page = LedgersPage(logged_in_page)
    ledgers_page.navigate()

    assert ledgers_page.search_ledger("Cash Ledger"), (
        "Cash Ledger not found in search"
    )

    row_data = ledgers_page.get_first_row_data()
    assert "Cash Ledger" in row_data["name"], (
        f"Expected 'Cash Ledger' in name, got '{row_data['name']}'"
    )


def test_search_ledger_by_bank(logged_in_page, funded_bank_account):
    """Search for the funded bank account's ledger (auto-created when bank was added)."""
    ledgers_page = LedgersPage(logged_in_page)
    ledgers_page.navigate()

    bank_name = funded_bank_account["bank_name"]
    assert ledgers_page.search_ledger(bank_name), (
        f"Bank ledger '{bank_name}' not found in search"
    )

    row_data = ledgers_page.get_first_row_data()
    assert bank_name in row_data["name"], (
        f"Expected '{bank_name}' in ledger name, got '{row_data['name']}'"
    )


def test_edit_ledger_opening_balance(logged_in_page):
    """Edit an un-transacted ledger's opening balance (DR and CR), and verify changes.

    Flow:
    1. Create fresh un-transacted bank accounts for DR and CR
    2. Set DR 200 on first ledger → verify it updated in the table
    3. Set CR 150 on second ledger → verify it updated in the table with Cr
    4. Clean up the created bank accounts
    """
    bank_page = BankAccountPage(logged_in_page)
    bank_page.navigate()
    fresh_bank_dr = generate_random_name("edit_dr")
    bank_page.add_bank_account(
        bank_name=fresh_bank_dr,
        branch="Automation Branch",
        account_number=str(random.randint(100000000000, 999999999999)),
        ifsc_code="IDFC0000899",
    )

    fresh_bank_cr = generate_random_name("edit_cr")
    bank_page.add_bank_account(
        bank_name=fresh_bank_cr,
        branch="Automation Branch",
        account_number=str(random.randint(100000000000, 999999999999)),
        ifsc_code="IDFC0000899",
    )

    try:
        ledgers_page = LedgersPage(logged_in_page)
        ledgers_page.navigate()

        # 1. Search fresh DR bank ledger
        ledgers_page.search_ledger(fresh_bank_dr)
        original_data = ledgers_page.get_first_row_data()
        assert original_data is not None, f"Ledger for {fresh_bank_dr} must exist"

        # 2. Edit to DR 200
        assert ledgers_page.edit_ledger(
            name=fresh_bank_dr,
            opening_balance="200",
            balance_type="dr",
        ), "Failed to update ledger to DR 200"

        # Verify the change in the table
        ledgers_page.navigate()
        ledgers_page.search_ledger(fresh_bank_dr)
        row_data = ledgers_page.get_first_row_data()
        assert "200" in row_data["opening_balance"], (
            f"Expected '200' in opening balance after DR edit, got '{row_data['opening_balance']}'"
        )

        # 3. Edit CR ledger to CR 150
        ledgers_page.navigate()
        assert ledgers_page.edit_ledger(
            name=fresh_bank_cr,
            opening_balance="150",
            balance_type="cr",
        ), "Failed to update ledger to CR 150"

        # Verify the CR change
        ledgers_page.navigate()
        ledgers_page.search_ledger(fresh_bank_cr)
        row_data = ledgers_page.get_first_row_data()
        assert "150" in row_data["opening_balance"], (
            f"Expected '150' in opening balance after CR edit, got '{row_data['opening_balance']}'"
        )
        assert "Cr" in row_data["opening_balance"], (
            f"Expected 'Cr' in opening balance, got '{row_data['opening_balance']}'"
        )
    finally:
        for bank in [fresh_bank_dr, fresh_bank_cr]:
            try:
                bank_page.navigate()
                if bank_page.search_bank_account(bank):
                    bank_page.delete_bank_account(bank)
            except Exception:
                pass
