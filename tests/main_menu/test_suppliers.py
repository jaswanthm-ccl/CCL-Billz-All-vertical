import pytest
import random
from pages.main_menu.suppliers_page import SuppliersPage
from pages.master_menu.cities_page import CitiesPage
from pages.master_menu.branches_page import BranchesPage
from utils.constants import BASE_URL, PURCHASES_URL
from utils.random_data import (
    generate_random_name,
    generate_random_email,
    generate_random_phone,
    generate_random_postal_code,
    generate_random_address,
    generate_random_gst,
)


def _supplier_data(prefix="auto_sup", city_name="Udumalpet_edit"):
    return {
        "name": generate_random_name(prefix),
        "contact_person": generate_random_name("contact"),
        "email": generate_random_email("supplier"),
        "phone": generate_random_phone(),
        "gst_number": generate_random_gst(),
        "state_name": "Tamil Nadu",
        "city_name": city_name,
        "postal_code": generate_random_postal_code(),
        "address": generate_random_address(),
        "notes": "automation test notes",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def module_city(module_page):
    cities_page = CitiesPage(module_page)
    cities_page.navigate()
    city_name = generate_random_name("auto_city_sup")
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
def supplier_cleanup(logged_in_page):
    created_suppliers = []
    yield created_suppliers
    supplier_page = SuppliersPage(logged_in_page)
    for name in list(created_suppliers):
        try:
            supplier_page.navigate()
            if supplier_page.search_supplier(name):
                if supplier_page.delete_supplier(name):
                    created_suppliers.remove(name)
                else:
                    print(f"Teardown Warning: Could not delete supplier {name}")
            else:
                created_suppliers.remove(name)
        except Exception as e:
            print(f"Teardown Failure: Supplier cleanup exception for {name}: {e}")


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
def suppliers_page(logged_in_page):
    page = SuppliersPage(logged_in_page)
    page.navigate()
    return page


@pytest.fixture
def make_supplier(suppliers_page, module_city, supplier_cleanup):
    def _make(prefix="auto_sup", **kwargs):
        suppliers_page.navigate()
        name = kwargs.pop("name", generate_random_name(prefix))
        kwargs.setdefault("city_name", module_city)
        suppliers_page.add_supplier(name=name, **kwargs)
        supplier_cleanup.append(name)
        return name
    return _make


# ---------------------------------------------------------------------------
# End-to-End CRUD Lifecycle Test
# ---------------------------------------------------------------------------

def test_supplier_crud_lifecycle(suppliers_page, module_city, supplier_cleanup):
    """Create -> Search -> View -> Edit -> Re-view -> Soft Delete -> Restore"""
    # 1. Create Supplier
    supplier_name = generate_random_name("life_sup")
    contact_person = generate_random_name("life_contact")
    email = generate_random_email("life")
    phone = generate_random_phone()
    gst = generate_random_gst()
    suppliers_page.add_supplier(
        name=supplier_name,
        contact_person=contact_person,
        email=email,
        phone=phone,
        gst_number=gst,
        city_name=module_city,
    )
    supplier_cleanup.append(supplier_name)

    # 2. Search
    assert suppliers_page.search_supplier(supplier_name), f"Supplier {supplier_name} should be searchable"

    # 3. View Original
    assert suppliers_page.view_supplier(
        supplier_name,
        expected_contact=contact_person,
        expected_email=email,
    ), "Original supplier details should match in View modal"

    # 4. Edit (Name, Contact Person, Email)
    new_name = generate_random_name("edited_sup")
    new_contact = generate_random_name("edited_contact")
    new_email = generate_random_email("edited_sup")
    assert suppliers_page.edit_supplier(
        old_name=supplier_name,
        new_name=new_name,
        new_contact=new_contact,
        new_email=new_email,
    )
    if supplier_name in supplier_cleanup:
        supplier_cleanup.remove(supplier_name)
    supplier_cleanup.append(new_name)

    # 5. Search & View Edited Details
    assert suppliers_page.search_supplier(new_name)
    assert suppliers_page.view_supplier(
        new_name,
        expected_contact=new_contact,
        expected_email=new_email,
    ), "Reopened View modal should reflect edited contact person and email"

    # 6. Soft Delete
    assert suppliers_page.delete_supplier(new_name), "Supplier should be soft-deleted"

    # 7. Restore
    assert suppliers_page.retrieve_supplier(new_name), "Supplier should be restored"
    assert suppliers_page.search_supplier(new_name), "Restored supplier should be visible in list"

    # Cleanup after explicit test verification
    if suppliers_page.delete_supplier(new_name):
        if new_name in supplier_cleanup:
            supplier_cleanup.remove(new_name)


def test_suppliers_visibility(suppliers_page):
    assert suppliers_page.is_suppliers_visible()


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_validate_supplier_required_fields(suppliers_page):
    assert suppliers_page.validate_required_fields()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("email", "invalid-email", id="invalid-email"),
        pytest.param(
            "email",
            "test@gmail",
            id="email-without-domain-suffix",
            marks=pytest.mark.xfail(reason="Bug #TBD: Email without TLD suffix (e.g. test@gmail) is accepted"),
        ),
        pytest.param(
            "phone",
            "1223456789",
            id="phone-invalid-start-digit",
            marks=pytest.mark.xfail(reason="Bug #TBD: Phone numbers starting outside 6-9 are accepted"),
        ),
        pytest.param("phone", "123", id="short-phone"),
        pytest.param("gst_number", "INVALIDGST123", id="invalid-gstin-format"),
        pytest.param("postal_code", "62AB12", id="alphanumeric-postal-code"),
        pytest.param("postal_code", "12345", id="short-postal-code"),
        pytest.param(
            "account_number",
            "123456789012345678901",
            id="overflow-account-number",
            marks=pytest.mark.xfail(reason="Bug #TBD: Overflow account numbers accepted without validation"),
        ),
        pytest.param(
            "ifsc",
            "INVALIDIFSC",
            id="invalid-ifsc-code",
            marks=pytest.mark.xfail(reason="Bug #TBD: Invalid IFSC code accepted without validation"),
        ),
    ],
)
def test_validate_supplier_field_formats(suppliers_page, module_city, field, value):
    assert suppliers_page.validate_invalid_field(
        name=generate_random_name("invalid_sup"),
        contact_person=generate_random_name("contact"),
        email=generate_random_email("valid"),
        phone=generate_random_phone(),
        gst_number=generate_random_gst(),
        state_name="Tamil Nadu",
        city_name=module_city,
        postal_code=generate_random_postal_code(),
        address=generate_random_address(),
        field=field,
        value=value,
    ), f"Expected validation feedback for invalid supplier {field}"


