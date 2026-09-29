"""Restaurant Cashier-Wise (Category-Wise) Sales Report Page Object.

Route: RESTAURANT_BASE_URL/reports/category-wise-sales
"""
from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page, Locator
from utils.res_constants import RESTAURANT_BASE_URL


class CategoryWiseSalesReportPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = f"{RESTAURANT_BASE_URL}/reports/category-wise-sales"
        self.last_report: dict = {}

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def cashier_select(self) -> Locator:
        return self.page.locator(".react-select__control").nth(1)

    @property
    def branch_select(self) -> Locator:
        return self.page.locator(".react-select__control").first

    @property
    def search_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Search|Filter", re.I)).first

    # ── Actions ─────────────────────────────────────────────────────────────

    def filter_report(
        self,
        cashier_name: str | None = None,
        branch_name: str | None = None,
    ) -> None:
        if cashier_name and cashier_name != "All Cashiers":
            try:
                if self.cashier_select.is_visible():
                    self.cashier_select.click()
                    self.page.wait_for_timeout(200)
                    opt = self.page.get_by_role("option", name=cashier_name, exact=False).first
                    if opt.count() > 0 and opt.is_visible():
                        opt.click()
                    else:
                        self.page.locator(".react-select__option").first.click()
            except Exception:
                pass

        if branch_name and branch_name != "All Branches":
            self.branch_select.wait_for(state="visible", timeout=5000)
            self.branch_select.click()
            option = self.page.get_by_role(
                "option", name=branch_name, exact=True
            )
            option.wait_for(state="visible", timeout=5000)
            option.click()
            selected = self.branch_select.locator(
                ".react-select__single-value"
            ).inner_text().strip()
            assert selected == branch_name, (
                f"Category-Wise selected '{selected}', expected '{branch_name}'"
            )

        btn = self.page.get_by_role("button", name=re.compile(r"Search|Filter", re.I)).first
        btn.wait_for(state="visible", timeout=5000)
        btn.click()
        overlay = self.page.locator(".loading-state-modern--overlay")
        if overlay.count():
            overlay.wait_for(state="hidden", timeout=15000)
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)

    def get_metric_value(self, card_label: str) -> Decimal:
        try:
            # 1. Find the element matching the card label (e.g. "Cash Income1,150" or "Sales90")
            el = self.page.get_by_text(re.compile(rf"{card_label}", re.I)).last
            el.wait_for(state="visible", timeout=5000)
            text = el.inner_text()

            # 2. Extract digits directly following the label
            match = re.search(rf"{card_label}\s*₹?\s*(-?[\d,]+(?:\.\d+)?)", text, re.I)
            if match:
                clean = match.group(1).replace(",", "")
                return Decimal(clean)

            # 3. Fallback: check parent element
            parent = el.locator("xpath=..")
            p_text = parent.inner_text()
            match = re.search(rf"{card_label}\s*₹?\s*(-?[\d,]+(?:\.\d+)?)", p_text, re.I)
            if match:
                clean = match.group(1).replace(",", "")
                return Decimal(clean)
        except Exception:
            pass
        return Decimal("0.00")

    def get_sales(self) -> Decimal:
        total = (self.last_report.get("totals") or {}).get("amount")
        if total is not None:
            return Decimal(str(total)).quantize(Decimal("0.01"))
        label = self.page.locator("span.text-muted").filter(
            has_text=re.compile(r"^Sales$", re.I)
        ).first
        value = label.locator("xpath=..").locator("span").nth(1).inner_text()
        return Decimal(value.replace(",", "").strip()).quantize(Decimal("0.01"))

    def get_cash_income(self) -> Decimal:
        total = (self.last_report.get("payment_mode_summary") or {}).get(
            "cash_income"
        )
        if total is not None:
            return Decimal(str(total)).quantize(Decimal("0.01"))
        card = self.page.locator(".card-body .border.rounded").filter(
            has=self.page.locator("h6").filter(
                has_text=re.compile(r"^Cash Income$", re.I)
            )
        ).first
        value = card.locator("h4").inner_text()
        return Decimal(value.replace(",", "").strip()).quantize(Decimal("0.01"))

    def get_upi_income(self) -> Decimal:
        return self.get_metric_value("UPI Income")

    def get_credit_income(self) -> Decimal:
        return self.get_metric_value("Credit Income")

    def get_table_rows(self) -> list[dict[str, str]]:
        rows = self.page.locator("table tbody tr").all()
        result = []
        for r in rows:
            cells = [td.inner_text().strip() for td in r.locator("td").all()]
            if cells:
                result.append({"cells": cells, "text": r.inner_text().strip()})
        return result
