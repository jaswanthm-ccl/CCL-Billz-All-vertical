import pytest
import random
from pages.main_menu.customers_page import CustomersPage
from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.branches_page import BranchesPage
from utils.constants import BASE_URL, SALES_URL
from utils.random_data import (
    generate_random_name,
    generate_random_email,
    generate_random_phone,
    generate_random_postal_code,
    generate_random_address,
    generate_random_gst,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def module_city(module_page):
    """Create a single city once per module, reused by customer tests,
    and delete it after the whole module has finished."""
    cities_page = CitiesPage(module_page)
    cities_page.navigate()
    city_name = generate_random_name("auto_city_cust")
    cities_page.add_city(city_name)
    yield city_name
    try:
        cities_page.navigate()
        if cities_page.search_city(city_name):
            cities_page.delete_city(city_name)
    except Exception as e:
        print(f"Teardown Failure: Failed to delete city {city_name}: {e}")


@pytest.fixture
def temp_branch(logged_in_page):
    branches_page = BranchesPage(logged_in_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    yield branch_name
    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown Failure: Failed to delete branch {branch_name}: {e}")
    branches_page.cleanup_auto_city(branch_name)


@pytest.fixture
def customer_cleanup(logged_in_page):
    created_customers = []
    yield created_customers
    customers_page = CustomersPage(logged_in_page)
    for name in list(created_customers):
        try:
            customers_page.navigate()
            if customers_page.search_customer(name):
                if customers_page.delete_customer(name):
                    created_customers.remove(name)
                else:
                    print(f"Teardown Warning: Could not delete customer {name}")
            else:
                created_customers.remove(name)
        except Exception as e:
            print(f"Teardown Failure: Customer cleanup exception for {name}: {e}")


@pytest.fixture
def product_cleanup(logged_in_page):
    from pages.main_menu.products_page import ProductsPage
    created_products = []
    yield created_products
    page_obj = ProductsPage(logged_in_page)
    for name in list(created_products):
        try:
            page_obj.navigate()
            if page_obj.is_product_active(name):
                if page_obj.delete_product(name):
                    created_products.remove(name)
                else:
                    print(f"Teardown Warning: Could not delete product {name}")
            else:
                created_products.remove(name)
        except Exception as e:
            print(f"Teardown Failure: Product cleanup exception for {name}: {e}")


@pytest.fixture
def customers_page(logged_in_page):
    page = CustomersPage(logged_in_page)
    page.navigate()
    return page


@pytest.fixture
def make_customer(customers_page, module_city, customer_cleanup):
    def _make(prefix="auto_cust", **kwargs):
        customers_page.navigate()
        name = kwargs.pop("name", generate_random_name(prefix))
        kwargs.setdefault("city_name", module_city)
        customers_page.add_customer(name=name, **kwargs)
        customer_cleanup.append(name)
        return name
    return _make


# ---------------------------------------------------------------------------
# End-to-End CRUD Lifecycle Test
# ---------------------------------------------------------------------------

def test_customer_crud_lifecycle(customers_page, module_city, customer_cleanup):
    """Create -> Search -> View -> Edit -> Re-open View & Verify -> Soft Delete -> Restore"""
    # 1. Create Customer
    customer_name = generate_random_name("life_cust")
    email = generate_random_email("life")
    phone = generate_random_phone()
    customers_page.add_customer(
        name=customer_name,
        customer_type="Person",
        email=email,
        phone=phone,
        city_name=module_city,
    )
    customer_cleanup.append(customer_name)

    # 2. Search Customer
    assert customers_page.search_customer(customer_name), f"Customer {customer_name} should be searchable"

    # 3. View Customer
    assert customers_page.view_customer(
        customer_name,
        expected_email=email,
        expected_phone=phone,
        expected_city=module_city,
    ), "Customer email, phone, and city should match in View modal"

    # 4. Edit Customer (Name, Email, Phone)
    new_name = generate_random_name("edited_cust")
    new_email = generate_random_email("edited")
    new_phone = generate_random_phone()
    assert customers_page.edit_customer(
        old_name=customer_name,
        new_name=new_name,
        new_email=new_email,
        new_phone=new_phone,
    )
    if customer_name in customer_cleanup:
        customer_cleanup.remove(customer_name)
    customer_cleanup.append(new_name)

    # 5. Search & View Edited Details
    assert customers_page.search_customer(new_name)
    assert customers_page.view_customer(
        new_name,
        expected_email=new_email,
        expected_phone=new_phone,
        expected_city=module_city,
    ), "Reopened View modal should maintain updated customer details"

    # 6. Soft Delete
    assert customers_page.delete_customer(new_name), "Customer should be soft-deleted"

    # 7. Restore
    assert customers_page.retrieve_customer(new_name), "Customer should be restored"
    assert customers_page.search_customer(new_name), "Restored customer should be visible in list"

    # Rule 2: Cleanup after explicit verification
    if customers_page.delete_customer(new_name):
        if new_name in customer_cleanup:
            customer_cleanup.remove(new_name)


# ---------------------------------------------------------------------------
# Customer Types & Address Coverage
# ---------------------------------------------------------------------------

def test_customer_types_person_and_company(customers_page, module_city, customer_cleanup):
    company_name = generate_random_name("comp_cust")
    gst = generate_random_gst()
    customers_page.add_customer(
        name=company_name,
        customer_type="Company",
        city_name=module_city,
        gst_number=gst,
    )
    customer_cleanup.append(company_name)

    assert customers_page.search_customer(company_name)
    assert customers_page.view_customer(company_name, expected_city=module_city)

    if customers_page.delete_customer(company_name):
        if company_name in customer_cleanup:
            customer_cleanup.remove(company_name)


def test_customer_address_variations(customers_page, module_city, customer_cleanup):
    cust_name = generate_random_name("addr_cust")
    customers_page.add_customer(
        name=cust_name,
        customer_type="Person",
        contact_person="Billing Delivery Contact",
        address_line1="123 Billing St",
        address_line2="Suite 450",
        state_name="Tamil Nadu",
        city_name=module_city,
        postal_code=generate_random_postal_code(),
        default_address=True,
    )
    customer_cleanup.append(cust_name)

    assert customers_page.search_customer(cust_name)
    assert customers_page.view_customer(cust_name, expected_city=module_city)

    if customers_page.delete_customer(cust_name):
        if cust_name in customer_cleanup:
            customer_cleanup.remove(cust_name)


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_validate_customer_required_fields(customers_page):
    assert customers_page.validate_required_fields()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("email", "invalid-email", id="invalid-email"),
        pytest.param("email", "test@gmail", id="email-without-domain-suffix"),
        pytest.param("phone", "123", id="short-phone"),
        pytest.param(
            "phone",
            "1223456789",
            id="phone-invalid-start-digit",
            marks=pytest.mark.xfail(reason="Bug #TBD: Phone numbers starting outside 6-9 are accepted"),
        ),
        pytest.param(
            "postal_code",
            "12345",
            id="short-postal-code",
            marks=pytest.mark.xfail(reason="Bug #TBD: 5-digit postal codes are accepted"),
        ),
        pytest.param(
            "postal_code",
            "62AB12",
            id="alphanumeric-postal-code",
            marks=pytest.mark.xfail(reason="Bug #TBD: Alphanumeric postal codes are accepted"),
        ),
        pytest.param(
            "gst_number",
            "INVALIDGST123",
            id="invalid-gst-format",
            marks=pytest.mark.xfail(reason="Bug #TBD: Invalid GST format is accepted"),
        ),
    ],
)
def test_validate_customer_invalid_fields(customers_page, module_city, field, value):
    assert customers_page.validate_invalid_field(
        name=generate_random_name("invalid_cust"),
        customer_type="Person",
        email=generate_random_email("valid"),
        phone=generate_random_phone(),
        notes="val note",
        contact_person="Contact Val",
        address_line1="Line 1",
        address_line2="Line 2",
        state_name="Tamil Nadu",
        city_name=module_city,
        postal_code=generate_random_postal_code(),
        field=field,
        value=value,
    ), f"Expected validation feedback for invalid {field}"


