"""Galaxy cities and branches: smoke only, retail covers the deep cases."""
import pytest

from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.cities_page import CitiesPage
from utils.random_data import generate_random_name

pytestmark = pytest.mark.smoke


@pytest.fixture
def cities_page(galaxy_logged_in_page, tenant):
    page_obj = CitiesPage(galaxy_logged_in_page, tenant)
    page_obj.navigate()
    return page_obj


def test_city_create_search_delete(cities_page, cleanup):
    name = cities_page.add_city(generate_random_name("GalaxyCity"))
    cleanup(f"city {name}", lambda: cities_page.ensure_deleted(name))

    assert cities_page.search_city(name)
    assert cities_page.delete_city(name)


def test_branch_create_search_delete(cities_page, galaxy_logged_in_page, tenant, cleanup):
    city_name = cities_page.add_city(generate_random_name("GalaxyCity"))
    cleanup(f"city {city_name}", lambda: cities_page.ensure_deleted(city_name))

    branches_page = BranchesPage(galaxy_logged_in_page, tenant)
    branch_name = branches_page.add_branch(city_name=city_name, name=generate_random_name("GalaxyBranch"))
    cleanup(f"branch {branch_name}", lambda: branches_page.ensure_deleted(branch_name))

    branches_page.navigate()
    assert branches_page.search_branch(branch_name)
    assert branches_page.delete_branch(branch_name)
