"""Restaurant Day Book Page Object.

Route: RES_DAY_BOOK_URL (/day-book)
Handles:
- Day Book table entries (Sales, Outdoor Catering, Purchases/GRN, Direct Expenses)
- Date and Category filters
- Reading metric summary cards:
  - Opening Balance (₹)
  - Total Income (₹)
  - Total Expense (₹)
  - Closing Balance (₹)
- Entry assertions (Debit, Credit, Reference Number, Payment Mode)
"""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_DAY_BOOK_URL


class DayBookPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_DAY_BOOK_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first

    @property
    def filter_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Filter|Search", re.I)).first

    # ── Metric Cards ─────────────────────────────────────────────────────────

    def get_metric_card_value(self, title: str) -> Decimal:
        card = self.page.locator(".card, div").filter(has_text=re.compile(title, re.I)).first
        try:
            card.wait_for(state="visible", timeout=5000)
            text = card.inner_text()
            match = re.search(r"₹\s*(-?[\d,]+\.?\d*)", text)
            if match:
                clean_str = match.group(1).replace(",", "")
                return Decimal(clean_str)
        except Exception:
            pass
        return Decimal("0.00")

    def get_opening_balance(self) -> Decimal:
        return self.get_metric_card_value("Opening Balance")

    def get_total_income(self) -> Decimal:
        return self.get_metric_card_value("Total Income")

    def get_total_expense(self) -> Decimal:
        return self.get_metric_card_value("Total Expense")

    def get_closing_balance(self) -> Decimal:
        return self.get_metric_card_value("Closing Balance")

    # ── Table Row Assertions ─────────────────────────────────────────────────

    def search_entry_in_day_book(self, reference_or_text: str) -> bool:
        try:
            row = self.page.locator("table tbody tr").filter(has_text=reference_or_text).first
            row.wait_for(state="visible", timeout=8000)
            return True
        except Exception:
            return False

    def get_entry_by_description(self, description: str) -> dict[str, str]:
        """Return the exact visible Day Book row for a known transaction."""
        row = self.page.locator("table tbody tr").filter(has_text=description).first
        row.wait_for(state="visible", timeout=10000)
        cells = [cell.inner_text().strip() for cell in row.locator("td").all()]
        assert len(cells) >= 6, (
            f"Day Book row for '{description}' has only {len(cells)} columns"
        )
        return {
            "date": cells[0],
            "category": cells[1],
            "type": cells[2],
            "payment": cells[3],
            "amount": cells[4],
            "description": cells[5],
        }

    def get_day_book_rows(self) -> list[dict[str, str]]:
        rows = self.page.locator("table tbody tr").all()
        result = []
        for r in rows:
            cells = [td.inner_text().strip() for td in r.locator("td").all()]
            if cells:
                result.append({"cells": cells, "text": r.inner_text().strip()})
        return result
