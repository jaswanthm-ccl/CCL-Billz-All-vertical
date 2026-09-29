"""Restaurant Procurement, Inventory & Indent Lifecycle End-to-End Regression Flow.

Path:
1. Setup isolated Supplier and Raw Material product.
2. Baseline inventory snapshot (S_0).
3. Procure 20 units on 100% credit (Paid ₹0) -> Stock +20, Supplier Debt = ₹2,000.
4. Verify inventory increase (S_1 = S_0 + 20).
5. Verify Supplier Debt reflects in Supplier Outstanding report.
6. Create & approve Indent for 5 units (kitchen raw material usage).
7. Verify stock usage decrement (S_2 = S_1 - 5).
8. Process Purchase Return of 3 units back to supplier.
9. Verify Return record in Purchase Returns history.
10. Strict Enterprise Stock Invariant: Final stock matches exactly S_0 + 20 - 5 - 3 = 12.
11. Verify adjusted supplier debt in Supplier Outstanding (₹2,000 - ₹300 = ₹1,700).
"""

from decimal import Decimal
import pytest

from pages.Verticals.Restaurant.main_menu.inventories_page import InventoriesPage
from pages.Verticals.Restaurant.main_menu.indents_page import IndentsPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchase_returns_page import PurchaseReturnsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from pages.Verticals.Restaurant.main_menu.suppliers_page import SuppliersPage
from pages.Verticals.Restaurant.report.supplier_outstanding_page import SupplierOutstandingPage
from utils.random_data import generate_random_name, generate_random_phone, generate_random_address


pytestmark = [pytest.mark.restaurant, pytest.mark.regression]


