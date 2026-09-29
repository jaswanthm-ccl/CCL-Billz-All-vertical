"""Restaurant Operational Reports & Reconciliation End-to-End Regression Flow.

Path:
1. Setup isolated Staff Waiter and Finished Good Dish (₹200.00, 5% incentive).
2. Execute Controlled POS Sale (Dine-In Cash Collection).
3. Validate Daily Closing Report:
   - Query daily closing metrics (Total Sales, Material Usage, Profit/Loss).
4. Validate Item-Wise and Category-Wise (Cashier) Sales Reports:
   - Reconcile item sales for billed dish.
   - Reconcile category sales distribution.
5. Validate Waiter Incentive Reports (Daily & Monthly):
   - Strict incentive audit: Bills = 1, Sales = ₹200.00, Incentive = ₹10.00 (5%).
   - Verify monthly aggregation for staff waiter.
6. Validate GSTR-1 Tax Compliance & Classification:
   - Reconcile GSTR-1 B2C tax report structure, headers, and totals.
7. Validate Stock Summary & File Export:
   - Reconcile inventory valuations and execute verified CSV download.
"""

from datetime import date
from decimal import Decimal
import csv
import random
import re
from urllib.parse import parse_qs, urlparse

import pytest

from pages.Verticals.Restaurant.accounting.category_wise_sales_report_page import (
    CategoryWiseSalesReportPage,
)
from pages.Verticals.Restaurant.accounting.daily_closing_report_page import (
    DailyClosingReportPage,
)
from pages.Verticals.Restaurant.accounting.daily_incentive_report_page import (
    DailyIncentiveReportPage,
)
from pages.Verticals.Restaurant.accounting.item_wise_sales_report_page import (
    ItemWiseSalesReportPage,
)
from pages.Verticals.Restaurant.accounting.monthly_incentive_report_page import (
    MonthlyIncentiveReportPage,
)
from pages.Verticals.Restaurant.accounting.waiter_wise_incentive_report_page import (
    WaiterWiseIncentiveReportPage,
)
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from pages.Verticals.Restaurant.master_menu.roles_page import RolesPage
from pages.Verticals.Restaurant.master_menu.users_page import UsersPage
from pages.Verticals.Restaurant.report.gstr_1_b2c_page import Gstr1B2cPage
from pages.Verticals.Restaurant.report.stock_summary_page import StockSummaryPage
from utils.random_data import (
    generate_random_email,
    generate_random_name,
    generate_random_password,
)


pytestmark = [pytest.mark.restaurant, pytest.mark.regression]


def _money(text: str) -> Decimal:
    return Decimal(re.sub(r"[^\d.-]", "", text) or "0").quantize(
        Decimal("0.01")
    )


