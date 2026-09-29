"""Restaurant SAC/HSN Code lifecycle and validation tests."""

import random
import string

import pytest

from pages.Verticals.Restaurant.master_menu.sac_hsn_code_page import SacHsnCodePage
from utils.random_data import generate_random_description


pytestmark = pytest.mark.restaurant


def generate_random_numeric_code() -> str:
    return str(random.randint(100000, 999999))


@pytest.fixture
def restaurant_sac_hsn_cleanup(res_logged_in_page):
    created_codes: list[str] = []
    yield created_codes

    page_obj = SacHsnCodePage(res_logged_in_page)
    for code in reversed(created_codes):
        try:
            page_obj.navigate()
            if page_obj.search_sac_hsn_code(code):
                delete_button = page_obj._row(code).locator(
                    'button[title="delete"]:has(i.bi-trash)'
                ).first
                if delete_button.is_visible():
                    page_obj.delete_sac_hsn_code(code)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant SAC/HSN code {code}: {exc}")


def test_restaurant_sac_hsn_crud_lifecycle(
    res_logged_in_page, restaurant_sac_hsn_cleanup
):
    page_obj = SacHsnCodePage(res_logged_in_page)
    page_obj.navigate()

    code = generate_random_numeric_code()
    description = generate_random_description("restaurant_sac_hsn")
    response = page_obj.add_sac_hsn_code(
        "SAC", code, description=description, sort_order=5
    )
    assert response.status in {200, 201}
    restaurant_sac_hsn_cleanup.append(code)
    assert page_obj.search_sac_hsn_code(code)
    assert page_obj.view_sac_hsn_code(code)

    updated_code = generate_random_numeric_code()
    updated_description = generate_random_description("restaurant_sac_hsn_updated")
    assert page_obj.edit_sac_hsn_code(
        code,
        updated_code,
        description=updated_description,
        sort_order=6,
    )
    restaurant_sac_hsn_cleanup.remove(code)
    restaurant_sac_hsn_cleanup.append(updated_code)

    assert page_obj.get_edit_values(updated_code) == {
        "code": updated_code,
        "sort_order": "6",
        "description": updated_description,
    }
    assert page_obj.delete_sac_hsn_code(updated_code)
    assert page_obj.retrieve_sac_hsn_code(updated_code)
    assert page_obj.search_sac_hsn_code(updated_code)


def test_restaurant_sac_hsn_required_code(res_logged_in_page):
    page_obj = SacHsnCodePage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_code()


@pytest.mark.parametrize(
    "invalid_kind",
    [
        pytest.param(
            "alphabetic",
            id="alphabetic",
            marks=pytest.mark.xfail(
                reason="Known product behavior: alphabetic SAC/HSN codes are accepted"
            ),
        ),
        pytest.param(
            "too-short",
            id="too-short",
            marks=pytest.mark.xfail(
                reason="Known product behavior: short SAC/HSN codes are accepted"
            ),
        ),
        pytest.param("too-long", id="too-long"),
    ],
)
def test_restaurant_sac_hsn_rejects_invalid_code(
    res_logged_in_page, restaurant_sac_hsn_cleanup, invalid_kind
):
    page_obj = SacHsnCodePage(res_logged_in_page)
    page_obj.navigate()
    if invalid_kind == "alphabetic":
        invalid_code = "".join(random.choices(string.ascii_uppercase, k=6))
    elif invalid_kind == "too-short":
        invalid_code = str(random.randint(10, 99))
    else:
        invalid_code = str(random.randint(100000000, 999999999))

    restaurant_sac_hsn_cleanup.append(invalid_code)
    assert page_obj.validate_invalid_code(invalid_code), (
        f"Expected visible validation feedback for code {invalid_code!r}"
    )


def test_restaurant_sac_hsn_rejects_invalid_sort_order(res_logged_in_page):
    page_obj = SacHsnCodePage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_invalid_sort_order("0")


def test_restaurant_sac_hsn_rejects_duplicate_code(
    res_logged_in_page, restaurant_sac_hsn_cleanup
):
    page_obj = SacHsnCodePage(res_logged_in_page)
    page_obj.navigate()

    code = generate_random_numeric_code()
    response = page_obj.add_sac_hsn_code("SAC", code)
    assert response.status in {200, 201}
    restaurant_sac_hsn_cleanup.append(code)
    assert page_obj.validate_duplicate_sac_hsn_code(code), (
        "A duplicate Restaurant SAC/HSN code must be rejected"
    )
