import pytest
import random
import string
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


@pytest.fixture(scope="module")
def module_category(module_page):
    categories_page = CategoriesPage(module_page)
    categories_page.navigate()
    cat_name = generate_random_name("p_cat")
    categories_page.add_category(name=cat_name, description="desc")
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
    brand_name = generate_random_name("p_brand")
    brand_page.add_brand(brand_name, "desc")
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
    unit_name = generate_random_name("p_unit")
    unit_page.add_unit_type(name=unit_name, unit="pcs", description="desc")
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
    sac_page.add_sac_hsn_code("SAC", sac_code, description="desc")
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
    city_name = generate_random_name("p_city")
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
    supplier_name = generate_random_name("p_sup")
    suppliers_page.add_supplier(
        name=supplier_name,
        contact_person="contact",
        email=generate_random_email("sup"),
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
def module_product(module_page, module_category, module_brand, module_unit_type, module_hsn_code):
    products_page = ProductsPage(module_page)
    products_page.navigate()
    product_name = generate_random_name("p_prod")
    products_page.add_product(
        name=product_name,
        brand_name=module_brand,
        category_name=module_category,
        hsn_code=module_hsn_code,
        unit_type=module_unit_type,
        cost_price="200",
        selling_price="300",
        gst_percentage="18%",
    )
    yield product_name
    try:
        products_page.navigate()
        if products_page.is_product_active(product_name):
            products_page.delete_product(product_name)
    except Exception as e:
        print(f"Teardown: Failed to delete product {product_name}: {e}")


def test_purchases_visibility(logged_in_page):
    purchases_page = PurchasesPage(logged_in_page)
    purchases_page.navigate()
    assert purchases_page.is_purchases_visible()


def test_add_purchase(
    logged_in_page, module_branch, module_supplier, module_product
):
    purchases_page = PurchasesPage(logged_in_page)
    purchases_page.navigate()
    ref_no = "ref_" + str(random.randint(100000, 999999))
    
    purchases_page.add_purchase(
        supplier=module_supplier,
        branch=module_branch,
        reference_no=ref_no,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[
            {"product": module_product, "quantity": 1, "price": "200"}
        ]
    )

    assert purchases_page.search_purchase(ref_no), f"Purchase {ref_no} should be searchable"
    assert purchases_page.view_purchase(
        ref_no,
        expected_supplier=module_supplier,
        expected_branch=module_branch,
        expected_product=module_product,
        expected_quantity="1",
        expected_total="200.00",
    ), f"Purchase {ref_no} persisted details should be viewable"
