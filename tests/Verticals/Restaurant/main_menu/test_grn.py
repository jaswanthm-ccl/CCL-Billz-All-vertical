"""Restaurant Goods Receipt Note (GRN) and Inventory Impact Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.grn_page import GrnPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.inventories_page import InventoriesPage


@pytest.fixture
def grn_cleanup(res_logged_in_page):
    created_prods = []
    yield {"prods": created_prods}

    page = res_logged_in_page
    prod_page = ProductsPage(page)
    prod_page.navigate()
    for prod_name in list(created_prods):
        try:
            if prod_page.delete_product(prod_name):
                created_prods.remove(prod_name)
        except Exception:
            pass


@pytest.mark.restaurant
def test_restaurant_grn_and_inventory_impact_lifecycle(
    res_logged_in_page, grn_cleanup, res_branch, res_supplier, res_category, res_department, res_unit_type
):
    """Test Purchase Order creation -> GRN Creation -> GRN Approval -> Inventory Update."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    grn_page = GrnPage(page)
    inv_page = InventoriesPage(page)

    raw_name = generate_random_name("auto_grn_raw")
    grn_cleanup["prods"].append(raw_name)

    # 1. Create Raw Material Product
    prod_page.navigate()
    prod_page.add_product(
        name=raw_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        product_type="Raw material",
    )

    # 2. Check Initial Stock
    inv_page.navigate()
    inv_page.filter_by_product_and_branch(product_name=raw_name, branch_name=res_branch)
    initial_stock = inv_page.get_available_stock_number(product_name=raw_name, branch_name=res_branch)

    # 3. Create PO and Open GRN
    po_id = grn_page.create_purchase_order_and_open_grn(
        branch_name=res_branch,
        supplier_name=res_supplier,
        product_name=raw_name,
        quantity="15",
    )
    assert po_id > 0, "Failed to create PO for GRN workflow"

    # 4. Create GRN
    grn_data = grn_page.create_grn(
        purchase_request_id=po_id,
        unit_price="65.00",
        received_quantity="15",
    )
    grn_id = grn_data.get("id")

    # 5. Approve GRN
    approved = grn_page.approve_grn(grn_id=grn_id)
    assert approved, f"GRN #{grn_id} was not approved successfully"

    # 6. Verify Stock Increase in Inventory
    inv_page.navigate()
    inv_page.filter_by_product_and_branch(product_name=raw_name, branch_name=res_branch)
    new_stock = inv_page.get_available_stock_number(product_name=raw_name, branch_name=res_branch)
    assert new_stock >= initial_stock + 15, f"Expected stock >= {initial_stock + 15}, got {new_stock}"
