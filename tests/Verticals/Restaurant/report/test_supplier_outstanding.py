"""Restaurant Supplier Outstanding Report Test Suite.

Route: /reports/supplier-outstanding
Verifies:
  1. Page loading, heading, and table headers
  2. API contract (items, pagination, summary)
  3. Search filter for known/unknown suppliers
  4. Outstanding sort ordering
  5. Credit purchase creates a Payable supplier outstanding entry
  6. Row count matches API response
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.report.supplier_outstanding_page import SupplierOutstandingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Tier 1: Structure & Page Load ─────────────────────────────────────────────

class TestResSupplierOutstandingStructure:
    """Verify page load and basic UI elements."""

    def test_page_loads_with_heading(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        data = report.navigate()

        assert report.heading_visible(), "Supplier Outstanding heading should be visible"

    def test_api_returns_expected_keys(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        data = report.navigate()

        assert "items" in data, f"Missing 'items' in response: {data.keys()}"
        assert "pagination" in data, f"Missing 'pagination' in response: {data.keys()}"
        assert "summary" in data, f"Missing 'summary' in response: {data.keys()}"

    def test_table_headers_present(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        report.navigate()

        headers = report.headers()
        assert len(headers) >= 5, f"Expected at least 5 table headers, got {len(headers)}: {headers}"
        header_text = " ".join(headers).upper()
        assert "SUPPLIER" in header_text, f"Missing SUPPLIER column: {headers}"
        assert "OUTSTANDING" in header_text, f"Missing OUTSTANDING column: {headers}"

    def test_rendered_row_count_matches_api(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        data = report.navigate()

        assert len(report.rows()) == len(data.get("items", []))


# ── Tier 2: Search & Filter Tests ─────────────────────────────────────────────

class TestResSupplierOutstandingFilters:
    """Verify search and filter controls."""

    def test_unknown_supplier_search_returns_empty(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        report.navigate()

        data = report.search("AUTOMATION-NO-SUCH-SUPPLIER-987654321")
        assert data.get("items", []) == [], "Unknown supplier should return empty results"
        assert data.get("summary", {}).get("total_parties", 0) == 0

    def test_outstanding_sort_descending(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        report.navigate()

        data = report.set_sort("outstanding_amount", "desc")
        amounts = [
            report.amount(item["outstanding_amount"])
            for item in data.get("items", [])
            if report.amount(item["outstanding_amount"]) > 0
        ]
        if len(amounts) >= 2:
            assert amounts == sorted(amounts, reverse=True), (
                f"Descending sort broken: {amounts}"
            )


# ── Tier 3: Summary Metrics ──────────────────────────────────────────────────

class TestResSupplierOutstandingSummary:
    """Verify summary metrics cards."""

    def test_summary_metrics_present(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        data = report.navigate()

        summary = data.get("summary", {})
        assert "total_outstanding" in summary, f"Missing total_outstanding in summary: {summary}"
        assert "total_parties" in summary, f"Missing total_parties in summary: {summary}"

    def test_summary_total_outstanding_is_non_negative(self, res_logged_in_page):
        page = res_logged_in_page
        report = SupplierOutstandingPage(page)
        data = report.navigate()

        total = Decimal(str(data.get("summary", {}).get("total_outstanding", 0)))
        assert total >= 0, f"Total outstanding should be >= 0, got {total}"


# ── Tier 4: Credit Purchase Creates Supplier Outstanding ──────────────────────

class TestResSupplierOutstandingCreditPurchase:
    """Create an unpaid purchase and verify it reflects in Supplier Outstanding."""

    def test_credit_purchase_creates_payable_entry(
        self, res_logged_in_page, res_branch, res_supplier,
        res_category, res_department, res_unit_type
    ):
        page = res_logged_in_page
        prod_page = ProductsPage(page)
        purchases = PurchasesPage(page)
        report = SupplierOutstandingPage(page)

        raw_mat = generate_random_name("so_raw")

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

            # 2. Create a Credit Purchase (paid_amount=0 on a 500 total = fully outstanding)
            result = purchases.add_purchase(
                supplier=res_supplier,
                branch=res_branch,
                reference_no=generate_random_name("SO_PUR"),
                paid_amount="0",
                purchase_type="Credit",
                products_data=[
                    {
                        "product": raw_mat,
                        "quantity": 5,
                        "price": "100",
                    }
                ],
            )
            assert result.total_amount == Decimal("500")

            # 3. Navigate to Supplier Outstanding report
            data = report.navigate()

            # 4. Search for the supplier
            search_data = report.search(res_supplier)
            party = report.find_party(search_data, res_supplier)

            assert party is not None, (
                f"Supplier '{res_supplier}' not found in Supplier Outstanding after credit purchase"
            )
            assert party["balance_type"] == "Payable", (
                f"Expected balance_type 'Payable', got: {party.get('balance_type')}"
            )
            assert report.amount(party["outstanding_amount"]) > 0, (
                f"Expected outstanding_amount > 0, got: {party.get('outstanding_amount')}"
            )

            # 5. Verify summary reflects outstanding
            summary = search_data.get("summary", {})
            total_outstanding = Decimal(str(summary.get("total_outstanding", 0)))
            assert total_outstanding > 0, (
                f"Total outstanding should be > 0 after credit purchase, got {total_outstanding}"
            )

        finally:
            try:
                prod_page.navigate()
                prod_page.delete_product(raw_mat)
            except Exception as e:
                print(f"Teardown warning (so_raw {raw_mat}): {e}")
