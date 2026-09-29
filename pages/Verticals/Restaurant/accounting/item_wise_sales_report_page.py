"""Restaurant Item-Wise Sales Report Page Object.

Route: RESTAURANT_BASE_URL/reports/item-wise-sales
"""
from __future__ import annotations

import re
from decimal import Decimal
from playwright.sync_api import Page, Locator
from utils.res_constants import RESTAURANT_BASE_URL


class ItemWiseSalesReportPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = f"{RESTAURANT_BASE_URL}/reports/item-wise-sales"

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def from_date_input(self) -> Locator:
        return self.page.locator("input[name='start_date'], input[name='from_date'], input[name='startDate']").first

    @property
    def to_date_input(self) -> Locator:
        return self.page.locator("input[name='end_date'], input[name='to_date'], input[name='endDate']").first

    @property
    def branch_select_control(self) -> Locator:
        return self.page.locator(".react-select__control").first

    @property
    def search_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Search|Filter", re.I)).first

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first

    @property
    def export_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Export", re.I)).or_(
            self.page.locator("button:has-text('Export'), a:has-text('Export')")
        ).first

    # ── Actions ─────────────────────────────────────────────────────────────

    def apply_filters(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        branch_name: str | None = None,
    ) -> None:
        if to_date and self.to_date_input.is_visible():
            self.to_date_input.fill(to_date)
        if from_date and self.from_date_input.is_visible():
            self.from_date_input.fill(from_date)
        if to_date and self.to_date_input.is_visible():
            self.to_date_input.fill(to_date)

        if branch_name and branch_name != "All Branches":
            try:
                if self.branch_select_control.is_visible():
                    self.branch_select_control.click()
                    self.page.wait_for_timeout(200)
                    self.page.keyboard.type(branch_name[:10])
                    self.page.wait_for_timeout(300)
                    opt = self.page.locator(".react-select__option").filter(has_text=branch_name).first
                    if opt.count() > 0 and opt.is_visible():
                        opt.click()
                    else:
                        self.page.locator(".react-select__option").first.click()
            except Exception:
                pass

        if self.search_button.is_visible():
            self.search_button.click()
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(500)

    def search_in_table(self, query: str) -> None:
        if self.search_input.is_visible():
            self.search_input.fill(query)
            self.search_input.press("Enter")
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(300)

    def get_table_headers(self) -> list[str]:
        return [th.inner_text().strip() for th in self.page.locator("table thead th").all()]

    def get_item_rows(self) -> list[dict[str, str]]:
        rows = self.page.locator("table tbody tr").all()
        result = []
        for r in rows:
            cells = [td.inner_text().strip() for td in r.locator("td").all()]
            if cells:
                result.append({"cells": cells, "text": r.inner_text().strip()})
        return result

    def find_item_in_report(self, item_name: str) -> bool:
        row = self.page.locator("table tbody tr").filter(has_text=item_name).first
        try:
            row.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False