@pytest.mark.parametrize(
    "duplicate_field",
    [
        "email",
        "phone",
        pytest.param(
            "gst_number",
            marks=pytest.mark.xfail(reason="Bug #TBD: Duplicate GST numbers are accepted"),
        ),
    ],
)
def test_reject_duplicate_customer_identifier(
    customers_page, module_city, customer_cleanup, duplicate_field
):
    duplicate_email = generate_random_email("duplicate")
    duplicate_phone = generate_random_phone()
    duplicate_gst = generate_random_gst()
    postal_code = generate_random_postal_code()

    first_name = generate_random_name("dup_cust")
    customers_page.add_customer(
        name=first_name,
        customer_type="Company" if duplicate_field == "gst_number" else "Person",
        email=duplicate_email,
        phone=duplicate_phone,
        city_name=module_city,
        postal_code=postal_code,
        gst_number=duplicate_gst,
    )
    customer_cleanup.append(first_name)

    second_email = generate_random_email("second_dup")
    second_phone = generate_random_phone()
    second_gst = generate_random_gst()

    if duplicate_field == "email":
        second_email = duplicate_email
    elif duplicate_field == "phone":
        second_phone = duplicate_phone
    elif duplicate_field == "gst_number":
        second_gst = duplicate_gst

    assert customers_page.validate_duplicate_customer(
        name=generate_random_name("second_dup_cust"),
        customer_type="Company" if duplicate_field == "gst_number" else "Person",
        email=second_email,
        phone=second_phone,
        notes="note",
        contact_person="contact",
        address_line1="line 1",
        address_line2="line 2",
        state_name="Tamil Nadu",
        city_name=module_city,
        postal_code=postal_code,
        gst_number=second_gst,
    ), f"Expected validation feedback for duplicate customer {duplicate_field}"

    if customers_page.delete_customer(first_name):
        if first_name in customer_cleanup:
            customer_cleanup.remove(first_name)


