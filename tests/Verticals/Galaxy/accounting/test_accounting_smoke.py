"""Galaxy smoke for accounting screens: each page loads on the Galaxy tenant."""
import pytest

from pages.accounting.balance_sheet_page import BalanceSheetPage
from pages.accounting.branch_fund_transfers_page import BranchFundTransfersPage
from pages.accounting.cash_flow_page import CashFlowPage
from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.accounting.day_book_page import DayBookPage
from pages.accounting.ledger_statement_page import LedgerStatementPage
from pages.accounting.profit_loss_page import ProfitLossPage
from pages.accounting.trial_balance_page import TrialBalancePage
from pages.accounting.voucher_history_page import VoucherHistoryPage

pytestmark = pytest.mark.smoke

PAGES = {
    "voucher_history": (VoucherHistoryPage, "is_page_visible"),
    "branch_fund_transfers": (BranchFundTransfersPage, "is_branch_fund_transfers_visible"),
    "day_book": (DayBookPage, "is_page_visible"),
    "profit_loss": (ProfitLossPage, "is_page_visible"),
    "trial_balance": (TrialBalancePage, "is_page_visible"),
    "balance_sheet": (BalanceSheetPage, "is_page_visible"),
    "cash_flow": (CashFlowPage, "is_page_visible"),
    "ledger_statement": (LedgerStatementPage, "is_page_visible"),
}


@pytest.mark.parametrize("screen", list(PAGES))
def test_page_loads(screen, galaxy_logged_in_page, tenant):
    page_cls, visible_check = PAGES[screen]
    page_obj = page_cls(galaxy_logged_in_page, tenant)
    page_obj.navigate()

    assert galaxy_logged_in_page.url.startswith(page_obj.url), f"{screen}: redirected to {galaxy_logged_in_page.url}"
    assert getattr(page_obj, visible_check)(), f"{screen}: page did not render on Galaxy"


def test_create_voucher_page_loads(galaxy_logged_in_page, tenant):
    page_obj = CreateVoucherPage(galaxy_logged_in_page, tenant)
    page_obj.navigate()

    assert galaxy_logged_in_page.url.startswith(page_obj.create_voucher_url)
    page_obj.select_voucher_type("Receipt")
    assert page_obj.submit_button().is_visible(), "Receipt Voucher form did not render on Galaxy"
