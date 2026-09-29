"""Restaurant Expenses Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.expenses_page import ExpensesPage


@pytest.mark.restaurant
def test_restaurant_expenses_lifecycle(res_logged_in_page):
    """Test adding an expense in restaurant tenant."""
    page = res_logged_in_page
    exp_page = ExpensesPage(page)
    exp_page.navigate()

    note = generate_random_name("exp_note")
    assert exp_page.add_expense(expense_group="Direct", amount="250", notes=note), "Failed to add expense"

