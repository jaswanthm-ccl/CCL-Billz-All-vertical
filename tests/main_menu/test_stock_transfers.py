import pytest
import random
import string
from pages.main_menu.stock_transfers_page import StockTransfersPage
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.suppliers_page import SuppliersPage
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.brands_page import BrandPage
from pages.master_menu.unit_types_page import UnitTypesPage
from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from utils.random_data import (
    generate_random_name,
    generate_random_email,
    generate_random_phone,
    generate_random_postal_code,
    generate_random_address,
)


def _random_gst():
    pan = (
        "".join(random.choices(string.ascii_uppercase, k=5))
        + "".join(random.choices(string.digits, k=4))
        + random.choice(string.ascii_uppercase)
    )
    return f"33{pan}1Z{random.choice(string.ascii_uppercase + string.digits)}"


# ──────────────────────────────────────────────────────────────────────────────
# Module-scoped fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def module_category(module_page):
    categories_page = CategoriesPage(module_page)
    categories_page.navigate()
    cat_name = generate_random_name("st_cat")
    categories_page.add_category(name=cat_name, description="stock transfer tests")
    categories_page.page.get_by_text("Category created successfully").wait_for(
        state="visible", timeout=5000
    )
    yield cat_name
    try:
        categories_page.navigate()
        if categories_page.search_category(cat_name):
            categories_page.delete_category(cat_name)
    except Exception as e:
        print(f"Teardown: Failed to delete category {cat_name}: {e}")


@pytest.fixture(scope="module")
def module_brand(module_page):
    brand_page = BrandPage(module_page)
    brand_page.navigate()
    brand_name = generate_random_name("st_brand")
    brand_page.add_brand(brand_name, "stock transfer tests")
    yield brand_name
    try:
        brand_page.navigate()
        if brand_page.search_brand(brand_name):
            brand_page.delete_brand(brand_name)
    except Exception as e:
        print(f"Teardown: Failed to delete brand {brand_name}: {e}")


@pytest.fixture(scope="module")
def module_unit_type(module_page):
    unit_page = UnitTypesPage(module_page)
    unit_page.navigate()
    unit_name = generate_random_name("st_unit")
    unit_page.add_unit_type(name=unit_name, unit="pcs", description="stock transfer tests")
    yield unit_name
    try:
        unit_page.navigate()
        if unit_page.search_unit_type(unit_name):
            unit_page.delete_unit_type(unit_name)
    except Exception as e:
        print(f"Teardown: Failed to delete unit type {unit_name}: {e}")


@pytest.fixture(scope="module")
def module_hsn_code(module_page):
    sac_page = SacHsnCodePage(module_page)
    sac_page.navigate()
    sac_code = str(random.randint(100000, 999999))
    sac_page.add_sac_hsn_code("SAC", sac_code, description="stock transfer tests")
    yield sac_code
    try:
        sac_page.navigate()
        if sac_page.search_sac_hsn_code(sac_code):
            sac_page.delete_sac_hsn_code(sac_code)
    except Exception as e:
        print(f"Teardown: Failed to delete HSN {sac_code}: {e}")


@pytest.fixture(scope="module")
def module_city(module_page):
    cities_page = CitiesPage(module_page)
    cities_page.navigate()
    city_name = generate_random_name("st_city")
    cities_page.add_city(city_name)
    yield city_name
    try:
        cities_page.navigate()
        if cities_page.search_city(city_name):
            cities_page.delete_city(city_name)
    except Exception as e:
        print(f"Teardown: Failed to delete city {city_name}: {e}")


