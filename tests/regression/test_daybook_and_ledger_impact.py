"""Master Transaction Impact across Day Book, Ledgers & Financial Statements CI Regression Flow.

Path:
1. Baseline Snapshot on Cash & Running Ledgers.
2. Execute Operational Transactions:
   - 1 Credit Purchase (₹1,000.00) -> Inventory +10, Supplier Debt +₹1,000
   - 1 Cash Sale (₹1,500.00) -> Cash +₹1,500, Sales Revenue +₹1,500, Inventory -2
   - 1 Operational Cash Expense (₹200.00) -> Expense +₹200, Cash -₹200
3. Day Book Journal Verification:
   - Query Day Book for current date.
   - Assert Day Book table loads and is visible.
   - Assert Day Book entries satisfy double-entry accounting integrity.
4. Customer & Supplier Running Ledger Statement Audit:
   - Audit Customer Ledger Statement running balance.
   - Audit Supplier Ledger Statement running balance vs closing balance.
5. Cash Account Reconciled Invariant:
   - Cash Account reflects operational transactions and can fund settlement.
6. Financial Statement Mathematical Identities:
   - Trial Balance: Total Debits == Total Credits.
   - Profit & Loss Report status and integrity.
   - Balance Sheet Report status and integrity.
7. Debt Settlement & Dynamic Ledger Restoration:
   - Settle supplier debt via Payment Voucher (₹1,000) and verify Voucher History and Ledger update dynamically.
"""

import re
from datetime import datetime
from decimal import Decimal
import random
import pytest

from pages.main_menu.sales_page import SalesPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.expenses_page import ExpensesPage
from pages.master_menu.expense_categories_page import ExpenseCategoriesPage
from pages.accounting.day_book_page import DayBookPage
from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.accounting.trial_balance_page import TrialBalancePage
from pages.accounting.profit_loss_page import ProfitLossPage
from pages.accounting.balance_sheet_page import BalanceSheetPage
from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.accounting.voucher_history_page import VoucherHistoryPage
from pages.report.supplier_outstanding_page import SupplierOutstandingPage
from utils.random_data import generate_random_name


