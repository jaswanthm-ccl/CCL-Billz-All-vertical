from pathlib import Path
from typing import Callable

import pytest

from tests.Verticals.Galaxy.data_fixtures import (  # noqa: F401  (re-exported as fixtures)
    galaxy_category,
    galaxy_city,
    galaxy_customer,
    galaxy_emi_provider,
    galaxy_serial_product,
    galaxy_stock,
    galaxy_supplier,
)
from utils.auth import login_storage_state
from utils.tenants import GALAXY

GALAXY_TESTS_DIR = Path(__file__).parent


def pytest_collection_modifyitems(config, items):
    # This hook receives every collected item in the session, not only this folder's.
    for item in items:
        if GALAXY_TESTS_DIR in Path(item.path).parents:
            item.add_marker(pytest.mark.galaxy)


@pytest.fixture(scope="session")
def tenant():
    return GALAXY


@pytest.fixture(scope="session")
def galaxy_auth_state(browser, tenant):
    return login_storage_state(browser, tenant)


@pytest.fixture
def galaxy_logged_in_page(browser, galaxy_auth_state):
    context = browser.new_context(
        storage_state=galaxy_auth_state,
        ignore_https_errors=True,
        viewport={"width": 1280, "height": 720},
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def cleanup(galaxy_logged_in_page):
    """Register teardown steps as cleanup(label, fn). They run in reverse order; any failure errors the test."""
    steps: list[tuple[str, Callable[[], object]]] = []
    yield lambda label, fn: steps.append((label, fn))

    failures = []
    for label, fn in reversed(steps):
        try:
            if fn() is False:
                failures.append(f"{label}: returned False")
        except Exception as exc:
            failures.append(f"{label}: {type(exc).__name__}: {exc}")
    if failures:
        pytest.fail("Galaxy cleanup left data behind:\n  " + "\n  ".join(failures), pytrace=False)
