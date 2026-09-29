import random
import pytest
from pages.master_menu.bank_accounts_page import BankAccountPage
from utils.random_data import generate_random_name

@pytest.fixture
def bank_account_cleanup(logged_in_page):
    created_accounts = []
    yield created_accounts
    bank_page = BankAccountPage(logged_in_page)
    for name in created_accounts:
        try:
            bank_page.navigate()
            if bank_page.search_bank_account(name):
                row = bank_page.page.locator("tbody tr").filter(
                    has=bank_page.page.get_by_text(name, exact=True)
                ).first
                if row.locator(
                    'button[title="delete"]:has(i.bi-trash)'
                ).is_visible():
                    bank_page.delete_bank_account(name)
        except Exception as e:
            print(f"Teardown: Failed to delete bank account {name}: {e}")



def test_bank_account_crud_lifecycle(logged_in_page, bank_account_cleanup):
    """ create - search - view - edit - delete - restore """
    page_obj = BankAccountPage(logged_in_page)
    page_obj.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    
    bank_name = generate_random_name("bank")
    branch = generate_random_name("branch")
    acc_num = str(random.randint(100000000000, 999999999999))
    ifsc = "IDFC0000899"

    # create
    page_obj.add_bank_account(bank_name, branch, acc_num, ifsc)
    bank_account_cleanup.append(bank_name)

    #search
    assert page_obj.search_bank_account(bank_name)

    #view
    assert page_obj.view_bank_account(bank_name)

    # edit
    new_name = generate_random_name("edited_bank")
    new_branch = generate_random_name("edited_branch")
    new_acc_num = str(random.randint(100000000000, 999999999999))
    new_ifsc = "HDFC0001234"
    assert page_obj.edit_bank_account(
        bank_name,
        new_name,
        new_branch=new_branch,
        new_account_number=new_acc_num,
        new_ifsc=new_ifsc,
    )
    bank_account_cleanup.remove(bank_name)
    bank_account_cleanup.append(new_name)
    assert page_obj.search_bank_account(new_name)
    assert page_obj.view_bank_account(
        new_name,
        expected_branch=new_branch,
        expected_account_number=new_acc_num,
        expected_ifsc=new_ifsc,
    ), "Edited Bank Account fields should persist in View"

    # soft delete
    assert page_obj.delete_bank_account(new_name)

    #restore
    assert page_obj.retrieve_bank_account(new_name)





def test_validate_bank_account(logged_in_page):
    page_obj = BankAccountPage(logged_in_page)
    page_obj.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    assert page_obj.validate_required_fields()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("account_number", "ABC123", id="invalid-account-number"),
        pytest.param("ifsc_code", "INVALID", id="invalid-ifsc"),
    ],
)
def test_validate_bank_account_formats(logged_in_page, field, value):
    page_obj = BankAccountPage(logged_in_page)
    page_obj.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    assert page_obj.validate_invalid_format(field, value), (
        f"Expected visible validation feedback for invalid {field}"
    )


def test_reject_alphanumeric_bank_account_number(logged_in_page):
    page_obj = BankAccountPage(logged_in_page)
    page_obj.navigate()
    logged_in_page.wait_for_load_state("networkidle")
    assert page_obj.validate_invalid_format("account_number", "78799900ghjg"), (
        "Expected account-number validation because only digits are allowed"
    )
