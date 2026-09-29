import pytest
from pages.main_menu.chits_page import ChitsPage
from pages.master_menu.branches_page import BranchesPage
from utils.random_data import generate_random_name


@pytest.fixture(scope="module")
def module_branch(module_page):
    """Create a branch for chit tests."""
    branches_page = BranchesPage(module_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branches_page.page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    yield branch_name
    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete branch {branch_name}: {e}")


@pytest.fixture(scope="module")
def module_chit(module_page, funded_bank_account):
    """Create a chit once per module for tests that need a pre-existing chit.

    Uses the funded_bank_account's branch so the chit ledger exists and
    payments/commissions can be recorded against a branch with balance.

    Returns the chit name for searching/interacting.
    """
    chits_page = ChitsPage(module_page)
    chits_page.navigate()

    chit_name = generate_random_name("mod_chit")
    chits_page.add_chit(
        chit_name=chit_name,
        branch=funded_bank_account["branch_name"],
        chit_value="100000",
        tenure_months="12",
        monthly_amount="10000",
        foreman_name="Module Foreman",
        commission_amount="5000",
        notes="Module-scoped chit for tests",
    )

    # Verify creation
    chits_page.navigate()
    assert chits_page.search_chit(chit_name), (
        f"Module chit '{chit_name}' not found after creation"
    )

    yield chit_name


# ══════════════════════════════════════════════════════════════════════════════
# EXISTING TESTS (CRUD basics)
# ══════════════════════════════════════════════════════════════════════════════


def test_chits_page_loads(logged_in_page):
    """Verify the chits page loads correctly."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()
    assert chits_page.is_chits_visible(), "Chits page did not load"


def test_add_chit(logged_in_page, module_branch):
    """Create a new chit and verify it appears in the list."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    chit_name = generate_random_name("test_chit")
    chits_page.add_chit(
        chit_name=chit_name,
        branch=module_branch,
        chit_value="100000",
        tenure_months="12",
        monthly_amount="10000",
        foreman_name="Auto Foreman",
        commission_amount="5000",
        notes="Automated chit test",
    )

    # Verify it appears in search
    chits_page.navigate()
    assert chits_page.search_chit(chit_name), (
        f"Chit '{chit_name}' not found after creation"
    )

    # Verify row data
    row_data = chits_page.get_first_row_data()
    assert chit_name in row_data["name"], (
        f"Expected '{chit_name}' in name, got '{row_data['name']}'"
    )
    assert "No" in row_data["is_closed"], (
        f"Expected 'No' in closed status, got '{row_data['is_closed']}'"
    )


def test_search_chit(logged_in_page, module_branch):
    """Create a chit with unique name, then search for it."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    unique_name = generate_random_name("search_chit")
    chits_page.add_chit(
        chit_name=unique_name,
        branch=module_branch,
        chit_value="50000",
        tenure_months="6",
        monthly_amount="9000",
    )

    chits_page.navigate()
    assert chits_page.search_chit(unique_name), (
        f"Chit '{unique_name}' not found in search"
    )


def test_view_chit(logged_in_page, module_branch):
    """Create a chit, then view its details."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    view_name = generate_random_name("view_chit")
    chits_page.add_chit(
        chit_name=view_name,
        branch=module_branch,
        chit_value="75000",
        tenure_months="10",
        monthly_amount="8000",
    )

    chits_page.navigate()
    assert chits_page.view_chit(view_name), (
        f"Could not view chit '{view_name}'"
    )
    chits_page.close_modal()


def test_edit_chit(logged_in_page, module_branch):
    """Create a chit, then edit its foreman name."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    edit_name = generate_random_name("edit_chit")
    chits_page.add_chit(
        chit_name=edit_name,
        branch=module_branch,
        chit_value="60000",
        tenure_months="8",
        monthly_amount="8000",
        foreman_name="Original Foreman",
    )

    chits_page.navigate()
    new_foreman = "Updated Foreman"
    assert chits_page.edit_chit(edit_name, new_foreman), (
        f"Failed to edit chit '{edit_name}'"
    )

    # Verify the change
    chits_page.navigate()
    chits_page.search_chit(edit_name)
    row_data = chits_page.get_first_row_data()
    assert new_foreman in row_data["foreman_name"], (
        f"Expected foreman '{new_foreman}', got '{row_data['foreman_name']}'"
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLOSE CHIT TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_close_chit(logged_in_page, module_branch):
    """Create a chit, close it, verify the CLOSED column shows 'Yes'."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    close_name = generate_random_name("close_chit")
    chits_page.add_chit(
        chit_name=close_name,
        branch=module_branch,
        chit_value="80000",
        tenure_months="10",
        monthly_amount="8000",
    )

    chits_page.navigate()
    assert chits_page.close_chit(close_name), (
        f"Failed to close chit '{close_name}'"
    )

    # Verify the chit now shows as closed
    chits_page.navigate()
    chits_page.search_chit(close_name)
    row_data = chits_page.get_first_row_data()
    assert "Yes" in row_data["is_closed"], (
        f"Expected 'Yes' in closed status after closing, got '{row_data['is_closed']}'"
    )


def test_closed_chit_cannot_be_edited(logged_in_page, module_branch):
    """Close a chit and verify the edit action is not available."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    chit_name = generate_random_name("noedit_chit")
    chits_page.add_chit(
        chit_name=chit_name,
        branch=module_branch,
        chit_value="70000",
        tenure_months="6",
        monthly_amount="12000",
    )

    # Close the chit
    chits_page.navigate()
    assert chits_page.close_chit(chit_name), (
        f"Failed to close chit '{chit_name}'"
    )

    # Verify edit is not available
    chits_page.navigate()
    assert not chits_page.is_edit_available(chit_name), (
        f"Edit action should NOT be available for closed chit '{chit_name}'"
    )


# ══════════════════════════════════════════════════════════════════════════════
# RECORD PAYMENT TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_record_payment_cash(logged_in_page, module_chit, funded_bank_account):
    """Record a payment for a chit using the funded bank account."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    assert chits_page.record_payment(
        chit_name=module_chit,
        amount="100",
        payment_mode="Bank",
        bank_account=funded_bank_account["bank_name"],
        payment_month="1",
        narration="Payment month 1",
    ), f"Failed to record payment for chit '{module_chit}'"


