"""Restaurant POS Billing, Payment Collection & Void Lifecycle End-to-End Regression Flow.

Path:
1. Setup eligible Waiter (with calculate_incentive role) and Finished Good dish (₹200, 5% incentive).
2. Order 1 (Happy Path Sale):
   - POS Dine-In -> Assign Waiter -> Enter Dish -> Settle & Bill.
   - Collect Cash payment.
   - Verify Order is SETTLED and PAID in Orders list.
   - Enterprise security rule: Verify Paid bill cannot be voided (Void button disabled).
   - Verify Cash inflow in Day Book.
   - Verify Waiter incentive reflects in Daily Incentive Report (1 bill, ₹200 sales, ₹10 incentive).
3. Order 2 (Void & Cancellation Lifecycle):
   - POS Dine-In -> Assign Waiter -> Enter Dish -> Settle & Bill (Payment remains PENDING).
   - Navigate to Orders list and verify PENDING status.
   - Void the bill with audit reason ("Customer cancelled dining order").
   - Verify Order status transitions to VOIDED.
   - Audit exclusion: Verify voided bill does NOT increment waiter bills, sales, or incentives.
"""

from datetime import date
from decimal import Decimal
import random
from urllib.parse import parse_qs, urlparse

import pytest

from pages.Verticals.Restaurant.accounting.daily_incentive_report_page import (
    DailyIncentiveReportPage,
)
from pages.Verticals.Restaurant.accounting.day_book_page import DayBookPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.master_menu.roles_page import RolesPage
from pages.Verticals.Restaurant.master_menu.users_page import UsersPage
from utils.random_data import (
    generate_random_email,
    generate_random_name,
    generate_random_password,
)


pytestmark = [pytest.mark.restaurant, pytest.mark.regression]


