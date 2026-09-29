import re

from playwright.sync_api import Locator, Page, expect

from utils.constants import BRANCH_FUND_TRANSFERS_URL


class BranchFundTransfersPage:
    """Page object for branch-to-branch cash and bank transfers."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = BRANCH_FUND_TRANSFERS_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.get_by_role("heading", name="Branch fund transfers").wait_for()

    def navigate_create(self) -> None:
        self.page.goto(f"{self.url}/create")
        self.page.get_by_role("button", name="Create transfer").wait_for()

    def is_branch_fund_transfers_visible(self) -> bool:
        return (
            self.page.get_by_role("heading", name="Branch fund transfers").is_visible()
            and self.page.get_by_role("button", name="New transfer").is_visible()
        )

    def _control(self, label: str, selector: str) -> Locator:
        container = self.page.locator("label", has_text=label).first.locator("xpath=..")
        return container.locator(selector).first

    @property
    def source_branch(self) -> Locator:
        return self._control("Source branch", "select")

    @property
    def destination_branch(self) -> Locator:
        return self._control("Destination branch", "select")

    @property
    def transfer_type(self) -> Locator:
        return self._control("Transfer type", "select")

    @property
    def source_bank_account(self) -> Locator:
        return self._control("Source bank account", "select")

    @property
    def destination_bank_account(self) -> Locator:
        return self._control("Destination bank account", "select")

    @property
    def amount(self) -> Locator:
        return self._control("Amount", "input")

    @property
    def remarks(self) -> Locator:
        return self._control("Remarks", "textarea")

    @property
    def available_balance(self) -> Locator:
        return self._control("Available balance", "input")

    @property
    def submit_button(self) -> Locator:
        return self.page.get_by_role("button", name="Create transfer")

    def select_branches(self, source: str, destination: str) -> None:
        self.source_branch.select_option(label=source)
        self.destination_branch.select_option(label=destination)

    def select_transfer_type(
        self,
        transfer_type: str,
        source_bank: str | None = None,
        destination_bank: str | None = None,
    ) -> None:
        self.transfer_type.select_option(transfer_type)
        if transfer_type == "bank":
            expect(self.source_bank_account).to_be_enabled()
            self.source_bank_account.select_option(label=source_bank)
            self.destination_bank_account.select_option(label=destination_bank)

    def wait_for_available_balance(self) -> float:
        expect(self.available_balance).not_to_have_value("—", timeout=10_000)
        value = self.available_balance.input_value().replace(",", "")
        return float(value)

    def create_transfer(
        self,
        source: str,
        destination: str,
        amount: str,
        remarks: str,
        transfer_type: str = "cash",
        source_bank: str | None = None,
        destination_bank: str | None = None,
    ) -> float:
        self.navigate_create()
        self.select_branches(source, destination)
        self.select_transfer_type(transfer_type, source_bank, destination_bank)
        balance_before = self.wait_for_available_balance()
        self.amount.fill(amount)
        self.remarks.fill(remarks)
        expect(self.submit_button).to_be_enabled()
        self.submit_button.click()
        self.page.wait_for_url(re.compile(r"/branch-fund-transfers/?$"), timeout=10_000)
        return balance_before

    def current_balance_for(
        self,
        source: str,
        destination: str,
        transfer_type: str = "cash",
        source_bank: str | None = None,
        destination_bank: str | None = None,
    ) -> float:
        self.navigate_create()
        self.select_branches(source, destination)
        self.select_transfer_type(transfer_type, source_bank, destination_bank)
        return self.wait_for_available_balance()

    def same_branch_error(self) -> Locator:
        return self.page.get_by_text("Source and destination branches must differ.")

    def exceeds_balance_error(self) -> Locator:
        return self.page.get_by_text("Amount exceeds available balance.")

    def search(self, text: str) -> None:
        search = self.page.get_by_placeholder("Search transfer no or remarks...")
        search.fill(text)
        expect(search).to_have_value(text)
        self.page.wait_for_timeout(700)

    def apply_filters(self, source: str, destination: str, transfer_type: str) -> None:
        for label, option in (
            ("Source branch", source),
            ("Destination branch", destination),
            ("Transfer type", transfer_type),
        ):
            control = (
                self.page.locator("label", has_text=label)
                .first.locator("xpath=..")
                .locator('input[role="combobox"]')
            )
            control.click()
            self.page.get_by_role("option", name=option, exact=True).click()
        self.page.get_by_role("button", name="Filter", exact=True).click()
        self.page.wait_for_timeout(700)

    def row_with_text(self, text: str) -> Locator:
        rows = self.page.locator("tbody tr")
        # Remarks are searchable but are not displayed as a list column. Every
        # caller first searches a unique marker, so one row is the read-back contract.
        expect(rows).to_have_count(1, timeout=10_000)
        return rows.first

    def open_details(self, text: str) -> Locator:
        row = self.row_with_text(text)
        expect(row).to_be_visible(timeout=10_000)
        view = row.locator("button[title='view'], button:has(.bi-eye)")
        if view.count() == 0:
            view = row.locator("button").last
        view.click()
        drawer = self.page.locator(".particulars-drawer-document").first
        expect(drawer).to_be_visible(timeout=10_000)
        return drawer

    @staticmethod
    def voucher_totals(drawer: Locator, heading: str) -> tuple[float, float]:
        section = drawer.locator(".card", has_text=heading).first
        text = section.inner_text()
        debit = sum(float(v.replace(",", "")) for v in re.findall(r"Dr .*? — ([\d,]+\.\d{2})", text))
        credit = sum(float(v.replace(",", "")) for v in re.findall(r"Cr .*? — ([\d,]+\.\d{2})", text))
        return debit, credit
