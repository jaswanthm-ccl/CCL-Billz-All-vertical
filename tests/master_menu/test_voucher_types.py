import pytest

from pages.master_menu.voucher_types_page import VoucherTypesPage


@pytest.fixture
def voucher_type_rollback(logged_in_page):
    changed: list[tuple[str, dict[str, str | bool]]] = []
    yield changed
    page_obj = VoucherTypesPage(logged_in_page)
    for name, original in reversed(changed):
        try:
            page_obj.navigate()
            page_obj.edit_voucher_type(name, original)
        except Exception as exc:
            print(f"Teardown: Failed to rollback voucher type {name}: {exc}")


def test_voucher_type_configuration_persists(
    logged_in_page, voucher_type_rollback
):
    page_obj = VoucherTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.is_voucher_types_visible()

    name = "Payment Voucher"
    original = page_obj.get_configuration(name)
    voucher_type_rollback.append((name, original))
    updated = {
        "prefix": "QAP" if original["prefix"] != "QAP" else "PAY",
        "numbering_method": "Manual Entry",
        "reset_frequency": "Never",
        "branch_wise_numbering": not bool(original["branch_wise_numbering"]),
        "allow_post_dated": not bool(original["allow_post_dated"]),
        "affects_inventory": not bool(original["affects_inventory"]),
        "is_optional": not bool(original["is_optional"]),
        "print_template": "qa-payment-template",
    }

    assert page_obj.edit_voucher_type(name, updated)
    page_obj.navigate()
    assert page_obj.get_configuration(name) == updated


def test_manual_numbering_disables_reset_frequency(logged_in_page):
    page_obj = VoucherTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.manual_numbering_sets_never("Payment Voucher")


def test_voucher_type_system_fields_are_read_only(logged_in_page):
    page_obj = VoucherTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.display_fields_are_read_only("Payment Voucher")


def test_voucher_type_prefix_validation(logged_in_page):
    page_obj = VoucherTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_prefix_max_length("Payment Voucher")
    assert page_obj.validate_prefix_invalid_pattern("Payment Voucher")

