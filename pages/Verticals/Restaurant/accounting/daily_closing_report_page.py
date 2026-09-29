"""Restaurant Daily Closing Report Page Object.

Route: RES_DAILY_CLOSING_URL (/reports/daily-closing)

Card labels (from source):
  "Total Sales"     → footer.total_sales
  "Total Expenses"  → footer.total_expenses  (label has suffix "(Incl. Indent Usage)")
  "Profit / Loss"   → footer.profit_loss
  "Material Usage"  → footer.indent_usage_amount
"""
from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_DAILY_CLOSING_URL


class DailyClosingReportPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_DAILY_CLOSING_URL
        self.last_report: dict = {}

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def branch_select_control(self) -> Locator:
        return self.page.locator(
            ".filter-item-modern .react-select__control, .react-select__control"
        ).last

    @property
    def search_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"^Search$", re.I)).first

    # ── Filter Actions ───────────────────────────────────────────────────────

    def filter_by_branch(self, branch_name: str | None = None) -> dict:
        """Selects branch (or All Branches) and triggers report search.
        Returns the parsed API response footer dict."""
        if "/reports/daily-closing" not in self.page.url:
            self.navigate()

        if branch_name and branch_name != "All Branches":
            self.branch_select_control.wait_for(state="visible", timeout=5000)
            self.branch_select_control.click()
            self.page.wait_for_timeout(300)
            self.page.keyboard.type(branch_name)
            option = self.page.get_by_role(
                "option", name=branch_name, exact=True
            )
            option.wait_for(state="visible", timeout=5000)
            option.click()
            selected = self.branch_select_control.locator(
                ".react-select__single-value"
            ).inner_text().strip()
            assert selected == branch_name, (
                f"Daily Closing selected '{selected}', expected '{branch_name}'"
            )

        with self.page.expect_response(
            lambda r: "reports/restaurant/daily-closing" in r.url and r.request.method == "GET",
            timeout=15000,
        ) as resp_info:
            self.search_button.click()

        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)

        try:
            body = resp_info.value.json()
            self.last_report = (body.get("data") or {}).get("footer") or {}
        except Exception:
            self.last_report = {}

        return self.last_report

    # ── API-based metric reads (most reliable) ───────────────────────────────

    def get_total_sales(self) -> Decimal:
        """Returns total_sales from the last API response."""
        return Decimal(str(self.last_report.get("total_sales", 0) or 0))

    def get_total_expenses(self) -> Decimal:
        """Returns total_expenses from the last API response."""
        return Decimal(str(self.last_report.get("total_expenses", 0) or 0))

    def get_material_usage(self) -> Decimal:
        """Returns indent_usage_amount from the last API response."""
        return Decimal(str(self.last_report.get("indent_usage_amount", 0) or 0))

    def get_profit_loss(self) -> Decimal:
        """Returns profit_loss from the last API response."""
        return Decimal(str(self.last_report.get("profit_loss", 0) or 0))

    # ── UI card reads (fallback / UI validation) ─────────────────────────────

    def get_card_metric(self, title: str) -> Decimal:
        """Extracts Decimal amount from a summary metric card by its h6 label."""
        # Cards: h6.text-muted (label) + h4 (value) inside .card-body
        card_body = self.page.locator(".card-body").filter(
            has=self.page.locator("h6").filter(has_text=re.compile(title, re.I))
        ).first
        try:
            card_body.wait_for(state="visible", timeout=5000)
            h4 = card_body.locator("h4").first
            text = h4.inner_text()
            match = re.search(r"[\d,]+\.?\d*", text)
            if match:
                return Decimal(match.group(0).replace(",", ""))
        except Exception:
            pass
        return Decimal("0.00")

    def is_page_visible(self) -> bool:
        return (
            self.page.get_by_text("Daily Closing Report", exact=False).first.is_visible()
            and self.search_button.is_visible()
        )
