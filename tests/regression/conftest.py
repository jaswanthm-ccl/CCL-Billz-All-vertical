"""Fixtures owned by cross-module regression flows.

Immutable metadata (City, Category, Brand, Unit Type, HSN) are session-scoped.
Dynamic transactional entities (Branches, Suppliers, Customers, Products) are
FUNCTION-SCOPED with worker_id and unique run IDs to guarantee 100% deterministic
isolation across concurrent and sequential test runs.
"""

import pytest
import random
import uuid
from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.brands_page import BrandPage
from pages.master_menu.unit_types_page import UnitTypesPage
from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from pages.main_menu.suppliers_page import SuppliersPage
from pages.main_menu.customers_page import CustomersPage
from pages.main_menu.products_page import ProductsPage
from utils.random_data import (
    generate_random_email,
    generate_random_phone,
    generate_random_postal_code,
    generate_random_address,
    generate_random_gst,
)


@pytest.fixture(scope="session")
def worker_id(request):
    """Return xdist worker ID or 'master' in single-threaded mode."""
    try:
        return request.config.workerinput["workerid"]
    except Exception:
        return "gw0"


@pytest.fixture(scope="session")
def session_page(browser, auth_state):
    """Session-scoped authenticated page for regression fixture setup."""
    context = browser.new_context(storage_state=auth_state, ignore_https_errors=True)
    page = context.new_page()
    yield page
    context.close()


# ── Immutable Master Data: Created once per test session ──────────────────────

@pytest.fixture(scope="session")
def regression_city(session_page, worker_id):
    """Session-scoped city for all regression flows."""
    cities_page = CitiesPage(session_page)
    cities_page.navigate()
    city_name = f"regr_{worker_id}_city_{uuid.uuid4().hex[:6]}"
    cities_page.add_city(city_name)
    session_page.get_by_text("City created successfully").wait_for(
        state="visible", timeout=5000
    )
    return city_name


@pytest.fixture(scope="session")
def regression_category(session_page, worker_id):
    """Session-scoped category for regression products."""
    categories_page = CategoriesPage(session_page)
    categories_page.navigate()
    cat_name = f"regr_{worker_id}_cat_{uuid.uuid4().hex[:6]}"
    categories_page.add_category(name=cat_name, description="Regression flows")
    session_page.get_by_text("Category created successfully").wait_for(
        state="visible", timeout=5000
    )
    return cat_name


@pytest.fixture(scope="session")
def regression_brand(session_page, worker_id):
    """Session-scoped brand for regression products."""
    brand_page = BrandPage(session_page)
    brand_page.navigate()
    brand_name = f"regr_{worker_id}_brand_{uuid.uuid4().hex[:6]}"
    brand_page.add_brand(brand_name, "Regression flows")
    return brand_name


@pytest.fixture(scope="session")
def regression_unit_type(session_page, worker_id):
    """Session-scoped unit type for regression products."""
    unit_page = UnitTypesPage(session_page)
    unit_page.navigate()
    unit_name = f"regr_{worker_id}_unit_{uuid.uuid4().hex[:6]}"
    unit_page.add_unit_type(name=unit_name, unit="pcs", description="Regression flows")
    return unit_name


@pytest.fixture(scope="session")
def regression_hsn_code(session_page):
    """Session-scoped HSN/SAC code for regression products."""
    sac_page = SacHsnCodePage(session_page)
    sac_page.navigate()
    sac_code = str(random.randint(100000, 999999))
    sac_page.add_sac_hsn_code("SAC", sac_code, description="Regression flows")
    return sac_code


# ── Dynamic Flow Data: Isolated per test execution ────────────────────────────

@pytest.fixture(scope="function")
def regression_branch_a(logged_in_page, worker_id):
    """Isolated Primary branch for a single regression flow."""
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    logged_in_page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    return branch_name


@pytest.fixture(scope="function")
def regression_branch_b(logged_in_page, worker_id):
    """Isolated Secondary branch for testing multi-location stock isolation."""
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    logged_in_page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    return branch_name


@pytest.fixture(scope="function")
def regression_supplier(logged_in_page, regression_city, worker_id):
    """Isolated supplier for a single regression flow (no shared debt)."""
    suppliers_page = SuppliersPage(logged_in_page)
    suppliers_page.navigate()
    supplier_name = f"regr_{worker_id}_supp_{uuid.uuid4().hex[:6]}"
    suppliers_page.add_supplier(
        name=supplier_name,
        contact_person="Regression Supplier Contact",
        email=generate_random_email("regr"),
        phone=generate_random_phone(),
        gst_number=generate_random_gst(),
        state_name="Tamil Nadu",
        city_name=regression_city,
        postal_code=generate_random_postal_code(),
        address=generate_random_address(),
    )
    return supplier_name


@pytest.fixture(scope="function")
def regression_customer(logged_in_page, regression_city, worker_id):
    """Isolated customer for a single regression flow (no shared debt)."""
    customers_page = CustomersPage(logged_in_page)
    customers_page.navigate()
    customer_name = f"regr_{worker_id}_cust_{uuid.uuid4().hex[:6]}"
    customers_page.add_customer(
        name=customer_name,
        customer_type="Person",
        email=generate_random_email("regr"),
        phone=generate_random_phone(),
        contact_person="Regression Customer Contact",
        address_line1=generate_random_address(),
        address_line2="Suite 100",
        state_name="Tamil Nadu",
        city_name=regression_city,
        postal_code=generate_random_postal_code(),
    )
    return customer_name


@pytest.fixture(scope="function")
def regression_product(
    logged_in_page,
    regression_category,
    regression_brand,
    regression_unit_type,
    regression_hsn_code,
    worker_id,
):
    """Isolated product for a single regression flow (clean stock baseline)."""
    products_page = ProductsPage(logged_in_page)
    products_page.navigate()
    product_name = f"regr_{worker_id}_prod_{uuid.uuid4().hex[:6]}"
    products_page.add_product(
        name=product_name,
        brand_name=regression_brand,
        category_name=regression_category,
        hsn_code=regression_hsn_code,
        unit_type=regression_unit_type,
        cost_price="100",
        selling_price="200",
        gst_percentage="18%",
    )
    return product_name


# Aliases for explicit isolation naming
isolated_branch_a = regression_branch_a
isolated_branch_b = regression_branch_b
isolated_supplier = regression_supplier
isolated_customer = regression_customer
isolated_product = regression_product