# ---------------------------------------------------------------------------
# Sale Deletion Interaction Test (MM-ADD-089 & Rule 15 Restriction Check)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="Bug #TBD: Customer assigned to an active sale can be deleted"
)
def test_delete_customer_with_active_sale_is_blocked(
    customers_page, make_customer, logged_in_page, temp_branch, product_cleanup, customer_cleanup
):
    from pages.main_menu.sales_page import SalesPage
    from pages.main_menu.products_page import ProductsPage
    from pages.master_menu.categories_page import CategoriesPage
    from pages.master_menu.brands_page import BrandPage
    from pages.master_menu.unit_types_page import UnitTypesPage
    from pages.master_menu.sac_hsn_code_page import SacHsnCodePage

    created_sale_id = None
    iso_cat = None
    iso_brand = None
    iso_unit = None
    iso_hsn = None
    iso_prod = None
    customer_name = None

    try:
        # 1. Create Category
        cat_page = CategoriesPage(logged_in_page)
        cat_page.navigate()
        iso_cat = generate_random_name("iso_sale_cat")
        cat_page.add_category(iso_cat, "1")

        # 2. Create Brand
        brand_page = BrandPage(logged_in_page)
        brand_page.navigate()
        iso_brand = generate_random_name("iso_sale_brand")
        brand_page.add_brand(iso_brand, "desc")

        # 3. Create Unit Type
        unit_page = UnitTypesPage(logged_in_page)
        unit_page.navigate()
        iso_unit = generate_random_name("iso_sale_unit")
        unit_page.add_unit_type(iso_unit, "pcs", "desc")

        # 4. Create HSN
        sac_page = SacHsnCodePage(logged_in_page)
        sac_page.navigate()
        iso_hsn = str(random.randint(100000, 999999))
        sac_page.add_sac_hsn_code("SAC", iso_hsn, "desc")

        # 5. Create Product & Opening Stock
        products_page = ProductsPage(logged_in_page)
        products_page.navigate()
        iso_prod = generate_random_name("iso_sale_prod")
        products_page.add_product(
            name=iso_prod,
            brand_name=iso_brand,
            category_name=iso_cat,
            hsn_code=iso_hsn,
            unit_type=iso_unit,
            cost_price="200",
            selling_price="300",
        )
        product_cleanup.append(iso_prod)

        products_page.update_opening_stock(
            name=iso_prod,
            branch_name=temp_branch,
            quantity="10",
            cost_price="200",
        )

        # 6. Create Customer
        customer_name = make_customer("block_del_cust")

        # 7. Create Sale & capture Sale ID
        sales_page = SalesPage(logged_in_page)
        sales_page.navigate()

        with logged_in_page.expect_response(
            lambda r: "sale" in r.url.lower() and r.request.method == "POST",
            timeout=15000
        ) as resp_info:
            sales_page.add_sale(
                customer_name=customer_name,
                branch_name=temp_branch,
                paid_amount="0",
                price="300",
                product_name=iso_prod,
                quantity=1,
                salesperson_name="Super Admin",
            )

        try:
            res_json = resp_info.value.json()
            created_sale_id = res_json.get("data", {}).get("id") or res_json.get("id")
        except Exception as parse_err:
            print(f"Warning: Could not extract sale ID: {parse_err}")

        # 8. Attempt Customer deletion & assert required restriction behavior (must be blocked)
        customers_page.navigate()
        deleted = customers_page.delete_customer(customer_name)

        # If application bug allowed deletion, customer was soft-deleted, so remove from cleanup list
        if deleted:
            if customer_name in customer_cleanup:
                customer_cleanup.remove(customer_name)

        assert not deleted, "Deleting a customer linked to an active sale must be blocked"

    finally:
        # Cleanup Order: Sale -> Customer -> Product -> HSN -> Unit Type -> Brand -> Category

        # 1. Sale Cleanup (Log if sale cannot be deleted via API due to immutability)
        if created_sale_id:
            sale_deleted = False
            for url in (
                f"{SALES_URL}/{created_sale_id}",
                f"{BASE_URL}/api/sales/{created_sale_id}",
                f"{BASE_URL}/api/v1/sales/{created_sale_id}",
            ):
                try:
                    res = logged_in_page.request.delete(url)
                    if res.status in (200, 204):
                        sale_deleted = True
                        break
                except Exception as e:
                    print(f"Teardown Attempt info for Sale ID {created_sale_id} at {url}: {e}")

            if not sale_deleted:
                print(f"Teardown Info: Sale ID {created_sale_id} is an active sale record (immutable transaction).")

        # 2. Customer Cleanup (only if not already deleted during test step)
        if customer_name and customer_name in customer_cleanup:
            try:
                customers_page.navigate()
                if customers_page.search_customer(customer_name):
                    if customers_page.delete_customer(customer_name):
                        customer_cleanup.remove(customer_name)
                    else:
                        print(f"Teardown Warning: Could not delete customer {customer_name}")
                else:
                    customer_cleanup.remove(customer_name)
            except Exception as e:
                print(f"Teardown Failure: Customer deletion exception for {customer_name}: {e}")

        # 3. Product Cleanup
        if iso_prod and iso_prod in product_cleanup:
            try:
                products_page = ProductsPage(logged_in_page)
                products_page.navigate()
                if products_page.is_product_active(iso_prod):
                    if products_page.delete_product(iso_prod):
                        product_cleanup.remove(iso_prod)
                    else:
                        print(f"Teardown Warning: Could not delete product {iso_prod}")
                else:
                    product_cleanup.remove(iso_prod)
            except Exception as e:
                print(f"Teardown Failure: Product deletion exception for {iso_prod}: {e}")

        # 4. HSN Cleanup
        if iso_hsn:
            try:
                sac_page = SacHsnCodePage(logged_in_page)
                sac_page.navigate()
                if sac_page.search_sac_hsn_code(iso_hsn):
                    try:
                        sac_page.delete_sac_hsn_code(iso_hsn)
                    except Exception as hsn_err:
                        print(f"Teardown Warning: HSN deletion for {iso_hsn}: {hsn_err}")
            except Exception as e:
                print(f"Teardown Failure: HSN search/deletion exception for {iso_hsn}: {e}")

        # 5. Unit Type Cleanup
        if iso_unit:
            try:
                unit_page = UnitTypesPage(logged_in_page)
                unit_page.navigate()
                if unit_page.search_unit_type(iso_unit):
                    try:
                        unit_page.delete_unit_type(iso_unit)
                    except Exception as unit_err:
                        print(f"Teardown Warning: Unit Type deletion for {iso_unit}: {unit_err}")
            except Exception as e:
                print(f"Teardown Failure: Unit Type search/deletion exception for {iso_unit}: {e}")

        # 6. Brand Cleanup
        if iso_brand:
            try:
                brand_page = BrandPage(logged_in_page)
                brand_page.navigate()
                if brand_page.search_brand(iso_brand):
                    try:
                        brand_page.delete_brand(iso_brand)
                    except Exception as brand_err:
                        print(f"Teardown Warning: Brand deletion for {iso_brand}: {brand_err}")
            except Exception as e:
                print(f"Teardown Failure: Brand search/deletion exception for {iso_brand}: {e}")

        # 7. Category Cleanup
        if iso_cat:
            try:
                cat_page = CategoriesPage(logged_in_page)
                cat_page.navigate()
                if cat_page.search_category(iso_cat):
                    try:
                        cat_page.delete_category(iso_cat)
                    except Exception as cat_err:
                        print(f"Teardown Warning: Category deletion for {iso_cat}: {cat_err}")
            except Exception as e:
                print(f"Teardown Failure: Category search/deletion exception for {iso_cat}: {e}")
