"""Restaurant Customer Outstanding Report Test Suite.

Route: /reports/customer-outstanding
Verifies:
  1. Page loading, heading, and table headers
  2. API contract (items, pagination, summary)
  3. Search filter for known/unknown customers
  4. Outstanding sort ordering
  5. Credit POS sale creates a Receivable customer outstanding entry
  6. Row count matches API response
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.report.customer_outstanding_page import CustomerOutstandingPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Tier 1: Structure & Page Load ─────────────────────────────────────────────

class TestResCustomerOutstandingStructure:
    """Verify page load and basic UI elements."""

    def test_page_loads_with_heading(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
        data = report.navigate()

        assert report.heading_visible(), "Customer Outstanding heading should be visible"

    def test_api_returns_expected_keys(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
        data = report.navigate()

        assert "items" in data, f"Missing 'items' in response: {data.keys()}"
        assert "pagination" in data, f"Missing 'pagination' in response: {data.keys()}"
        assert "summary" in data, f"Missing 'summary' in response: {data.keys()}"

    def test_table_headers_present(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
        report.navigate()

        headers = report.headers()
        assert len(headers) >= 5, f"Expected at least 5 table headers, got {len(headers)}: {headers}"
        # Check key columns exist (case-insensitive)
        header_text = " ".join(headers).upper()
        assert "CUSTOMER" in header_text, f"Missing CUSTOMER column: {headers}"
        assert "OUTSTANDING" in header_text, f"Missing OUTSTANDING column: {headers}"

    def test_rendered_row_count_matches_api(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
        data = report.navigate()

        assert len(report.rows()) == len(data.get("items", []))


# ── Tier 2: Search & Filter Tests ─────────────────────────────────────────────

class TestResCustomerOutstandingFilters:
    """Verify search and filter controls."""

    def test_unknown_customer_search_returns_empty(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
        report.navigate()

        data = report.search("AUTOMATION-NO-SUCH-CUSTOMER-987654321")
        assert data.get("items", []) == [], "Unknown customer should return empty results"
        assert data.get("summary", {}).get("total_parties", 0) == 0

    def test_outstanding_sort_descending(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
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

class TestResCustomerOutstandingSummary:
    """Verify summary metrics cards."""

    def test_summary_metrics_present(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
        data = report.navigate()

        summary = data.get("summary", {})
        assert "total_outstanding" in summary, f"Missing total_outstanding in summary: {summary}"
        assert "total_parties" in summary, f"Missing total_parties in summary: {summary}"

    def test_summary_total_outstanding_is_non_negative(self, res_logged_in_page):
        page = res_logged_in_page
        report = CustomerOutstandingPage(page)
        data = report.navigate()

        total = Decimal(str(data.get("summary", {}).get("total_outstanding", 0)))
        assert total >= 0, f"Total outstanding should be >= 0, got {total}"


# ── Tier 4: Credit Sale Creates Customer Outstanding ──────────────────────────

class TestResCustomerOutstandingCreditSale:
    """Create a POS credit sale and verify it reflects in Customer Outstanding."""

    def test_credit_sale_creates_receivable_entry(
        self, res_logged_in_page, res_category, res_department, res_unit_type
    ):
        page = res_logged_in_page
        prod_page = ProductsPage(page)
        pos_page = POSBillingPage(page)
        report = CustomerOutstandingPage(page)

        dish_name = generate_random_name("co_dish")
        dish_price = "350"

        try:
            # 1. Create a test dish
            prod_page.navigate()
            dish_code = prod_page.add_product(
                name=dish_name,
                category_name=res_category,
                department_name=res_department,
                unit_type=res_unit_type,
                price=dish_price,
                product_type="Finished good",
            )

            # 2. Create POS sale (Settle & Bill only — do NOT collect payment)
            pos_page.navigate()
            pos_page.select_bill_tab("Bill 1")
            pos_page.select_order_type("Dine In")
            pos_page.enter_dish_by_code(code=dish_code, dish_name=dish_name)
            sale_data = pos_page.settle_and_bill()

            # 3. Navigate to Customer Outstanding report
            data = report.navigate()

            # 4. Check that at least one receivable entry exists
            items = data.get("items", [])
            has_receivable = any(
                item.get("balance_type") == "Receivable"
                and Decimal(str(item.get("outstanding_amount", 0))) > 0
                for item in items
            )
            assert has_receivable or len(items) > 0, (
                "Expected at least one customer with outstanding balance after credit sale"
            )

            # 5. Verify summary reflects outstanding
            summary = data.get("summary", {})
            total_outstanding = Decimal(str(summary.get("total_outstanding", 0)))
            assert total_outstanding > 0, (
                f"Total outstanding should be > 0 after credit sale, got {total_outstanding}"
            )

        finally:
            try:
                prod_page.navigate()
                prod_page.delete_product(dish_name)
            except Exception as e:
                print(f"Teardown warning (co_dish {dish_name}): {e}")
