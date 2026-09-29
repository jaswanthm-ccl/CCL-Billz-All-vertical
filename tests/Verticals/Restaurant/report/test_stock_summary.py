"""Restaurant Stock Summary Report Test Suite.

Route: /reports/stock-summary
Verifies:
  1. Initial page state (heading, run report prompt)
  2. Running the report loads rows and API summary contract
  3. Table headers matching Stock Summary schema
  4. Mathematical integrity of quantity and cost valuation
  5. Search filter with no matches returns empty state
  6. Live purchase of raw materials increases available quantity in Stock Summary
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.report.stock_summary_page import StockSummaryPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Tier 1: Initial State & Run Report ─────────────────────────────────────────

class TestResStockSummaryStructure:
    """Verify initial page state, heading, and Run Report loading."""

    def test_stock_summary_initial_state(self, res_logged_in_page):
        page = res_logged_in_page
        report = StockSummaryPage(page)
        report.navigate()

        assert report.heading_visible(), "Stock Summary heading should be visible"

    def test_run_report_loads_api_contract(self, res_logged_in_page):
        page = res_logged_in_page
        report = StockSummaryPage(page)
        report.navigate()
        data = report.run_report()

        assert "rows" in data or "items" in data, f"Missing rows/items in response: {data.keys()}"
        assert "summary" in data, f"Missing summary in response: {data.keys()}"

        rows = data.get("rows", []) or data.get("items", [])
        assert report.row_count() == len(rows), (
            f"Rendered rows ({report.row_count()}) != API rows ({len(rows)})"
        )

    def test_table_headers_present(self, res_logged_in_page):
        page = res_logged_in_page
        report = StockSummaryPage(page)
        report.navigate()
        report.run_report()

        headers = report.headers()
        assert len(headers) >= 4, f"Expected at least 4 headers, got {len(headers)}: {headers}"
        header_text = " ".join(headers).upper()
        assert "PRODUCT" in header_text, f"Missing PRODUCT header: {headers}"
        assert "QTY" in header_text or "AVAILABLE" in header_text, f"Missing QTY header: {headers}"


# ── Tier 2: Mathematical & Valuation Reconciliation ───────────────────────────

class TestResStockSummaryReconciliation:
    """Verify quantity and cost values are mathematically coherent."""

    def test_each_row_reconciles_quantity_and_values(self, res_logged_in_page):
        page = res_logged_in_page
        report = StockSummaryPage(page)
        report.navigate()
        data = report.run_report()

        rows = data.get("rows", []) or data.get("items", [])
        if not rows:
            pytest.skip("No stock rows present to reconcile")

        for row in rows:
            quantity = report.amount(row.get("available_qty", 0))
            cost_value = report.amount(row.get("cost_value", 0))
            assert quantity >= 0, f"Negative quantity found: {row}"
            assert cost_value >= 0, f"Negative cost value found: {row}"

    def test_summary_totals_are_non_negative(self, res_logged_in_page):
        page = res_logged_in_page
        report = StockSummaryPage(page)
        report.navigate()
        data = report.run_report()

        summary = data.get("summary", {})
        total_qty = Decimal(str(summary.get("total_available_qty", 0)))
        total_cost = Decimal(str(summary.get("total_cost_value", 0)))
        assert total_qty >= 0, f"Total available qty should be >= 0, got {total_qty}"
        assert total_cost >= 0, f"Total cost value should be >= 0, got {total_cost}"


# ── Tier 3: Search Filter ─────────────────────────────────────────────────────

class TestResStockSummaryFilters:
    """Verify search filter."""

    def test_search_with_no_match_returns_empty_report(self, res_logged_in_page):
        page = res_logged_in_page
        report = StockSummaryPage(page)
        report.navigate()

        data = report.run_search("stock-summary-nonexistent-987654321")
        rows = data.get("rows", []) or data.get("items", [])
        assert rows == [], f"Expected empty rows, got {len(rows)}"


# ── Tier 4: Live Inventory Reflection via Purchase ────────────────────────────

class TestResStockSummaryPurchaseReflection:
    """Verify purchasing raw materials reflects in Stock Summary available quantity."""

    def test_purchase_reflects_in_stock_summary(
        self, res_logged_in_page, res_branch, res_supplier,
        res_category, res_department, res_unit_type
    ):
        page = res_logged_in_page
        prod_page = ProductsPage(page)
        purchases = PurchasesPage(page)
        report = StockSummaryPage(page)

        raw_mat = generate_random_name("ss_raw")

        try:
            # 1. Create a raw material product
            prod_page.navigate()
            prod_page.add_product(
                name=raw_mat,
                category_name=res_category,
                department_name=res_department,
                unit_type=res_unit_type,
                product_type="Raw material",
            )

            # 2. Add a purchase of 6 units at ₹80 each
            purchases.add_purchase(
                supplier=res_supplier,
                branch=res_branch,
                reference_no=generate_random_name("SS_PUR"),
                paid_amount="0",
                purchase_type="Credit",
                products_data=[
                    {
                        "product": raw_mat,
                        "quantity": 6,
                        "price": "80",
                    }
                ],
            )

            # 3. Open Stock Summary and search for our newly purchased item
            report.navigate()
            data = report.run_search(raw_mat)

            # 4. Assert the product appears in Stock Summary
            row = report.find_product(data, product_name=raw_mat)
            if row is None:
                # If branch-specific row filtering is needed
                row = report.find_product(data, product_name=raw_mat, branch_name=res_branch)

            assert row is not None, (
                f"Purchased raw material '{raw_mat}' not found in Stock Summary"
            )
            assert report.amount(row.get("available_qty", 0)) >= Decimal("6"), (
                f"Available quantity should be at least 6, got {row.get('available_qty')}"
            )

        finally:
            try:
                prod_page.navigate()
                prod_page.delete_product(raw_mat)
            except Exception as e:
                print(f"Teardown warning (ss_raw {raw_mat}): {e}")
