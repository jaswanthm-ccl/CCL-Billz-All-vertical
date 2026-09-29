"""Restaurant Outstanding Bills Report Test Suite.

Route: /vouchers/outstanding
Verifies:
  1. Page loads and defaults to Sales outstanding view
  2. Credit Sale (POS settle without collecting payment) appears in Sales outstanding
  3. Switching filter to Purchases shows Purchase outstanding bills
  4. Credit Purchase (partial payment) appears in Purchases outstanding
  5. Filter controls (type, status) work correctly
  6. Bill amount reconciliation: Total == Settled + Outstanding
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.report.outstanding_bills_page import OutstandingBillsPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.restaurant


# ── Tier 1: Structure & Default State ─────────────────────────────────────────

class TestResOutstandingBillsStructure:
    """Verify page load, heading, and default filter state."""

    def test_outstanding_bills_page_loads(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        data = report.navigate("sales")

        assert report.heading_visible(), "Outstanding Bills heading should be visible"
        assert "items" in data and "pagination" in data, f"Unexpected response shape: {data.keys()}"

    def test_sales_is_default_bill_type(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        report.navigate("sales")

        assert report.selected_type() == "sales", "Default bill type should be 'sales'"

    def test_table_headers_match_sales_schema(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        report.navigate("sales")

        headers = report.headers()
        assert "Invoice No." in headers or "Invoice" in headers, f"Missing Invoice column: {headers}"
        assert any(h in headers for h in ("Customer", "Party")), f"Missing Customer column: {headers}"
        assert "Outstanding" in headers, f"Missing Outstanding column: {headers}"


# ── Tier 2: Filter Controls ──────────────────────────────────────────────────

class TestResOutstandingBillsFilters:
    """Verify type and status filter switching."""

    def test_switch_to_purchases_type(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        report.navigate("sales")
        data = report.set_type("purchases")

        assert report.selected_type() == "purchases", "Type filter should switch to purchases"
        headers = report.headers()
        assert any(h in headers for h in ("Supplier", "Party")), f"Missing Supplier column: {headers}"

    def test_pending_status_filter(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        report.navigate("sales")
        data = report.set_status("pending")

        assert report.selected_status() == "pending"
        for item in data.get("items", []):
            assert item["payment_status"] == "pending", f"Non-pending item found: {item}"

    def test_switch_to_purchases_via_navigate(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        data = report.navigate("purchases")

        assert report.selected_type() == "purchases"
        for item in data.get("items", []):
            assert item.get("type") == "purchase", f"Non-purchase item found: {item}"


# ── Tier 3: Bill Amount Reconciliation ────────────────────────────────────────

class TestResOutstandingBillsReconciliation:
    """Verify financial integrity of outstanding bill amounts."""

    def test_each_bill_total_equals_settled_plus_outstanding(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        data = report.navigate("sales")

        items = data.get("items", [])
        if not items:
            pytest.skip("No outstanding sales bills in test environment")

        for item in items:
            total = report.amount(item["invoice_amount"])
            settled = report.amount(item["settled_amount"])
            outstanding = report.amount(item["outstanding_amount"])
            assert total == settled + outstanding, (
                f"Reconciliation failed: {total} != {settled} + {outstanding} for {item}"
            )

    def test_all_outstanding_amounts_are_positive(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        data = report.navigate("sales")

        items = data.get("items", [])
        if not items:
            pytest.skip("No outstanding sales bills in test environment")

        for item in items:
            assert report.amount(item["outstanding_amount"]) > 0, (
                f"Zero/negative outstanding found: {item}"
            )

    def test_rendered_row_count_matches_api(self, res_logged_in_page):
        page = res_logged_in_page
        report = OutstandingBillsPage(page)
        data = report.navigate("sales")

        assert len(report.rows()) == len(data.get("items", []))


# ── Tier 4: Credit Sale Creates Outstanding Bill ──────────────────────────────

class TestResOutstandingBillsCreditSale:
    """Create a POS sale without collecting payment and verify it appears as outstanding."""

    def test_credit_sale_appears_in_outstanding(
        self, res_logged_in_page, res_category, res_department, res_unit_type
    ):
        page = res_logged_in_page
        prod_page = ProductsPage(page)
        pos_page = POSBillingPage(page)
        report = OutstandingBillsPage(page)

        dish_name = generate_random_name("ob_dish")
        dish_price = "250"

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
            invoice_no = str(sale_data.get("invoice_no", "") or sale_data.get("id", ""))

            # 3. Navigate to Outstanding Bills (sales view)
            data = report.navigate("sales")

            # 4. Verify our unpaid sale appears
            bill = report.find_bill(data, party_name="Walk")
            if bill is None:
                # Try searching by invoice number
                search_data = report.search(invoice_no, "sales")
                bill = report.find_bill(search_data, party_name="Walk")

            assert bill is not None, (
                f"Credit sale (invoice {invoice_no}) not found in Outstanding Bills"
            )
            assert bill["payment_status"] in ("pending", "partial"), (
                f"Expected pending/partial status, got: {bill['payment_status']}"
            )
            assert report.amount(bill["outstanding_amount"]) > 0, (
                f"Outstanding amount should be > 0, got: {bill['outstanding_amount']}"
            )

        finally:
            try:
                prod_page.navigate()
                prod_page.delete_product(dish_name)
            except Exception as e:
                print(f"Teardown warning (ob_dish {dish_name}): {e}")


# ── Tier 5: Credit Purchase Creates Outstanding Bill ──────────────────────────

class TestResOutstandingBillsCreditPurchase:
    """Create a purchase with partial payment and verify it appears in purchases outstanding."""

    def test_credit_purchase_appears_in_outstanding(
        self, res_logged_in_page, res_branch, res_supplier,
        res_category, res_department, res_unit_type
    ):
        page = res_logged_in_page
        prod_page = ProductsPage(page)
        purchases = PurchasesPage(page)
        report = OutstandingBillsPage(page)

        raw_mat = generate_random_name("ob_raw")

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
                reference_no=generate_random_name("OB_PUR"),
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

            assert result.total_amount == Decimal("500"), (
                f"Expected purchase total 500, got {result.total_amount}"
            )

            # 3. Navigate to Outstanding Bills → switch to Purchases view (load up to 100 rows)
            data = report.load_all("purchases")

            # 4. Verify our unpaid purchase appears
            bill = report.find_bill(data, party_name=res_supplier)
            if bill is None:
                search_data = report.search(res_supplier, "purchases")
                bill = report.find_bill(search_data, party_name=res_supplier)
            if bill is None and result.reference_no:
                search_data = report.search(result.reference_no, "purchases")
                bill = report.find_bill(search_data, party_name=res_supplier)

            assert bill is not None, (
                f"Credit purchase for supplier '{res_supplier}' not found in Outstanding Bills"
            )
            assert bill["payment_status"] in ("pending", "partial"), (
                f"Expected pending/partial status, got: {bill['payment_status']}"
            )
            assert report.amount(bill["outstanding_amount"]) > 0, (
                f"Outstanding amount should be > 0, got: {bill['outstanding_amount']}"
            )
        finally:
            try:
                prod_page.navigate()
                prod_page.delete_product(raw_mat)
            except Exception as e:
                print(f"Teardown warning (ob_raw {raw_mat}): {e}")
