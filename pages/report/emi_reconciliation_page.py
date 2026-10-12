from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Callable
from urllib.parse import urlparse

from playwright.sync_api import Page, Response, TimeoutError as PlaywrightTimeoutError

from pages.common.base_page import BasePage
from utils.tenants import Tenant
from utils.constants import LIST_TIMEOUT, UI_TIMEOUT


def _parse_currency(text: str) -> Decimal:
    cleaned = re.sub(r"[^\d.]", "", text)
    return Decimal(cleaned) if cleaned else Decimal("0.00")


class EmiReconciliationPage(BasePage):
    PATH = "/reports/emi-provider-reconciliation"

    def __init__(self, page: Page, tenant: Tenant | None = None) -> None:
        super().__init__(page, tenant)

    @staticmethod
    def _is_report_response(response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        if response.request.method != "GET" or response.request.resource_type not in {"fetch", "xhr"}:
            return False
        return path.endswith("/accounting/emi-provider-reconciliation") or path.endswith(
            "/emi-provider-reconciliation"
        )

    def _reload_report(self, action: Callable[[], object]) -> None:
        with self.page.expect_response(self._is_report_response, timeout=LIST_TIMEOUT):
            action()
        self.page.locator("table tbody tr, body").first.wait_for(state="visible", timeout=UI_TIMEOUT)

    def navigate(self) -> None:
        self._reload_report(lambda: self.page.goto(self.url))
        self.apply_date_filter()

    def apply_date_filter(self) -> None:
        """Opens filter modal and clicks Apply when present (report often already loaded on navigate)."""
        try:
            filter_btn = self.page.locator(
                "button:has(.bi-funnel), button:has(.bi-filter)"
            ).first
            if filter_btn.count() > 0 and filter_btn.is_visible():
                filter_btn.click()

            apply_btn = self.page.get_by_role("button", name="Apply").first
            if apply_btn.count() == 0 or not apply_btn.is_visible():
                return
            try:
                self._reload_report(lambda: apply_btn.click())
            except PlaywrightTimeoutError:
                # Same date range may not re-hit the API.
                pass
        except Exception:
            pass

    def get_summary_cards(self) -> dict[str, Decimal]:
        """Extracts values from the top KPI summary cards."""
        cards = {
            "total_financed": Decimal("0.00"),
            "total_settled": Decimal("0.00"),
            "total_outstanding": Decimal("0.00"),
            "total_processing_charges": Decimal("0.00"),
        }

        page_text = self.page.locator("body").inner_text()

        m_fin = re.search(r"Total Financed\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_fin:
            cards["total_financed"] = _parse_currency(m_fin.group(1))

        m_set = re.search(r"Total Settled\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_set:
            cards["total_settled"] = _parse_currency(m_set.group(1))

        m_out = re.search(r"Total Outstanding\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_out:
            cards["total_outstanding"] = _parse_currency(m_out.group(1))

        m_pc = re.search(r"Total Processing Charges\s*[\n\r]*\s*₹?\s*([\d,]+\.?\d*)", page_text, re.I)
        if m_pc:
            cards["total_processing_charges"] = _parse_currency(m_pc.group(1))

        return cards

    def set_page_size(self, size: str = "100") -> None:
        """Sets table page size when a rows-per-page control is present."""
        try:
            for control in self.page.locator(".react-select__control").all():
                control.click()
                opt = self.page.locator(".react-select__option").filter(
                    has_text=re.compile(rf"{size}\s*rows", re.I)
                ).first
                try:
                    opt.wait_for(state="visible", timeout=1000)
                except PlaywrightTimeoutError:
                    self.page.keyboard.press("Escape")
                    continue
                try:
                    self._reload_report(lambda: opt.click())
                except PlaywrightTimeoutError:
                    opt.click()
                return
        except Exception:
            pass

    def search_provider(self, name: str) -> bool:
        self.set_page_size("100")
        body_text = self.page.locator("body").inner_text()
        return name in body_text or f"{name} Receivable" in body_text

    def get_provider_reconciliation_row(self, name: str) -> dict[str, Any]:
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
