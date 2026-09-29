import pytest
import random
import string
import os
from pages.main_menu.purchase_request_page import PurchaseRequestPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.suppliers_page import SuppliersPage
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.brands_page import BrandPage
from pages.master_menu.unit_types_page import UnitTypesPage
from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from utils.random_data import generate_random_name, generate_random_email, generate_random_phone, generate_random_postal_code, generate_random_address


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
    cat_name = generate_random_name("pr_cat")
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
    brand_name = generate_random_name("pr_brand")
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
    unit_name = generate_random_name("pr_unit")
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
    city_name = generate_random_name("pr_city")
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
def module_products(module_page, module_category, module_brand, module_unit_type, module_hsn_code):
    """Create the two products purchase-request tests need, once per module."""
    products_page = ProductsPage(module_page)
    created = []

    def _make(prefix, cost_price, selling_price):
        products_page.navigate()
        name = generate_random_name(prefix)
        products_page.add_product(
            name=name,
            brand_name=module_brand,
            category_name=module_category,
            hsn_code=module_hsn_code,
            unit_type=module_unit_type,
            cost_price=cost_price,
            selling_price=selling_price,
            gst_percentage="18%",
        )
        created.append(name)
        return name

    prod1 = _make("auto_prod", "100", "150")
    prod2 = _make("auto_prod", "120", "180")

    yield {"product1": prod1, "product2": prod2}

    for name in created:
        try:
            products_page.navigate()
            if products_page.search_product(name):
                products_page.delete_product(name)
        except Exception as e:
            print(f"Teardown: Failed to delete product {name}: {e}")


@pytest.fixture(scope="module")
def module_supplier(module_page, module_city):
    """A single module-scoped supplier shared across all tests in this file."""
    suppliers_page = SuppliersPage(module_page)
    suppliers_page.navigate()
    supplier_name = generate_random_name("pr_sup")
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
def master_data(
    module_branch, module_supplier, module_products, module_city,
    module_category, module_brand, module_unit_type, module_hsn_code,
):
    """Bundle the master-data into a single dict. Since all dependencies
    are module-scoped, we can make master_data module-scoped as well, which
    reuses the exact same records across all tests."""
    return {
        "branch": module_branch,
        "supplier": module_supplier,
        "product1": module_products["product1"],
        "product2": module_products["product2"],
        "city": module_city,
        "category": module_category,
        "brand": module_brand,
        "unit_type": module_unit_type,
        "hsn": module_hsn_code,
    }


# ---------------------------------------------------------------------------
# Page & factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def purchase_request_cleanup(logged_in_page):
    created_requests = []
    yield created_requests
    pr_page = PurchaseRequestPage(logged_in_page)
    failures = []
    for supplier_name in created_requests:
        try:
            pr_page.navigate()
            if pr_page.search_purchase_request(supplier_name):
                if not pr_page.delete_purchase_request(supplier_name):
                    failures.append(supplier_name)
        except Exception as e:
            print(f"Teardown: Failed to delete purchase request for supplier {supplier_name}: {e}")
            failures.append(supplier_name)

    # Purchase requests are looked up by supplier name only, and this module
    # reuses a single shared supplier across every test. A silently failed
    # cleanup here would leave a stale request behind that later tests could
    # mistake for their own (the page object clicks the first matching row).
    # Fail loudly instead of masking that risk.
    assert not failures, (
        f"Teardown left stale purchase request(s) for supplier(s): {failures}. "
        "This can cause later tests in this module to act on the wrong row."
    )


@pytest.fixture
def purchase_requests_page(logged_in_page):
    """A PurchaseRequestPage already navigated to the purchase requests list."""
    page = PurchaseRequestPage(logged_in_page)
    page.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    return page


@pytest.fixture
def make_purchase_request(purchase_requests_page, master_data, purchase_request_cleanup):
    """Factory that creates a purchase request against the shared module
    master data (branch/supplier/products) and registers it for cleanup.
    Returns the supplier name, which is how purchase requests are looked up."""
    def _make(
        priority="Medium", quantity=1, notes="auto_test_notes", product=None,
        products_data=None,
    ):
        purchase_requests_page.navigate()
        purchase_requests_page.page.wait_for_load_state("networkidle")
        items = products_data or [
            {"product": product or master_data["product1"], "quantity": quantity}
        ]
        purchase_requests_page.add_purchase_request(
            branch=master_data["branch"],
            supplier=master_data["supplier"],
            priority=priority,
            products_data=items,
            notes=notes,
        )
        purchase_request_cleanup.append(master_data["supplier"])
        return master_data["supplier"]
    return _make



