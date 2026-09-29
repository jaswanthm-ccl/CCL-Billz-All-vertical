"""Shared setup for Restaurant accounting report integration tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import random
from urllib.parse import parse_qs, urlparse

import pytest

from pages.Verticals.Restaurant.main_menu.billing_page import POSBillingPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.master_menu.roles_page import RolesPage
from pages.Verticals.Restaurant.master_menu.users_page import UsersPage
from utils.random_data import (
    generate_random_email,
    generate_random_name,
    generate_random_password,
)


@pytest.fixture(scope="session")
def res_incentive_sale(
    browser,
    res_auth_state,
    res_branch,
    res_category,
    res_department,
    res_unit_type,
):
    """Create one eligible staff sale reused by all three incentive reports."""
    context = browser.new_context(
        storage_state=res_auth_state,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()
    role_name = generate_random_name("res_incentive_role")
    employee_name = generate_random_name("res_incentive_staff")
    dish_name = generate_random_name("res_incentive_dish")

    billing = POSBillingPage(page)
    with page.expect_response(
        lambda response: (
            response.request.method == "GET"
            and "/lists/waiters" in response.url
            and "branch_id=" in response.url
        ),
        timeout=15000,
    ) as initial_waiter_response_info:
        billing.navigate()
    waiter_query = parse_qs(urlparse(initial_waiter_response_info.value.url).query)
    pos_branch_id = int(waiter_query["branch_id"][0])

    roles = RolesPage(page)
    roles.navigate()
    roles.add_role_with_permissions(role_name, ["calculate_incentive"])

    users = UsersPage(page)
    users.navigate()
    submitted_user = users.add_user(
        name=employee_name,
        email=generate_random_email("res_incentive"),
        password=generate_random_password(),
        branch_name=None,
        role_name=role_name,
        branch_id=pos_branch_id,
        can_login=False,
        user_code=str(random.randint(100000, 999999)),
    )

    products = ProductsPage(page)
    products.navigate()
    dish_code = products.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="180",
        product_type="Finished good",
        incentive_percentage="5",
    )

    with page.expect_response(
        lambda response: (
            response.request.method == "GET"
            and "/lists/waiters" in response.url
        ),
        timeout=15000,
    ) as waiter_response_info:
        billing.navigate()
    waiter_payload = waiter_response_info.value.json()
    waiters = waiter_payload.get("data") or []
    assert any(row.get("name") == employee_name for row in waiters), (
        f"Eligible staff '{employee_name}' was excluded from POS waiters. "
        f"Waiter request: {waiter_response_info.value.url}; "
        f"submitted user: {submitted_user}; waiters: {waiters}"
    )
    billing.select_bill_tab("Bill 1")
    billing.select_order_type("Dine In")
    billing.select_waiter(employee_name)
    billing.enter_dish_by_code(dish_code, dish_name=dish_name)
    sale = billing.settle_and_bill()
    sale_id = sale.get("id")
    identifiers = [
        str(value)
        for value in (
            sale.get("order_token"),
            sale.get("invoice_id"),
            sale.get("invoice_no"),
            sale_id,
        )
        if value
    ]
    assert sale_id and identifiers, f"Incentive sale lacked identity: {sale}"
    billing.collect_cash_payment(identifiers)

    yield {
        "employee": employee_name,
        "branch": submitted_user["_branch_name"],
        "date": date.today().isoformat(),
        "month": date.today().strftime("%b %Y"),
        "sales": Decimal("180.00"),
        "incentive": Decimal("9.00"),
        "bills": 1,
        "sale_id": str(sale_id),
    }

    # These records are retained because the sale is accounting history.
    context.close()
