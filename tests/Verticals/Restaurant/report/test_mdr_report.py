"""Restaurant POS UPI sale through MDR settlement and report reconciliation."""

from datetime import datetime, time, timedelta
from decimal import Decimal
import random

import pytest

from pages.Verticals.Restaurant.accounting.create_voucher_page import CreateVoucherPage
from pages.Verticals.Restaurant.accounting.vouchers_page import VouchersPage
from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.master_menu.bank_accounts_page import BankAccountsPage
from pages.Verticals.Restaurant.report.mdr_report_page import MdrReportPage
from utils.random_data import generate_random_name


pytestmark = pytest.mark.restaurant


def test_restaurant_pos_upi_mdr_settlement_and_report(
    res_logged_in_page,
    res_category,
    res_department,
    res_unit_type,
):
    page = res_logged_in_page
    yesterday = datetime.combine(datetime.now().date() - timedelta(days=1), time(12))
    today = datetime.combine(datetime.now().date(), time(12))
    settlement_date = today.date().isoformat()
    bank_name = generate_random_name("res_mdr_bank")
    dish_name = generate_random_name("res_mdr_dish")
    narration = generate_random_name("res_mdr_report")

    bank_page = BankAccountsPage(page)
    bank_page.navigate()
    bank_page.add_bank_account(
        bank_name,
        "Restaurant Automation",
        str(random.randint(100000000000, 999999999999)),
        "HDFC0001234",
    )

    # MDR uses the selected bank's previous-day sales. Freeze the browser date
    # while creating and collecting the POS bill, then restore today.
    page.clock.set_fixed_time(yesterday)
    products = ProductsPage(page)
    products.navigate()
    dish_code = products.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="500",
        product_type="Finished good",
    )

    billing = POSBillingPage(page)
    billing.navigate()
    billing.select_bill_tab("Bill 1")
    billing.select_order_type("Dine In")
    billing.select_waiter("Waiter")
    billing.enter_dish_by_code(dish_code, dish_name=dish_name)
    sale = billing.settle_and_bill()
    sale_id = sale.get("id")
    bill_reference = sale.get("invoice_id") or sale.get("invoice_no") or sale_id
    assert sale_id and bill_reference, f"Sale response lacked bill identity: {sale}"
    assert str(sale.get("sale_date", "")).startswith(yesterday.date().isoformat()), sale

    bill_identifiers = [
        str(value)
        for value in (
            sale.get("order_token"),
            sale.get("invoice_id"),
            sale.get("invoice_no"),
            sale_id,
        )
        if value
    ]
    paid_sale = billing.collect_upi_payment(bill_identifiers, bank_name)
    assert Decimal(str(paid_sale.get("paid_amount"))) == Decimal("500")

    page.clock.set_fixed_time(today)
    voucher_page = CreateVoucherPage(page)
    voucher = voucher_page.create_mdr_settlement_voucher(
        bank_ledger=bank_name,
        mdr_amount="2",
        settlement_date=settlement_date,
        expected_gross="500",
        remarks=narration,
    )

    history = VouchersPage(page)
    history.navigate_history()
    assert history.view_voucher_by_number(voucher.voucher_no)
    detail = page.locator("body").inner_text()
    assert bank_name in detail
    assert "Bank Charges Ledger" in detail
    assert "2.00" in detail

    report = MdrReportPage(page)
    report.navigate()
    data = report.apply_filters(
        from_date=settlement_date,
        to_date=settlement_date,
        bank_name=bank_name,
    )
    entry = report.find_entry(data, narration=narration)
    assert entry is not None, "Created Restaurant MDR settlement is missing"
    assert entry["voucher_no"] == voucher.voucher_no
    assert report.amount(entry["gross"]) == Decimal("500.00")
    assert report.amount(entry["net_settlement"]) == Decimal("498.00")
    assert report.amount(entry["mdr_charge"]) == Decimal("2.00")
    assert Decimal(str(entry["mdr_percentage"])) == Decimal("0.4")

    summary = report.find_bank_summary(data, bank_name=bank_name)
    assert summary is not None
    assert summary["voucher_count"] == 1
    assert report.amount(summary["total_gross"]) == Decimal("500.00")
    assert report.amount(summary["total_net_settlement"]) == Decimal("498.00")
    assert report.amount(summary["total_mdr_charge"]) == Decimal("2.00")
