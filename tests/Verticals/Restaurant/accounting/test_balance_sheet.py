"""Restaurant Balance Sheet Report Accounting Test Suite.

Route: /reports/balance-sheet
Focuses on the Fundamental Accounting Equation:
  Total Assets == Total Liabilities + Total Equity
  and verifies live POS sales reflect in Assets & Equity.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.accounting.balance_sheet_page import BalanceSheetPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Structure & Baseline Balance ──────────────────────────────────────────────

class TestResBalanceSheetStructure:
    """Verify page loading and fundamental balance sheet equation."""

    def test_balance_sheet_page_loads_and_is_balanced(self, res_logged_in_page):
        page = res_logged_in_page
        report_page = BalanceSheetPage(page)
        report = report_page.navigate()

        assert report_page.is_page_visible(), "Balance Sheet page elements should be visible"
        assert report_page.last_status == 200, f"Expected HTTP 200, got {report_page.last_status}"

        total_assets = Decimal(str(report.get("assets", {}).get("total") or 0))
        total_liabilities = Decimal(str(report.get("liabilities", {}).get("total") or 0))
        total_equity = Decimal(str(report.get("equity", {}).get("total") or 0))
        total_liabilities_and_equity = Decimal(str(report.get("total_liabilities_and_equity") or (total_liabilities + total_equity)))

        # Balance Sheet Identity: Total Assets == Total Liabilities + Total Equity
        assert total_assets == total_liabilities_and_equity, (
            f"Balance Sheet Equation Violation: Assets ({total_assets}) != Liabilities+Equity ({total_liabilities_and_equity})"
        )


# ── Tier 2: Filter Tests ──────────────────────────────────────────────────────

class TestResBalanceSheetFilters:
    """Verify Date, Branch, and Clear Filter operations."""

    def test_date_is_required_validation(self, res_logged_in_page):
        report_page = BalanceSheetPage(res_logged_in_page)
        report_page.navigate()
        report_page.submit_without_date()
        expect(report_page.date_validation_error()).to_be_visible()

    def test_as_of_date_filter_updates_report(self, res_logged_in_page):
        report_page = BalanceSheetPage(res_logged_in_page)
        report_page.navigate()
        report = report_page.apply_filters("2099-12-31")

        assert report["as_of_date"] == "2099-12-31", f"Expected as_of_date '2099-12-31', got {report.get('as_of_date')}"

    def test_clear_filters_restores_today(self, res_logged_in_page):
        report_page = BalanceSheetPage(res_logged_in_page)
        report_page.navigate()
        report_page.apply_filters("2099-12-31")
        report = report_page.clear_filters()

        assert report_page.as_of_date.input_value() == date.today().isoformat()
        assert report["as_of_date"] == date.today().isoformat()
        assert report["branch_id"] is None

    def test_branch_filter_applies_correctly(self, res_logged_in_page, res_branch):
        report_page = BalanceSheetPage(res_logged_in_page)
        report_page.navigate()
        report = report_page.apply_filters(date.today().isoformat(), branch=res_branch)

        assert report_page.is_page_visible()
        assert report_page.last_status == 200, f"Expected HTTP 200, got {report_page.last_status}"


# ── Live Accounting Reflection ────────────────────────────────────────────────

class TestResBalanceSheetAccounting:
    """Verify live POS sales reflect in Balance Sheet and preserve the balance equation."""

    def test_pos_billing_reflects_in_balance_sheet_equation(
        self, res_logged_in_page, res_category, res_department, res_unit_type
    ):
        page = res_logged_in_page
        report_page = BalanceSheetPage(page)
        prod_page = ProductsPage(page)
        pos_page = POSBillingPage(page)

        # 1. Capture Balance Sheet Totals BEFORE Sale
        report_before = report_page.navigate()
        assets_before = Decimal(str(report_before.get("assets", {}).get("total") or 0))
        liabilities_before = Decimal(str(report_before.get("liabilities", {}).get("total") or 0))
        equity_before = Decimal(str(report_before.get("equity", {}).get("total") or 0))
        liab_eq_before = Decimal(str(report_before.get("total_liabilities_and_equity") or (liabilities_before + equity_before)))

        dish_name = generate_random_name("bs_dish")
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

            # 4. Capture Balance Sheet Totals AFTER Sale
            report_after = report_page.navigate()
            assets_after = Decimal(str(report_after.get("assets", {}).get("total") or 0))
            liabilities_after = Decimal(str(report_after.get("liabilities", {}).get("total") or 0))
            equity_after = Decimal(str(report_after.get("equity", {}).get("total") or 0))
            liab_eq_after = Decimal(str(report_after.get("total_liabilities_and_equity") or (liabilities_after + equity_after)))

            print(f"\n[Balance Sheet Delta Verification]")
            print(f"  Before Sale -> Assets: ₹{assets_before}, Liab+Equity: ₹{liab_eq_before}")
            print(f"  Sale Amount -> ₹{sale_amount}")
            print(f"  After Sale  -> Assets: ₹{assets_after} (+₹{assets_after - assets_before}), Liab+Equity: ₹{liab_eq_after} (+₹{liab_eq_after - liab_eq_before})")
            print(f"  Balanced?   -> {assets_after == liab_eq_after} (Assets == Liabilities + Equity)")

            # 5. Assert Accounting Invariants:
            # a) Assets increased by at least the sale amount (Cash in Hand asset increased)
            assert assets_after >= assets_before + sale_amount, (
                f"Assets did not increase by ₹{sale_amount}. Before: {assets_before}, After: {assets_after}"
            )

            # b) Liabilities + Equity increased by at least the sale amount (Retained Earnings increased)
            assert liab_eq_after >= liab_eq_before + sale_amount, (
                f"Liabilities+Equity did not increase by ₹{sale_amount}. Before: {liab_eq_before}, After: {liab_eq_after}"
            )

            # c) Fundamental Accounting Equation: Total Assets == Total Liabilities + Total Equity
            assert assets_after == liab_eq_after, (
                f"Balance Sheet Out of Balance: Assets ({assets_after}) != Liabilities+Equity ({liab_eq_after})"
            )

        finally:
            # 6. Guaranteed Teardown (Clean up dish)
            try:
                prod_page.navigate()
                prod_page.delete_product(dish_name)
            except Exception as e:
                print(f"Teardown warning (bs_dish {dish_name}): {e}")
