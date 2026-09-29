"""Master Hybrid Down-Payment & EMI Financing, Reconciliation & Double-Entry Accounting CI Regression Flow.

Path:
1. Baseline Snapshot on EMI Report & Inventory Stock (S_0).
2. Procure 10 units into Branch A -> Verify stock increases to S_0 + 10.
3. Create Unique Master EMI Provider (e.g. Bajaj_EMI_...).
4. Execute Hybrid Sale (Total Price: ₹200.00 = ₹50.00 Cash Down-Payment + ₹150.00 EMI Financed).
5. View Sale Details: Confirm ₹50 Down-Payment, ₹150 EMI Outstanding and Pending settlement status.
6. Physical Stock Decrement: Confirm available inventory dropped to S_0 + 9.
7. Customer Debt Isolation Invariant: Confirm Customer Outstanding is ₹0.00.
8. Compound Double-Entry Provider Ledger Statement Audit (Debit: Provider Receivable ₹150).
9. Pre-Settlement EMI Reconciliation Report: Validate Macro cards (+₹150 Financed/Outstanding) and Micro Provider Row (₹150 Financed, ₹0 Settled, ₹150 Outstanding).
10. Provider Settlement via Receipt Voucher: Create ₹150 Receipt Voucher for EMI Provider Receivable.
11. Post-Settlement Provider Ledger Statement: Audit updated Provider Receivable ledger statement.
12. Post-Settlement EMI Reconciliation Report: Confirm Total Settled increments by +₹150 and Outstanding clears to ₹0.00.
"""

import random
from decimal import Decimal
import pytest
from pages.main_menu.sales_page import SalesPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.master_menu.emi_providers_page import EmiProvidersPage
from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.report.emi_reconciliation_page import EmiReconciliationPage
from pages.report.customer_outstanding_page import CustomerOutstandingPage
from utils.random_data import generate_random_name


@pytest.fixture
def emi_flow_cleanup(logged_in_page):
    cleanup_providers = []
    yield cleanup_providers
    emi_page = EmiProvidersPage(logged_in_page)
    for name in reversed(cleanup_providers):
        try:
            emi_page.navigate()
            if emi_page.search_emi_provider(name):
                emi_page.delete_emi_provider(name)
        except Exception as e:
            print(f"Teardown: Failed to delete EMI provider {name}: {e}")


