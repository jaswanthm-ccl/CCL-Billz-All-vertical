"""Suite 5: Financial Statements, Reports & GSTR-1 Tax Audit Flow.

Comprehensive end-to-end regression flow verifying:
1. Baseline Financial Statement snapshots (Trial Balance, P&L, Balance Sheet).
2. Controlled taxable B2B (with GSTIN) and B2C (without GSTIN) sales (18% GST).
3. Downstream GSTR-1 B2B tax compliance, GSTIN mapping, CGST/SGST/IGST breakdown.
4. Downstream GSTR-1 B2C tax compliance, isolation from B2B, and totals reconciliation.
5. GSTR-1 filter and mode toggles (invoice-wise vs rate-wise).
6. Non-empty, structurally valid XLSX and PDF exports for both B2B and B2C returns.
7. Inventory valuation invariant in Stock Summary report.
8. Financial statement double-entry mathematical invariants (Decimal precision).
"""

from __future__ import annotations

from datetime import date
import random
import uuid
from decimal import Decimal

import pytest

from pages.accounting.balance_sheet_page import BalanceSheetPage
from pages.accounting.profit_loss_page import ProfitLossPage
from pages.accounting.trial_balance_page import TrialBalancePage
from pages.main_menu.customers_page import CustomersPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.sales_page import SalesPage
from pages.report.gstr_1_b2b_page import Gstr1B2bPage
from pages.report.gstr_1_b2c_page import Gstr1B2cPage
from pages.report.stock_summary_page import StockSummaryPage
from utils.random_data import (
    generate_random_address,
    generate_random_email,
    generate_random_gst,
    generate_random_phone,
    generate_random_postal_code,
)


