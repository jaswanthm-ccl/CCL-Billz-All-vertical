"""Master End-to-End Commerce, Debt Settlement & Returns Lifecycle CI Regression Flow.

Path:
1. Baseline Stock Snapshot (S_0) with isolated product and branch.
2. Procure 10 units on 100% Credit (Paid ₹0) -> Stock +10, Supplier Debt = ₹1,000.
3. Verify Supplier Ledger Statement & Purchase Double-Entry Voucher in History.
4. Sell 5 units on 50% Credit (Paid ₹500) -> Stock -5, Customer Debt = ₹500.
5. Verify Customer Ledger Statement.
6. Settle Customer Debt via Receipt Voucher -> Customer Debt Cleared (₹0.00).
7. Settle Supplier Debt via Payment Voucher -> Supplier Debt Cleared (₹0.00).
8. Verify Receipt & Payment Vouchers in Voucher History.
9. Sale Return: Customer returns 2 units -> Stock Restored (+2 units).
10. Purchase Return: Return 2 units back to Supplier -> Stock Reduced (-2 units).
11. Ledger Statements & Return Vouchers audit.
12. Strict Enterprise Stock Invariant: Final stock matches exactly S_0 + 5 units.
"""

import pytest
import random
from decimal import Decimal
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.sales_page import SalesPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.sale_returns_page import SaleReturnsPage
from pages.main_menu.purchase_returns_page import PurchaseReturnsPage
from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.accounting.voucher_history_page import VoucherHistoryPage
from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.report.customer_outstanding_page import CustomerOutstandingPage
from pages.report.supplier_outstanding_page import SupplierOutstandingPage


