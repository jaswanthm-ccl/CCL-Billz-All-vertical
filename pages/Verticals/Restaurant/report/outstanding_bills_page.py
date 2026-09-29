"""Restaurant Outstanding Bills Page Object.

Route: RESTAURANT_BASE_URL/vouchers/outstanding
Inherits from shared OutstandingBillsPage and overrides the URL.
"""
from __future__ import annotations

import re

from playwright.sync_api import Page

from pages.report.outstanding_bills_page import OutstandingBillsPage as SharedOutstandingBillsPage
from utils.res_constants import RES_OUTSTANDING_BILLS_URL


class OutstandingBillsPage(SharedOutstandingBillsPage):
    """Restaurant adapter for the Outstanding Bills report page."""

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.url = RES_OUTSTANDING_BILLS_URL

    def expand_filters(self) -> None:
        """Expand the modern filter panel so type/status selects become visible."""
        type_sel = self.page.locator("#outstanding-bill-type, select[name='type']").first
        if type_sel.count() > 0 and type_sel.is_visible():
            return

        # Try multiple toggle strategies for the restaurant filter panel
        toggles = [
            self.page.locator(".filters-header-modern").first,
            self.page.locator(".filters-toggle-btn").first,
            self.page.locator("button[aria-label='Expand filters']").first,
            self.page.locator("button:has(i.bi-chevron-down), button:has(i.bi-funnel)").first,
            self.page.get_by_role("button", name=re.compile(r"Filter", re.I)).first,
        ]

        for toggle in toggles:
            try:
                if toggle.count() > 0 and toggle.is_visible():
                    toggle.click()
                    self.page.wait_for_timeout(500)
                    if type_sel.is_visible():
                        return
            except Exception:
                continue

        # Fallback: force visibility via JS if the panel exists but is hidden
        try:
            self.page.evaluate("""
                document.querySelectorAll('.filter-select-modern, #outstanding-bill-type, #outstanding-bill-status')
                    .forEach(el => {
                        let parent = el.closest('.filters-body-modern, .filters-content, .collapse');
                        if (parent) {
                            parent.style.display = 'block';
                            parent.classList.add('show');
                        }
                    });
            """)
            self.page.wait_for_timeout(300)
        except Exception:
            pass