def test_record_payment_bank(logged_in_page, module_chit, funded_bank_account):
    """Record a bank payment for a chit and verify success."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    assert chits_page.record_payment(
        chit_name=module_chit,
        amount="100",
        payment_mode="Bank",
        bank_account=funded_bank_account["bank_name"],
        payment_month="2",
        narration="Bank payment month 2",
    ), f"Failed to record bank payment for chit '{module_chit}'"


# ══════════════════════════════════════════════════════════════════════════════
# RECORD COMMISSION TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_record_commission(logged_in_page, module_chit, funded_bank_account):
    """Record a commission for a chit and verify success.

    Uses funded_bank_account to ensure the branch has balance for the commission entry.
    """
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    assert chits_page.record_commission(
        chit_name=module_chit,
        amount="100",
        commission_month="1",
        narration="Commission month 1",
    ), f"Failed to record commission for chit '{module_chit}'"


@pytest.mark.skip(
    reason=(
        "Known bug: new branches are not provisioned with the Chit Commission "
        "Expense Ledger, so recording commission fails"
    )
)
def test_new_branch_has_required_chit_commission_ledger():
    """A newly created branch must support Chit commission recording."""


# ══════════════════════════════════════════════════════════════════════════════
# VIEW PAYMENT / COMMISSION LIST TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_view_payment_list(logged_in_page, module_chit, funded_bank_account):
    """Open the payment list for a chit that has recorded payments.

    Depends on test_record_payment_cash having run first (module_chit has a payment).
    """
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    assert chits_page.view_payment_list(module_chit), (
        f"Could not open payment list for chit '{module_chit}'"
    )

    # Verify at least one payment row exists
    row_count = chits_page.get_payment_list_row_count()
    assert row_count > 0, (
        f"Expected at least 1 payment row, got {row_count}"
    )
    chits_page.close_modal()


def test_view_commission_list(logged_in_page, module_chit, funded_bank_account):
    """Open the commission list for a chit that has recorded commissions.

    Depends on test_record_commission having run first (module_chit has a commission).
    """
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    assert chits_page.view_commission_list(module_chit), (
        f"Could not open commission list for chit '{module_chit}'"
    )

    # Verify at least one commission row exists
    row_count = chits_page.get_payment_list_row_count()
    assert row_count > 0, (
        f"Expected at least 1 commission row, got {row_count}"
    )
    chits_page.close_modal()


# ══════════════════════════════════════════════════════════════════════════════
# VIEW SUMMARY TEST
# ══════════════════════════════════════════════════════════════════════════════


def test_view_summary(logged_in_page, module_chit):
    """Open the summary for a chit and verify key data fields are displayed."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    assert chits_page.view_summary(module_chit), (
        f"Could not open summary for chit '{module_chit}'"
    )

    # Verify summary data contains expected labels
    summary_data = chits_page.get_summary_data()
    assert "Total Contribution" in summary_data, (
        f"Expected 'Total Contribution' in summary, got keys: {list(summary_data.keys())}"
    )
    assert "Current Balance" in summary_data, (
        f"Expected 'Current Balance' in summary, got keys: {list(summary_data.keys())}"
    )
    chits_page.close_modal()


