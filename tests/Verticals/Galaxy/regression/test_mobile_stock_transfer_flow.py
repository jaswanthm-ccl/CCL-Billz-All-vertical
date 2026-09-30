"""Galaxy end-to-end: a phone moves to another branch by serial, and each branch sells only what it holds.

1. Two serial-tracked phones are purchased into the Galaxy branch (galaxy_stock fixture).
2. Serial A is transferred to a second branch.
3. Inventory: the Galaxy branch holds only serial B; the second branch holds serial A.
4. The Galaxy branch can no longer sell serial A.
5. The second branch sells serial A, and it leaves that branch's stock.

Stock transfers have no delete in the UI, so they stay on the tenant.
"""
import contextlib

import pytest

from pages.main_menu.inventories_page import InventoriesPage
from pages.main_menu.sales_page import SalesPage
from pages.main_menu.stock_transfers_page import StockTransfersPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH
from utils.galaxy_constants import GALAXY_TRACKED_ATTRIBUTE

pytestmark = pytest.mark.regression

PRICE = "15000"


def test_transferred_serial_moves_branch_and_is_sold_only_there(
    galaxy_logged_in_page, tenant, galaxy_stock, galaxy_second_branch, galaxy_customer
):
    page = galaxy_logged_in_page
    product, serials, _ = galaxy_stock
    moved, stayed = serials

    # 2. Transfer serial A
    transfers_page = StockTransfersPage(page, tenant)
    transfers_page.add_stock_transfer(
        GALAXY_BRANCH, galaxy_second_branch, [{"product": product, "serials": [moved]}], remarks="Galaxy serial transfer",
    )
    sent = transfers_page.last_transfer_response["payload"]["items"][0]
    assert sent.get("unit_attribute_values") == [moved] or sent.get("quantity") == 1, f"Transfer sent: {sent}"

    # 3. Each branch holds its own serial
    inventories_page = InventoriesPage(page, tenant)
    inventories_page.navigate()
    assert inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE, branch=GALAXY_BRANCH) == [stayed]
    inventories_page.navigate()
    assert inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE, branch=galaxy_second_branch) == [moved]

    # 4. The Galaxy branch can't sell the serial it no longer holds
    sales_page = SalesPage(page, tenant)
    with contextlib.suppress(Exception):
        sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[moved])
    assert sales_page.last_sale_response.get("status") not in (200, 201), (
        f"Galaxy branch sold serial {moved} after it was transferred out: {sales_page.last_sale_response}"
    )

    # 5. The second branch sells it
    sales_page.add_sale(galaxy_customer, galaxy_second_branch, PRICE, PRICE, product_name=product, serials=[moved])
    assert sales_page.last_sale_response.get("status") in (200, 201), (
        f"Second branch could not sell transferred serial {moved}: {sales_page.last_sale_response}"
    )
    inventories_page.navigate()
    assert moved not in inventories_page.get_available_units(product, GALAXY_TRACKED_ATTRIBUTE, branch=galaxy_second_branch)
