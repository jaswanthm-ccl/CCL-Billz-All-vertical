"""Galaxy EMI providers: finance partners used for EMI sales and reconciliation."""
import pytest

from pages.master_menu.emi_providers_page import EmiProvidersPage
from utils.random_data import generate_random_name


@pytest.fixture
def emi_page(galaxy_logged_in_page, tenant):
    page_obj = EmiProvidersPage(galaxy_logged_in_page, tenant)
    page_obj.navigate()
    return page_obj


def test_create_provider_creates_receivable_ledger(emi_page, cleanup):
    name = generate_random_name("galaxy_emi")
    response = emi_page.add_emi_provider(name)
    cleanup(f"EMI provider {name}", lambda: emi_page.ensure_deleted(name))

    ledger = response.json()["data"]["ledger"]
    assert ledger["name"] == f"{name} Receivable"
    assert ledger["type"] == "emi_provider"
    assert emi_page.get_linked_ledger(name) == f"{name} Receivable"


def test_emi_provider_lifecycle(emi_page, cleanup):
    name = generate_random_name("galaxy_emi")
    emi_page.add_emi_provider(name)
    cleanup(f"EMI provider {name}", lambda: emi_page.ensure_deleted(name))

    assert emi_page.search_emi_provider(name)
    assert emi_page.view_emi_provider(name)

    updated_name = generate_random_name("galaxy_emi_edit")
    assert emi_page.edit_emi_provider(old_name=name, new_name=updated_name)
    cleanup(f"EMI provider {updated_name}", lambda: emi_page.ensure_deleted(updated_name))
    emi_page.navigate()
    assert emi_page.search_emi_provider(updated_name)

    assert emi_page.delete_emi_provider(updated_name)
    emi_page.navigate()
    assert emi_page.is_emi_provider_deleted(updated_name), "Deleted provider should show the restore action"

    assert emi_page.restore_emi_provider(updated_name)
    emi_page.navigate()
    assert not emi_page.is_emi_provider_deleted(updated_name), "Restored provider should be active again"


def test_reject_duplicate_provider_name(emi_page, cleanup):
    name = generate_random_name("galaxy_emi_dup")
    emi_page.add_emi_provider(name)
    cleanup(f"EMI provider {name}", lambda: emi_page.ensure_deleted(name))
    emi_page.navigate()

    assert emi_page.validate_duplicate_name(name)


def test_provider_name_is_required(emi_page):
    emi_page.add_button.click()
    emi_page.dialog.get_by_role("button", name="Create").click()

    assert emi_page.dialog.get_by_text("Name is required", exact=False).is_visible()