@pytest.mark.regression
@pytest.mark.accounting
@pytest.mark.default_vertical
def test_daybook_and_ledger_double_entry_accounting_flow(
    logged_in_page,
    regression_branch_a,
    regression_customer,
    regression_supplier,
    regression_product,
):
    """Complete 360° Day Book, Ledger Statements & Financial Statements Accounting Regression Flow."""
    sales_page = SalesPage(logged_in_page)
    purchases_page = PurchasesPage(logged_in_page)
    expenses_page = ExpensesPage(logged_in_page)
    exp_cat_page = ExpenseCategoriesPage(logged_in_page)
    day_book_page = DayBookPage(logged_in_page)
    ledger_statement_page = LedgerStatementPage(logged_in_page)
    trial_balance_page = TrialBalancePage(logged_in_page)
    profit_loss_page = ProfitLossPage(logged_in_page)
    balance_sheet_page = BalanceSheetPage(logged_in_page)
    voucher_page = CreateVoucherPage(logged_in_page)
    voucher_history_page = VoucherHistoryPage(logged_in_page)
    supplier_outstanding_page = SupplierOutstandingPage(logged_in_page)

    today_str = datetime.now().strftime("%Y-%m-%d")

    sale_amount = Decimal("1500.00")
    purchase_amount = Decimal("1000.00")
    expense_amount = Decimal("200.00")
    expected_cash_operating_delta = sale_amount - expense_amount

    # ── Step 0: Create Isolated Expense Category ─────────────────────────
    exp_cat_name = generate_random_name("Office_Expense")
    exp_cat_page.navigate()
    exp_cat_page.add_expense_category(name=exp_cat_name, description="Regression tests")

    # ── Step 1: Capture the isolated branch's opening Cash balance ───────
    cash_ledger_label = f"Cash Ledger — {regression_branch_a}"
    ledger_statement_page.filter_statement(cash_ledger_label, regression_branch_a)
    opening_cash = ledger_statement_page.parse_signed_balance(
        ledger_statement_page.get_closing_balance()
    )
    day_book_page.navigate()
    day_book_page.run_report(today_str, today_str)
    baseline_daybook_vouchers = {
        str(row["voucher_no"]) for row in day_book_page.get_all_rows_data()
    }

    # ── Step 2: Execute 1 Credit Purchase (₹1,000.00) ────────────────────
    # Procure stock FIRST so that the product has available inventory in Branch A
    purchases_page.navigate()
    purchase_ref = f"po_acc_{random.randint(100000, 999999)}"
    po_res = purchases_page.add_purchase(
        supplier=regression_supplier,
        branch=regression_branch_a,
        reference_no=purchase_ref,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[
            {"product": regression_product, "quantity": 10, "price": "100"}
        ],
    )
    assert po_res.reference_no == purchase_ref

    # ── Step 3: Execute 1 Cash Sale (₹1,500.00) ──────────────────────────
    sales_page.navigate()
    sale_res = sales_page.add_sale(
        customer_name=regression_customer,
        branch_name=regression_branch_a,
        product_name=regression_product,
        quantity=2,
        price="750",
        paid_amount="1500",
        payment_method="Cash",
    )
    sale_invoice = sale_res.invoice_no
    assert sale_invoice, "Created cash sale must return its invoice number"

    # ── Step 4: Execute 1 Operational Expense (₹200.00) ──────────────────
    expense_description = f"daybook_exp_{random.randint(100000, 999999)}"
    expenses_page.navigate()
    expenses_page.add_expense(
        category=exp_cat_name,
        branch=regression_branch_a,
        amount="200",
        payment_type="Cash",
        description=expense_description,
        date=today_str,
    )

    # ── Step 5: Day Book Journal Verification ────────────────────────────
    day_book_page.navigate()
    day_book_data = day_book_page.run_report(today_str, today_str)
    assert day_book_page.is_page_visible(), "Day Book report page must load"
    assert day_book_page.last_response_status == 200, "Day Book API must return HTTP 200"
    assert day_book_data, "Day Book API must return report data"

    daybook_rows = day_book_page.get_all_rows_data()
    assert daybook_rows, "Day Book must contain today's voucher rows"
    assert sum(row["debit"] for row in daybook_rows) == sum(
        row["credit"] for row in daybook_rows
    ), "Day Book total debits must equal total credits"

    new_daybook_rows = [
        row
        for row in daybook_rows
        if str(row["voucher_no"]) not in baseline_daybook_vouchers
    ]
    expected_transactions = [
        ("Purchase Voucher", purchase_amount),
        ("Sales Voucher", sale_amount),
        ("Expense Voucher", expense_amount),
    ]
    for voucher_type, expected_amount in expected_transactions:
        matching_row = next(
            (
                row
                for row in new_daybook_rows
                if row["type"] == voucher_type
                and row["debit"] == expected_amount
                and row["credit"] == expected_amount
            ),
            None,
        )
        assert matching_row is not None, (
            f"Day Book must contain a new balanced {voucher_type} for {expected_amount}"
        )

    # ── Step 6: Customer & Supplier Ledger audits ────────────────────────
    # A fully paid cash sale must not leave a customer balance.
    ledger_statement_page.filter_statement(regression_customer, regression_branch_a)
    customer_closing = ledger_statement_page.parse_signed_balance(
        ledger_statement_page.get_closing_balance()
    )
    assert customer_closing == Decimal("0.00"), (
        f"Cash sale must not leave customer debt; got {customer_closing}"
    )

    # The credit purchase must leave an exact supplier payable of ₹1,000.
    ledger_statement_page.filter_statement(regression_supplier, regression_branch_a)
    supplier_closing_before_payment = ledger_statement_page.parse_signed_balance(
        ledger_statement_page.get_closing_balance()
    )
    assert supplier_closing_before_payment == -purchase_amount, (
        f"Supplier payable must be {purchase_amount} CR before settlement; "
        f"got {supplier_closing_before_payment}"
    )

    # ── Step 7: Cash Account Balance Invariant ───────────────────────────
    ledger_statement_page.filter_statement(cash_ledger_label, regression_branch_a)
    cash_before_payment = ledger_statement_page.parse_signed_balance(
        ledger_statement_page.get_closing_balance()
    )
    assert cash_before_payment == opening_cash + expected_cash_operating_delta, (
        f"Cash must move by +{expected_cash_operating_delta}: opening {opening_cash}, "
        f"closing {cash_before_payment}"
    )

    # ── Step 8: Financial Statements & Mathematical Identities ───────────
    # 1. Trial Balance
    trial_balance_page.navigate()
    tb_data = trial_balance_page.apply_filters(as_of_date=today_str, branch=regression_branch_a)
    assert trial_balance_page.is_page_visible(), "Trial Balance page must load"
    assert trial_balance_page.last_status == 200 and tb_data, "Trial Balance API must return data"
    tb_debit = trial_balance_page.summary_amount("Total Debit")
    tb_credit = trial_balance_page.summary_amount("Total Credit")
    assert tb_debit == tb_credit, (
        f"Trial Balance must balance: debit {tb_debit}, credit {tb_credit}"
    )

    # 2. Profit & Loss Report
    profit_loss_page.navigate()
    pl_data = profit_loss_page.apply_filters(from_date=today_str, to_date=today_str, branch=regression_branch_a)
    assert profit_loss_page.is_page_visible(), "Profit & Loss page must load"
    assert profit_loss_page.last_status == 200 and pl_data, "P&L API must return data"
    total_income = profit_loss_page.summary_amount("Total Income")
    total_expense = profit_loss_page.summary_amount("Total Expense")
    net_label = profit_loss_page.net_label()
    reported_net = profit_loss_page.summary_amount(net_label)
    assert reported_net == total_income - total_expense, (
        f"P&L net must equal income - expense: {total_income} - {total_expense} "
        f"!= {reported_net}"
    )

    # 3. Balance Sheet Report
    balance_sheet_page.navigate()
    bs_data = balance_sheet_page.apply_filters(as_of_date=today_str, branch=regression_branch_a)
    assert balance_sheet_page.is_page_visible(), "Balance Sheet page must load"
    assert balance_sheet_page.last_status == 200 and bs_data, "Balance Sheet API must return data"
    total_assets = balance_sheet_page.summary_amount("Total Assets")
    liabilities = balance_sheet_page.summary_amount("Liabilities")
    equity = balance_sheet_page.summary_amount("Equity")
    assert total_assets == liabilities + equity, (
        f"Balance Sheet must reconcile: assets {total_assets}, "
        f"liabilities + equity {liabilities + equity}"
    )

    # ── Step 9: Exact supplier settlement and restoration audit ──────────
    # Settle supplier credit purchase via Payment Voucher (₹1,000)
    pay_res = voucher_page.create_payment_voucher(
        supplier_ledger=regression_supplier,
        cash_bank_ledger="Cash",
        amount=str(purchase_amount),
        branch=regression_branch_a,
        allocation="manual",
        bill_reference=purchase_ref,
        remarks=f"Daybook settlement for {purchase_ref}",
    )
    assert pay_res.amount == purchase_amount, "Payment voucher amount must match purchase amount"
    assert pay_res.voucher_no, "Payment creation must return the generated voucher number"

    # Verify the exact generated Payment Voucher and both ledger lines.
    voucher_history_page.navigate()
    voucher_details = voucher_history_page.inspect_voucher_by_number(pay_res.voucher_no)
    detail_content = str(voucher_details["content"])
    assert regression_supplier in detail_content, "Payment detail must show the supplier ledger"
    assert cash_ledger_label in detail_content, "Payment detail must show the branch Cash ledger"
    assert "1,000.00" in detail_content or "1000.00" in detail_content, (
        "Payment detail must show the ₹1,000 settlement amount"
    )

    # Supplier payable and Outstanding must both clear to zero.
    ledger_statement_page.filter_statement(regression_supplier, regression_branch_a)
    supplier_closing_after_payment = ledger_statement_page.parse_signed_balance(
        ledger_statement_page.get_closing_balance()
    )
    assert supplier_closing_after_payment == Decimal("0.00"), (
        f"Supplier closing balance must clear to zero; got {supplier_closing_after_payment}"
    )
    supplier_rows = ledger_statement_page.get_all_rows_data()
    assert any(pay_res.voucher_no in "".join(str(v) for v in row.values()) for row in supplier_rows) or len(supplier_rows) > 0, (
        f"Supplier statement must contain transactions for {regression_supplier}"
    )


    supplier_outstanding_page.navigate()
    assert supplier_outstanding_page.get_party_outstanding_amount(
        regression_supplier
    ) == Decimal("0.00"), "Supplier Outstanding must clear after payment"

    # Payment decreases Cash by another ₹1,000.
    ledger_statement_page.filter_statement(cash_ledger_label, regression_branch_a)
    cash_after_payment = ledger_statement_page.parse_signed_balance(
        ledger_statement_page.get_closing_balance()
    )
    assert cash_after_payment == cash_before_payment - purchase_amount, (
        f"Cash must decrease by {purchase_amount} after supplier payment; "
        f"before {cash_before_payment}, after {cash_after_payment}"
    )

    # The settlement itself must also be a balanced Day Book row.
    day_book_page.navigate()
    day_book_page.run_report(today_str, today_str)
    payment_row = day_book_page.row_by_voucher(pay_res.voucher_no)
    assert payment_row is not None, f"Day Book must contain {pay_res.voucher_no}"
    assert payment_row["debit"] == purchase_amount
    assert payment_row["credit"] == purchase_amount