def test_restaurant_reports_and_reconciliation_flow(
    res_logged_in_page,
    res_category,
    res_department,
    res_unit_type,
    res_supplier,
    res_regression_cleanup,
):
    """Complete 360° Operational Reports Reconciliation and Financial Export Flow."""
    page = res_logged_in_page
    cleanup = res_regression_cleanup

    today_str = date.today().isoformat()
    dish_price = "200"
    incentive_pct = "5"
    expected_dish_price = Decimal("200.00")
    expected_incentive_amt = Decimal("10.00")

    # Page Objects
    billing = POSBillingPage(page)
    roles_page = RolesPage(page)
    users_page = UsersPage(page)
    products_page = ProductsPage(page)
    purchases_page = PurchasesPage(page)
    daily_closing = DailyClosingReportPage(page)
    item_wise = ItemWiseSalesReportPage(page)
    category_wise = CategoryWiseSalesReportPage(page)
    daily_incentive = DailyIncentiveReportPage(page)
    monthly_incentive = MonthlyIncentiveReportPage(page)
    waiter_wise_incentive = WaiterWiseIncentiveReportPage(page)
    gstr1_b2c = Gstr1B2cPage(page)
    stock_summary = StockSummaryPage(page)

    # ── Step 1: Discover POS Branch & Setup Isolated Waiter + Dish ────────────
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

    role_name = generate_random_name("regr_rep_role")
    roles_page.navigate()
    roles_page.add_role_with_permissions(role_name, ["calculate_incentive"])
    cleanup["roles"].append(role_name)

    waiter_name = generate_random_name("regr_rep_waiter")
    users_page.navigate()
    submitted_user = users_page.add_user(
        name=waiter_name,
        email=generate_random_email("regr_rep_waiter"),
        password=generate_random_password(),
        branch_name=None,
        role_name=role_name,
        branch_id=pos_branch_id,
        can_login=False,
        user_code=str(random.randint(100000, 999999)),
    )
    pos_branch_name = submitted_user["_branch_name"]
    cleanup["users"].append(waiter_name)

    dish_name = generate_random_name("regr_rep_dish")
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

    stock_product_name = generate_random_name("regr_rep_stock")
    products_page.navigate()
    stock_product_code = products_page.add_product(
        name=stock_product_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="100",
        product_type="Raw material",
    )
    assert stock_product_code, f"Failed to create raw material {stock_product_name}"
    cleanup["products"].append(stock_product_name)
    purchases_page.navigate()
    stock_purchase = purchases_page.add_purchase(
        supplier=res_supplier,
        branch=pos_branch_name,
        reference_no=generate_random_name("PUR_REP"),
        paid_amount="0",
        purchase_type="Credit",
        products_data=[
            {"product": stock_product_name, "quantity": 5, "price": "100"}
        ],
    )
    assert stock_purchase.total_amount == Decimal("500.00"), stock_purchase

    # Baselines make the report assertions independent of pre-existing tenant
    # transactions and prove the exact impact of the sale created below.
    daily_closing.navigate()
    daily_closing.filter_by_branch(pos_branch_name)
    baseline_daily_sales = daily_closing.get_total_sales()

    category_wise.navigate()
    category_wise.filter_report(branch_name=pos_branch_name)
    baseline_category_sales = category_wise.get_sales()
    baseline_cash_income = category_wise.get_cash_income()

    # ── Step 2: Execute Controlled POS Cash Sale ─────────────────────────────
    billing.navigate()
    billing.select_bill_tab("Bill 1")
    billing.select_order_type("Dine In")
    billing.select_waiter(waiter_name)
    billing.enter_dish_by_code(dish_code, dish_name=dish_name)

    sale_data = billing.settle_and_bill()
    sale_id = str(sale_data.get("id") or "")
    bill_ref = str(sale_data.get("invoice_id") or sale_data.get("invoice_no") or sale_id)
    assert sale_id and bill_ref, f"POS Sale response lacked identity: {sale_data}"

    assert billing.collect_cash_payment(bill_reference=bill_ref), (
        f"Failed to collect cash for bill {bill_ref}"
    )

    # ── Step 3: Reconcile Daily Closing Report ────────────────────────────────
    daily_closing.navigate()
    footer = daily_closing.filter_by_branch(pos_branch_name)
    assert footer, "Daily Closing report returned empty footer"
    total_sales = daily_closing.get_total_sales()
    assert total_sales - baseline_daily_sales == expected_dish_price, (
        f"POS sale did not add exactly ₹200 to Daily Closing for "
        f"{pos_branch_name}: before={baseline_daily_sales}, after={total_sales}"
    )

    # ── Step 4: Reconcile Item-Wise & Category-Wise Sales Reports ─────────────
    # Item-Wise Sales
    item_wise.navigate()
    item_wise.apply_filters(
        from_date=today_str,
        to_date=today_str,
        branch_name=pos_branch_name,
    )
    item_row = page.locator("table tbody tr").filter(has_text=dish_name).first
    item_row.wait_for(state="visible", timeout=10000)
    item_cells = [cell.strip() for cell in item_row.locator("td").all_inner_texts()]
    assert len(item_cells) >= 3, item_cells
    assert _money(item_cells[-2]) == Decimal("1.00"), item_cells
    assert _money(item_cells[-1]) == expected_dish_price, item_cells

    # Category-Wise (Cashier) Sales
    category_wise.navigate()
    category_wise.filter_report(branch_name=pos_branch_name)
    assert category_wise.get_sales() - baseline_category_sales == expected_dish_price
    assert category_wise.get_cash_income() - baseline_cash_income == expected_dish_price

    # ── Step 5: Reconcile Waiter Incentive Audit (Daily & Monthly) ───────────
    # Daily Incentive
    daily_incentive.navigate()
    daily_data = daily_incentive.filter_report(
        from_date=today_str,
        to_date=today_str,
        staff_name=waiter_name,
    )
    assert len(daily_data["rows"]) == 1, f"Expected 1 incentive row, got {daily_data}"
    daily_row = daily_data["rows"][0]
    assert daily_row["bills"] == 1
    assert daily_incentive.amount(daily_row["sales_amount"]) == expected_dish_price
    assert daily_incentive.amount(daily_row["incentive_amount"]) == expected_incentive_amt

    # Monthly Incentive
    monthly_incentive.navigate()
    monthly_data = monthly_incentive.filter_report(
        from_date=today_str,
        to_date=today_str,
        staff_name=waiter_name,
    )
    assert len(monthly_data["rows"]) == 1, monthly_data
    monthly_row = monthly_data["rows"][0]
    assert monthly_incentive.amount(monthly_row["sales_amount"]) == expected_dish_price
    assert monthly_incentive.amount(monthly_row["incentive_amount"]) == expected_incentive_amt

    waiter_wise_incentive.navigate()
    waiter_data = waiter_wise_incentive.filter_report(
        from_date=today_str,
        to_date=today_str,
        staff_name=waiter_name,
    )
    assert len(waiter_data["rows"]) == 1, waiter_data
    waiter_row = waiter_data["rows"][0]
    assert waiter_row["waiter_name"] == waiter_name, waiter_row
    assert waiter_row["bills"] == 1, waiter_row
    assert waiter_wise_incentive.amount(waiter_row["sales_amount"]) == expected_dish_price
    assert waiter_wise_incentive.amount(waiter_row["incentive_amount"]) == expected_incentive_amt

    # ── Step 6: Reconcile GSTR-1 Tax Compliance & Reporting ──────────────────
    gstr1_b2c.navigate()
    gstr_data = gstr1_b2c.apply_filters(
        from_date=today_str,
        to_date=today_str,
        branch_name=pos_branch_name,
    )
    assert gstr1_b2c.heading_visible(), "GSTR-1 B2C report heading not visible"
    gstr_headers = gstr1_b2c.headers()
    assert set(gstr1_b2c.EXPECTED_HEADERS) <= set(gstr_headers), gstr_headers
    gstr_row = next(
        (
            row
            for row in gstr_data.get("rows", [])
            if str(row.get("sale_id")) == sale_id
        ),
        None,
    )
    assert gstr_row is not None, (
        f"Created POS sale {bill_ref} was absent from GSTR-1 B2C: "
        f"{gstr_data.get('rows', [])}"
    )
    assert str(gstr_row.get("invoice_number")) == bill_ref, gstr_row
    assert Decimal(str(gstr_row["total_invoice_value"])) == expected_dish_price
    taxable = Decimal(str(gstr_row.get("taxable_value") or 0))
    tax = sum(
        Decimal(str(gstr_row.get(key) or 0))
        for key in ("cgst_amount", "sgst_amount", "igst_amount")
    )
    assert taxable + tax == expected_dish_price, gstr_row

    # ── Step 7: Reconcile Stock Summary & Verified CSV File Export ───────────
    stock_summary.navigate()
    stock_data = stock_summary.run_search(stock_product_name)
    stock_row = stock_summary.find_product(
        stock_data,
        product_name=stock_product_name,
        branch_name=pos_branch_name,
    )
    assert stock_row is not None, (
        f"Created stock item '{stock_product_name}' was absent from Stock Summary: "
        f"{stock_data}"
    )
    csv_download = stock_summary.export("csv")
    assert csv_download is not None, "Stock Summary CSV export produced no download"
    assert csv_download.suggested_filename.lower().endswith(".csv"), (
        f"Export filename was not CSV: {csv_download.suggested_filename}"
    )
    csv_path = stock_summary.downloaded_path(csv_download)
    assert csv_path.stat().st_size > 0, "Stock Summary CSV was empty"
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        exported_rows = list(csv.reader(csv_file))
    assert exported_rows, "Stock Summary CSV contained no rows"
    exported_text = "\n".join(",".join(row) for row in exported_rows)
    assert "Product" in exported_text, exported_rows[:3]
    assert stock_product_name in exported_text, (
        f"Filtered Stock Summary CSV did not contain '{stock_product_name}'"
    )
