import random
import string

import pytest

from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from utils.random_data import generate_random_description


def generate_random_numeric_code() -> str:
    return str(random.randint(100000, 999999))


@pytest.fixture
def sac_hsn_cleanup(logged_in_page):
    created_codes: list[str] = []
    yield created_codes
    page_obj = SacHsnCodePage(logged_in_page)
    for code in reversed(created_codes):
        try:
            page_obj.navigate()
            if page_obj.search_sac_hsn_code(code):
                row = page_obj._row(code)
                delete_button = row.locator(
                    'button[title="delete"]:has(i.bi-trash)'
                ).first
                if delete_button.is_visible():
                    page_obj.delete_sac_hsn_code(code)
        except Exception as exc:
            print(f"Teardown: Failed to delete SAC/HSN code {code}: {exc}")


def test_sac_hsn_crud_lifecycle(logged_in_page, sac_hsn_cleanup):
    page_obj = SacHsnCodePage(logged_in_page)
    page_obj.navigate()
    assert page_obj.is_sac_hsn_visible()

    code = generate_random_numeric_code()
    description = generate_random_description("sac_hsn")
    response = page_obj.add_sac_hsn_code(
        "SAC", code, description=description, sort_order=5
    )
    assert response.status in {200, 201}
    sac_hsn_cleanup.append(code)
    assert page_obj.search_sac_hsn_code(code)
    assert page_obj.view_sac_hsn_code(code)

    new_code = generate_random_numeric_code()
    new_description = generate_random_description("sac_hsn_updated")
    assert page_obj.edit_sac_hsn_code(
        code, new_code, description=new_description, sort_order=6
    )
    sac_hsn_cleanup.remove(code)
    sac_hsn_cleanup.append(new_code)

    values = page_obj.get_edit_values(new_code)
    assert values == {
        "code": new_code,
        "sort_order": "6",
        "description": new_description,
    }

    assert page_obj.delete_sac_hsn_code(new_code)
    assert page_obj.retrieve_sac_hsn_code(new_code)
    assert page_obj.search_sac_hsn_code(new_code)


def test_sac_hsn_required_code(logged_in_page):
    page_obj = SacHsnCodePage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_code()


@pytest.mark.parametrize(
    "invalid_kind",
    [
        pytest.param(
            "alphabetic",
            id="alphabetic",
            marks=pytest.mark.xfail(
                reason="Known bug: Alphabetic HSN/SAC codes are accepted"
            ),
        ),
        pytest.param(
            "too-short",
            id="too-short",
            marks=pytest.mark.xfail(
                reason="Known bug: Short HSN/SAC codes are accepted"
            ),
        ),
        pytest.param("too-long", id="too-long"),
    ],
)
def test_validate_sac_hsn_code_format(
    logged_in_page, sac_hsn_cleanup, invalid_kind
):
    page_obj = SacHsnCodePage(logged_in_page)
    page_obj.navigate()
    if invalid_kind == "alphabetic":
        invalid_code = "".join(random.choices(string.ascii_uppercase, k=6))
    elif invalid_kind == "too-short":
        invalid_code = str(random.randint(10, 99))
    else:
        invalid_code = str(random.randint(100000000, 999999999))
    sac_hsn_cleanup.append(invalid_code)
    assert page_obj.validate_invalid_code(invalid_code), (
        f"Expected visible code validation feedback for {invalid_code!r}"
    )


def test_sac_hsn_sort_order_minimum(logged_in_page):
    page_obj = SacHsnCodePage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_invalid_sort_order("0")


def test_duplicate_sac_hsn_code(logged_in_page, sac_hsn_cleanup):
    page_obj = SacHsnCodePage(logged_in_page)
    page_obj.navigate()

    code = generate_random_numeric_code()
    response = page_obj.add_sac_hsn_code("SAC", code)
    assert response.status in {200, 201}
    sac_hsn_cleanup.append(code)

    assert page_obj.validate_duplicate_sac_hsn_code(code), (
        "Expected UI validation feedback and HTTP rejection for duplicate code"
    )
