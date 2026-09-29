import pytest
from pages.auth.login_page import LoginPage
from utils.res_constants import (
    RESTAURANT_BASE_URL,
    RESTAURANT_USER_1_EMAIL,
    RESTAURANT_USER_1_PASSWORD,
    RESTAURANT_TEST_TABLE,
)
from utils.tenants import RESTAURANT


@pytest.fixture(scope="session")
def res_auth_state(browser):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    login_page = LoginPage(page)
    page.goto(RESTAURANT_BASE_URL + "/login", wait_until="domcontentloaded")
    login_page.login(RESTAURANT_USER_1_EMAIL, RESTAURANT_USER_1_PASSWORD)
    page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
    page.wait_for_load_state("networkidle")
    storage_state = context.storage_state()
    context.close()
    yield storage_state


@pytest.fixture
def res_logged_in_page(browser, res_auth_state, request):
    context = browser.new_context(
        storage_state=res_auth_state,
        ignore_https_errors=True,
        viewport={
            "width": 1280,
            "height": 720,
        },
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def seeded_res_table(browser, res_auth_state):
    from pages.Verticals.Restaurant.main_menu.tables_page import TablesPage

    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()
    table_page = TablesPage(page)
    table_page.navigate()

    # Fast-check: if table already exists, reuse it immediately with 0 overhead
    if not table_page.is_table_visible(RESTAURANT_TEST_TABLE):
        table_page.add_table(name=RESTAURANT_TEST_TABLE, capacity="4")

    context.close()
    yield RESTAURANT_TEST_TABLE


@pytest.fixture(scope="session")
def res_branch(browser, res_auth_state):
    """Creates a dedicated branch inside the restaurant app and cleans it up after the session."""
    from utils.random_data import (
        generate_random_name,
        generate_random_code,
        generate_random_address,
        generate_random_phone,
        generate_random_email,
        generate_random_postal_code,
    )
    from pages.master_menu.branches_page import BranchesPage
    from pages.master_menu.cities_page import CitiesPage

    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()

    # 1. Create a City inside the Restaurant app
    page.goto(f"{RESTAURANT_BASE_URL}/cities")
    page.wait_for_load_state("networkidle")
    city_name = f"ResCity_{generate_random_code('C')}"
    page.get_by_role("button", name="Add City").click()
    page.locator(".react-select__input-container").nth(1).click()
    page.get_by_role("option", name="Tamil Nadu").click()
    page.locator('input[name="name"]').fill(city_name)
    page.get_by_role("button", name="Create").click()
    page.wait_for_timeout(1000)

    # 2. Create a Branch inside the Restaurant app
    page.goto(f"{RESTAURANT_BASE_URL}/branches")
    page.wait_for_load_state("networkidle")
    branch_name = generate_random_name("ResBranch")
    page.get_by_role("button", name="Add Branch").click()
    page.locator('input[name="name"]').fill(branch_name)
    page.locator('input[name="code"]').fill(generate_random_code("BR"))
    page.locator('input[name="address"]').fill(generate_random_address())
    page.locator("input[name='state_id']").locator("xpath=..").locator(".react-select__input-container").click()
    page.get_by_role("option", name="Tamil Nadu").click()
    city_container = page.locator("input[name='city_id']").locator("xpath=..").locator(".react-select__input-container")
    city_container.click()
    page.keyboard.type(city_name)
    page.get_by_role("option", name=city_name, exact=False).first.click()
    page.locator('input[name="postal_code"]').fill(generate_random_postal_code())
    page.get_by_role("textbox", name="Enter 10-digit phone number").fill(generate_random_phone())
    page.locator('input[name="email"]').fill(generate_random_email())
    page.get_by_role("button", name="Create").click()
    page.get_by_text("Branch created successfully.").wait_for(state="visible", timeout=5000)
    context.close()

    yield branch_name

    # Session Teardown
    td_context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    td_page = td_context.new_page()
    try:
        bp = BranchesPage(td_page, RESTAURANT)
        bp.navigate()
        bp.delete_branch(branch_name)

        cp = CitiesPage(td_page, RESTAURANT)
        cp.navigate()
        cp.delete_city(city_name)
    except Exception as e:
        print(f"Teardown warning (res_branch {branch_name}): {e}")
    finally:
        td_context.close()


@pytest.fixture(scope="session")
def res_department(browser, res_auth_state):
    """Creates a dedicated department inside the restaurant app database and cleans it up after the session."""
    from pages.Verticals.Restaurant.main_menu.departments_page import DepartmentsPage
    from utils.random_data import generate_random_name

    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()
    dept_page = DepartmentsPage(page)
    dept_page.navigate()
    dept_name = generate_random_name("Kitchen")
    dept_page.add_department(name=dept_name)
    context.close()

    yield dept_name

    # Session Teardown
    td_context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    td_page = td_context.new_page()
    try:
        td_dept_page = DepartmentsPage(td_page)
        td_dept_page.navigate()
        td_dept_page.delete_department(name=dept_name)
    except Exception as e:
        print(f"Teardown warning (res_department {dept_name}): {e}")
    finally:
        td_context.close()


@pytest.fixture(scope="session")
def res_category(browser, res_auth_state):
    """Creates a dedicated category inside the restaurant app database and cleans it up after the session."""
    from pages.master_menu.categories_page import CategoriesPage
    from utils.random_data import generate_random_name

    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()
    cat_page = CategoriesPage(page, RESTAURANT)
    cat_page.navigate()
    cat_name = generate_random_name("FoodCat")
    cat_page.add_category(name=cat_name)
    context.close()

    yield cat_name

    # Session Teardown
    td_context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    td_page = td_context.new_page()
    try:
        td_cat_page = CategoriesPage(td_page, RESTAURANT)
        td_cat_page.navigate()
        td_cat_page.delete_category(cat_name)
    except Exception as e:
        print(f"Teardown warning (res_category {cat_name}): {e}")
    finally:
        td_context.close()


@pytest.fixture(scope="session")
def res_unit_type(browser, res_auth_state):
    """Creates a dedicated unit type inside the restaurant app database and cleans it up after the session."""
    from pages.master_menu.unit_types_page import UnitTypesPage
    from utils.random_data import generate_random_name, generate_random_code

    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()
    unit_page = UnitTypesPage(page, RESTAURANT)
    unit_page.navigate()
    unit_name = generate_random_name("UnitKg")
    unit_symbol = generate_random_code("UK")
    unit_page.add_unit_type(name=unit_name, unit=unit_symbol, description="Unit for recipes")
    context.close()

    yield unit_name

    # Session Teardown
    td_context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    td_page = td_context.new_page()
    try:
        td_unit_page = UnitTypesPage(td_page, RESTAURANT)
        td_unit_page.navigate()
        td_unit_page.delete_unit_type(unit_name)
    except Exception as e:
        print(f"Teardown warning (res_unit_type {unit_name}): {e}")
    finally:
        td_context.close()


@pytest.fixture(scope="session")
def res_supplier(browser, res_auth_state):
    """Creates a dedicated supplier inside the restaurant app database and cleans it up after the session."""
    from pages.main_menu.suppliers_page import SuppliersPage
    from utils.random_data import generate_random_name, generate_random_phone, generate_random_email, generate_random_address

    context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    page = context.new_page()
    supp_page = SuppliersPage(page)
    supp_page.url = f"{RESTAURANT_BASE_URL}/suppliers"
    supp_page.navigate()
    supp_name = generate_random_name("ResSupp")
    supp_page.add_supplier(
        name=supp_name,
        contact_person=f"{supp_name} Contact",
        email=generate_random_email(),
        phone=generate_random_phone(),
        address=generate_random_address(),
    )
    context.close()

    yield supp_name

    # Session Teardown
    td_context = browser.new_context(storage_state=res_auth_state, ignore_https_errors=True)
    td_page = td_context.new_page()
    try:
        td_supp_page = SuppliersPage(td_page)
        td_supp_page.url = f"{RESTAURANT_BASE_URL}/suppliers"
        td_supp_page.navigate()
        td_supp_page.delete_supplier(supp_name)
    except Exception as e:
        print(f"Teardown warning (res_supplier {supp_name}): {e}")
    finally:
        td_context.close()
