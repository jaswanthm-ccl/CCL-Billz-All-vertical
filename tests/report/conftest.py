"""Reuse completed accounting dependencies for report lifecycle tests."""

import pytest

from pages.main_menu.customers_page import CustomersPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.sales_page import SalesPage
from tests.accounting.conftest import (
    module_bank_account,
    module_branch,
    module_city,
    module_customer,
    module_outstanding_purchase,
    module_outstanding_sale,
    module_product,
    module_product_deps,
    module_supplier,
    voucher_funded_state,
)
from utils.random_data import (
    generate_random_email,
    generate_random_gst,
    generate_random_name,
    generate_random_phone,
    generate_random_postal_code,
)


@pytest.fixture(scope="module")
def gstr_b2b_sale(
    module_page,
    module_branch,
    module_city,
    module_product,
):
    """Create one same-state, 18% Company sale that must classify as B2B."""
    customer_name = generate_random_name("gstr_b2b_company")
    gstin = generate_random_gst()
    CustomersPage(module_page).add_customer(
        name=customer_name,
        customer_type="Company",
        email=generate_random_email("gstr_b2b"),
        phone=generate_random_phone(),
        city_name=module_city,
        postal_code=generate_random_postal_code(),
        gst_number=gstin,
    )

    products_page = ProductsPage(module_page)
    products_page.navigate()
    products_page.update_opening_stock(
        name=module_product,
        branch_name=module_branch,
        quantity="5",
        cost_price="100",
    )
    SalesPage(module_page).add_sale(
        customer_name=customer_name,
        branch_name=module_branch,
        product_name=module_product,
        quantity=1,
        price="118",
        paid_amount="0",
    )
    return {
        "customer_name": customer_name,
        "gstin": gstin,
        "invoice_total": "118.00",
        "taxable_value": "100.00",
        "cgst": "9.00",
        "sgst": "9.00",
        "igst": "0.00",
    }


@pytest.fixture(scope="module")
def gstr_b2c_sale(
    module_page,
    module_branch,
    module_customer,
    module_product,
):
    """Create one same-state, 18% Person sale that must classify as B2C."""
    products_page = ProductsPage(module_page)
    products_page.navigate()
    products_page.update_opening_stock(
        name=module_product,
        branch_name=module_branch,
        quantity="5",
        cost_price="100",
    )
    SalesPage(module_page).add_sale(
        customer_name=module_customer,
        branch_name=module_branch,
        product_name=module_product,
        quantity=1,
        price="118",
        paid_amount="0",
    )
    return {
        "customer_name": module_customer,
        "branch_name": module_branch,
        "invoice_total": "118.00",
        "taxable_value": "100.00",
        "cgst": "9.00",
        "sgst": "9.00",
        "igst": "0.00",
    }


__all__ = [
    "module_bank_account",
    "module_branch",
    "module_city",
    "module_customer",
    "module_outstanding_purchase",
    "module_outstanding_sale",
    "module_product",
    "module_product_deps",
    "module_supplier",
    "voucher_funded_state",
    "gstr_b2b_sale",
    "gstr_b2c_sale",
]
