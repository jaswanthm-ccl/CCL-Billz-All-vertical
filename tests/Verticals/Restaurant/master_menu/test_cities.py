"""Restaurant City lifecycle and validation tests."""

import pytest

from pages.Verticals.Restaurant.master_menu.cities_page import CitiesPage
from utils.random_data import generate_random_name


pytestmark = pytest.mark.restaurant


@pytest.fixture
def restaurant_city_cleanup(res_logged_in_page):
    created_cities: list[str] = []
    yield created_cities
    page_obj = CitiesPage(res_logged_in_page)
    for name in reversed(created_cities):
        try:
            page_obj.navigate()
            if page_obj.search_city(name):
                delete_button = page_obj._row(name).locator(
                    'button[title="delete"]:has(i.bi-trash)'
                ).first
                if delete_button.is_visible():
                    page_obj.delete_city(name)
        except Exception as exc:
            print(f"Teardown: failed to delete Restaurant city {name}: {exc}")


def test_restaurant_city_crud_lifecycle(
    res_logged_in_page, restaurant_city_cleanup
):
    page_obj = CitiesPage(res_logged_in_page)
    page_obj.navigate()
    name = page_obj.add_city()
    restaurant_city_cleanup.append(name)
    assert page_obj.search_city(name)

    updated_name = generate_random_name("res_updated_city")
    assert page_obj.edit_city(name, updated_name)
    restaurant_city_cleanup.remove(name)
    restaurant_city_cleanup.append(updated_name)
    assert page_obj.search_city(updated_name)
    assert page_obj.verify_city_name(updated_name)
    assert page_obj.delete_city(updated_name)
    assert page_obj.retrieve_city(updated_name)


def test_restaurant_city_name_is_required(res_logged_in_page):
    page_obj = CitiesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_name()


def test_restaurant_city_name_maximum_length(res_logged_in_page):
    page_obj = CitiesPage(res_logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_name_too_long("C" * 101)


def test_restaurant_city_rejects_duplicate_name(
    res_logged_in_page, restaurant_city_cleanup
):
    page_obj = CitiesPage(res_logged_in_page)
    page_obj.navigate()
    name = generate_random_name("res_duplicate_city")
    page_obj.add_city(name)
    restaurant_city_cleanup.append(name)
    assert page_obj.validate_duplicate_city(name)