@pytest.mark.parametrize(
    "duplicate_field",
    [
        pytest.param(
            "email",
            marks=pytest.mark.xfail(
                reason="Bug #TBD: Duplicate supplier email is accepted by backend without rejection"
            ),
        ),
        pytest.param(
            "phone",
            marks=pytest.mark.xfail(
                reason="Bug #TBD: Duplicate supplier phone is accepted by backend without rejection"
            ),
        ),
        "gst_number",
    ],
)
def test_reject_duplicate_supplier_identifier(
    suppliers_page, module_city, supplier_cleanup, duplicate_field
):
    first_email = generate_random_email("sup_dup")
    first_phone = generate_random_phone()
    first_gst = generate_random_gst()

    first_name = generate_random_name("dup_sup_base")
    suppliers_page.add_supplier(
        name=first_name,
        contact_person="First Contact",
        email=first_email,
        phone=first_phone,
        gst_number=first_gst,
        city_name=module_city,
    )
    supplier_cleanup.append(first_name)

    second_email = generate_random_email("sup_dup_2")
    second_phone = generate_random_phone()
    second_gst = generate_random_gst()

    if duplicate_field == "email":
        second_email = first_email
    elif duplicate_field == "phone":
        second_phone = first_phone
    elif duplicate_field == "gst_number":
        second_gst = first_gst

    assert suppliers_page.validate_duplicate_supplier(
        name=generate_random_name("dup_sup_sec"),
        contact_person="Second Contact",
        email=second_email,
        phone=second_phone,
        gst_number=second_gst,
        state_name="Tamil Nadu",
        city_name=module_city,
        postal_code=generate_random_postal_code(),
        address=generate_random_address(),
    ), f"Expected duplicate validation for an existing supplier {duplicate_field}"

    if suppliers_page.delete_supplier(first_name):
        if first_name in supplier_cleanup:
            supplier_cleanup.remove(first_name)