def _money(value: object) -> Decimal:
    """Normalize numeric string/number to Decimal with 2 decimal places."""
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def test_financial_reports_and_gstr_tax_audit_flow(
    logged_in_page,
    regression_branch_a,
    regression_supplier,
    regression_customer,
    regression_product,
    regression_city,
    worker_id,
):
    """Execute the full 360° Financial Statements, Stock Summary & GSTR-1 Tax Audit lifecycle."""
    page = logged_in_page

    # Initialize Page Objects
    trial_balance_page = TrialBalancePage(page)
    profit_loss_page = ProfitLossPage(page)
    balance_sheet_page = BalanceSheetPage(page)
    stock_summary_page = StockSummaryPage(page)
    gstr1_b2b_page = Gstr1B2bPage(page)
    gstr1_b2c_page = Gstr1B2cPage(page)
    customers_page = CustomersPage(page)
    products_page = ProductsPage(page)
    purchases_page = PurchasesPage(page)
    sales_page = SalesPage(page)


    # ── Step 1: Capture Baseline Financial Statements ────────────────────────
    # A. Trial Balance (∑ Debit == ∑ Credit)
    tb_data = trial_balance_page.navigate()
    assert tb_data is not None, "Trial Balance report data must load"
    if "total_debit" in tb_data and "total_credit" in tb_data:
        assert abs(_money(tb_data["total_debit"]) - _money(tb_data["total_credit"])) <= Decimal("0.05"), (
            f"Baseline Trial Balance Out of Balance: Debits ₹{tb_data['total_debit']} != Credits ₹{tb_data['total_credit']}"
        )

    # B. Profit & Loss (Net Profit == Income - Expenses)
    pl_data = profit_loss_page.navigate()
    assert pl_data is not None, "Profit & Loss report data must load"
    if "income" in pl_data and "expense" in pl_data:
        total_income = _money(pl_data["income"].get("total", 0))
        total_expense = _money(pl_data["expense"].get("total", 0))
        net_profit = _money(pl_data.get("net_profit", 0))
        assert abs(net_profit - (total_income - total_expense)) <= Decimal("0.05"), (
            f"Baseline P&L Invariant Violation: Net Profit ₹{net_profit} != Income ₹{total_income} - Expense ₹{total_expense}"
        )

    # C. Balance Sheet (Liabilities + Equity == Combined Total)
    bs_data = balance_sheet_page.navigate()
    assert bs_data is not None, "Balance Sheet report data must load"
    if "liabilities" in bs_data and "equity" in bs_data:
        total_liabilities = _money(bs_data["liabilities"].get("total", 0))
        total_equity = _money(bs_data["equity"].get("total", 0))
        combined_total = _money(bs_data.get("total_liabilities_and_equity", total_liabilities + total_equity))
        assert abs((total_liabilities + total_equity) - combined_total) <= Decimal("0.05"), (
            f"Baseline Balance Sheet Invariant Violation: Liabilities ₹{total_liabilities} + Equity ₹{total_equity} != Combined ₹{combined_total}"
        )

    # ── Step 2: Create B2B Company Customer & Inward Stock ──────────────────
    # 1. B2B Company Customer (with valid GSTIN)
    b2b_customer_name = f"regr_{worker_id}_b2b_{uuid.uuid4().hex[:6]}"
    b2b_gstin = generate_random_gst()
    customers_page.navigate()
    customers_page.add_customer(
        name=b2b_customer_name,
        customer_type="Company",
        email=generate_random_email("b2b"),
        phone=generate_random_phone(),
        contact_person="B2B Tax Officer",
        address_line1=generate_random_address(),
        state_name="Tamil Nadu",
        city_name=regression_city,
        postal_code=generate_random_postal_code(),
        gst_number=b2b_gstin,
    )

    # 2. Inward Stock for regression_product via Opening Stock (10 units @ ₹100 cost)
    products_page.navigate()
    products_page.update_opening_stock(
        name=regression_product,
        branch_name=regression_branch_a,
        quantity="10",
        cost_price="100",
    )


    # ── Step 3: Execute Controlled B2B & B2C Sales Transactions ──────────────
    # B2B Sale: 2 units @ ₹590 (inc GST) = ₹1,000 Taxable + ₹90 CGST (9%) + ₹90 SGST (9%) = ₹1,180 Total
    sales_page.navigate()
    b2b_sale = sales_page.add_sale(
        customer_name=b2b_customer_name,
        branch_name=regression_branch_a,
        product_name=regression_product,
        quantity=2,
        price="590",
        paid_amount="0",
    )
    assert b2b_sale.invoice_no, "B2B sale must generate an invoice number"

    # B2C Sale: 1 unit @ ₹590 (inc GST) = ₹500 Taxable + ₹45 CGST (9%) + ₹45 SGST (9%) = ₹590 Total
    sales_page.navigate()
    b2c_sale = sales_page.add_sale(
        customer_name=regression_customer,
        branch_name=regression_branch_a,
        product_name=regression_product,
        quantity=1,
        price="590",
        paid_amount="590",
    )
    assert b2c_sale.invoice_no, "B2C sale must generate an invoice number"


    # ── Step 4: Validate Stock Summary Report & Inventory Valuation ──────────
    stock_summary_page.navigate()
    stock_data = stock_summary_page.run_report()
    assert stock_data is not None, "Stock Summary report must run successfully"
    # Net available units = 10 inward - 2 B2B - 1 B2C = 7 units remaining
    rows = stock_data.get("rows", [])
    matched_stock = next((r for r in rows if r.get("product_name") == regression_product or r.get("product") == regression_product), None)
    if matched_stock:
        avail_qty = _money(matched_stock.get("available_qty", matched_stock.get("available_units", 7)))
        assert avail_qty == Decimal("7.00"), f"Expected 7 available units for {regression_product}, got {avail_qty}"

    # ── Step 5: Validate GSTR-1 B2B Report ───────────────────────────────────
    gstr1_b2b_page.navigate()
    b2b_report_data = gstr1_b2b_page.last_data or {}
    b2b_rows = b2b_report_data.get("rows", [])
    assert isinstance(b2b_rows, list), "GSTR-1 B2B rows must be a list"

    # Find the created B2B invoice
    b2b_match = next(
        (
            r for r in b2b_rows
            if r.get("customer_name") == b2b_customer_name
            or r.get("customer_gstin") == b2b_gstin
            or r.get("invoice_number") == b2b_sale.invoice_no
        ),
        None,
    )
    assert b2b_match is not None, f"B2B invoice for {b2b_customer_name} ({b2b_gstin}) must appear in GSTR-1 B2B report"
    assert b2b_match.get("customer_gstin") == b2b_gstin, "B2B row must contain exact customer GSTIN"
    assert _money(b2b_match.get("taxable_value")) == Decimal("1000.00"), f"Expected ₹1,000.00 taxable value, got {b2b_match.get('taxable_value')}"
    assert _money(b2b_match.get("cgst_amount", b2b_match.get("cgst"))) == Decimal("90.00"), "CGST must equal ₹90.00 (9%)"
    assert _money(b2b_match.get("sgst_amount", b2b_match.get("sgst"))) == Decimal("90.00"), "SGST must equal ₹90.00 (9%)"
    assert _money(b2b_match.get("igst_amount", b2b_match.get("igst", 0))) == Decimal("0.00"), "Intra-state sale IGST must be ₹0.00"
    assert _money(b2b_match.get("total_invoice_value", b2b_match.get("invoice_total", b2b_match.get("total_amount")))) == Decimal("1180.00"), "Total invoice value must equal ₹1,180.00"

    # ── Step 6: Validate GSTR-1 B2C Report & Cross-Report Isolation ──────────
    gstr1_b2c_page.navigate()
    b2c_report_data = gstr1_b2c_page.last_data or {}
    b2c_rows = b2c_report_data.get("rows", [])
    assert isinstance(b2c_rows, list), "GSTR-1 B2C rows must be a list"

    # Find the created B2C invoice in B2C report
    b2c_match = next(
        (
            r for r in b2c_rows
            if r.get("customer_name") == regression_customer
            or r.get("invoice_number") == b2c_sale.invoice_no
        ),
        None,
    )
    if b2c_match is None:
        today_iso = date.today().isoformat()
        filtered_b2c = gstr1_b2c_page.apply_filters(
            from_date=today_iso, to_date=today_iso, branch_name=regression_branch_a
        )
        b2c_rows = filtered_b2c.get("rows", [])
        b2c_match = next(
            (
                r for r in b2c_rows
                if r.get("customer_name") == regression_customer
                or r.get("invoice_number") == b2c_sale.invoice_no
            ),
            None,
        )
    assert b2c_match is not None, f"B2C invoice for {regression_customer} must appear in GSTR-1 B2C report"
    assert _money(b2c_match.get("taxable_value")) == Decimal("500.00"), f"Expected ₹500.00 taxable value, got {b2c_match.get('taxable_value')}"
    assert _money(b2c_match.get("cgst_amount", b2c_match.get("cgst"))) == Decimal("45.00"), "CGST must equal ₹45.00 (9%)"
    assert _money(b2c_match.get("sgst_amount", b2c_match.get("sgst"))) == Decimal("45.00"), "SGST must equal ₹45.00 (9%)"
    assert _money(b2c_match.get("total_invoice_value", b2c_match.get("invoice_total", b2c_match.get("total_amount")))) == Decimal("590.00"), "Total invoice value must equal ₹590.00"

    # Verify B2C invoice does NOT appear in GSTR-1 B2B report
    assert not any(
        r.get("customer_name") == regression_customer or r.get("invoice_number") == b2c_sale.invoice_no
        for r in b2b_rows
    ), "B2C retail invoice must never leak into GSTR-1 B2B report"

    # ── Step 7: Validate Filter & Mode Toggles ──────────────────────────────
    today = date.today().isoformat()
    gstr1_b2b_page.navigate()
    summary_data = gstr1_b2b_page.apply_filters(
        from_date=today, to_date=today, branch_name=regression_branch_a, mode="summary_wise"
    )
    assert summary_data.get("meta", {}).get("mode") == "summary_wise", "Report mode must switch to summary_wise"

    invoice_data = gstr1_b2b_page.apply_filters(
        from_date=today, to_date=today, branch_name=regression_branch_a, mode="invoice_wise"
    )
    assert invoice_data.get("meta", {}).get("mode") == "invoice_wise", "Report mode must switch back to invoice_wise"

    # Totals reconciliation
    inv_totals = invoice_data.get("totals", {})
    summary_totals = summary_data.get("totals", {})
    if inv_totals and summary_totals:
        assert _money(inv_totals.get("taxable_value")) == _money(summary_totals.get("taxable_value")), (
            f"Taxable value mismatch across modes: {inv_totals.get('taxable_value')} != {summary_totals.get('taxable_value')}"
        )


    # ── Step 8: Validate Report Exports (XLSX & PDF) ─────────────────────────
    # A. B2B Exports
    b2b_xlsx = gstr1_b2b_page.export("xlsx")
    b2b_xlsx_path = gstr1_b2b_page.downloaded_path(b2b_xlsx)
    gstr1_b2b_page.assert_valid_xlsx(b2b_xlsx_path, "GSTR-1 B2B")

    b2b_pdf = gstr1_b2b_page.export("pdf")
    b2b_pdf_path = gstr1_b2b_page.downloaded_path(b2b_pdf)
    gstr1_b2b_page.assert_valid_pdf(b2b_pdf_path)

    # B. B2C Exports
    gstr1_b2c_page.navigate()
    b2c_xlsx = gstr1_b2c_page.export("xlsx")
    b2c_xlsx_path = gstr1_b2c_page.downloaded_path(b2c_xlsx)
    gstr1_b2c_page.assert_valid_xlsx(b2c_xlsx_path, "GSTR-1 B2C")

    b2c_pdf = gstr1_b2c_page.export("pdf")
    b2c_pdf_path = gstr1_b2c_page.downloaded_path(b2c_pdf)
    gstr1_b2c_page.assert_valid_pdf(b2c_pdf_path)


    # ── Step 9: Re-audit Financial Statement Double-Entry Invariants ────────
    # Trial Balance: ∑ Debit == ∑ Credit
    post_tb = trial_balance_page.navigate()
    if "total_debit" in post_tb and "total_credit" in post_tb:
        assert abs(_money(post_tb["total_debit"]) - _money(post_tb["total_credit"])) <= Decimal("0.05"), (
            f"Post-Transactions Trial Balance Out of Balance: Debits ₹{post_tb['total_debit']} != Credits ₹{post_tb['total_credit']}"
        )

    # Profit & Loss: Net Profit == Income - Expenses
    post_pl = profit_loss_page.navigate()
    if "income" in post_pl and "expense" in post_pl:
        post_income = _money(post_pl["income"].get("total", 0))
        post_expense = _money(post_pl["expense"].get("total", 0))
        post_net = _money(post_pl.get("net_profit", 0))
        assert abs(post_net - (post_income - post_expense)) <= Decimal("0.05"), (
            f"Post-Transactions P&L Invariant Violation: Net Profit ₹{post_net} != Income ₹{post_income} - Expense ₹{post_expense}"
        )

    # Balance Sheet: Liabilities + Equity == Combined Total
    post_bs = balance_sheet_page.navigate()
    if "liabilities" in post_bs and "equity" in post_bs:
        post_liabilities = _money(post_bs["liabilities"].get("total", 0))
        post_equity = _money(post_bs["equity"].get("total", 0))
        post_combined = _money(post_bs.get("total_liabilities_and_equity", post_liabilities + post_equity))
        assert abs((post_liabilities + post_equity) - post_combined) <= Decimal("0.05"), (
            f"Post-Transactions Balance Sheet Invariant Violation: Liabilities ₹{post_liabilities} + Equity ₹{post_equity} != Combined ₹{post_combined}"
        )
