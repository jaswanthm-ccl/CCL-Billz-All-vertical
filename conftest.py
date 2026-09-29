import os
import shutil
from urllib.parse import urlparse
import pytest
from pages.auth.login_page import LoginPage
from utils.constants import ADMIN_EMAIL, ADMIN_PASSWORD, BASE_URL


def pytest_configure(config):
    # Safety Check: Mutation Guard & Environment Lockout
    allow_mutating = os.getenv("ALLOW_MUTATING_TESTS", "0")
    test_env = os.getenv("TEST_ENV", "dev").lower()

    hostname = urlparse(BASE_URL).netloc.lower()
    forbidden_terms = ["uat", "prod", "production", "live"]
    if any(term in hostname.split(".") for term in forbidden_terms) or any(term in hostname.split("-") for term in forbidden_terms):
        raise pytest.UsageError(
            f"SAFETY LOCKOUT: Tests are configured against protected host '{hostname}'. "
            f"Automated test execution with mutations is blocked against production/UAT domains."
        )

    if allow_mutating != "1":
        raise pytest.UsageError(
            "SAFETY LOCKOUT: ALLOW_MUTATING_TESTS=1 is required in .env or environment to execute tests."
        )

    if test_env not in ["dev", "staging", "local", "test"]:
        raise pytest.UsageError(
            f"SAFETY LOCKOUT: Invalid TEST_ENV='{test_env}'. Must be one of ['dev', 'staging', 'local', 'test']."
        )


def pytest_addoption(parser):
    parser.addoption(
        "--playback",
        action="store_true",
        default=False,
        help="Enable the interactive draggable playback control panel"
    )


@pytest.fixture(autouse=True, scope="session")
def _playback_control(request):
    ui_enabled = request.config.getoption("--playback", default=False)
    request.config._playback_enabled = ui_enabled
    if ui_enabled:
        from utils.playback import playback
        playback.start()
        yield
        playback.stop()
    else:
        yield

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "ignore_https_errors": True,
        "viewport": {"width": 1280, "height": 720}
    }

@pytest.fixture(scope="session")
def auth_state(browser):
    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720}
    )
    page = context.new_page()
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    page.wait_for_url(lambda url: "/login" not in url, timeout=10000)
    page.wait_for_load_state("networkidle")


    storage_state = context.storage_state()
    context.close()

    yield storage_state

@pytest.fixture
def logged_in_page(browser, auth_state, request):
    video_option = request.config.getoption("--video", default="off")
    context_kwargs = {
        "storage_state": auth_state,
        "ignore_https_errors": True,
        "viewport": {"width": 1280, "height": 720},
    }
    if video_option in ["on", "retain-on-failure"]:
        os.makedirs("videos", exist_ok=True)
        context_kwargs["record_video_dir"] = "videos"
        context_kwargs["record_video_size"] = {"width": 1280, "height": 720}

    context = browser.new_context(**context_kwargs)
    tracing_option = request.config.getoption("--tracing", default="off")
    if tracing_option in ["on", "retain-on-failure"]:
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    yield page
    if tracing_option in ["on", "retain-on-failure"]:
        os.makedirs("test-results", exist_ok=True)
        trace_path = os.path.join("test-results", f"{request.node.name}_trace.zip")
        context.tracing.stop(path=trace_path)
        # Also create root trace.zip for quick one-line inspection
        shutil.copyfile(trace_path, "trace.zip")
    context.close()

