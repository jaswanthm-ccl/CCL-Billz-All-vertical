"""Restaurant Universal Voucher creation and accounting coverage."""

from __future__ import annotations

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.Verticals.Restaurant.accounting.create_voucher_page import CreateVoucherPage
from pages.Verticals.Restaurant.accounting.vouchers_page import VouchersPage
from pages.Verticals.Restaurant.main_menu.customers_page import CustomersPage
from pages.Verticals.Restaurant.main_menu.outdoor_billing_page import OutdoorBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from utils.models import VoucherResult
from utils.random_data import generate_random_name


pytestmark = pytest.mark.restaurant


@pytest.fixture(scope="module")
def res_voucher_state(
    browser,
    res_auth_state,
    res_branch,
    res_supplier,
    res_category,
    res_unit_type,
    res_department,
):
    """Create one reusable customer bill and supplier bill for this module."""
    context = browser.new_context(
        storage_state=res_auth_state,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()
    customer_name = generate_random_name("voucher_customer")
    dish_name = generate_random_name("voucher_dish")
    raw_material = generate_random_name("voucher_raw")
    purchase_reference = generate_random_name("voucher_purchase")

    customers = CustomersPage(page)
    customers.navigate()
    customers.add_customer(name=customer_name)

    products = ProductsPage(page)
    products.navigate()
    products.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="300",
        product_type="Finished good",
    )
    products.navigate()
    products.add_product(
        name=raw_material,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        product_type="Raw material",
    )

    outdoor = OutdoorBillingPage(page)
    outdoor.navigate()
    outdoor.create_booking(
        branch_name=res_branch,
        dish_name=dish_name,
        customer_name=customer_name,
        quantity="1",
        unit_price="300",
        advance_amount="0",
        advance_notes="Restaurant receipt voucher automation",
    )
    outdoor.navigate()
    outdoor.create_booking(
        branch_name=res_branch,
        dish_name=dish_name,
        quantity="1",
        unit_price="500",
        advance_amount="500",
        advance_notes="Fund branch Cash Ledger for Payment Voucher automation",
    )

    purchases = PurchasesPage(page)
    purchases.navigate()
    purchase = purchases.add_purchase(
        supplier=res_supplier,
        branch=res_branch,
        reference_no=purchase_reference,
        paid_amount="0",
        purchase_type="Credit",
        products_data=[
            {"product": raw_material, "quantity": "1", "price": "200"}
        ],
    )
    assert purchase.reference_no == purchase_reference
    assert purchase.total_amount == Decimal("200")

    yield {
        "customer": customer_name,
        "supplier": res_supplier,
        "branch": res_branch,
        "sale_amount": "300",
        "purchase_amount": "200",
        "purchase_reference": purchase_reference,
    }

    # These records have accounting history and are intentionally retained.
    context.close()


def assert_voucher_detail(
    page,
    result: VoucherResult,
    expected_ledgers: tuple[str, str],
) -> None:
    """Prove the created voucher is auditable and double-entry balanced."""
    assert result.voucher_id, "Voucher API response must include an ID"
    assert result.voucher_no, "Voucher API response must include a voucher number"

    history = VouchersPage(page)
    history.navigate_history()
    assert history.view_voucher_by_number(result.voucher_no), (
        f"Voucher {result.voucher_no} was not found in Voucher History"
    )

    detail = page.locator("body").inner_text()
    assert result.voucher_no in detail
    for ledger in expected_ledgers:
        assert ledger.lower() in detail.lower(), (
            f"Voucher {result.voucher_no} does not show ledger '{ledger}'"
        )
    assert "DR" in detail and "CR" in detail
    formatted_amount = f"{result.amount:,.2f}"
    assert detail.count(formatted_amount) >= 2, (
        f"Voucher {result.voucher_no} must show equal {formatted_amount} "
        "debit and credit entries"
    )


