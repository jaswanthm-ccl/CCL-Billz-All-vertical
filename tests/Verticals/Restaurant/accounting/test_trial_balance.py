"""Restaurant Trial Balance Report Accounting Test Suite.

Route: /reports/trial-balance
Focuses on Core Financial Invariant:
  1. Live POS Sale increases Total Debits and Total Credits by the sale amount.
  2. Total Debits strictly equals Total Credits (Total Debit == Total Credit).
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.accounting.trial_balance_page import TrialBalancePage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Structure & Baseline Balance ──────────────────────────────────────────────

class TestResTrialBalanceStructure:
    """Verify page loading and fundamental balanced state."""

    def test_trial_balance_page_loads_and_is_balanced(self, res_logged_in_page):
        page = res_logged_in_page
        report_page = TrialBalancePage(page)
        report = report_page.navigate()

        assert report_page.is_page_visible(), "Trial Balance page elements should be visible"
        assert report_page.last_status == 200, f"Expected HTTP 200, got {report_page.last_status}"

        total_debit = Decimal(str(report.get("total_debit") or 0))
        total_credit = Decimal(str(report.get("total_credit") or 0))

        # Financial Invariant: Debits must equal Credits
        assert total_debit == total_credit, (
            f"Accounting Invariant Violation: Total Debit ({total_debit}) != Total Credit ({total_credit})"
        )


# ── Live Accounting Reflection ────────────────────────────────────────────────

class TestResTrialBalanceAccounting:
    """Verify live POS sales reflect in Trial Balance and preserve equal debit/credit identity."""

    def test_pos_billing_increases_trial_balance_and_maintains_equality(
        self, res_logged_in_page, res_category, res_department, res_unit_type
    ):
        page = res_logged_in_page
        report_page = TrialBalancePage(page)
        prod_page = ProductsPage(page)
        pos_page = POSBillingPage(page)

        # 1. Capture Trial Balance Totals BEFORE Sale
        report_before = report_page.navigate()
        debit_before = Decimal(str(report_before.get("total_debit") or 0))
        credit_before = Decimal(str(report_before.get("total_credit") or 0))

        dish_name = generate_random_name("tb_dish")
        dish_price = "180"
        sale_amount = Decimal(dish_price)

        try:
            # 2. Create Test Dish
            prod_page.navigate()
            dish_code = prod_page.add_product(
                name=dish_name,
                category_name=res_category,
                department_name=res_department,
                unit_type=res_unit_type,
                price=dish_price,
                product_type="Finished good",
            )

            # 3. Complete POS Dine-In Cash Sale
            pos_page.navigate()
            pos_page.select_bill_tab("Bill 1")
            pos_page.select_order_type("Dine In")
            pos_page.enter_dish_by_code(code=dish_code, dish_name=dish_name)

            sale_data = pos_page.settle_and_bill()
            invoice_ref = str(sale_data.get("invoice_no") or sale_data.get("id", ""))
            pos_page.collect_cash_payment(bill_reference=invoice_ref)

            # 4. Capture Trial Balance Totals AFTER Sale
            report_after = report_page.navigate()
            debit_after = Decimal(str(report_after.get("total_debit") or 0))
            credit_after = Decimal(str(report_after.get("total_credit") or 0))

            print(f"\n[Trial Balance Delta Verification]")
            print(f"  Before Sale -> Debit: ₹{debit_before}, Credit: ₹{credit_before}")
            print(f"  Sale Amount -> ₹{sale_amount}")
            print(f"  After Sale  -> Debit: ₹{debit_after} (+₹{debit_after - debit_before}), Credit: ₹{credit_after} (+₹{credit_after - credit_before})")
            print(f"  Balanced?   -> {debit_after == credit_after} (Debit == Credit)")

            # 5. Assert Accounting Invariants:
            # a) Debits increased by at least the sale amount (Cash in hand debited)
            assert debit_after >= debit_before + sale_amount, (
                f"Total Debit did not increase by ₹{sale_amount}. Before: {debit_before}, After: {debit_after}"
            )

            # b) Credits increased by at least the sale amount (Sales revenue credited)
            assert credit_after >= credit_before + sale_amount, (
                f"Total Credit did not increase by ₹{sale_amount}. Before: {credit_before}, After: {credit_after}"
            )

            # c) Fundamental Accounting Identity: Debits MUST strictly EQUAL Credits
            assert debit_after == credit_after, (
                f"Trial Balance Out of Balance after sale: Total Debit ({debit_after}) != Total Credit ({credit_after})"
            )

        finally:
            # 6. Guaranteed Teardown (Clean up dish)
            try:
                prod_page.navigate()
                prod_page.delete_product(dish_name)
            except Exception as e:
                print(f"Teardown warning (tb_dish {dish_name}): {e}")
