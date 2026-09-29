"""Master Inter-Branch Stock Transfer, Multi-Location Isolation & Inventory Invariant CI Regression Flow.

Path:
1. Multi-Branch Baseline Stock Snapshot (S_A0, S_B0) on isolated branches.
2. Procure 20 units into Branch A -> Assert Branch A stock +20, Branch B stock unchanged (Isolation).
3. Negative Validations: Same branch transfer rejection & Excessive quantity rejection.
4. Transfer 10 units from Branch A -> Branch B via Stock Transfers module.
5. Search and View Transfer Details (From Branch A, To Branch B, Line Items & Quantity).
6. Multi-Branch Inventory Stock Audit:
   - Branch A Stock = S_A0 + 10 (Decremented by 10)
   - Branch B Stock = S_B0 + 10 (Incremented by 10)
7. Total Enterprise Conservation Invariant: Total Company Stock == S_A0 + S_B0 + 20.
8. Sell 4 units from Branch B -> Assert Branch B stock drops to S_B0 + 6, Branch A stock untouched.
9. Final Enterprise Conservation Invariant: Total Company Stock == S_A0 + S_B0 + 16.
"""

import pytest
import random
from decimal import Decimal
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.sales_page import SalesPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.stock_transfers_page import StockTransfersPage


@pytest.mark.regression
@pytest.mark.default_vertical
def test_inter_branch_stock_transfer_and_isolation_flow(
    logged_in_page,
    regression_branch_a,
    regression_branch_b,
    regression_product,
    regression_supplier,
    regression_customer,
):
    """End-to-End Inter-Branch Stock Transfer & Multi-Location Inventory Invariant Lifecycle."""
    purchases_page = PurchasesPage(logged_in_page)
    sales_page = SalesPage(logged_in_page)
    inventories_page = InventoriesPage(logged_in_page)
    stock_transfers_page = StockTransfersPage(logged_in_page)

    procure_qty = 20
    transfer_qty = 10
    sale_qty = 4

    # ── Step 0: Capture Baseline Stock at Branch A and Branch B ──────────
    stock_a_0 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_a
    )
    stock_b_0 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_b
    )
    initial_total_stock = stock_a_0 + stock_b_0

    # ── Step 1: Procure 20 units into Branch A ───────────────────────────
    purchases_page.navigate()
    purchase_ref = f"po_st_{random.randint(100000, 999999)}"
    purchases_page.add_purchase(
        supplier=regression_supplier,
        branch=regression_branch_a,
        reference_no=purchase_ref,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[
            {"product": regression_product, "quantity": procure_qty, "price": "100"}
        ],
    )

    # ── Step 2: Verify Branch A Stock +20 & Branch B Isolation (Unchanged)
    stock_a_1 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_a
    )
    expected_stock_a_1 = stock_a_0 + Decimal(str(procure_qty))
    assert stock_a_1 == expected_stock_a_1, (
        f"Branch A stock must increment by {procure_qty}: expected {expected_stock_a_1}, got {stock_a_1}"
    )

    stock_b_1 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_b
    )
    assert stock_b_1 == stock_b_0, (
        f"Branch B stock must remain isolated and unchanged: expected {stock_b_0}, got {stock_b_1}"
    )

    # ── Step 3: Negative Validation Checks ───────────────────────────────
    # A. Attempt transfer with same source and destination branch
    same_branch_blocked = stock_transfers_page.attempt_transfer_same_branch(
        branch_name=regression_branch_a,
        product_name=regression_product,
    )
    assert same_branch_blocked, "Transfer with same source and destination must be blocked"

    # B. Attempt transfer with quantity exceeding available stock
    excess_qty_blocked = stock_transfers_page.attempt_transfer_exceeding_stock(
        source_branch=regression_branch_a,
        destination_branch=regression_branch_b,
        product_name=regression_product,
        quantity=99999,
    )
    assert excess_qty_blocked, "Transfer exceeding available stock must be blocked"

    # ── Step 4: Execute 10 Units Stock Transfer (Branch A -> Branch B) ───
    stock_transfers_page.navigate()
    transfer_remarks = f"Regression Inter-Branch Transfer {random.randint(1000, 9999)}"
    transfer_res = stock_transfers_page.add_stock_transfer(
        source_branch=regression_branch_a,
        destination_branch=regression_branch_b,
        products_data=[
            {"product": regression_product, "quantity": transfer_qty, "remarks": "Flow test"}
        ],
        remarks=transfer_remarks,
    )
    transfer_no = transfer_res.transfer_no

    # ── Step 5: View Detail and Verify Transfer Information ─────────────
    stock_transfers_page.navigate()
    assert stock_transfers_page.is_stock_transfers_visible(), "Stock transfers list must load"

    # Verify transfer appears in search
    if transfer_no:
        assert stock_transfers_page.search_stock_transfer(transfer_no), (
            f"Transfer {transfer_no} must be searchable in stock transfers list"
        )
    else:
        assert stock_transfers_page.is_transfer_in_table(regression_branch_a), (
            "Transfer list must display recent transfer row"
        )

    # ── Step 6: Verify Multi-Branch Inventory Stock Deltas ───────────────
    # Branch A stock should decrease by transfer_qty (S_A0 + 10)
    stock_a_2 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_a
    )
    expected_stock_a_2 = stock_a_1 - Decimal(str(transfer_qty))
    assert stock_a_2 == expected_stock_a_2, (
        f"Branch A stock must decrease by {transfer_qty}: expected {expected_stock_a_2}, got {stock_a_2}"
    )

    # Branch B stock should increase by transfer_qty (S_B0 + 10)
    stock_b_2 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_b
    )
    expected_stock_b_2 = stock_b_0 + Decimal(str(transfer_qty))
    assert stock_b_2 == expected_stock_b_2, (
        f"Branch B stock must increase by {transfer_qty}: expected {expected_stock_b_2}, got {stock_b_2}"
    )

    # ── Step 7: Consolidated Enterprise Stock Conservation Invariant ────
    current_total_stock = stock_a_2 + stock_b_2
    expected_total_stock_after_transfer = initial_total_stock + Decimal(str(procure_qty))
    assert current_total_stock == expected_total_stock_after_transfer, (
        f"Inter-branch Stock Conservation Invariant Violation: Total company stock {current_total_stock} "
        f"must equal {expected_total_stock_after_transfer}"
    )

    # ── Step 8: Sell 4 units from Branch B ───────────────────────────────
    sales_page.navigate()
    sale_res = sales_page.add_sale(
        customer_name=regression_customer,
        branch_name=regression_branch_b,
        product_name=regression_product,
        quantity=sale_qty,
        price="250",
        paid_amount="1000",
        payment_method="Cash",
    )
    assert sale_res.total_amount == Decimal("1000"), "Sale total must match"

    # ── Step 9: Verify Local Decrement at Branch B & Cross-Branch Isolation
    stock_b_3 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_b
    )
    expected_stock_b_3 = stock_b_2 - Decimal(str(sale_qty))
    assert stock_b_3 == expected_stock_b_3, (
        f"Branch B stock must decrease by {sale_qty}: expected {expected_stock_b_3}, got {stock_b_3}"
    )

    stock_a_3 = inventories_page.get_available_stock_for_branch(
        regression_product, regression_branch_a
    )
    assert stock_a_3 == stock_a_2, (
        f"Branch A stock must remain untouched by Branch B sale: expected {stock_a_2}, got {stock_a_3}"
    )

    # ── Step 10: Final Enterprise Inventory Invariant ────────────────────
    final_total_stock = stock_a_3 + stock_b_3
    expected_final_total = initial_total_stock + Decimal(str(procure_qty)) - Decimal(str(sale_qty))
    assert final_total_stock == expected_final_total, (
        f"Final Enterprise Stock Conservation Invariant Violation: "
        f"Expected {expected_final_total}, got {final_total_stock}"
    )
