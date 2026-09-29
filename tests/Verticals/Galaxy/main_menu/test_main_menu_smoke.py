"""Galaxy smoke for main-menu screens that behave like retail: each page loads on the Galaxy tenant."""
import pytest

from pages.main_menu.batches_page import BatchesPage
from pages.main_menu.chits_page import ChitsPage
from pages.main_menu.expenses_page import ExpensesPage
from pages.main_menu.purchase_request_page import PurchaseRequestPage
from pages.main_menu.sales_quotes_page import SalesQuotesPage
from pages.main_menu.stock_transfers_page import StockTransfersPage

pytestmark = pytest.mark.smoke

PAGES = {
    "sales_quotes": (SalesQuotesPage, "is_sales_quotes_visible"),
    "purchase_requests": (PurchaseRequestPage, "is_purchase_requests_visible"),
    "batches": (BatchesPage, "is_batches_visible"),
    "expenses": (ExpensesPage, "is_expenses_visible"),
    "stock_transfers": (StockTransfersPage, "is_stock_transfers_visible"),
    "chits": (ChitsPage, "is_chits_visible"),
}


@pytest.mark.parametrize("screen", list(PAGES))
def test_page_loads(screen, galaxy_logged_in_page, tenant):
    page_cls, visible_check = PAGES[screen]
    page_obj = page_cls(galaxy_logged_in_page, tenant)
    page_obj.navigate()
    galaxy_logged_in_page.wait_for_load_state("networkidle")

    assert galaxy_logged_in_page.url.startswith(page_obj.url), f"{screen}: redirected to {galaxy_logged_in_page.url}"
    assert getattr(page_obj, visible_check)(), f"{screen}: page did not render on Galaxy"
