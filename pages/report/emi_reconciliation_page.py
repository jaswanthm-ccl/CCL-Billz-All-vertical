from __future__ import annotations

import re
from typing import Any
from playwright.sync_api import Page

from utils.constants import (
    EMI_RECONCILIATION_URL,
    LIST_TIMEOUT,
    SEARCH_DEBOUNCE_MS,
    SETTLED_TIMEOUT,
    UI_TIMEOUT,
)


from decimal import Decimal


def _parse_currency(text: str) -> Decimal:
    cleaned = re.sub(r"[^\d.]", "", text)
    return Decimal(cleaned) if cleaned else Decimal("0.00")


class EmiReconciliationPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = EMI_RECONCILIATION_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")
        self.apply_date_filter()

    def apply_date_filter(self) -> None:
        """Opens filter modal and clicks Apply to trigger report data fetch."""
        try:
            filter_btn = self.page.locator("button:has(.bi-funnel), button:has(.bi-filter), button:has-text('Filter')").first
            if filter_btn.count() > 0 and filter_btn.is_visible():
                filter_btn.click()
                self.page.wait_for_timeout(400)

            apply_btn = self.page.get_by_role("button", name="Apply").first
            if apply_btn.count() > 0 and apply_btn.is_visible():
                apply_btn.click()
                self.page.wait_for_load_state("networkidle")
                self.page.wait_for_timeout(1000)
        except Exception:
            pass

    def get_summary_cards(self) -> dict[str, Decimal]:
        """Extracts values from the top KPI summary cards."""
        self.page.wait_for_load_state("networkidle")
        cards = {
            "total_financed": Decimal("0.00"),
            "total_settled": Decimal("0.00"),
            "total_outstanding": Decimal("0.00"),
            "total_processing_charges": Decimal("0.00"),
        }

        # Scan text on page for the 4 metrics
        page_text = self.page.locator("body").inner_text()
        
        # Search for Total Financed
        m_fin = re.search(r"Total Financed\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_fin:
            cards["total_financed"] = _parse_currency(m_fin.group(1))

        # Search for Total Settled
        m_set = re.search(r"Total Settled\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_set:
            cards["total_settled"] = _parse_currency(m_set.group(1))

        # Search for Total Outstanding
        m_out = re.search(r"Total Outstanding\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_out:
            cards["total_outstanding"] = _parse_currency(m_out.group(1))

        # Search for Total Processing Charges
        m_pc = re.search(r"Total Processing Charges\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_pc:
            cards["total_processing_charges"] = _parse_currency(m_pc.group(1))

        return cards

    def set_page_size(self, size: str = "100") -> None:
        """Sets table page size to ensure all recent records are rendered."""
        try:
            controls = self.page.locator(".react-select__control").all()
            for c in controls:
                c.click()
                self.page.wait_for_timeout(300)
                opt = self.page.locator(".react-select__option").filter(has_text=re.compile(rf"{size}\s*rows", re.I)).first
                if opt.count() > 0 and opt.is_visible():
                    opt.click()
                    self.page.wait_for_timeout(400)
            self.page.wait_for_load_state("networkidle")
        except Exception:
            pass

    def search_provider(self, name: str) -> bool:
        self.page.wait_for_load_state("networkidle")
        self.set_page_size("100")
        body_text = self.page.locator("body").inner_text()
        return name in body_text or f"{name} Receivable" in body_text

    def get_provider_reconciliation_row(self, name: str) -> dict[str, Any]:
        self.page.wait_for_load_state("networkidle")
        row = self.page.locator("table tbody tr").filter(has_text=name).first
        if not (row.count() > 0 and row.is_visible()):
            self.set_page_size("100")
            row = self.page.locator("table tbody tr").filter(has_text=name).first

        if row.count() > 0 and row.is_visible():
            cells = row.locator("td").all()
            texts = [c.inner_text().strip() for c in cells]
            # Headers: ['S.NO', 'INVOICE', 'PROVIDER', 'FINANCED', 'SETTLED', 'OUTSTANDING', 'STATUS', ...]
            return {
                "invoice": texts[1] if len(texts) > 1 else "",
                "provider_name": texts[2] if len(texts) > 2 else texts[0] if len(texts) > 0 else "",
                "total_financed": _parse_currency(texts[3]) if len(texts) > 3 else _parse_currency(texts[1]) if len(texts) > 1 else Decimal("0.00"),
                "total_settled": _parse_currency(texts[4]) if len(texts) > 4 else _parse_currency(texts[2]) if len(texts) > 2 else Decimal("0.00"),
                "total_outstanding": _parse_currency(texts[5]) if len(texts) > 5 else _parse_currency(texts[3]) if len(texts) > 3 else Decimal("0.00"),
                "processing_charges": _parse_currency(texts[12]) if len(texts) > 12 else Decimal("0.00"),
                "raw_text": row.inner_text() or "",
            }
        return {
            "invoice": "",
            "provider_name": name,
            "total_financed": Decimal("0.00"),
            "total_settled": Decimal("0.00"),
            "total_outstanding": Decimal("0.00"),
            "processing_charges": Decimal("0.00"),
            "raw_text": self.page.locator("body").inner_text(),
        }


