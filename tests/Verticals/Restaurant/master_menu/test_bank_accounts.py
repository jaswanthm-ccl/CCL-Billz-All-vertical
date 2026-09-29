"""Restaurant Bank Account lifecycle and validation tests."""

import random

import pytest

from pages.Verticals.Restaurant.master_menu.bank_accounts_page import (
    BankAccountsPage,
)
from utils.random_data import generate_random_name


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_bank_cleanup(res_logged_in_page):
    created_accounts: list[str] = []
    yield created_accounts
    page_obj = BankAccountsPage(res_logged_in_page)
    for name in reversed(created_accounts):
        try:
            page_obj.navigate()
            if page_obj.search_bank_account(name):
                delete_button = page_obj._row(name).locator(
                    'button[title="delete"]:has(i.bi-trash)'
                ).first
                if delete_button.is_visible():
                    page_obj.delete_bank_account(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant bank account {name}: {exc}")


def test_restaurant_bank_account_crud_lifecycle(
    res_logged_in_page, restaurant_bank_cleanup
):
    page_obj = BankAccountsPage(res_logged_in_page)
    page_obj.navigate()
    name = generate_random_name("res_bank")
    branch = generate_random_name("res_bank_branch")
    account_number = str(random.randint(100000000000, 999999999999))
    page_obj.add_bank_account(name, branch, account_number, "IDFC0000899")
    restaurant_bank_cleanup.append(name)
    assert page_obj.search_bank_account(name)
    assert page_obj.view_bank_account(name)

    updated_name = generate_random_name("res_updated_bank")
    updated_branch = generate_random_name("res_updated_bank_branch")
    updated_account = str(random.randint(100000000000, 999999999999))
    assert page_obj.edit_bank_account(
        name,
        updated_name,
        new_branch=updated_branch,
        new_account_number=updated_account,
        new_ifsc="HDFC0001234",
    )
    restaurant_bank_cleanup.remove(name)
    restaurant_bank_cleanup.append(updated_name)
    assert page_obj.view_bank_account(
        updated_name,
        expected_branch=updated_branch,
        expected_account_number=updated_account,
        expected_ifsc="HDFC0001234",
    )
    assert page_obj.delete_bank_account(updated_name)
    assert page_obj.retrieve_bank_account(updated_name)


def test_restaurant_bank_account_required_fields(res_logged_in_page):
    page_obj = BankAccountsPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_fields()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("account_number", "ABC123"),
        ("ifsc_code", "INVALID"),
    ],
)
def test_restaurant_bank_account_rejects_invalid_format(
    res_logged_in_page, field, value
):
    page_obj = BankAccountsPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_invalid_format(field, value)
