import pytest
from pages.master_menu.emi_providers_page import EmiProvidersPage
from utils.random_data import generate_random_name


@pytest.fixture
def emi_provider_cleanup(logged_in_page):
    created_providers = []
    yield created_providers
    page_obj = EmiProvidersPage(logged_in_page)
    for name in reversed(created_providers):
        try:
            page_obj.navigate()
            if page_obj.search_emi_provider(name):
                row = page_obj._row(name)
                if row.locator('button[title="delete"]:has(i.bi-trash)').is_visible():
                    page_obj.delete_emi_provider(name)
        except Exception as e:
            print(f"Teardown: Failed to delete EMI provider {name}: {e}")


def test_emi_provider_crud_lifecycle(logged_in_page, emi_provider_cleanup):
    """Full E2E CRUD & Soft-Delete Restore Lifecycle for EMI Provider."""
    page_obj = EmiProvidersPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.is_emi_providers_visible(), "EMI Providers page should be visible"

    # 1. Create EMI Provider
    provider_name = generate_random_name("Bajaj_EMI")
    page_obj.add_emi_provider(name=provider_name)
    emi_provider_cleanup.append(provider_name)

    # 2. Search and verify created row
    assert page_obj.search_emi_provider(provider_name), f"EMI Provider {provider_name} should appear in list"

    # 3. View EMI Provider details
    assert page_obj.view_emi_provider(provider_name), f"EMI Provider {provider_name} view modal should display details"

    # 4. Edit EMI Provider
    updated_name = generate_random_name("Bajaj_EMI_Edit")
    assert page_obj.edit_emi_provider(old_name=provider_name, new_name=updated_name)
    emi_provider_cleanup.remove(provider_name)
    emi_provider_cleanup.append(updated_name)
    assert page_obj.search_emi_provider(updated_name), f"Edited EMI Provider {updated_name} should appear in list"

    # 5. Soft Delete EMI Provider
    assert page_obj.delete_emi_provider(updated_name), f"EMI Provider {updated_name} should be soft deleted"

    # 6. Restore Soft-Deleted EMI Provider
    assert page_obj.restore_emi_provider(updated_name), f"EMI Provider {updated_name} should be restored"
    assert page_obj.search_emi_provider(updated_name), f"Restored EMI Provider {updated_name} should be active"

    # Final cleanup delete
    assert page_obj.delete_emi_provider(updated_name)
    emi_provider_cleanup.remove(updated_name)


def test_emi_provider_validation_rules(logged_in_page):
    """Validates required field errors on empty submission."""
    page_obj = EmiProvidersPage(logged_in_page)
    page_obj.navigate()
    
    page_obj.add_button.click()
    page_obj.dialog.get_by_role("button", name="Create").click()
    assert page_obj.dialog.get_by_text("Name is required", exact=False).is_visible()