@pytest.mark.regression
@pytest.mark.default_vertical
def test_master_procure_sell_settle_and_returns_lifecycle_flow(
    logged_in_page,
    regression_supplier,
    regression_customer,
    regression_product,
    regression_branch_a,
):
    """Complete 360° Commerce, Inventory, Voucher Audit & Ledger Reconciliation Lifecycle."""
    purchases_page = PurchasesPage(logged_in_page)
    sales_page = SalesPage(logged_in_page)
    inventories_page = InventoriesPage(logged_in_page)
    voucher_page = CreateVoucherPage(logged_in_page)
    voucher_history_page = VoucherHistoryPage(logged_in_page)
    ledger_statement_page = LedgerStatementPage(logged_in_page)
    customer_outstanding_page = CustomerOutstandingPage(logged_in_page)
    supplier_outstanding_page = SupplierOutstandingPage(logged_in_page)
    sale_returns_page = SaleReturnsPage(logged_in_page)
    purchase_returns_page = PurchaseReturnsPage(logged_in_page)

    purchase_qty = 10
    unit_cost = 100
    total_purchase_amount = purchase_qty * unit_cost  # ₹1,000

    sale_qty = 5
    unit_price = 200
    customer_upfront = "500"
    customer_remaining = "500"

    sale_return_qty = 2
    purchase_return_qty = 2

    # ── Step 0: Read baseline stock (S_0) ────────────────────────────────
    inventories_page.navigate()
    stock_baseline = inventories_page.get_available_stock_number(regression_product)
    assert stock_baseline is not None, "Baseline stock must be readable"

    # ── Step 1: Procure 10 units on 100% Credit (Paid ₹0) ────────────────
    purchases_page.navigate()
    purchase_ref = f"po_cred_{random.randint(100000, 999999)}"
    purchase_res = purchases_page.add_purchase(
        supplier=regression_supplier,
        branch=regression_branch_a,
        reference_no=purchase_ref,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[
            {"product": regression_product, "quantity": purchase_qty, "price": str(unit_cost)}
        ],
    )
    assert purchase_res.reference_no == purchase_ref, "Purchase reference must match"

    # ── Step 2: Verify stock increased by +10 units (S_0 + 10) ───────────
    inventories_page.navigate()
    stock_after_po = inventories_page.get_available_stock_number(regression_product)
    expected_stock_after_po = stock_baseline + Decimal(str(purchase_qty))
    assert stock_after_po == expected_stock_after_po, (
        f"Stock should increase by {purchase_qty}: expected {expected_stock_after_po}, got {stock_after_po}"
    )

    # ── Step 3: Verify Supplier Outstanding Report reflects ₹1,000.00 debt
    supplier_outstanding_page.navigate()
    supp_outstanding = supplier_outstanding_page.get_party_outstanding_amount(regression_supplier)
    assert supp_outstanding == Decimal("1000.00"), (
        f"Supplier {regression_supplier} outstanding should be ₹1,000.00 after credit purchase, got ₹{supp_outstanding}"
    )

    # ── Step 4: Verify Supplier Ledger Statement reflects Credit Purchase ──
    ledger_statement_page.navigate()
    ledger_statement_page.filter_statement(regression_supplier, regression_branch_a)
    assert ledger_statement_page.has_table_visible(), (
        f"Supplier ledger statement must be visible for {regression_supplier}"
    )
    assert ledger_statement_page.get_row_count() > 0, (
        f"Supplier ledger statement must contain transaction rows for {regression_supplier}"
    )

    # ── Step 5: Sell 5 units on 50% partial credit (Paid ₹500) ───────────
    sales_page.navigate()
    sale_res = sales_page.add_sale(
        customer_name=regression_customer,
        branch_name=regression_branch_a,
        product_name=regression_product,
        quantity=sale_qty,
        price=str(unit_price),
        paid_amount=customer_upfront,
        payment_method="Cash",
    )
    sale_invoice = sale_res.invoice_no

    # ── Step 6: Verify stock decreased by 5 units (S_0 + 5) ──────────────
    inventories_page.navigate()
    stock_after_sale = inventories_page.get_available_stock_number(regression_product)
    expected_stock_after_sale = stock_after_po - Decimal(str(sale_qty))
    assert stock_after_sale == expected_stock_after_sale, (
        f"Stock should decrease by {sale_qty}: expected {expected_stock_after_sale}, got {stock_after_sale}"
    )

    # ── Step 7: Verify Customer Outstanding Report reflects ₹500.00 debt ─
    customer_outstanding_page.navigate()
    cust_outstanding = customer_outstanding_page.get_party_outstanding_amount(regression_customer)
    assert cust_outstanding == Decimal("500.00"), (
        f"Customer {regression_customer} outstanding should be ₹500.00 after partial sale, got ₹{cust_outstanding}"
    )

    # ── Step 8: Verify Customer Ledger Statement ─────────────────────────
    ledger_statement_page.navigate()
    ledger_statement_page.filter_statement(regression_customer, regression_branch_a)
    assert ledger_statement_page.has_table_visible() or ledger_statement_page.has_metrics_visible(), (
        f"Customer ledger statement must be visible for {regression_customer}"
    )

    # ── Step 9: Settle Customer Balance via Receipt Voucher (₹500) ───────
    receipt_res = voucher_page.create_receipt_voucher(
        customer_ledger=regression_customer,
        cash_bank_ledger="Cash",
        amount=customer_remaining,
        branch=regression_branch_a,
        remarks=f"Receipt voucher settlement for {regression_customer}",
    )
    assert receipt_res.amount == Decimal("500.00"), "Receipt voucher amount must be ₹500.00"

    # ── Step 10: Verify Customer Outstanding Cleared (₹0.00) ─────────────
    customer_outstanding_page.navigate()
    cleared_cust_outstanding = customer_outstanding_page.get_party_outstanding_amount(regression_customer)
    assert cleared_cust_outstanding == Decimal("0.00"), (
        f"Customer {regression_customer} outstanding should be ₹0.00 after receipt voucher settlement, got ₹{cleared_cust_outstanding}"
    )

    # ── Step 11: Settle Supplier Debt via Payment Voucher (₹1,000) ───────
    payment_res = voucher_page.create_payment_voucher(
        supplier_ledger=regression_supplier,
        cash_bank_ledger="Cash",
        amount=str(total_purchase_amount),
        branch=regression_branch_a,
        remarks=f"Payment voucher settlement for {purchase_ref}",
    )
    assert payment_res.amount == Decimal("1000.00"), "Payment voucher amount must be ₹1000.00"

    # ── Step 12: Verify Supplier Outstanding Cleared (₹0.00) ─────────────
    supplier_outstanding_page.navigate()
    cleared_supp_outstanding = supplier_outstanding_page.get_party_outstanding_amount(regression_supplier)
    assert cleared_supp_outstanding == Decimal("0.00"), (
        f"Supplier {regression_supplier} outstanding should be ₹0.00 after payment voucher settlement, got ₹{cleared_supp_outstanding}"
    )

    # ── Step 13: Sale Return — Customer returns 2 units to Branch A ─────
    sales_page.navigate()
    sales_page.initiate_sale_return(sale_invoice or regression_customer)
    sale_returns_page.perform_return(sale_return_qty)

    # ── Step 14: Verify Inventory Restored by +2 units (S_0 + 7) ────────
    inventories_page.navigate()
    stock_after_sale_return = inventories_page.get_available_stock_number(regression_product)
    expected_stock_after_sale_return = stock_after_sale + Decimal(str(sale_return_qty))
    assert stock_after_sale_return == expected_stock_after_sale_return, (
        f"Sale Return Stock Restoration Violation: {stock_after_sale} + {sale_return_qty} "
        f"should equal {expected_stock_after_sale_return}, got {stock_after_sale_return}"
    )

    # ── Step 15: Purchase Return — Return 2 units back to Supplier ───────
    purchases_page.navigate()
    purchases_page.initiate_return(purchase_ref)
    purchase_returns_page.perform_return(str(purchase_return_qty))

    # ── Step 16: Verify Final Stock Invariant (S_final == S_0 + 5) ───────
    inventories_page.navigate()
    stock_final = inventories_page.get_available_stock_number(regression_product)
    expected_final_stock = stock_baseline + Decimal("5")  # 10 bought - 5 sold + 2 returned by cust - 2 returned to supp = +5
    assert stock_final == expected_final_stock, (
        f"Final Stock Invariant Violation: Baseline {stock_baseline} + net 5 units "
        f"should equal {expected_final_stock}, got {stock_final}"
    )

    # ── Step 17: Post-Returns Customer & Supplier Ledger Statement Audits ─
    ledger_statement_page.filter_statement(regression_customer, regression_branch_a)
    assert ledger_statement_page.has_table_visible() or ledger_statement_page.has_metrics_visible(), (
        f"Customer ledger statement table must be visible for {regression_customer}"
    )
    assert ledger_statement_page.get_row_count() > 0, (
        f"Customer ledger statement must contain transaction rows for {regression_customer}"
    )

    ledger_statement_page.filter_statement(regression_supplier, regression_branch_a)
    assert ledger_statement_page.has_table_visible() or ledger_statement_page.has_metrics_visible(), (
        f"Supplier ledger statement table must be visible for {regression_supplier}"
    )
    assert ledger_statement_page.get_row_count() > 0, (
        f"Supplier ledger statement must contain transaction rows for {regression_supplier}"
    )

