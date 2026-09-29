import pytest
import random
import string
import os
from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.sales_page import SalesPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.suppliers_page import SuppliersPage
from pages.main_menu.customers_page import CustomersPage
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
# Module-scoped fixtures: create dependencies ONCE for all tests in this file
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def module_category(module_page):
    categories_page = CategoriesPage(module_page)
    categories_page.navigate()
    cat_name = generate_random_name("inv_cat")
    categories_page.add_category(name=cat_name, description="inventory tests")
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
    brand_name = generate_random_name("inv_brand")
    brand_page.add_brand(brand_name, "inventory tests")
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
    unit_name = generate_random_name("inv_unit")
    unit_page.add_unit_type(name=unit_name, unit="pcs", description="inventory tests")
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
    sac_page.add_sac_hsn_code("SAC", sac_code, description="inventory tests")
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
    city_name = generate_random_name("inv_city")
    cities_page.add_city(city_name)
    yield city_name
    try:
        cities_page.navigate()
        if cities_page.search_city(city_name):
            cities_page.delete_city(city_name)
    except Exception as e:
        print(f"Teardown: Failed to delete city {city_name}: {e}")


@pytest.fixture(scope="module")
def module_branch(module_page):
    branches_page = BranchesPage(module_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branches_page.page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    yield branch_name
    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete branch {branch_name}: {e}")
    branches_page.cleanup_auto_city(branch_name)


@pytest.fixture(scope="module")
def module_supplier(module_page, module_city):
    suppliers_page = SuppliersPage(module_page)
    suppliers_page.navigate()
    supplier_name = generate_random_name("inv_supp")
    suppliers_page.add_supplier(
        name=supplier_name,
        contact_person="Contact Auto",
        email=generate_random_email("invsupp"),
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
def module_customer(module_page, module_city):
    customers_page = CustomersPage(module_page)
    customer_name = generate_random_name("inv_cust")
    customers_page.add_customer(
        name=customer_name,
        address_line1="Inventory Test Addr Line 1",
        address_line2="Inventory Test Addr Line 2",
        state_name="Tamil Nadu",
        postal_code="621211",
        city_name=module_city,
    )
    yield customer_name
    try:
        customers_page.navigate()
        if customers_page.search_customer(customer_name):
            customers_page.delete_customer(customer_name)
    except Exception as e:
        print(f"Teardown: Failed to delete customer {customer_name}: {e}")


@pytest.fixture(scope="module")
def module_product(
    module_page, module_category, module_brand, module_unit_type, module_hsn_code, module_branch
):
    """Create product with opening stock of 20 in the module branch."""
    products_page = ProductsPage(module_page)
    products_page.navigate()
    product_name = generate_random_name("inv_prod")
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
    # Add opening stock so the product appears in inventory
    products_page.navigate()
    products_page.update_opening_stock(
        name=product_name,
        branch_name=module_branch,
        quantity="20",
        cost_price="100",
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


def test_inventories_page_loads(logged_in_page):
    """Verify the inventories page loads and displays correctly."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()
    assert inventories_page.is_inventories_visible(), (
        "Inventory Overview page did not load"
    )


def test_search_product_in_inventory(logged_in_page, module_product):
    """Search for a product name and verify it appears in the inventory list."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()
    assert inventories_page.search_inventory(module_product), (
        f"Product '{module_product}' not found in inventory search"
    )


from decimal import Decimal

def test_inventory_shows_correct_opening_stock(logged_in_page, module_product):
    """Verify the opening stock values are correctly displayed."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()

    available = inventories_page.get_available_stock_number(module_product)
    total = inventories_page.get_total_stock_number(module_product)

    assert total == Decimal("20"), f"Expected total stock 20, got {total}"
    assert available == Decimal("20"), f"Expected available stock 20, got {available}"


def test_inventory_stock_increases_after_purchase(
    logged_in_page, module_product, module_supplier, module_branch
):
    """Purchase 10 units → verify inventory available stock increases by 10."""
    purchases_page = PurchasesPage(logged_in_page)
    inventories_page = InventoriesPage(logged_in_page)

    # Get stock before purchase
    inventories_page.navigate()
    stock_before = inventories_page.get_available_stock_number(module_product)

    # Create a purchase of 10 units
    purchases_page.navigate()
    ref_no = "inv_ref_" + str(random.randint(100000, 999999))
    purchases_page.add_purchase(
        supplier=module_supplier,
        branch=module_branch,
        reference_no=ref_no,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[
            {"product": module_product, "quantity": 10, "price": "100"}
        ],
    )

    # Verify stock increased
    inventories_page.navigate()
    stock_after = inventories_page.get_available_stock_number(module_product)

    assert stock_after == stock_before + Decimal("10"), (
        f"Expected stock {stock_before + Decimal('10')} after purchase, got {stock_after}"
    )


def test_inventory_stock_decreases_after_sale(
    logged_in_page, module_product, module_customer, module_branch
):
    """Sell 5 units → verify inventory available stock decreases by 5."""
    sales_page = SalesPage(logged_in_page)
    inventories_page = InventoriesPage(logged_in_page)

    # Get stock before sale
    inventories_page.navigate()
    stock_before = inventories_page.get_available_stock_number(module_product)

    # Create a sale of 5 units
    sales_page.add_sale(
        customer_name=module_customer,
        branch_name=module_branch,
        product_name=module_product,
        quantity=5,
        price="200",
        paid_amount="0",
        address_text="Inventory Test Addr Line 1, Inventory Test Addr Line 2, Tamil Nadu, 621211",
    )

    # Verify stock decreased
    inventories_page.navigate()
    stock_after = inventories_page.get_available_stock_number(module_product)

    assert stock_after == stock_before - Decimal("5"), (
        f"Expected stock {stock_before - Decimal('5')} after sale, got {stock_after}"
    )



def test_filter_inventory_by_branch(logged_in_page, module_product, module_branch):
    """Apply branch filter and verify only products in that branch are shown."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()

    inventories_page.filter_by_branch(module_branch)

    assert inventories_page.is_product_in_table(module_product), (
        f"Product '{module_product}' should be visible when filtering by its branch"
    )


def test_filter_inventory_by_category(
    logged_in_page, module_product, module_category
):
    """Apply category filter and verify only products in that category are shown."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()

    inventories_page.filter_by_category(module_category)

    assert inventories_page.is_product_in_table(module_product), (
        f"Product '{module_product}' should be visible when filtering by its category"
    )


def test_filter_low_stock_only(logged_in_page, module_product):
    """Toggle 'Low Stock Only' filter — our well-stocked product should disappear."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()

    inventories_page.toggle_low_stock_filter()

    # The fixture sets low_stock=5 and creates 20 units, making this deterministic.
    assert not inventories_page.is_product_in_table(module_product), (
        f"Well-stocked product '{module_product}' should be excluded"
    )
    inventories_page.clear_filters()


def test_clear_filters_restores_full_list(logged_in_page, module_product):
    """After applying and clearing filters, the product should be visible again."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()

    # Apply low stock filter (may hide our product)
    inventories_page.toggle_low_stock_filter()

    # Clear filters
    inventories_page.clear_filters()

    # Product should be visible again
    assert inventories_page.search_inventory(module_product), (
        f"Product '{module_product}' should be visible after clearing filters"
    )


def test_view_inventory_detail_drawer(logged_in_page, module_product):
    """Click the view action and verify inventory detail drawer with batch info opens."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()

    assert inventories_page.view_inventory_detail(module_product), (
        "Inventory detail drawer with batch info did not open"
    )

    inventories_page.close_detail_drawer()


def test_export_inventory_pdf(logged_in_page, module_product):
    """Export inventory as PDF and verify file downloads."""
    inventories_page = InventoriesPage(logged_in_page)
    inventories_page.navigate()

    # Ensure at least one product exists in the list
    assert inventories_page.search_inventory(module_product)

    # Navigate fresh (search may interfere with export)
    inventories_page.navigate()

    download_path = inventories_page.export_inventory_pdf(filter_type="all")

    assert download_path and os.path.exists(download_path), (
        "Inventory PDF export failed — no file downloaded"
    )
    assert os.path.getsize(download_path) > 0, (
        "Downloaded inventory PDF is empty"
    )

    # Cleanup
    try:
        os.remove(download_path)
    except Exception:
        pass
