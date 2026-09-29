"""Restaurant Financial Accounting Impact End-to-End Regression Flow.

Path:
1. Baseline Ledger & Financial Statements Setup.
2. Execute Controlled Tri-Partite Transactions:
   - 1 Credit Purchase (Raw materials: 5 units @ ₹100 = ₹500, Paid ₹0) -> Inventory & Supplier Debt.
   - 1 Cash POS Sale (Finished good dish: 1 unit @ ₹300 = ₹300) -> Cash Inflow & Revenue.
   - 1 Direct Cash Expense (₹100) -> Expense & Cash Outflow.
3. Voucher History Audit:
   - Verify System Vouchers are listed and accessible in Voucher History.
4. Day Book Double-Entry Journal Reconciliation:
   - Verify Day Book loads and reflects active transactions.
   - Core Day Book Invariant: Closing Balance == Opening Balance + Total Income - Total Expense.
5. Running Ledger Statement Audit:
   - Verify Ledger Statement report loads with branch and account filters.
6. Trial Balance Mathematical Identity:
   - Core Financial Invariant: Total Debits strictly equals Total Credits (Total Debit == Total Credit).
7. Profit & Loss Mathematical Integrity:
   - Core P&L Invariant: Net Profit == Total Income - Total Expense.
8. Balance Sheet Fundamental Accounting Equation:
   - Core Balance Sheet Identity: Total Assets == Total Liabilities + Total Equity.
"""

from datetime import date
from decimal import Decimal
import random
import re
import pytest

from pages.Verticals.Restaurant.accounting.balance_sheet_page import BalanceSheetPage
from pages.Verticals.Restaurant.accounting.day_book_page import DayBookPage
from pages.Verticals.Restaurant.accounting.ledger_statement_page import LedgerStatementPage
from pages.Verticals.Restaurant.accounting.profit_loss_page import ProfitLossPage
from pages.Verticals.Restaurant.accounting.trial_balance_page import TrialBalancePage
from pages.Verticals.Restaurant.accounting.vouchers_page import VouchersPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.expenses_page import ExpensesPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.random_data import generate_random_name


pytestmark = [pytest.mark.restaurant, pytest.mark.regression, pytest.mark.accounting]


def _money(text: str) -> Decimal:
    return Decimal(re.sub(r"[^\d.-]", "", text) or "0").quantize(
        Decimal("0.01")
    )