@pytest.fixture(scope="module")
def module_source_branch(module_page ):
    """Source branch — stock will be transferred FROM here."""
    branches_page = BranchesPage(module_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch(name=generate_random_name("st_src_br"))
    branches_page.page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    yield branch_name
    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete source branch {branch_name}: {e}")


@pytest.fixture(scope="module")
def module_destination_branch(module_page):
    """Destination branch — stock will be transferred TO here."""
    branches_page = BranchesPage(module_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch(name=generate_random_name("st_dst_br"))
    branches_page.page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    yield branch_name
    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete destination branch {branch_name}: {e}")


@pytest.fixture(scope="module")
def module_supplier(module_page, module_city):
    suppliers_page = SuppliersPage(module_page)
    suppliers_page.navigate()
    supplier_name = generate_random_name("st_supp")
    suppliers_page.add_supplier(
        name=supplier_name,
        contact_person="Contact Auto",
        email=generate_random_email("stsupp"),
        phone=generate_random_phone(),
        gst_number=_random_gst(),
        state_name="Tamil Nadu",
        city_name=module_city,
        postal_code=generate_random_postal_code(),
        address=generate_random_address(),
    )
    yield supplier_name
    try:
        suppliers_page.navigate()
        if suppliers_page.search_supplier(supplier_name):
            suppliers_page.delete_supplier(supplier_name)
    except Exception as e:
        print(f"Teardown: Failed to delete supplier {supplier_name}: {e}")


@pytest.fixture(scope="module")
def module_product(
    module_page,
    module_category,
    module_brand,
    module_unit_type,
    module_hsn_code,
    module_source_branch,
    module_supplier,
):
    """Create product and purchase 50 units into the source branch (so we have stock to transfer)."""
    products_page = ProductsPage(module_page)
    purchases_page = PurchasesPage(module_page)

    # Create the product
    products_page.navigate()
    product_name = generate_random_name("st_prod")
    products_page.add_product(
        name=product_name,
        brand_name=module_brand,
        category_name=module_category,
        hsn_code=module_hsn_code,
        unit_type=module_unit_type,
        cost_price="100",
        selling_price="200",
        gst_percentage="18%",
    )

    # Purchase 50 units into the source branch (creates stock)
    purchases_page.navigate()
    ref_no = "st_ref_" + str(random.randint(100000, 999999))
    purchases_page.add_purchase(
        supplier=module_supplier,
        branch=module_source_branch,
        reference_no=ref_no,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[
            {"product": product_name, "quantity": 50, "price": "100"}
        ],
    )

    yield product_name
    try:
        products_page.navigate()
        if products_page.search_product(product_name):
            products_page.delete_product(product_name)
    except Exception as e:
        print(f"Teardown: Failed to delete product {product_name}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Tests — each function is independent
# ──────────────────────────────────────────────────────────────────────────────


def test_stock_transfers_page_loads(logged_in_page):
    """Verify the stock transfers page loads with title and add button."""
    st_page = StockTransfersPage(logged_in_page)
    st_page.navigate()
    assert st_page.is_stock_transfers_visible(), (
        "Stock transfers page did not load correctly"
    )


def test_add_stock_transfer(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """Create a stock transfer of 5 units and verify it appears in the list."""
    st_page = StockTransfersPage(logged_in_page)

    transfer_no = st_page.add_stock_transfer(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        products_data=[{"product": module_product, "quantity": 5}],
        remarks="Automated test transfer",
    )

    # Navigate to list and verify the transfer exists
    st_page.navigate()
    # Search by source branch name (transfer_no may be None if we couldn't extract it)
    assert st_page.is_transfer_in_table(module_source_branch), (
        "Stock transfer not found in list after creation"
    )


def test_search_stock_transfer(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """Create a transfer, find its number via branch filter, then search by that number."""
    st_page = StockTransfersPage(logged_in_page)

    # 1. Create a stock transfer
    st_page.add_stock_transfer(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        products_data=[{"product": module_product, "quantity": 2}],
        remarks="search_test_transfer",
    )

    # 2. Filter by our unique source branch → only our transfers show up
    st_page.navigate()
    st_page.filter_by_source_branch(module_source_branch)

    # 3. Grab the transfer number from the first (most recent) row
    transfer_no = st_page.get_first_transfer_no()
    assert transfer_no.startswith("TRF-"), f"Unexpected transfer number: {transfer_no}"

    # 4. Clear the filter so we're back to full list
    st_page.clear_filters()

    # 5. Search by that transfer number
    assert st_page.search_stock_transfer(transfer_no), (
        f"Stock transfer '{transfer_no}' not found via search"
    )


def test_view_stock_transfer_detail(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """Create a transfer, find its number via filter, search it, then view and verify details."""
    st_page = StockTransfersPage(logged_in_page)

    # 1. Create a stock transfer
    st_page.add_stock_transfer(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        products_data=[{"product": module_product, "quantity": 3}],
        remarks="view_detail_test",
    )

    # 2. Filter by our source branch to isolate our transfer
    st_page.navigate()
    st_page.filter_by_source_branch(module_source_branch)

    # 3. Get the transfer number
    transfer_no = st_page.get_first_transfer_no()

    # 4. Clear filter, search by transfer number, and view it
    st_page.clear_filters()
    assert st_page.search_stock_transfer(transfer_no), (
        f"Transfer '{transfer_no}' not found in search"
    )

    assert st_page.view_stock_transfer(transfer_no), (
        "Stock transfer detail page did not load"
    )

    # 5. Verify detail content
    assert st_page.is_product_in_detail_items(module_product), (
        f"Product '{module_product}' not found in transfer line items"
    )


def test_stock_decreases_in_source_branch_after_transfer(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """After a stock transfer, source branch inventory should decrease."""
    inventories_page = InventoriesPage(logged_in_page)
    st_page = StockTransfersPage(logged_in_page)

    # Get stock in source branch before transfer
    inventories_page.navigate()
    inventories_page.filter_by_branch(module_source_branch)
    stock_before = inventories_page.get_available_stock_number(module_product)
    inventories_page.clear_filters()

    # Transfer 4 units out of source branch
    st_page.add_stock_transfer(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        products_data=[{"product": module_product, "quantity": 4}],
    )

    # Verify source branch stock decreased
    inventories_page.navigate()
    inventories_page.filter_by_branch(module_source_branch)
    stock_after = inventories_page.get_available_stock_number(module_product)

    assert stock_after == stock_before - 4, (
        f"Source branch stock: expected {stock_before - 4}, got {stock_after}"
    )


def test_stock_increases_in_destination_branch_after_transfer(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """After a stock transfer, destination branch inventory should increase."""
    inventories_page = InventoriesPage(logged_in_page)
    st_page = StockTransfersPage(logged_in_page)

    # Get stock in destination branch before transfer
    inventories_page.navigate()
    inventories_page.filter_by_branch(module_destination_branch)
    stock_before = inventories_page.get_available_stock_number(module_product)
    inventories_page.clear_filters()

    # Transfer 3 units into destination branch
    st_page.add_stock_transfer(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        products_data=[{"product": module_product, "quantity": 3}],
    )

    # Verify destination branch stock increased
    inventories_page.navigate()
    inventories_page.filter_by_branch(module_destination_branch)
    stock_after = inventories_page.get_available_stock_number(module_product)

    assert stock_after == stock_before + 3, (
        f"Destination branch stock: expected {stock_before + 3}, got {stock_after}"
    )


def test_filter_by_source_branch(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """Filter stock transfers by source branch and verify results."""
    st_page = StockTransfersPage(logged_in_page)

    # Ensure at least one transfer exists
    st_page.add_stock_transfer(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        products_data=[{"product": module_product, "quantity": 1}],
    )

    st_page.navigate()
    st_page.filter_by_source_branch(module_source_branch)

    assert st_page.is_transfer_in_table(module_source_branch), (
        "No transfers found when filtering by source branch"
    )


def test_filter_by_destination_branch(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """Filter stock transfers by destination branch and verify results."""
    st_page = StockTransfersPage(logged_in_page)

    # Ensure at least one transfer exists
    st_page.add_stock_transfer(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        products_data=[{"product": module_product, "quantity": 1}],
    )

    st_page.navigate()
    st_page.filter_by_destination_branch(module_destination_branch)

    assert st_page.is_transfer_in_table(module_destination_branch), (
        "No transfers found when filtering by destination branch"
    )


def test_validation_same_branch_rejected(
    logged_in_page, module_product, module_source_branch
):
    """Verify that source and destination cannot be the same branch."""
    st_page = StockTransfersPage(logged_in_page)
    assert st_page.attempt_transfer_same_branch(
        branch_name=module_source_branch,
        product_name=module_product,
    ), "Same branch as source and destination should be rejected"


def test_validation_quantity_exceeds_stock(
    logged_in_page, module_product, module_source_branch, module_destination_branch
):
    """Verify that quantity exceeding available stock is rejected."""
    st_page = StockTransfersPage(logged_in_page)
    assert st_page.attempt_transfer_exceeding_stock(
        source_branch=module_source_branch,
        destination_branch=module_destination_branch,
        product_name=module_product,
        quantity=99999,  # Way more than available
    ), "Transfer quantity exceeding available stock should be rejected"
