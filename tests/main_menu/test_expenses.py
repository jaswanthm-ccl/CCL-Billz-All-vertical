import pytest
from pages.main_menu.expenses_page import ExpensesPage
from pages.master_menu.expense_categories_page import ExpenseCategoriesPage
from pages.master_menu.branches_page import BranchesPage
from utils.random_data import generate_random_name


# ──────────────────────────────────────────────────────────────────────────────
# Module-scoped fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def module_expense_category(module_page):
    """Create an expense category for all expense tests."""
    cat_page = ExpenseCategoriesPage(module_page)
    cat_page.navigate()
    cat_name = generate_random_name("exp_cat")
    cat_page.add_expense_category(cat_name, description="expense test category")
    yield cat_name
    try:
        cat_page.navigate()
        if cat_page.search_expense_category(cat_name):
            cat_page.delete_expense_category(cat_name)
    except Exception as e:
        print(f"Teardown: Failed to delete expense category {cat_name}: {e}")


@pytest.fixture(scope="module")
def module_branch(module_page):
    """Create a branch for expense tests."""
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


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_expenses_page_loads(logged_in_page):
    """Verify the expenses page loads correctly."""
    expenses_page = ExpensesPage(logged_in_page)
    expenses_page.navigate()
    assert expenses_page.is_expenses_visible(), "Expenses page did not load"


def test_add_expense_bank(
    logged_in_page, module_expense_category, module_branch, funded_bank_account
):
    """Create an expense paid by Bank Account and verify it appears.

    The funded_bank_account fixture (session-scoped) creates a bank account
    funded via a ₹500 sale. We use it here to pay for our expense.
    """
    expenses_page = ExpensesPage(logged_in_page)
    expenses_page.navigate()

    expenses_page.add_expense(
        category=module_expense_category,
        branch=module_branch,
        amount="200",
        payment_type="Bank Account",
        bank_account=funded_bank_account["bank_name"],
        description="Bank expense auto test",
    )

    # Verify: filter by branch to isolate our expense
    expenses_page.navigate()
    expenses_page.filter_by_branch(module_branch)

    row_data = expenses_page.get_first_row_data()
    assert module_expense_category in row_data["category"], (
        f"Expected category '{module_expense_category}', got '{row_data['category']}'"
    )
    assert "200" in row_data["amount"], (
        f"Expected amount '200', got '{row_data['amount']}'"
    )


def test_add_expense_cash(
    logged_in_page, module_expense_category, funded_bank_account
):
    """Create an expense paid by Cash from the funded branch.

    The funded_bank_account fixture sells a product via Cash into its branch,
    so that branch has cash balance for this expense.
    """
    expenses_page = ExpensesPage(logged_in_page)
    expenses_page.navigate()

    expenses_page.add_expense(
        category=module_expense_category,
        branch=funded_bank_account["branch_name"],
        amount="50",
        payment_type="Cash",
        description="Cash expense auto test",
    )

    # Verify: search for our expense
    expenses_page.navigate()
    assert expenses_page.search_expense("Cash expense auto test"), (
        "Cash expense not found in search"
    )


def test_filter_by_branch(
    logged_in_page, module_expense_category, module_branch
):
    """Filter expenses by branch and verify results."""
    expenses_page = ExpensesPage(logged_in_page)
    expenses_page.navigate()

    expenses_page.filter_by_branch(module_branch)

    # After filtering, search for our specific expense to be sure
    assert expenses_page.search_expense("Bank expense auto test"), (
        "Bank expense not found after filtering by branch"
    )


def test_filter_by_category(
    logged_in_page, module_expense_category, module_branch
):
    """Filter expenses by category and verify results."""
    expenses_page = ExpensesPage(logged_in_page)
    expenses_page.navigate()

    expenses_page.filter_by_category(module_expense_category)

    row_data = expenses_page.get_first_row_data()
    assert module_expense_category in row_data["category"], (
        f"Expected category '{module_expense_category}', got '{row_data['category']}'"
    )


def test_search_expense(logged_in_page):
    """Search for an expense by description."""
    expenses_page = ExpensesPage(logged_in_page)
    expenses_page.navigate()

    assert expenses_page.search_expense("Bank expense auto test"), (
        "Expense not found by description search"
    )