@pytest.fixture(scope="module")
def module_page(browser, auth_state, request):
    video_option = request.config.getoption("--video", default="off")
    context_kwargs = {
        "storage_state": auth_state,
        "ignore_https_errors": True,
        "viewport": {"width": 1280, "height": 720},
    }
    if video_option in ["on", "retain-on-failure"]:
        os.makedirs("videos", exist_ok=True)
        context_kwargs["record_video_dir"] = "videos"
        context_kwargs["record_video_size"] = {"width": 1280, "height": 720}

    context = browser.new_context(**context_kwargs)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def funded_bank_account(browser, auth_state):
    """A bank account funded with ₹500 via a small Sale.

    Creates minimal dependencies: 1 product (using existing deps), 1 bank
    account, 1 sale. Uses ₹500 (not ₹100k) to minimise report noise.
    """
    from pages.master_menu.bank_accounts_page import BankAccountPage
    from pages.master_menu.categories_page import CategoriesPage
    from pages.master_menu.brands_page import BrandPage
    from pages.master_menu.unit_types_page import UnitTypesPage
    from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
    from pages.master_menu.branches_page import BranchesPage
    from pages.main_menu.products_page import ProductsPage
    from pages.main_menu.customers_page import CustomersPage
    from pages.main_menu.sales_page import SalesPage
    from utils.random_data import generate_random_name
    import random

    context = browser.new_context(storage_state=auth_state, ignore_https_errors=True)
    page = context.new_page()

    # 1. Branch (own branch to avoid "Main Branch" naming issues)
    branches_page = BranchesPage(page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branches_page.page.get_by_text("Branch created successfully.").wait_for(state="visible", timeout=5000)

    # 2. Product dependencies
    categories_page = CategoriesPage(page)
    categories_page.navigate()
    cat_name = generate_random_name("fund_cat")
    categories_page.add_category(name=cat_name, description="bank funding")
    categories_page.page.get_by_text("Category created successfully").wait_for(state="visible", timeout=5000)

    brand_page = BrandPage(page)
    brand_page.navigate()
    brand_name = generate_random_name("fund_brand")
    brand_page.add_brand(brand_name, "bank funding")

    unit_page = UnitTypesPage(page)
    unit_page.navigate()
    unit_name = generate_random_name("fund_unit")
    unit_page.add_unit_type(name=unit_name, unit="pcs", description="bank funding")

    sac_page = SacHsnCodePage(page)
    sac_page.navigate()
    sac_code = str(random.randint(100000, 999999))
    sac_page.add_sac_hsn_code("SAC", sac_code, description="bank funding")

    products_page = ProductsPage(page)
    products_page.navigate()
    product_name = generate_random_name("fund_prod")
    products_page.add_product(
        name=product_name,
        brand_name=brand_name,
        category_name=cat_name,
        hsn_code=sac_code,
        unit_type=unit_name,
        cost_price="1",
        selling_price="500",
        gst_percentage="18%",
    )

    # 2. Customer
    customers_page = CustomersPage(page)
    customer_name = generate_random_name("fund_cust")
    customers_page.add_customer(name=customer_name)

    # 3. Bank account
    bank_page = BankAccountPage(page)
    bank_page.navigate()
    bank_name = generate_random_name("fund_bank")
    bank_page.add_bank_account(
        bank_name=bank_name,
        branch="Automation Bank Branch",
        account_number=str(random.randint(100000000000, 999999999999)),
        ifsc_code="IDFC0000899",
    )

    # 4. Add opening stock (2 units — one for bank sale, one for cash sale)
    products_page.navigate()
    products_page.update_opening_stock(
        name=product_name,
        branch_name=branch_name,
        quantity="2",
        cost_price="1",
    )

    # 5. Sell one unit via bank — funds the bank account with ₹500
    sales_page = SalesPage(page)
    sales_page.add_sale(
        customer_name=customer_name,
        branch_name=branch_name,
        product_name=product_name,
        price="500",
        paid_amount="500",
        payment_method=bank_name,
    )

    # 6. Sell another unit via cash — funds the branch's cash with ₹500
    sales_page.add_sale(
        customer_name=customer_name,
        branch_name=branch_name,
        product_name=product_name,
        price="500",
        paid_amount="500",
        payment_method="Cash",
    )

    yield {"bank_name": bank_name, "branch_name": branch_name}

    # Sale references keep these undeletable — just close context
    context.close()


@pytest.fixture(autouse=True)
def auto_test_banner(request):
    """Integrates with playback overlay if active (--playback)."""
    playback_enabled = getattr(request.config, "_playback_enabled", False)
    if not playback_enabled:
        return

    # Only run for tests that request a page fixture
    page_fixtures = ["page", "logged_in_page", "module_page"]
    page = None
    for name in page_fixtures:
        if name in request.fixturenames:
            try:
                page = request.getfixturevalue(name)
                break
            except Exception:
                pass

    if not page:
        return

    # Get test name and format it nicely
    test_name = request.node.name
    display_name = test_name.replace("test_", "").replace("_", " ").title()

    try:
        from utils.playback import playback
        playback.test_name = f"Running: {display_name}"
        playback._update(page)
    except Exception:
        pass


@pytest.fixture
def debug_pause(request):
    """A fixture that returns a helper function to pause execution for debugging.
    If running in headed mode, it prompts the user in the terminal to press Enter.
    If a page is passed, it visually highlights the pause on the test name banner.
    """
    def _pause(page=None, duration=None, message="Paused for debugging"):
        import time

        is_headed = False
        try:
            is_headed = request.config.getoption("--headed")
        except Exception:
            pass

        # Update the banner/playback visually to indicate a pause
        if page:
            try:
                page.evaluate(f"""
                    (() => {{
                        const banner = document.getElementById('playwright-test-banner');
                        if (banner) {{
                            banner.innerText = '⏸️ {message}';
                            banner.style.backgroundColor = '#ff9800'; // Orange
                            banner.style.borderBottom = '2px solid #f57c00';
                        }}
                        const pbTitle = document.getElementById('pb-title');
                        if (pbTitle) {{
                            pbTitle.textContent = ' - ⏸️ {message}';
                            pbTitle.style.color = '#ff9800';
                        }}
                    }})()
                """)
            except Exception:
                pass

        print(f"\n[DEBUG PAUSE] {message}")
        if duration is not None:
            print(f"Sleeping for {duration} seconds...")
            time.sleep(duration)
        else:
            if is_headed:
                input(f"Paused: {message}. Press Enter in terminal to continue...")
            else:
                print("Running in headless mode, sleeping for 2 seconds instead of waiting for input...")
                time.sleep(2)

        # Restore original banner/playback status
        if page:
            try:
                test_name = request.node.name
                display_name = test_name.replace("test_", "").replace("_", " ").title()
                page.evaluate(f"""
                    (() => {{
                        const banner = document.getElementById('playwright-test-banner');
                        if (banner) {{
                            banner.innerText = 'Running: {display_name}';
                            banner.style.backgroundColor = '#ffeb3b';
                            banner.style.borderBottom = '2px solid #fbc02d';
                        }}
                        const pbTitle = document.getElementById('pb-title');
                        if (pbTitle) {{
                            pbTitle.textContent = ' - {display_name}';
                            pbTitle.style.color = '#ffeb3b';
                        }}
                    }})()
                """)
            except Exception:
                pass

    return _pause


# Pytest hooks for tracking fixture setup/teardown phases
def pytest_fixture_setup(fixturedef, request):
    """Called before a fixture's setup starts."""
    if getattr(request.config, "_playback_enabled", False):
        try:
            from utils.playback import playback
            playback.test_name = f"Fixture Setup: {fixturedef.argname}"
        except Exception:
            pass


def pytest_runtest_setup(item):
    """Called before a test's setup starts (before running fixtures)."""
    if getattr(item.config, "_playback_enabled", False):
        try:
            from utils.playback import playback
            display_name = item.name.replace("test_", "").replace("_", " ").title()
            playback.test_name = f"Preparing: {display_name}"
        except Exception:
            pass


def pytest_runtest_call(item):
    """Called to run the test case itself."""
    if getattr(item.config, "_playback_enabled", False):
        try:
            from utils.playback import playback
            display_name = item.name.replace("test_", "").replace("_", " ").title()
            playback.test_name = f"Running: {display_name}"
        except Exception:
            pass


def pytest_runtest_teardown(item, nextitem):
    """Called before a test's teardown starts."""
    if getattr(item.config, "_playback_enabled", False):
        try:
            from utils.playback import playback
            display_name = item.name.replace("test_", "").replace("_", " ").title()
            playback.test_name = f"Teardown: {display_name}"
        except Exception:
            pass