def test_pos_billing_payment_and_void_lifecycle_flow(
    res_logged_in_page,
    res_category,
    res_department,
    res_unit_type,
    res_regression_cleanup,
):
    """Complete End-to-End POS Billing, Cash Collection, Void Invariant & Incentive Audit."""
    page = res_logged_in_page
    cleanup = res_regression_cleanup

    # Page Objects
    billing = POSBillingPage(page)
    roles_page = RolesPage(page)
    users_page = UsersPage(page)
    products_page = ProductsPage(page)
    day_book = DayBookPage(page)
    daily_incentive = DailyIncentiveReportPage(page)

    today_str = date.today().isoformat()
    dish_price = "200"
    incentive_pct = "5"
    expected_dish_price = Decimal("200.00")
    expected_incentive_amt = Decimal("10.00")  # 5% of 200

    # ── Step 1: Discover Active POS Branch & Setup Isolated Waiter ─────────────
    with page.expect_response(
        lambda response: (
            response.request.method == "GET"
            and "/lists/waiters" in response.url
            and "branch_id=" in response.url
        ),
        timeout=15000,
    ) as waiter_resp_info:
        billing.navigate()
    waiter_query = parse_qs(urlparse(waiter_resp_info.value.url).query)
    pos_branch_id = int(waiter_query["branch_id"][0])

    # Create Role with 'calculate_incentive' permission
    role_name = generate_random_name("regr_waiter_role")
    roles_page.navigate()
    roles_page.add_role_with_permissions(role_name, ["calculate_incentive"])
    cleanup["roles"].append(role_name)

    # Create Waiter User assigned to the active POS branch
    waiter_name = generate_random_name("regr_waiter")
    users_page.navigate()
    users_page.add_user(
        name=waiter_name,
        email=generate_random_email("regr_waiter"),
        password=generate_random_password(),
        branch_name=None,
        role_name=role_name,
        branch_id=pos_branch_id,
        can_login=False,
        user_code=str(random.randint(100000, 999999)),
    )
    cleanup["users"].append(waiter_name)

    # Create Finished Good Dish with 5% Incentive
    dish_name = generate_random_name("regr_dish")
    products_page.navigate()
    dish_code = products_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price=dish_price,
        product_type="Finished good",
        incentive_percentage=incentive_pct,
    )
    assert dish_code, f"Failed to create menu dish {dish_name}"
    cleanup["products"].append(dish_name)

    # ── Step 2: Order 1 (Happy Path Settle & Cash Collection) ─────────────────
    billing.navigate()
    billing.select_bill_tab("Bill 1")
    billing.select_order_type("Dine In")
    billing.select_waiter(waiter_name)
    billing.enter_dish_by_code(dish_code, dish_name=dish_name)

    sale_1 = billing.settle_and_bill()
    sale_1_id = str(sale_1.get("id"))
    bill_ref_1 = str(sale_1.get("invoice_id") or sale_1.get("invoice_no") or sale_1_id)
    assert sale_1_id and bill_ref_1, f"Sale 1 response lacked identity: {sale_1}"

    bill_1_identifiers = [
        str(val)
        for val in (
            sale_1.get("order_token"),
            sale_1.get("invoice_id"),
            sale_1.get("invoice_no"),
            sale_1_id,
        )
        if val
    ]

    # Collect cash payment
    assert billing.collect_cash_payment(bill_reference=bill_1_identifiers), (
        f"Cash collection failed for Order 1 {bill_ref_1}"
    )

    # ── Step 3: Verify Paid Bill Invariants in Orders List ────────────────────
    billing.navigate_to_orders_list()
    settled_row = billing.find_order_row(bill_ref_1, sale_id=sale_1_id)
    row_1_text = settled_row.inner_text().upper()
    assert "SETTLED" in row_1_text and "PAID" in row_1_text, (
        f"Order 1 was not marked SETTLED/PAID: {row_1_text}"
    )

    # Invariant: A paid restaurant bill must NEVER allow voiding
    void_btn_1 = settled_row.get_by_title("Void Bill", exact=True)
    assert void_btn_1.is_visible(), "Void button not rendered for Order 1"
    assert void_btn_1.get_attribute("aria-disabled") == "true", (
        "Enterprise security breach: Paid restaurant bill has Void button enabled"
    )

    # ── Step 4: Verify Revenue Inflow in Day Book ─────────────────────────────
    day_book.navigate()
    day_book_entry = day_book.get_entry_by_description(bill_ref_1)
    day_book_amount = Decimal(
        day_book_entry["amount"].replace("₹", "").replace(",", "").strip()
    )
    assert day_book_entry["type"].strip().lower() == "income", day_book_entry
    assert day_book_entry["payment"].strip().lower() == "cash", day_book_entry
    assert day_book_amount == expected_dish_price, (
        f"Day Book cash income should be ₹{expected_dish_price:.2f}, "
        f"got ₹{day_book_amount:.2f}: {day_book_entry}"
    )

    # ── Step 5: Verify Waiter Incentive for Order 1 ───────────────────────────
    daily_incentive.navigate()
    inc_data_1 = daily_incentive.filter_report(
        from_date=today_str,
        to_date=today_str,
        staff_name=waiter_name,
    )
    assert len(inc_data_1["rows"]) == 1, f"Expected 1 incentive row, got: {inc_data_1}"
    inc_row_1 = inc_data_1["rows"][0]
    assert inc_row_1["bills"] == 1
    assert daily_incentive.amount(inc_row_1["sales_amount"]) == expected_dish_price
    assert daily_incentive.amount(inc_row_1["incentive_amount"]) == expected_incentive_amt
    assert daily_incentive.get_table_rows(), "Incentive UI did not render table row"

    # ── Step 6: Order 2 (Create Unpaid Dine-In Bill) ──────────────────────────
    billing.navigate()
    billing.select_bill_tab("Bill 1")
    billing.select_order_type("Dine In")
    billing.select_waiter(waiter_name)
    billing.enter_dish_by_code(dish_code, dish_name=dish_name)

    sale_2 = billing.settle_and_bill()
    sale_2_id = str(sale_2.get("id"))
    bill_ref_2 = str(sale_2.get("invoice_id") or sale_2.get("invoice_no") or sale_2_id)
    assert sale_2_id and bill_ref_2, f"Sale 2 response lacked identity: {sale_2}"

    # ── Step 7: Void Order 2 in Orders List ───────────────────────────────────
    billing.navigate_to_orders_list()
    pending_row = billing.find_order_row(bill_ref_2, sale_id=sale_2_id)
    pending_text = pending_row.inner_text().upper()
    assert "PENDING" in pending_text, (
        f"Order 2 should be in PENDING state before payment: {pending_text}"
    )

    # Void the pending bill with audit reason
    void_payload = billing.void_bill(
        bill_reference=bill_ref_2,
        reason="Customer cancelled dining order",
        sale_id=sale_2_id,
    )
    assert void_payload is not None, "Void API returned no payload"

    # Verify order is marked VOIDED
    voided_row = billing.find_order_row(bill_ref_2, sale_id=sale_2_id)
    assert "VOIDED" in voided_row.inner_text().upper(), (
        f"Order 2 row was not marked VOIDED: {voided_row.inner_text()}"
    )

    # ── Step 8: Verify Void Exclusion Invariant in Daily Incentive Report ─────
    # The voided bill must NOT add to waiter sales, bills, or incentives!
    daily_incentive.navigate()
    inc_data_post_void = daily_incentive.filter_report(
        from_date=today_str,
        to_date=today_str,
        staff_name=waiter_name,
    )
    assert len(inc_data_post_void["rows"]) == 1, (
        f"Voided bill caused duplicate rows in incentive report: {inc_data_post_void}"
    )
    post_row = inc_data_post_void["rows"][0]
    assert post_row["bills"] == 1, (
        f"Incentive bill count increased after void! Expected 1, got {post_row['bills']}"
    )
    assert daily_incentive.amount(post_row["sales_amount"]) == expected_dish_price, (
        f"Sales amount increased after void! Expected ₹200.00, got {post_row['sales_amount']}"
    )
    assert daily_incentive.amount(post_row["incentive_amount"]) == expected_incentive_amt, (
        f"Incentive amount increased after void! Expected ₹10.00, got {post_row['incentive_amount']}"
    )
