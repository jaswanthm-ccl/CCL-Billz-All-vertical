"""Restaurant Outdoor Billing & Customer Settlement End-to-End Regression Flow.

Path:
1. Setup isolated Customer and Menu Dish (₹250.00).
2. Create Outdoor Booking: 4 units @ ₹250 = ₹1,000.00 total with ₹200.00 cash advance (Pending balance ₹800.00).
3. Verify Customer Outstanding shows pending receivable of exactly ₹800.00.
4. Record Settlement Payment of remaining ₹800.00 in Outdoor Billing.
5. Close Bill to complete outdoor catering lifecycle.
6. Verify Customer Outstanding is fully cleared (₹0.00 / Nil).
7. Verify Cash Inflows reflect in Day Book.
"""

from decimal import Decimal
import pytest

from pages.Verticals.Restaurant.accounting.customer_outstanding_page import (
    CustomerOutstandingPage,
)
from pages.Verticals.Restaurant.accounting.day_book_page import DayBookPage
from pages.Verticals.Restaurant.main_menu.customers_page import CustomersPage
from pages.Verticals.Restaurant.main_menu.outdoor_billing_page import OutdoorBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name, generate_random_phone


pytestmark = [pytest.mark.restaurant, pytest.mark.regression]


def test_outdoor_billing_and_customer_settlement_flow(
    res_logged_in_page,
    res_branch,
    res_category,
    res_department,
    res_unit_type,
    res_regression_cleanup,
):
    """Complete 360° Outdoor Catering, Advance Collection, Debt Reconciliation & Bill Closure."""
    page = res_logged_in_page
    cleanup = res_regression_cleanup

    # Page Objects
    customers_page = CustomersPage(page)
    products_page = ProductsPage(page)
    outdoor_page = OutdoorBillingPage(page)
    customer_outstanding_page = CustomerOutstandingPage(page)
    day_book_page = DayBookPage(page)

    customer_name = generate_random_name("regr_catering_cust")
    dish_name = generate_random_name("regr_catering_dish")
    unit_price = Decimal("250.00")
    order_qty = Decimal("4")
    booking_total = unit_price * order_qty  # ₹1,000.00
    advance_amount = Decimal("200.00")
    expected_pending = booking_total - advance_amount  # ₹800.00

    # ── Step 1: Create Isolated Customer & Catering Dish ─────────────────────
    customers_page.navigate()
    assert customers_page.add_customer(
        name=customer_name,
        phone=generate_random_phone(),
    ), f"Failed to create customer {customer_name}"
    cleanup["customers"].append(customer_name)

    products_page.navigate()
    dish_code = products_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price=str(unit_price),
        product_type="Finished good",
    )
    assert dish_code, f"Failed to create catering dish {dish_name}"
    cleanup["products"].append(dish_name)

    # ── Step 2: Create Outdoor Booking with Partial Cash Advance ──────────────
    outdoor_page.navigate()
    booking_data = outdoor_page.create_booking(
        branch_name=res_branch,
        customer_name=customer_name,
        dish_name=dish_name,
        dish_code=dish_code,
        quantity=str(int(order_qty)),
        unit_price=str(unit_price),
        advance_amount=str(advance_amount),
        advance_payment_mode="cash",
        advance_notes="Outdoor banquet advance token",
        notes="Corporate banquet catering order",
    )
    booking_id = str(booking_data.get("id") or "")
    booking_ref = str(booking_data.get("booking_ref") or booking_id)
    assert booking_id and booking_ref, f"Booking response lacked identity: {booking_data}"

    # ── Step 3: Verify Customer Outstanding Shows Pending Receivable ──────────
    customer_outstanding_page.navigate()
    customer_outstanding_page.select_branch(res_branch)
    open_data = customer_outstanding_page.search(customer_name)
    open_party = customer_outstanding_page.find_party(open_data, customer_name)
    assert open_party is not None, (
        f"Customer {customer_name} was absent from Customer Outstanding report"
    )
    assert customer_outstanding_page.amount(open_party["outstanding_amount"]) == expected_pending, (
        f"Expected outstanding ₹{expected_pending}, got {open_party['outstanding_amount']}"
    )
    assert open_party["balance_type"] == "Receivable", (
        f"Expected Receivable balance type, got {open_party.get('balance_type')}"
    )

    # Verify customer ledger statement drawer
    ledger = customer_outstanding_page.open_ledger(customer_name)
    assert ledger.get("rows") is not None, f"Ledger drawer lacked rows: {ledger}"
    assert customer_outstanding_page.amount(ledger.get("current_balance", 0)) == expected_pending, (
        f"Ledger balance mismatch: expected {expected_pending}, got {ledger.get('current_balance')}"
    )

    # ── Step 4: Settle Remaining Balance in Outdoor Booking ───────────────────
    outdoor_page.navigate()
    assert outdoor_page.search_booking(customer_name), (
        f"Outdoor booking for customer {customer_name} not found in search"
    )
    view_details = outdoor_page.view_booking(customer_name)
    assert customer_name in view_details["content"], "View dialog did not display customer details"

    settlement_payment = outdoor_page.record_settlement_payment(
        amount=str(expected_pending),
        notes="Final banquet balance settlement",
    )
    assert settlement_payment, "Record settlement payment returned no booking data"
    assert customer_outstanding_page.amount(
        settlement_payment.get("received_amount", 0)
    ) == booking_total, settlement_payment
    assert customer_outstanding_page.amount(
        settlement_payment.get("balance_amount", 0)
    ) == Decimal("0.00"), settlement_payment

    # ── Step 5: Close Bill to Finalize Outdoor Catering ───────────────────────
    assert outdoor_page.close_bill(), "Failed to close outdoor catering bill"
    outdoor_page.close_modal()

    # ── Step 6: Verify Customer Outstanding Drops to Exactly Zero ────────────
    customer_outstanding_page.navigate()
    customer_outstanding_page.select_branch(res_branch)
    cleared_data = customer_outstanding_page.search(customer_name)
    cleared_party = customer_outstanding_page.find_party(cleared_data, customer_name)
    if cleared_party is not None:
        assert customer_outstanding_page.amount(cleared_party["outstanding_amount"]) == Decimal("0.00"), (
            f"Customer outstanding did not drop to 0: {cleared_party['outstanding_amount']}"
        )
        assert cleared_party["balance_type"] in ("Nil", "None", "-"), (
            f"Expected Nil balance type, got {cleared_party.get('balance_type')}"
        )
        cleared_ledger = customer_outstanding_page.open_ledger(customer_name)
        assert customer_outstanding_page.amount(
            cleared_ledger.get("current_balance", 0)
        ) == Decimal("0.00"), cleared_ledger
    else:
        assert cleared_data.get("items", []) == [], (
            f"Unexpected outstanding records for cleared customer {customer_name}"
        )

    # ── Step 7: Verify Actual Cash Received in Day Book ──────────────────────
    day_book_page.navigate()
    day_book_entry = day_book_page.get_entry_by_description(booking_ref)
    day_book_amount = Decimal(
        day_book_entry["amount"].replace("₹", "").replace(",", "").strip()
    )
    assert day_book_entry["category"].strip().lower() == "outdoor billing", (
        day_book_entry
    )
    assert day_book_entry["type"].strip().lower() == "income", day_book_entry
    assert day_book_entry["payment"].strip().lower() == "cash", day_book_entry
    assert day_book_amount == booking_total, (
        f"Outdoor Day Book income should be ₹{booking_total:.2f}, "
        f"got ₹{day_book_amount:.2f}: {day_book_entry}"
    )