def test_purchase_request_visibility(purchase_requests_page):
    assert purchase_requests_page.is_purchase_requests_visible()


def test_add_purchase_request(purchase_requests_page, make_purchase_request):
    supplier = make_purchase_request(quantity=5)
    assert purchase_requests_page.search_purchase_request(supplier)


def test_search_purchase_request(purchase_requests_page, make_purchase_request):
    supplier = make_purchase_request(quantity=2, notes="search_test")
    assert purchase_requests_page.search_purchase_request(supplier)


def test_create_purchase_request_with_multiple_items(
    purchase_requests_page, make_purchase_request, master_data
):
    supplier = make_purchase_request(
        priority="High",
        products_data=[
            {"product": master_data["product1"], "quantity": 2},
            {"product": master_data["product2"], "quantity": 3},
        ],
        notes="multi_item_test",
    )
    assert purchase_requests_page.purchase_request_contains_products(
        supplier, [master_data["product1"], master_data["product2"]]
    )


def test_view_purchase_request(purchase_requests_page, make_purchase_request, master_data):
    supplier = make_purchase_request(priority="Urgent", quantity=3, notes="view_test")
    assert purchase_requests_page.view_purchase_request(
        supplier_name=supplier,
        first_product_name=master_data["product1"],
        priority="Urgent",
    )


def test_edit_purchase_request(purchase_requests_page, make_purchase_request, master_data):
    supplier = make_purchase_request(priority="Low", quantity=1, notes="edit_test")

    # Edit to add a second product line
    assert purchase_requests_page.edit_purchase_request(
        supplier_name=supplier,
        new_product_name=master_data["product2"],
        new_quantity=10,
    )


def test_download_purchase_request(purchase_requests_page, make_purchase_request):
    supplier = make_purchase_request(priority="High", quantity=4, notes="download_test")

    download = purchase_requests_page.download_purchase_request(supplier)
    assert download is not None
    path = download.path()
    assert path and os.path.exists(path), "Purchase request download failed"
    assert os.path.getsize(path) > 0, "Downloaded purchase request file is empty"


def test_delete_purchase_request(purchase_requests_page, make_purchase_request, purchase_request_cleanup):
    supplier = make_purchase_request(priority="Medium", quantity=2, notes="delete_test")
    assert purchase_requests_page.delete_purchase_request(supplier)
    purchase_request_cleanup.remove(supplier)


def test_retrieve_purchase_request(purchase_requests_page, make_purchase_request):
    supplier = make_purchase_request(priority="Medium", quantity=2, notes="retrieve_test")
    assert purchase_requests_page.delete_purchase_request(supplier)
    assert purchase_requests_page.retrieve_purchase_request(supplier)
    assert purchase_requests_page.search_purchase_request(supplier)


def test_validate_purchase_request_required_fields(purchase_requests_page):
    assert purchase_requests_page.validate_required_fields()


@pytest.mark.parametrize("quantity", [0, -1], ids=["zero", "negative"])
def test_reject_invalid_purchase_request_quantity(
    purchase_requests_page, master_data, quantity
):
    assert purchase_requests_page.validate_invalid_quantity(
        branch=master_data["branch"],
        supplier=master_data["supplier"],
        priority="Medium",
        product=master_data["product1"],
        quantity=quantity,
    ), f"Expected validation feedback for quantity {quantity}"


@pytest.mark.skip(
    reason="Known bug: supplier assigned to an active purchase request can be deleted"
)
def test_delete_supplier_assigned_to_purchase_request_is_blocked(
    logged_in_page, make_purchase_request
):
    supplier = make_purchase_request(quantity=2, notes="supplier_dependency")
    suppliers_page = SuppliersPage(logged_in_page)
    suppliers_page.navigate()
    assert not suppliers_page.delete_supplier(supplier), (
        "A supplier assigned to an active purchase request must not be deleted"
    )
