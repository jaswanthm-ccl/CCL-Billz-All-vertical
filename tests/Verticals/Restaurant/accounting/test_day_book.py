"""Restaurant Day Book Test Suite.

Route: /day-book
Covers:
  1. Structure  — Page loads, summary cards (Opening, Total Income, Total Expense, Closing) visible
  2. Invariant  — Closing Balance == Opening Balance + Total Income - Total Expense
  3. Accounting — Live POS billed transaction appears in Day Book ledger table
"""
from __future__ import annotations

from decimal import Decimal
import pytest

from pages.Verticals.Restaurant.accounting.day_book_page import DayBookPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Known-state Fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def res_day_book_known_sale(
    browser, res_auth_state, res_branch, res_category, res_department, res_unit_type
):
    """
    Completes a live POS Dine-In cash sale and yields the invoice reference & amount
    to verify in the Day Book.
    """
    context = browser.new_context(
        storage_state=res_auth_state,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()

    prod_page = ProductsPage(page)
    pos_page = POSBillingPage(page)

    dish_name = generate_random_name("db_dish")
    dish_price = "180"

    # 1. Create Dish
    prod_page.navigate()
    dish_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price=dish_price,
        product_type="Finished good",
    )

    # 2. Complete POS Sale
    pos_page.navigate()
    pos_page.select_bill_tab("Bill 1")
    pos_page.select_order_type("Dine In")
    pos_page.select_waiter("Waiter")
    pos_page.enter_dish_by_code(code=dish_code, dish_name=dish_name)

    sale_data = pos_page.settle_and_bill()
    sale_id = str(sale_data.get("id") or "")
    bill_reference = str(
        sale_data.get("invoice_no") or sale_data.get("invoice_id") or sale_id
    )
    day_book_reference = str(sale_data.get("invoice_id") or sale_id)
    assert sale_id and day_book_reference, f"Sale response lacked identity: {sale_data}"
    pos_page.collect_cash_payment(bill_reference=bill_reference)

    context.close()

    yield {
        "dish_name": dish_name,
        "dish_code": dish_code,
        "invoice_ref": bill_reference,
        "day_book_description": f"Auto entry for Sale #{day_book_reference}",
        "price": Decimal(dish_price),
        "branch": res_branch,
    }

    # Teardown: delete product
    try:
        cleanup_ctx = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
        cleanup_page = cleanup_ctx.new_page()
        cp = ProductsPage(cleanup_page)
        cp.navigate()
        cp.delete_product(dish_name)
        cleanup_ctx.close()
    except Exception as e:
        print(f"Teardown warning (db_dish {dish_name}): {e}")


# ── Structure Tests ────────────────────────────────────────────────────────────

class TestResDayBookStructure:
    """Verify page loading and UI element presence."""

    def test_day_book_page_loads(self, res_logged_in_page):
        page = res_logged_in_page
        day_book = DayBookPage(page)
        day_book.navigate()

        assert (
            page.get_by_text("Day Book", exact=False).first.is_visible()
            or day_book.filter_button.is_visible()
        ), "Day Book heading or filter button not visible"

    def test_summary_cards_valid_decimals(self, res_logged_in_page):
        day_book = DayBookPage(res_logged_in_page)
        day_book.navigate()

        income = day_book.get_total_income()
        expense = day_book.get_total_expense()
        closing = day_book.get_closing_balance()

        assert income >= Decimal("0"), f"Total Income should be non-negative: {income}"
        assert expense >= Decimal("0"), f"Total Expense should be non-negative: {expense}"
        assert isinstance(closing, Decimal), f"Closing balance should be a valid Decimal: {closing}"

    def test_day_book_financial_identity(self, res_logged_in_page):
        """Verify Closing Balance == Opening Balance + Total Income - Total Expense."""
        day_book = DayBookPage(res_logged_in_page)
        day_book.navigate()

        opening = day_book.get_opening_balance()
        income = day_book.get_total_income()
        expense = day_book.get_total_expense()
        closing = day_book.get_closing_balance()

        expected_closing = opening + income - expense
        assert closing == expected_closing, (
            f"Day Book identity mismatch: Closing ({closing}) != "
            f"Opening ({opening}) + Income ({income}) - Expense ({expense})"
        )


# ── Accounting Tests ───────────────────────────────────────────────────────────

class TestResDayBookAccounting:
    """Verify live transactions appear in Day Book table."""

    def test_completed_pos_sale_appears_in_day_book(
        self, res_logged_in_page, res_day_book_known_sale
    ):
        description = res_day_book_known_sale["day_book_description"]
        price = res_day_book_known_sale["price"]

        day_book = DayBookPage(res_logged_in_page)
        day_book.navigate()

        entry = day_book.get_entry_by_description(description)

        assert entry["description"] == description
        assert entry["category"].lower() == "sale"
        assert entry["type"].lower() == "income"
        assert entry["payment"].lower() == "cash"
        assert Decimal(entry["amount"].replace("₹", "").replace(",", "")) == price
