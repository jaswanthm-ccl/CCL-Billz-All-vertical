"""Restaurant Voucher History transaction coverage."""

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.accounting.vouchers_page import VouchersPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.random_data import generate_random_name


pytestmark = pytest.mark.restaurant


def test_purchase_creates_visible_restaurant_system_voucher(
    res_logged_in_page,
    res_branch,
    res_supplier,
    res_category,
    res_department,
    res_unit_type,
):
    """A posted Purchase must create an auditable system Purchase Voucher."""
    product_name = generate_random_name("voucher_history_raw")
    reference = generate_random_name("VH_PUR")
    amount = "125.37"
    products = ProductsPage(res_logged_in_page)
    purchases = PurchasesPage(res_logged_in_page)
    vouchers = VouchersPage(res_logged_in_page)

    products.navigate()
    products.add_product(
        name=product_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        product_type="Raw material",
    )

    result = purchases.add_purchase(
        supplier=res_supplier,
        branch=res_branch,
        reference_no=reference,
        paid_amount="0",
        purchase_type="Credit",
        products_data=[
            {"product": product_name, "quantity": 1, "price": amount}
        ],
    )
    assert result.reference_no == reference
    assert result.total_amount == Decimal(amount)

    vouchers.navigate_history()
    vouchers.include_system_vouchers()
    row = vouchers.get_voucher_row("Purchase Voucher", amount)

    assert row["voucher_no"], "Generated Purchase Voucher number is missing"
    assert row["type"].lower() == "purchase voucher"
    assert row["source"].lower() == "system"
    assert amount in row["amount"]
    assert row["status"].lower() == "active"

    voucher_no = vouchers.open_voucher("Purchase Voucher", amount)
    detail = res_logged_in_page.locator("body").inner_text()
    assert voucher_no in detail
    assert res_supplier in detail
    assert "Purchase Ledger" in detail
    assert "DR" in detail and "CR" in detail
    assert detail.count(amount) >= 2, (
        f"Purchase Voucher must show equal {amount} debit and credit entries"
    )