# ---------------------------------------------------------------------------
# Purchase Deletion Interaction Test (Supplier Linked to Active Purchase)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="Bug #TBD: Supplier assigned to an active purchase can be deleted"
)
def test_delete_supplier_with_active_purchase_is_blocked(
    suppliers_page, make_supplier, logged_in_page, temp_branch, product_cleanup, supplier_cleanup
):
    from pages.main_menu.purchases_page import PurchasesPage
    from pages.main_menu.products_page import ProductsPage
    from pages.master_menu.categories_page import CategoriesPage
    from pages.master_menu.brands_page import BrandPage
    from pages.master_menu.unit_types_page import UnitTypesPage
    from pages.master_menu.sac_hsn_code_page import SacHsnCodePage

    created_purchase_id = None
    iso_cat = None
    iso_brand = None
    iso_unit = None
    iso_hsn = None
    iso_prod = None
    supplier_name = None

    try:
        # 1. Create Category
        cat_page = CategoriesPage(logged_in_page)
        cat_page.navigate()
        iso_cat = generate_random_name("iso_pur_cat")
        cat_page.add_category(iso_cat, "1")

        # 2. Create Brand
        brand_page = BrandPage(logged_in_page)
        brand_page.navigate()
        iso_brand = generate_random_name("iso_pur_brand")
        brand_page.add_brand(iso_brand, "desc")

        # 3. Create Unit Type
        unit_page = UnitTypesPage(logged_in_page)
        unit_page.navigate()
        iso_unit = generate_random_name("iso_pur_unit")
        unit_page.add_unit_type(iso_unit, "pcs", "desc")

        # 4. Create HSN
        sac_page = SacHsnCodePage(logged_in_page)
        sac_page.navigate()
        iso_hsn = str(random.randint(100000, 999999))
        sac_page.add_sac_hsn_code("SAC", iso_hsn, "desc")

        # 5. Create Product
        products_page = ProductsPage(logged_in_page)
        products_page.navigate()
        iso_prod = generate_random_name("iso_pur_prod")
        products_page.add_product(
            name=iso_prod,
            brand_name=iso_brand,
            category_name=iso_cat,
            hsn_code=iso_hsn,
            unit_type=iso_unit,
            cost_price="150",
            selling_price="250",
        )
        product_cleanup.append(iso_prod)

        # 6. Create Supplier
        supplier_name = make_supplier("block_pur_sup")

        # 7. Create Purchase & capture Purchase ID
        purchases_page = PurchasesPage(logged_in_page)
        purchases_page.navigate()

        ref_no = f"PO_{random.randint(1000, 9999)}"
        with logged_in_page.expect_response(
            lambda r: "purchase" in r.url.lower() and r.request.method == "POST",
            timeout=15000
        ) as resp_info:
            purchases_page.add_purchase(
                supplier=supplier_name,
                branch=temp_branch,
                reference_no=ref_no,
                paid_amount="0",
                purchase_type="Cash",
                products_data=[{"product": iso_prod, "quantity": 5, "price": "150"}],
            )

        try:
            res_json = resp_info.value.json()
            created_purchase_id = res_json.get("data", {}).get("id") or res_json.get("id")
        except Exception as parse_err:
            print(f"Warning: Could not extract purchase ID: {parse_err}")

        # 8. Attempt Supplier deletion & assert required restriction behavior (must be blocked)
        suppliers_page.navigate()
        deleted = suppliers_page.delete_supplier(supplier_name)

        if deleted:
            if supplier_name in supplier_cleanup:
                supplier_cleanup.remove(supplier_name)

        assert not deleted, "Deleting a supplier linked to an active purchase must be blocked"

    finally:
        # Cleanup Order: Purchase -> Supplier -> Product -> HSN -> Unit Type -> Brand -> Category

        # 1. Purchase Cleanup
        if created_purchase_id:
            pur_deleted = False
            for url in (
                f"{PURCHASES_URL}/{created_purchase_id}",
                f"{BASE_URL}/api/purchases/{created_purchase_id}",
                f"{BASE_URL}/api/v1/purchases/{created_purchase_id}",
            ):
                try:
                    res = logged_in_page.request.delete(url)
                    if res.status in (200, 204):
                        pur_deleted = True
                        break
                except Exception as e:
                    print(f"Teardown Attempt info for Purchase ID {created_purchase_id} at {url}: {e}")

            if not pur_deleted:
                print(f"Teardown Info: Purchase ID {created_purchase_id} is an active purchase record.")

        # 2. Supplier Cleanup (only if not already deleted during test step)
        if supplier_name and supplier_name in supplier_cleanup:
            try:
                suppliers_page.navigate()
                if suppliers_page.search_supplier(supplier_name):
                    if suppliers_page.delete_supplier(supplier_name):
                        supplier_cleanup.remove(supplier_name)
                    else:
                        print(f"Teardown Warning: Could not delete supplier {supplier_name}")
                else:
                    supplier_cleanup.remove(supplier_name)
            except Exception as e:
                print(f"Teardown Failure: Supplier deletion exception for {supplier_name}: {e}")

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