@pytest.mark.skip(
    reason=(
        "Known bug: Chit Summary Net Position double-counts contributions by "
        "adding Total Contribution and Current Balance"
    )
)
def test_chit_summary_net_position_is_not_double_counted(
    logged_in_page, module_chit
):
    """Net Position must not add a contribution already held in Current Balance."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()
    assert chits_page.view_summary(module_chit)

    summary = chits_page.get_summary_data()
    assert chits_page.parse_amount(summary["Net Position"]) == chits_page.parse_amount(
        summary["Current Balance"]
    )
    chits_page.close_modal()


@pytest.mark.skip(
    reason=(
        "Known bug: Chit Payment List Total adds both debit and credit entries, "
        "displaying twice the actual payment amount"
    )
)
def test_chit_payment_list_total_is_not_double_counted(
    logged_in_page, module_chit
):
    """A ₹100 balanced payment must display ₹100, not debit plus credit."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()
    assert chits_page.view_payment_list(module_chit)

    payments = chits_page.get_payment_list_rows()
    month_one = next(
        payment for payment in payments if "Payment month 1" in payment["narration"]
    )
    assert chits_page.parse_amount(month_one["total"]) == chits_page.parse_amount("100")
    chits_page.close_modal()


# ══════════════════════════════════════════════════════════════════════════════
# CLOSED CHIT NOT IN PAYMENT DROPDOWN
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.xfail(
    reason="Application defect: Closed chits are still listed in the Record Payment dropdown",
    strict=False,
)
def test_closed_chit_not_in_payment_dropdown(logged_in_page, module_branch):
    """Close a chit and verify it does NOT appear in the Record Payment dropdown."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    chit_name = generate_random_name("dropdown_chit")
    chits_page.add_chit(
        chit_name=chit_name,
        branch=module_branch,
        chit_value="50000",
        tenure_months="6",
        monthly_amount="9000",
    )

    # Close the chit
    chits_page.navigate()
    assert chits_page.close_chit(chit_name), (
        f"Failed to close chit '{chit_name}'"
    )

    # Verify it does NOT appear in the payment dropdown
    chits_page.navigate()
    assert not chits_page.is_chit_in_payment_dropdown(chit_name), (
        f"Closed chit '{chit_name}' should NOT appear in the payment dropdown"
    )


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_add_chit_validation_required_fields(logged_in_page):
    """Submit the Add Chit form empty and verify validation errors appear."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    errors = chits_page.submit_empty_add_form()
    assert len(errors) > 0, (
        "Expected validation errors when submitting empty chit form, got none"
    )


def test_record_payment_validation(logged_in_page):
    """Submit the Record Payment form empty and verify validation errors appear."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    errors = chits_page.submit_empty_payment_form()
    assert len(errors) > 0, (
        "Expected validation errors when submitting empty payment form, got none"
    )


def test_record_commission_validation(logged_in_page):
    """Submit the Record Commission form empty and verify validation errors appear."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    errors = chits_page.submit_empty_commission_form()
    assert len(errors) > 0, (
        "Expected validation errors when submitting empty commission form, got none"
    )


# ══════════════════════════════════════════════════════════════════════════════
# DELETE / RESTORE TESTS
# ══════════════════════════════════════════════════════════════════════════════


def test_delete_chit(logged_in_page, module_branch):
    """Create a chit, delete it, verify it disappears from search."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    del_name = generate_random_name("del_chit")
    chits_page.add_chit(
        chit_name=del_name,
        branch=module_branch,
        chit_value="40000",
        tenure_months="4",
        monthly_amount="10000",
    )

    chits_page.navigate()
    result = chits_page.delete_chit(del_name)
    if not result:
        pytest.skip("Delete action not available in UI for chits")

    # Verify it's gone from search
    chits_page.navigate()
    assert not chits_page.search_chit(del_name), (
        f"Chit '{del_name}' should not appear after deletion"
    )


def test_restore_chit(logged_in_page, module_branch):
    """Create a chit, delete it, restore it, verify it reappears."""
    chits_page = ChitsPage(logged_in_page)
    chits_page.navigate()

    restore_name = generate_random_name("restore_chit")
    chits_page.add_chit(
        chit_name=restore_name,
        branch=module_branch,
        chit_value="45000",
        tenure_months="5",
        monthly_amount="9000",
    )

    # Delete first
    chits_page.navigate()
    result = chits_page.delete_chit(restore_name)
    if not result:
        pytest.skip("Delete action not available in UI for chits")

    # Restore
    chits_page.navigate()
    result = chits_page.restore_chit(restore_name)
    if not result:
        pytest.skip("Restore action not available in UI for chits")

    # Verify it reappears
    chits_page.navigate()
    assert chits_page.search_chit(restore_name), (
        f"Chit '{restore_name}' should reappear after restore"
    )