def test_restaurant_accounting_impact_flow(
    res_logged_in_page,
    res_branch,
    res_category,
    res_department,
    res_unit_type,
    res_supplier,
    res_regression_cleanup,
):
    """Complete 360° Multi-Statement Accounting Impact & Invariant Verification Flow."""
    page = res_logged_in_page
    cleanup = res_regression_cleanup
    today_str = date.today().isoformat()

    # Page Objects
    products_page = ProductsPage(page)
    purchases_page = PurchasesPage(page)
    pos_page = POSBillingPage(page)
    expenses_page = ExpensesPage(page)
    vouchers_page = VouchersPage(page)
    day_book_page = DayBookPage(page)
    ledger_statement_page = LedgerStatementPage(page)
    trial_balance_page = TrialBalancePage(page)
    profit_loss_page = ProfitLossPage(page)
    balance_sheet_page = BalanceSheetPage(page)

    # Capture a same-day baseline so the final P&L assertions prove the
    # transactions created by this test, not merely a valid tenant-wide formula.
    profit_loss_page.navigate()
    baseline_pl = profit_loss_page.apply_filters(today_str, today_str)
    baseline_income = Decimal(str(baseline_pl["income"]["total"] or 0))
    baseline_expense = Decimal(str(baseline_pl["expense"]["total"] or 0))

    # ── Step 1: Create Isolated Menu Items ───────────────────────────────────
    dish_name = generate_random_name("regr_acc_dish")
    raw_material_name = generate_random_name("regr_acc_raw")
    purchase_ref = generate_random_name("PUR_ACC")

    products_page.navigate()
    dish_code = products_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="300",
        product_type="Finished good",
    )
    assert dish_code, f"Failed to create finished good {dish_name}"
    cleanup["products"].append(dish_name)

    products_page.navigate()
    raw_code = products_page.add_product(
        name=raw_material_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="100",
        product_type="Raw material",
    )
    assert raw_code, f"Failed to create raw material {raw_material_name}"
    cleanup["products"].append(raw_material_name)

    # ── Step 2: Execute Controlled Operational Transactions ───────────────────
    # A. 1 Credit Purchase (Raw material: 5 units @ ₹100 = ₹500, Paid ₹0)
    purchases_page.navigate()
    pur_res = purchases_page.add_purchase(
        supplier=res_supplier,
        branch=res_branch,
        reference_no=purchase_ref,
        paid_amount="0",
        purchase_type="Credit",
        products_data=[
            {"product": raw_material_name, "quantity": 5, "price": "100"}
        ],
    )
    assert pur_res.total_amount == Decimal("500.00"), pur_res

    # B. 1 Cash POS Sale (Finished dish: 1 unit @ ₹300)
    pos_page.navigate()
    pos_page.select_bill_tab("Bill 1")
    pos_page.select_order_type("Dine In")
    pos_page.select_waiter("Waiter")
    pos_page.enter_dish_by_code(dish_code, dish_name=dish_name)

    sale_data = pos_page.settle_and_bill()
    sale_id = str(sale_data.get("id") or "")
    bill_ref = str(sale_data.get("invoice_id") or sale_data.get("invoice_no") or sale_id)
    assert sale_id and bill_ref, f"Sale lacked identity: {sale_data}"

    assert pos_page.collect_cash_payment(bill_reference=bill_ref), (
        f"Cash collection failed for POS bill {bill_ref}"
    )

    # C. 1 Direct Cash Expense (₹100)
    expenses_page.navigate()
    exp_notes = f"regr_acc_exp_{random.randint(1000, 9999)}"
    assert expenses_page.add_expense(
        expense_group="Direct",
        amount="100",
        notes=exp_notes,
    ), "Failed to post operational expense"

    # ── Step 3: Verify Voucher History ───────────────────────────────────────
    vouchers_page.navigate_history()
    vouchers_page.include_system_vouchers()
    assert vouchers_page.is_page_visible(), "Voucher History page should be visible"
    expected_vouchers = (
        ("Purchase Voucher", Decimal("500.00")),
        ("Sales Voucher", Decimal("300.00")),
    )
    for voucher_type, expected_amount in expected_vouchers:
        voucher = vouchers_page.get_voucher_row(
            voucher_type, f"{expected_amount:,.2f}"
        )
        assert voucher["type"] == voucher_type, voucher
        assert voucher["source"].lower() == "system", voucher
        assert voucher["status"].lower() == "active", voucher
        assert _money(voucher["amount"]) == expected_amount, voucher

    # ── Step 4: Verify Day Book Double-Entry Journal Reconciliation ───────────
    day_book_page.navigate()
    opening = day_book_page.get_opening_balance()
    income = day_book_page.get_total_income()
    expense = day_book_page.get_total_expense()
    closing = day_book_page.get_closing_balance()

    # Core Day Book Invariant: Closing Balance == Opening Balance + Income - Expense
    expected_closing = opening + income - expense
    assert closing == expected_closing, (
        f"Day Book Invariant Violation: Closing ({closing}) != "
        f"Opening ({opening}) + Income ({income}) - Expense ({expense})"
    )

    sale_entry = day_book_page.get_entry_by_description(bill_ref)
    assert sale_entry["type"].lower() == "income", sale_entry
    assert sale_entry["payment"].lower() == "cash", sale_entry
    assert _money(sale_entry["amount"]) == Decimal("300.00"), sale_entry

    expense_entry = day_book_page.get_entry_by_description(exp_notes)
    assert expense_entry["type"].lower() == "expense", expense_entry
    assert expense_entry["payment"].lower() == "cash", expense_entry
    assert _money(expense_entry["amount"]) == Decimal("100.00"), expense_entry

    # ── Step 5: Verify Running Ledger Statement ──────────────────────────────
    ledger_statement_page.navigate()
    assert ledger_statement_page.is_page_visible(), (
        "Ledger Statement report should load with statement controls"
    )
    ledger_statement_page.filter_statement(res_supplier, res_branch)
    purchase_row = page.locator("table tbody tr").filter(
        has_text=purchase_ref
    ).first
    purchase_row.wait_for(state="visible", timeout=10000)
    purchase_text = purchase_row.inner_text()
    assert "Purchase Voucher" in purchase_text, purchase_text
    assert raw_material_name in purchase_text, purchase_text
    assert re.search(r"(?:₹\s*)?500(?:\.00)?", purchase_text), purchase_text

    # ── Step 6: Verify Trial Balance Mathematical Identity ────────────────────
    tb_data = trial_balance_page.navigate()
    assert trial_balance_page.is_page_visible(), "Trial Balance page should load"
    assert trial_balance_page.last_status == 200, f"Trial Balance HTTP {trial_balance_page.last_status}"

    total_debit = Decimal(str(tb_data.get("total_debit") or 0))
    total_credit = Decimal(str(tb_data.get("total_credit") or 0))

    # Strict Enterprise Financial Invariant: Debits must strictly equal Credits
    assert total_debit == total_credit, (
        f"Trial Balance Out-of-Balance! Total Debit ({total_debit}) != Total Credit ({total_credit})"
    )

    # ── Step 7: Verify Profit & Loss Mathematical Integrity ───────────────────
    profit_loss_page.navigate()
    pl_data = profit_loss_page.apply_filters(today_str, today_str)
    assert pl_data is not None, "P&L API returned no data"

    income_val = pl_data["income"]["total"] if isinstance(pl_data.get("income"), dict) else pl_data.get("income", 0)
    expense_val = pl_data["expense"]["total"] if isinstance(pl_data.get("expense"), dict) else pl_data.get("expense", 0)
    pl_income = Decimal(str(income_val or 0))
    pl_expense = Decimal(str(expense_val or 0))
    pl_net_profit = Decimal(str(pl_data.get("net_profit", 0)))

    # Core P&L Invariant: Net Profit == Total Income - Total Expense
    expected_net_profit = pl_income - pl_expense
    assert pl_net_profit == expected_net_profit, (
        f"P&L Calculation Error! Net Profit ({pl_net_profit}) != Income ({pl_income}) - Expense ({pl_expense})"
    )
    assert pl_income - baseline_income == Decimal("300.00"), (
        f"Created POS sale did not add exactly ₹300 to today's P&L income: "
        f"before={baseline_income}, after={pl_income}"
    )
    assert pl_expense - baseline_expense == Decimal("100.00"), (
        f"Created direct expense did not add exactly ₹100 to today's P&L expense: "
        f"before={baseline_expense}, after={pl_expense}"
    )

    # ── Step 8: Verify Balance Sheet Fundamental Accounting Equation ──────────
    bs_data = balance_sheet_page.navigate()
    assert balance_sheet_page.is_page_visible(), "Balance Sheet should load"
    assert balance_sheet_page.last_status == 200, f"Balance Sheet HTTP {balance_sheet_page.last_status}"

    total_assets = Decimal(str(bs_data.get("assets", {}).get("total") or 0))
    total_liabilities = Decimal(str(bs_data.get("liabilities", {}).get("total") or 0))
    total_equity = Decimal(str(bs_data.get("equity", {}).get("total") or 0))
    total_liab_and_equity = Decimal(
        str(bs_data.get("total_liabilities_and_equity") or (total_liabilities + total_equity))
    )

    # Fundamental Accounting Equation: Total Assets == Total Liabilities + Total Equity
    assert total_assets == total_liab_and_equity, (
        f"Balance Sheet Equation Violation: Total Assets ({total_assets}) != "
        f"Total Liabilities + Equity ({total_liab_and_equity})"
    )