class TestRestaurantPaymentVoucher:
    def test_restaurant_payment_voucher_creation(
        self, res_logged_in_page, res_voucher_state
    ):
        voucher_page = CreateVoucherPage(res_logged_in_page)
        result = voucher_page.create_payment_voucher(
            supplier_ledger=res_voucher_state["supplier"],
            cash_bank_ledger="Cash Ledger",
            amount="100",
            branch=res_voucher_state["branch"],
            allocation="auto",
            remarks="Restaurant Payment Voucher automation",
        )

        assert_voucher_detail(
            res_logged_in_page,
            result,
            (res_voucher_state["supplier"], "Cash Ledger"),
        )


class TestRestaurantReceiptVoucher:
    def test_restaurant_receipt_voucher_creation(
        self, res_logged_in_page, res_voucher_state
    ):
        voucher_page = CreateVoucherPage(res_logged_in_page)
        result = voucher_page.create_receipt_voucher(
            customer_ledger=res_voucher_state["customer"],
            cash_bank_ledger="Cash Ledger",
            amount="100",
            branch=res_voucher_state["branch"],
            allocation="auto",
            remarks="Restaurant Receipt Voucher automation",
        )

        assert_voucher_detail(
            res_logged_in_page,
            result,
            (res_voucher_state["customer"], "Cash Ledger"),
        )


class TestRestaurantContraVoucher:
    def test_restaurant_contra_voucher_creation(self, res_logged_in_page):
        voucher_page = CreateVoucherPage(res_logged_in_page)
        result = voucher_page.create_contra_voucher(
            preset="cash_to_bank",
            amount="1",
            remarks="Restaurant Contra Voucher automation",
        )

        assert_voucher_detail(
            res_logged_in_page,
            result,
            (result.debit_ledger, result.credit_ledger),
        )


class TestRestaurantJournalVoucher:
    def test_restaurant_journal_balanced_entry(
        self, res_logged_in_page, res_voucher_state
    ):
        voucher_page = CreateVoucherPage(res_logged_in_page)
        result = voucher_page.create_journal_voucher(
            entries=[
                {
                    "ledger": res_voucher_state["supplier"],
                    "type": "debit",
                    "amount": "10",
                },
                {
                    "ledger": res_voucher_state["customer"],
                    "type": "credit",
                    "amount": "10",
                },
            ],
            remarks="Restaurant balanced Journal Voucher automation",
        )

        assert_voucher_detail(
            res_logged_in_page,
            result,
            (res_voucher_state["supplier"], res_voucher_state["customer"]),
        )

    def test_restaurant_journal_unbalanced_entry_rejected(
        self, res_logged_in_page, res_voucher_state
    ):
        voucher_page = CreateVoucherPage(res_logged_in_page)
        voucher_page.navigate_journal()
        voucher_page._fill_journal_line(
            0, res_voucher_state["supplier"], "debit", "20"
        )
        voucher_page._fill_journal_line(
            1, res_voucher_state["customer"], "credit", "10"
        )

        assert voucher_page.is_unbalanced_error_visible()
        assert not voucher_page.is_submit_enabled()

    def test_restaurant_journal_add_and_remove_lines(self, res_logged_in_page):
        voucher_page = CreateVoucherPage(res_logged_in_page)
        voucher_page.navigate_journal()
        rows = voucher_page._journal_rows()
        initial_count = rows.count()

        voucher_page._add_journal_line()
        expect(rows).to_have_count(initial_count + 1)

        voucher_page._remove_journal_line(initial_count)
        expect(rows).to_have_count(initial_count)

    def test_restaurant_journal_zero_amount_rejected(
        self, res_logged_in_page, res_voucher_state
    ):
        voucher_page = CreateVoucherPage(res_logged_in_page)
        voucher_page.navigate_journal()
        voucher_page._fill_journal_line(
            0, res_voucher_state["supplier"], "debit", "0"
        )
        voucher_page._fill_journal_line(
            1, res_voucher_state["customer"], "credit", "0"
        )

        assert not voucher_page.is_submit_enabled()