def test_procurement_inventory_and_indent_lifecycle_flow(
    res_logged_in_page,
    res_branch,
    res_department,
    res_category,
    res_unit_type,
    res_regression_cleanup,
):
    """Complete 360° Restaurant Procurement, Stock Invariant, Indent & Return Lifecycle."""
    page = res_logged_in_page
    cleanup = res_regression_cleanup

    # Page Objects
    products_page = ProductsPage(page)
    suppliers_page = SuppliersPage(page)
    purchases_page = PurchasesPage(page)
    inventories_page = InventoriesPage(page)
    indents_page = IndentsPage(page)
    returns_page = PurchaseReturnsPage(page)
    supplier_outstanding_page = SupplierOutstandingPage(page)

    # ── Step 1: Setup Isolated Test Entities ──────────────────────────────────
    supplier_name = generate_random_name("regr_sup")
    raw_material_name = generate_random_name("regr_raw")
    purchase_reference = generate_random_name("PUR_REGR")

    # Create Supplier
    suppliers_page.navigate()
    assert suppliers_page.add_supplier(
        name=supplier_name,
        phone=generate_random_phone(),
        address=generate_random_address(),
    ), f"Failed to create supplier {supplier_name}"
    cleanup["suppliers"].append(supplier_name)

    # Create Raw Material Product
    products_page.navigate()
    raw_code = products_page.add_product(
        name=raw_material_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="100",
        product_type="Raw material",
    )
    assert raw_code, f"Failed to create raw material product {raw_material_name}"
    cleanup["products"].append(raw_material_name)

    # ── Step 2: Baseline Inventory Snapshot (S_0) ────────────────────────────
    inventories_page.navigate()
    inventories_page.search_inventory(raw_material_name)
    initial_stock = inventories_page.get_available_stock_number(
        raw_material_name, res_branch
    )
    assert initial_stock == Decimal("0"), f"Expected initial stock 0, got {initial_stock}"

    # ── Step 3: Procure 20 units on 100% Credit (Paid ₹0) ───────────────────
    purchase_qty = 20
    unit_cost = 100
    total_purchase_amount = Decimal(str(purchase_qty * unit_cost))  # ₹2,000.00

    purchases_page.navigate()
    purchase_result = purchases_page.add_purchase(
        supplier=supplier_name,
        branch=res_branch,
        reference_no=purchase_reference,
        paid_amount="0",
        purchase_type="Credit",
        products_data=[
            {
                "product": raw_material_name,
                "quantity": purchase_qty,
                "price": str(unit_cost),
            }
        ],
    )
    assert purchase_result.total_amount == total_purchase_amount, (
        f"Purchase total mismatch: expected {total_purchase_amount}, got {purchase_result.total_amount}"
    )

    # ── Step 4: Verify Inventory Increase (S_1 = S_0 + 20) ───────────────────
    inventories_page.navigate()
    assert inventories_page.search_inventory(raw_material_name)
    stock_after_purchase = inventories_page.get_available_stock_number(
        raw_material_name, res_branch
    )
    expected_stock_1 = initial_stock + Decimal(str(purchase_qty))
    assert stock_after_purchase == expected_stock_1, (
        f"Inventory post-purchase mismatch: expected {expected_stock_1}, got {stock_after_purchase}"
    )

    # ── Step 5: Verify Supplier Debt in Supplier Outstanding Report ──────────
    supplier_outstanding_page.navigate()
    supplier_debt = supplier_outstanding_page.get_party_outstanding_amount(
        supplier_name
    )
    assert supplier_debt == total_purchase_amount, (
        f"Supplier outstanding should be ₹{total_purchase_amount:.2f}, "
        f"got ₹{supplier_debt:.2f}"
    )

    # ── Step 6: Create & Approve Indent for 5 units (Kitchen Usage) ───────────
    indent_qty = 5
    indents_page.navigate()
    indent_id = indents_page.create_indent(
        branch_name=res_branch,
        department_name=res_department,
        mode="Manual",
        items=[{"name": raw_material_name, "quantity": str(indent_qty)}],
        approve_immediately=True,
    )
    assert indent_id, "Failed to create & approve indent"
    cleanup["indents"].append(indent_id)

    assert indents_page.search_indent(indent_id)
    indent_status = indents_page.get_indent_status(indent_id)
    assert "approved" in indent_status.lower(), (
        f"Expected approved status for indent {indent_id}, got '{indent_status}'"
    )

    # ── Step 7: Verify Stock Decrement after Indent Approval (S_2 = S_1 - 5) ─
    inventories_page.navigate()
    assert inventories_page.search_inventory(raw_material_name)
    stock_after_indent = inventories_page.get_available_stock_number(
        raw_material_name, res_branch
    )
    expected_stock_2 = stock_after_purchase - Decimal(str(indent_qty))
    assert stock_after_indent == expected_stock_2, (
        f"Stock post-indent mismatch: expected {expected_stock_2}, got {stock_after_indent}"
    )

    # ── Step 8: Process Purchase Return of 3 units back to Supplier ───────────
    return_qty = 3
    purchases_page.navigate()
    purchases_page.initiate_return(purchase_reference)
    return_data = returns_page.perform_return(quantity=str(return_qty))
    assert return_data, "Purchase Return submission returned no data"

    # ── Step 9: Verify Return Details in Purchase Returns History ─────────────
    returns_page.filter_returns(
        branch_name=res_branch,
        supplier_name=supplier_name,
    )
    return_amount_str = f"{return_qty * unit_cost:.2f}"
    assert returns_page.verify_return_details(
        product_name=raw_material_name,
        supplier_name=supplier_name,
        branch_name=res_branch,
        quantity=str(return_qty),
        price=str(unit_cost),
        total_amount=return_amount_str,
    )

    # ── Step 10: Strict Enterprise Stock Invariant ───────────────────────────
    # Invariant: S_final == S_0 + 20 - 5 - 3 = 12
    inventories_page.navigate()
    assert inventories_page.search_inventory(raw_material_name)
    final_stock = inventories_page.get_available_stock_number(
        raw_material_name, res_branch
    )
    expected_final_stock = stock_after_indent - Decimal(str(return_qty))  # 15 - 3 = 12
    assert final_stock == expected_final_stock, (
        f"Final inventory invariant broken! Expected {expected_final_stock}, got {final_stock}"
    )

    # ── Step 11: Verify Adjusted Supplier Debt in Supplier Outstanding ────────
    # Expected remaining debt = 2,000 - 300 = 1,700
    expected_debt = total_purchase_amount - Decimal(str(return_qty * unit_cost))
    supplier_outstanding_page.navigate()
    adjusted_debt = supplier_outstanding_page.get_party_outstanding_amount(
        supplier_name
    )
    assert adjusted_debt == expected_debt, (
        f"Supplier outstanding should be ₹{expected_debt:.2f} after the return, "
        f"got ₹{adjusted_debt:.2f}"
    )