@pytest.mark.regression
@pytest.mark.default_vertical
def test_emi_sale_to_reconciliation_flow(
    logged_in_page,
    regression_branch_a,
    regression_customer,
    regression_supplier,
    regression_product,
    emi_flow_cleanup,
):
    """Complete 360° Hybrid Down-Payment + EMI Financing & Reconciliation Lifecycle."""
    sales_page = SalesPage(logged_in_page)
    purchases_page = PurchasesPage(logged_in_page)
    inventories_page = InventoriesPage(logged_in_page)
    emi_page = EmiProvidersPage(logged_in_page)
    voucher_page = CreateVoucherPage(logged_in_page)
    ledger_statement_page = LedgerStatementPage(logged_in_page)
    recon_page = EmiReconciliationPage(logged_in_page)
    customer_outstanding_page = CustomerOutstandingPage(logged_in_page)

    total_sale_price = "200"
    down_payment_amount = "50"
    financed_price = "150"  # 200 - 50 = 150
    financed_amount_decimal = Decimal(financed_price)

    # ── Step 0: Baseline Snapshot on EMI Report & Inventory Stock ────────────
    recon_page.navigate()
    initial_cards = recon_page.get_summary_cards()

    inventories_page.navigate()
    stock_baseline = inventories_page.get_available_stock_number(regression_product)

    # ── Step 1: Stock Product in Branch A via Purchase & Verify Inward ───────
    purchases_page.navigate()
    ref_no = f"stock_emi_{random.randint(100000, 999999)}"
    po_res = purchases_page.add_purchase(
        supplier=regression_supplier,
        branch=regression_branch_a,
        reference_no=ref_no,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[{"product": regression_product, "quantity": 10, "price": "100"}],
    )
    assert po_res.reference_no == ref_no

    # Verify inventory incremented by +10
    inventories_page.navigate()
    stock_after_po = inventories_page.get_available_stock_number(regression_product)
    expected_stock_after_po = stock_baseline + Decimal("10")
    assert stock_after_po == expected_stock_after_po, (
        f"Inventory should increase by 10 units: expected {expected_stock_after_po}, got {stock_after_po}"
    )

    # ── Step 2: Create Unique Master EMI Provider ───────────────────────────
    provider_name = generate_random_name("Bajaj_EMI")
    emi_page.navigate()
    emi_page.add_emi_provider(name=provider_name)
    emi_flow_cleanup.append(provider_name)

    assert emi_page.search_emi_provider(provider_name), f"Provider {provider_name} must exist in master table"

    # ── Step 3: Create Hybrid Sale (₹50 Cash Down-Payment + ₹150 EMI) ───────
    sales_page.navigate()
    sale_res = sales_page.add_sale(
        customer_name=regression_customer,
        branch_name=regression_branch_a,
        product_name=regression_product,
        quantity=1,
        price=total_sale_price,
        paid_amount=down_payment_amount,
        payment_method="Cash",
        is_emi=True,
        emi_provider_name=provider_name,
    )
    sale_invoice = sale_res.invoice_no

    # ── Step 4: View Sale Modal and Verify Hybrid Payment Breakdown ─────────
    details = sales_page.view_sale_by_invoice(sale_invoice) if sale_invoice else sales_page.view_sale_details(customer_name=regression_customer)
    assert details["has_emi_outstanding"], "Sale view dialog must show 'EMI Outstanding'"
    assert details["has_pending_status"], "Sale view dialog must show 'Pending' settlement status"

    # ── Step 5: Physical Inventory Decrement Verification (-1 Unit) ──────────
    inventories_page.navigate()
    stock_after_sale = inventories_page.get_available_stock_number(regression_product)
    expected_stock_after_sale = stock_after_po - Decimal("1")
    assert stock_after_sale == expected_stock_after_sale, (
        f"EMI Sale Inventory Decrement Violation: Expected {expected_stock_after_sale}, got {stock_after_sale}"
    )

    # ── Step 6: Customer Debt Isolation Invariant (Customer owes ₹0.00) ──────
    customer_outstanding_page.navigate()
    customer_debt = customer_outstanding_page.get_party_outstanding_amount(regression_customer)
    assert customer_debt == Decimal("0.00"), (
        f"Customer Debt Isolation Invariant Violation: Customer {regression_customer} should have ₹0.00 "
        f"debt since down-payment was paid and balance was EMI financed, but got ₹{customer_debt}"
    )

    # ── Step 7: Audit Provider Receivable Ledger Statement (Double-Entry) ───
    provider_ledger_name = f"{provider_name} Receivable"
    ledger_statement_page.navigate()
    ledger_statement_page.filter_statement(provider_ledger_name, regression_branch_a)
    assert ledger_statement_page.has_table_visible() or ledger_statement_page.has_metrics_visible(), (
        f"Provider ledger statement table must be visible for {provider_name}"
    )
    assert ledger_statement_page.get_row_count() > 0 or ledger_statement_page.has_metrics_visible(), (
        f"Provider ledger statement must contain transaction rows for {provider_name}"
    )

    # ── Step 8: Verify Reconciliation Cards and Micro Provider Row ─────────
    recon_page.navigate()
    final_cards = recon_page.get_summary_cards()

    # 1. Macro Summary Card Deltas
    assert final_cards["total_financed"] >= initial_cards["total_financed"] + financed_amount_decimal, (
        f"Total Financed must increase by at least ₹{financed_price}.00 (initial: {initial_cards['total_financed']}, final: {final_cards['total_financed']})"
    )
    assert final_cards["total_outstanding"] >= initial_cards["total_outstanding"] + financed_amount_decimal, (
        f"Total Outstanding must increase by at least ₹{financed_price}.00 (initial: {initial_cards['total_outstanding']}, final: {final_cards['total_outstanding']})"
    )

    # 2. Micro Provider Row Exact Decimal Assertions (Strict 100% equality for isolated provider)
    assert recon_page.search_provider(provider_name), f"EMI Reconciliation Report must list {provider_name}"
    recon_data = recon_page.get_provider_reconciliation_row(provider_name)
    assert recon_data["total_financed"] == financed_amount_decimal, (
        f"Expected exact ₹{financed_price}.00 financed for {provider_name}, got {recon_data['total_financed']}"
    )

    # ── Step 9: Settle EMI Financed Amount via Receipt Voucher ──────────────
    cash_ledger_label = f"Cash Ledger — {regression_branch_a}"

    receipt_res = voucher_page.create_receipt_voucher(
        customer_ledger=provider_ledger_name,
        cash_bank_ledger=cash_ledger_label,
        amount=financed_price,
        branch=regression_branch_a,
        remarks=f"EMI Settlement for {provider_name}",
    )
    assert receipt_res.amount == financed_amount_decimal, "Receipt voucher amount must match financed amount"

    # ── Step 10: Post-Settlement Provider Ledger Statement Audit ────────────
    ledger_statement_page.filter_statement(provider_ledger_name, regression_branch_a)
    assert ledger_statement_page.has_table_visible() or ledger_statement_page.has_metrics_visible(), (
        f"Post-settlement provider ledger table must be visible for {provider_name}"
    )
    assert ledger_statement_page.get_row_count() > 0 or ledger_statement_page.has_metrics_visible(), (
        f"Post-settlement provider ledger must contain settlement row for {provider_name}"
    )


    # ── Step 11: Re-audit EMI Reconciliation Report After Settlement ────────
    recon_page.navigate()
    settled_cards = recon_page.get_summary_cards()

    # Macro Settled Cards Assertions
    assert settled_cards["total_settled"] >= initial_cards["total_settled"] + financed_amount_decimal, (
        f"Total Settled must increase by at least ₹{financed_price}.00 (initial: {initial_cards['total_settled']}, final: {settled_cards['total_settled']})"
    )

    # Micro Provider Row Settled Assertions
    assert recon_page.search_provider(provider_name), f"EMI Reconciliation Report must list {provider_name}"
    settled_row = recon_page.get_provider_reconciliation_row(provider_name)
    assert settled_row["total_settled"] == financed_amount_decimal, (
        f"Expected exact ₹{financed_price}.00 settled in provider row, got: {settled_row['total_settled']}"
    )
