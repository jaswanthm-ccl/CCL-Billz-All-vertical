import pytest
import random
from pages.main_menu.products_page import ProductsPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.brands_page import BrandPage
from pages.master_menu.unit_types_page import UnitTypesPage
from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from pages.master_menu.branches_page import BranchesPage
from utils.random_data import generate_random_name


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
        print(f"Teardown: Failed to delete branch {branch_name}: {e}")
    branches_page.cleanup_auto_city(branch_name)


@pytest.fixture
def products_page(logged_in_page):
    page = ProductsPage(logged_in_page)
    page.navigate()
    return page


@pytest.fixture
def product_cleanup(logged_in_page):
    created_products = []
    yield created_products
    page_obj = ProductsPage(logged_in_page)
    for name in list(created_products):
        try:
            page_obj.navigate()
            if page_obj.is_product_active(name):
                page_obj.delete_product(name)
        except Exception as e:
            print(f"Teardown: Failed to delete product {name}: {e}")


# ---------------------------------------------------------------------------
# End-to-End CRUD Lifecycle Test
# ---------------------------------------------------------------------------

def test_product_crud_lifecycle(products_page, product_dependencies, product_cleanup):
    """Create -> Search -> View -> Edit -> Re-open View & Verify -> Soft Delete -> Restore"""
    # 1. Create Product
    product_name = generate_random_name("life_prod")
    products_page.add_product(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
        cost_price="200",
        selling_price="300",
    )
    product_cleanup.append(product_name)

    # 2. Search Product
    assert products_page.search_product(product_name), f"Product {product_name} should be searchable"

    # 3. View Original
    assert products_page.view_product(
        product_name,
        expected_brand=product_dependencies["brand"],
        expected_category=product_dependencies["category"],
    ), "Original product brand and category should match in View modal"

    # 4. Edit Product (Name, Cost Price, Selling Price)
    new_name = generate_random_name("edited_prod")
    assert products_page.edit_product(product_name, new_name, new_cost_price="250", new_selling_price="350")
    if product_name in product_cleanup:
        product_cleanup.remove(product_name)
    product_cleanup.append(new_name)

    # 5. Search & View Edited Details
    assert products_page.search_product(new_name)
    assert products_page.view_product(
        new_name,
        expected_brand=product_dependencies["brand"],
        expected_category=product_dependencies["category"],
        expected_cost_price="250",
        expected_selling_price="350",
    ), "Reopened View modal should maintain product relationship details"

    # 6. Soft Delete
    assert products_page.delete_product(new_name), "Product should be soft-deleted"

    # 7. Restore
    assert products_page.retrieve_product(new_name), "Product should be restored"
    assert products_page.search_product(new_name), "Restored product should be visible in list"

    # Rule 2: Cleanup after explicit verification
    if products_page.delete_product(new_name):
        if new_name in product_cleanup:
            product_cleanup.remove(new_name)


def test_opening_stock_update(products_page, product_dependencies, product_cleanup, temp_branch):
    products_page.navigate()
    product_name = generate_random_name("stock_prod")
    products_page.add_product(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
    )
    product_cleanup.append(product_name)
    assert products_page.update_opening_stock(product_name, temp_branch, "10", "2500")
    if products_page.delete_product(product_name):
        if product_name in product_cleanup:
            product_cleanup.remove(product_name)


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_validate_product_required_fields(products_page):
    assert products_page.validate_required_fields()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("cost_price", "-1", id="negative-cost-price"),
        pytest.param("selling_price", "-1", id="negative-selling-price"),
        pytest.param("low_stock", "-1", id="negative-low-stock"),
    ],
)
def test_reject_negative_product_values(
    products_page, product_dependencies, product_cleanup, field, value
):
    product_name = generate_random_name(f"invalid_{field}")
    product_cleanup.append(product_name)
    assert products_page.validate_invalid_numeric_field(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
        field=field,
        value=value,
    ), f"Expected validation feedback for negative {field}"
    if product_name in product_cleanup:
        product_cleanup.remove(product_name)


def test_reject_duplicate_product_name(products_page, product_dependencies, product_cleanup):
    product_name = generate_random_name("dup_prod")
    products_page.add_product(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
    )
    product_cleanup.append(product_name)

    assert products_page.validate_duplicate_product(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
    ), "Expected validation feedback for a duplicate product name"

    if products_page.delete_product(product_name):
        if product_name in product_cleanup:
            product_cleanup.remove(product_name)


# ---------------------------------------------------------------------------
# Dependency-deletion protection tests (Isolated entity creation)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="Bug #TBD: brand assigned to an active product can be deleted"
)
def test_delete_brand_assigned_to_product_is_blocked(
    logged_in_page, product_dependencies, products_page, product_cleanup
):
    brand_page = BrandPage(logged_in_page)
    brand_page.navigate()
    iso_brand = generate_random_name("iso_brand")
    brand_page.add_brand(iso_brand, "isolated brand desc")

    products_page.navigate()
    product_name = generate_random_name("b_dep_prod")
    products_page.add_product(
        name=product_name,
        brand_name=iso_brand,
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
    )
    product_cleanup.append(product_name)

    brand_page.navigate()
    deleted = brand_page.delete_brand(iso_brand)

    # Teardown local entities
    products_page.navigate()
    if products_page.is_product_active(product_name):
        products_page.delete_product(product_name)
        if product_name in product_cleanup:
            product_cleanup.remove(product_name)

    if not deleted:
        brand_page.navigate()
        if brand_page.search_brand(iso_brand):
            brand_page.delete_brand(iso_brand)

    assert not deleted, "An assigned brand must not be deleted"


