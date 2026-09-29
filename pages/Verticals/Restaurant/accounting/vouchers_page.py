"""Restaurant Voucher History page object."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

from pages.accounting.voucher_history_page import VoucherHistoryPage
from utils.res_constants import RESTAURANT_BASE_URL


class VouchersPage(VoucherHistoryPage):
    """Use the shared Voucher History contract against the Restaurant tenant."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.create_url = f"{RESTAURANT_BASE_URL}/vouchers/create"
        self.history_url = f"{RESTAURANT_BASE_URL}/vouchers/history"
        self.url = self.history_url

    def navigate_create(self) -> None:
        self.page.goto(self.create_url)
        self.page.wait_for_load_state("networkidle")

    def navigate_history(self) -> None:
        self.navigate()

    def include_system_vouchers(self) -> None:
        label = self.page.get_by_text(
            re.compile(r"Include system vouchers", re.IGNORECASE)
        ).first
        checkbox = label.locator("xpath=..").locator("input[type='checkbox']")
        if checkbox.count() == 0:
            checkbox = self.page.locator(
                "input.form-check-input[type='checkbox']"
            ).first
        checkbox.wait_for(state="visible", timeout=5000)
        if not checkbox.is_checked():
            checkbox.check()
            self.page.wait_for_timeout(500)
            self.page.wait_for_load_state("networkidle")

    def row_for_voucher(self, voucher_type: str, amount: str) -> Locator:
        row = (
            self.page.locator("table tbody tr")
            .filter(has_text=voucher_type)
            .filter(has_text=amount)
            .first
        )
        row.wait_for(state="visible", timeout=10000)
        return row

    def get_voucher_row(self, voucher_type: str, amount: str) -> dict[str, str]:
        row = self.row_for_voucher(voucher_type, amount)
        cells = row.locator("td").all_inner_texts()
        return {
            "voucher_no": cells[0].strip() if len(cells) > 0 else "",
            "type": cells[1].strip() if len(cells) > 1 else "",
            "source": cells[2].strip() if len(cells) > 2 else "",
            "bill": cells[3].strip() if len(cells) > 3 else "",
            "amount": cells[4].strip() if len(cells) > 4 else "",
            "status": cells[5].strip() if len(cells) > 5 else "",
        }

    def open_voucher(self, voucher_type: str, amount: str) -> str:
        row = self.row_for_voucher(voucher_type, amount)
        voucher_no = row.locator("td").first.inner_text().strip()
        action = row.locator(
            "td:first-child a, button[title='View'], a[title='View'], "
            "button[title='view'], a[title='view']"
        ).first
        action.wait_for(state="visible", timeout=5000)
        action.click()
        self.page.wait_for_url(
            lambda url: "/vouchers/" in url and "/history" not in url,
            timeout=10000,
        )
        self.page.get_by_role("heading", name="Ledger entries", exact=True).wait_for(
            state="visible", timeout=10000
        )
        return voucher_no
