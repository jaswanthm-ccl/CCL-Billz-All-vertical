import pytest
import random
import string
import os
from pages.main_menu.sales_quotes_page import SalesQuotesPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.customers_page import CustomersPage
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.brands_page import BrandPage
from pages.master_menu.unit_types_page import UnitTypesPage
from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from utils.random_data import generate_random_name, generate_random_email, generate_random_phone, generate_random_postal_code, generate_random_address


@pytest.fixture(scope="module")
def module_category(module_page):
    categories_page = CategoriesPage(module_page)
    categories_page.navigate()
    cat_name = generate_random_name("sq_cat")
    categories_page.add_category(name=cat_name, description="desc")
    categories_page.page.get_by_text("Category created successfully").wait_for(state="visible", timeout=5000)
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
    brand_name = generate_random_name("sq_brand")
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
    unit_name = generate_random_name("sq_unit")
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
    city_name = generate_random_name("sq_city")
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
    branches_page.page.get_by_text("Branch created successfully.").wait_for(state="visible", timeout=5000)
    yield branch_name
    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete branch {branch_name}: {e}")
    branches_page.cleanup_auto_city(branch_name)


@pytest.fixture(scope="module")
def module_customer(module_page):
    customers_page = CustomersPage(module_page)
    customers_page.navigate()
    customer_name = generate_random_name("sq_cust")
    customers_page.add_customer(customer_name)
    yield customer_name
    try:
        customers_page.navigate()
        if customers_page.search_customer(customer_name):
            customers_page.delete_customer(customer_name)
    except Exception as e:
        print(f"Teardown: Failed to delete customer {customer_name}: {e}")


@pytest.fixture(scope="module")
def module_product(module_page, module_category, module_brand, module_unit_type, module_hsn_code, module_branch):
    products_page = ProductsPage(module_page)
    products_page.navigate()
    product_name = generate_random_name("sq_prod")
    products_page.add_product(
        name=product_name,
        brand_name=module_brand,
        category_name=module_category,
        hsn_code=module_hsn_code,
        unit_type=module_unit_type,
        cost_price="4000",
        selling_price="5000",
        gst_percentage="18%",
    )
    # Add opening stock to the product so it can be sold/quoted
    products_page.navigate()
    products_page.update_opening_stock(
        name=product_name,
        branch_name=module_branch,
        quantity="100",
        cost_price="4000"
    )
    yield product_name
    try:
        products_page.navigate()
        if products_page.search_product(product_name):
            products_page.delete_product(product_name)
    except Exception as e:
        print(f"Teardown: Failed to delete product {product_name}: {e}")


def test_sales_quotes_crud_flow(
    logged_in_page, module_customer, module_branch, module_product
):
    sales_quotes_page = SalesQuotesPage(logged_in_page)

    # 1. Create a Sales Quote
    sales_quotes_page.navigate()
    sales_quotes_page.add_sales_quote(
        customer=module_customer,
        branch=module_branch,
        product=module_product,
        quantity=1
    )

    # 2. Search & View details
    assert sales_quotes_page.view_sales_quote(
        query=module_customer,
        customer_name=module_customer,
        branch_name=module_branch
    )

    # 3. Edit & Update Quantity
    sales_quotes_page.edit_sales_quote(query=module_customer, new_quantity=2)

    # 4. Delete the quote
    sales_quotes_page.delete_sales_quote(query=module_customer)

    # 5. Restore/Retrieve the quote
    sales_quotes_page.retrieve_sales_quote(query=module_customer)

    # 6. Download the quote and verify file size
    download_path = sales_quotes_page.download_sales_quote(query=module_customer)
    assert download_path and os.path.exists(download_path), "File download failed"
    assert os.path.getsize(download_path) > 0, "Downloaded file is empty"

    # Cleanup download file
    try:
        os.remove(download_path)
    except Exception:
        pass

    # 7. Delete quote again to leave database clean for fixture teardown
    sales_quotes_page.delete_sales_quote(query=module_customer)