@pytest.mark.xfail(
    reason="Bug #TBD: brand remains undeletable after its assigned product is deleted"
)
def test_delete_brand_after_assigned_product_is_deleted(
    logged_in_page, product_dependencies, product_cleanup
):
    brand_page = BrandPage(logged_in_page)
    brand_page.navigate()
    brand_name = generate_random_name("del_prod_brand")
    brand_page.add_brand(brand_name, "brand dependency validation")

    product_page = ProductsPage(logged_in_page)
    product_page.navigate()
    product_name = generate_random_name("del_brand_dep_prod")
    product_page.add_product(
        name=product_name,
        brand_name=brand_name,
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
    )
    product_cleanup.append(product_name)

    assert product_page.delete_product(product_name)
    if product_name in product_cleanup:
        product_cleanup.remove(product_name)

    brand_page.navigate()
    deleted = brand_page.delete_brand(brand_name)
    if not deleted:
        try:
            brand_page.delete_brand(brand_name)
        except Exception:
            pass

    assert deleted, "A brand should be deletable after its assigned product is deleted"


@pytest.mark.xfail(reason="Bug #TBD: category assigned to an active product can be deleted")
def test_delete_category_assigned_to_product_is_blocked(
    logged_in_page, product_dependencies, products_page, product_cleanup
):
    category_page = CategoriesPage(logged_in_page)
    category_page.navigate()
    iso_cat = generate_random_name("iso_cat")
    category_page.add_category(name=iso_cat, description="iso desc")

    products_page.navigate()
    product_name = generate_random_name("c_dep_prod")
    products_page.add_product(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=iso_cat,
        hsn_code=product_dependencies["hsn_code"],
        unit_type=product_dependencies["unit_type"],
    )
    product_cleanup.append(product_name)

    category_page.navigate()
    deleted = category_page.delete_category(iso_cat)

    products_page.navigate()
    if products_page.is_product_active(product_name):
        products_page.delete_product(product_name)
        if product_name in product_cleanup:
            product_cleanup.remove(product_name)

    if not deleted:
        category_page.navigate()
        if category_page.search_category(iso_cat):
            category_page.delete_category(iso_cat)

    assert not deleted, "An assigned category must not be deleted"


@pytest.mark.xfail(reason="Bug #TBD: unit type assigned to an active product can be deleted")
def test_delete_unit_type_assigned_to_product_is_blocked(
    logged_in_page, product_dependencies, products_page, product_cleanup
):
    unit_page = UnitTypesPage(logged_in_page)
    unit_page.navigate()
    iso_unit = generate_random_name("iso_unit")
    unit_page.add_unit_type(name=iso_unit, unit="pcs", description="iso desc")

    products_page.navigate()
    product_name = generate_random_name("u_dep_prod")
    products_page.add_product(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=product_dependencies["category"],
        hsn_code=product_dependencies["hsn_code"],
        unit_type=iso_unit,
    )
    product_cleanup.append(product_name)

    unit_page.navigate()
    deleted = unit_page.delete_unit_type(iso_unit)

    products_page.navigate()
    if products_page.is_product_active(product_name):
        products_page.delete_product(product_name)
        if product_name in product_cleanup:
            product_cleanup.remove(product_name)

    if not deleted:
        unit_page.navigate()
        if unit_page.search_unit_type(iso_unit):
            unit_page.delete_unit_type(iso_unit)

    assert not deleted, "An assigned unit type must not be deleted"


@pytest.mark.xfail(reason="Bug #TBD: HSN/SAC code assigned to an active product can be deleted")
def test_delete_hsn_sac_assigned_to_product_is_blocked(
    logged_in_page, product_dependencies, products_page, product_cleanup
):
    hsn_page = SacHsnCodePage(logged_in_page)
    hsn_page.navigate()
    iso_hsn = str(random.randint(100000, 999999))
    hsn_page.add_sac_hsn_code("SAC", iso_hsn, description="iso desc")

    products_page.navigate()
    product_name = generate_random_name("h_dep_prod")
    products_page.add_product(
        name=product_name,
        brand_name=product_dependencies["brand"],
        category_name=product_dependencies["category"],
        hsn_code=iso_hsn,
        unit_type=product_dependencies["unit_type"],
    )
    product_cleanup.append(product_name)

    hsn_page.navigate()
    deleted = hsn_page.delete_sac_hsn_code(iso_hsn)

    products_page.navigate()
    if products_page.is_product_active(product_name):
        products_page.delete_product(product_name)
        if product_name in product_cleanup:
            product_cleanup.remove(product_name)

    if not deleted:
        hsn_page.navigate()
        if hsn_page.search_sac_hsn_code(iso_hsn):
            hsn_page.delete_sac_hsn_code(iso_hsn)

    assert not deleted, "An assigned HSN/SAC code must not be deleted"
