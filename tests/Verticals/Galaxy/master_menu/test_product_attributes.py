"""Galaxy product unit attributes: the tracked per-unit identifier and other attributes."""
import pytest

from pages.master_menu.product_attributes_page import ProductAttributesPage
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def attributes_page(galaxy_logged_in_page, tenant):
    page_obj = ProductAttributesPage(galaxy_logged_in_page, tenant)
    page_obj.navigate()
    return page_obj


def test_tracked_attribute_is_unique(attributes_page):
    unique_flag = attributes_page.get_unique_flag(GALAXY_TRACKED_ATTRIBUTE)

    assert unique_flag is not None, f"Tracked attribute '{GALAXY_TRACKED_ATTRIBUTE}' is missing on Galaxy"
    assert unique_flag == "yes", (
        f"'{GALAXY_TRACKED_ATTRIBUTE}' must be Unique so one unit can't be stocked or sold twice; "
        f"list shows '{unique_flag}'"
    )


@pytest.mark.parametrize("unique, expected_flag", [(True, "yes"), (False, "no")], ids=["unique", "non-unique"])
def test_create_attribute_records_unique_flag(attributes_page, cleanup, unique, expected_flag):
    name = generate_random_name("galaxy_attr")
    response = attributes_page.add_product_attribute(
        name=name, unique=unique, description=generate_random_description("galaxy_attr_desc")
    )
    cleanup(f"product attribute {name}", lambda: attributes_page.ensure_deleted(name))

    assert response is not None and response.status in (200, 201), "Product attribute create API did not succeed"
    attributes_page.navigate()
    assert attributes_page.get_unique_flag(name) == expected_flag


def test_reject_duplicate_attribute_name(attributes_page, cleanup):
    name = generate_random_name("galaxy_dup_attr")
    attributes_page.add_product_attribute(name=name)
    cleanup(f"product attribute {name}", lambda: attributes_page.ensure_deleted(name))
    attributes_page.navigate()

    assert attributes_page.validate_duplicate_name(name)


def test_reject_duplicate_of_tracked_attribute(attributes_page):
    assert attributes_page.validate_duplicate_name(GALAXY_TRACKED_ATTRIBUTE)


def test_attribute_name_is_required(attributes_page):
    assert attributes_page.validate_required_fields()


def test_reject_overlength_attribute_name(attributes_page):
    assert attributes_page.validate_name_too_long("A" * 256)


@pytest.mark.xfail(
    reason=(
        "App bug: ProductUnitAttributeList.tsx shows the Actions column only when the user LACKS "
        "view/update/delete permissions (inverted canAccess check), so admins can't view, edit or delete"
    )
)
def test_attribute_rows_have_actions(attributes_page):
    assert attributes_page.has_row_actions(GALAXY_TRACKED_ATTRIBUTE)
