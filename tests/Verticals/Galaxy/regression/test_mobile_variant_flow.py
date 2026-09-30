"""Galaxy end-to-end: one phone model in two RAM variants, bought and sold per variant by serial.

1. A serial-tracked phone is created with 8GB and 12GB RAM variants.
2. One purchase buys one serial of each variant.
3. Inventory lists each serial under its own variant.
4. The 12GB serial is sold.
5. The 12GB variant has no units left; the 8GB unit is untouched.
"""
import pytest

from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH, new_serials
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE
from utils.random_data import generate_random_code, generate_random_name

pytestmark = pytest.mark.regression


@pytest.fixture
def variant_phone(galaxy_logged_in_page, tenant, galaxy_category, cleanup):
    """(base product name, 8GB variant name, 12GB variant name) of a new serial-tracked phone."""
    products_page = ProductsPage(galaxy_logged_in_page, tenant)
    products_page.navigate()
    name = generate_random_name("galaxy_variant_phone")
    small, large = f"{name} 8GB", f"{name} 12GB"
    response = products_page.add_product(
        name, None, galaxy_category, None, None, "12000", "15000",
        unit_attribute=GALAXY_TRACKED_ATTRIBUTE,
        attribute_keys=["RAM"],
        variants=[
            {"attributes": {"RAM": "8"}, "name": small, "cost_price": "12000", "selling_price": "15000"},
            {"attributes": {"RAM": "12"}, "name": large, "cost_price": "15000", "selling_price": "18000"},
        ],
    )
    assert response is not None and response.ok, "Variant phone setup failed"
    cleanup(f"product {name}", lambda: products_page.ensure_deleted(name))
    return name, small, large


def test_each_variant_keeps_its_own_serials_through_purchase_and_sale(
    galaxy_logged_in_page, tenant, variant_phone, galaxy_supplier, galaxy_customer
):
    page = galaxy_logged_in_page
    base, small, large = variant_phone
    small_serial, large_serial = new_serials(2)

    def units(variant, expected):
        return inventories_page.wait_for_available_units(variant, GALAXY_TRACKED_ATTRIBUTE, expected, search=base)

    # 2. Buy one serial of each variant
    purchases_page = PurchasesPage(page, tenant)
    purchases_page.add_purchase(
        galaxy_supplier, GALAXY_BRANCH, generate_random_code("GLX"), "0", "Cash",
        products_data=[
            {"product": small, "price": "12000", "serials": [small_serial]},
            {"product": large, "price": "15000", "serials": [large_serial]},
        ],
    )
    assert purchases_page.last_purchase_response.get("status") in (200, 201), (
        f"Variant purchase failed: {purchases_page.last_purchase_response}"
    )

    # 3. Each serial sits under its own variant
    inventories_page = InventoriesPage(page, tenant)
    assert units(small, [small_serial]) == [small_serial]
    assert units(large, [large_serial]) == [large_serial]

    # 4. Sell the 12GB phone
    sales_page = SalesPage(page, tenant)
    sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, "18000", "18000", product_name=large, serials=[large_serial])
    assert sales_page.last_sale_response.get("status") in (200, 201), f"Variant sale failed: {sales_page.last_sale_response}"

    # 5. Only the 12GB stock moved
    assert units(large, []) == []
    assert units(small, [small_serial]) == [small_serial]
