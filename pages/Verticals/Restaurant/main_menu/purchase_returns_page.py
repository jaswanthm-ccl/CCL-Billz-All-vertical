"""Restaurant Purchase Returns Page Object.

Route: RES_PURCHASES_URL/return (/purchase-returns)
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from playwright.sync_api import Page, Locator
from utils.res_constants import RESTAURANT_BASE_URL


class PurchaseReturnsPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = f"{RESTAURANT_BASE_URL}/purchase-returns"

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first

    def search_return(self, query: str) -> bool:
        self.search_input.wait_for(state="visible", timeout=5000)
        self.search_input.fill(query)
        self.search_input.press("Enter")
        self.page.wait_for_load_state("networkidle")
        try:
            self.page.locator("table tbody tr").filter(has_text=query).first.wait_for(state="visible", timeout=5000)
            return True
        except Exception:
            return False

    def perform_return(self, quantity: str) -> dict:
        """Submit the currently open Purchase Return form and return its API data."""
        responses: list[dict] = []

        def capture(response) -> None:
            path = urlparse(response.url).path.rstrip("/")
            if response.request.method == "POST" and path.endswith("/purchase-return"):
                try:
                    body = response.json()
                except Exception:
                    body = {}
                responses.append(
                    {
                        "ok": response.ok,
                        "status": response.status,
                        "body": body,
                    }
                )

        self.page.on("response", capture)
        try:
            quantity_field = self.page.get_by_placeholder("Quantity").first
            quantity_field.wait_for(state="visible", timeout=10000)
            quantity_field.fill(str(quantity))
            self.page.get_by_role("button", name="Return", exact=True).click()

            confirmation = self.page.get_by_role("dialog").filter(
                has_text="Confirm Purchase Return"
            ).first
            try:
                confirmation.wait_for(state="visible", timeout=1500)
                confirmation.get_by_role("button", name="Yes", exact=True).click()
            except Exception:
                pass

            self.page.wait_for_url(
                lambda url: "/purchases" in url and "/add" not in url,
                timeout=15000,
            )
            self.page.wait_for_load_state("networkidle")
        finally:
            self.page.remove_listener("response", capture)

        assert responses, "Purchase Return form did not submit its POST request"
        response = responses[-1]
        assert response["ok"], (
            f"Purchase Return failed: HTTP {response['status']}, {response['body']}"
        )
        body = response["body"]
        return body.get("data") or body

    def filter_returns(self, branch_name: str, supplier_name: str) -> None:
        self.navigate()

        expand = self.page.get_by_role(
            "button", name=re.compile(r"Expand filters", re.I)
        ).first
        try:
            if expand.is_visible():
                expand.click()
        except Exception:
            pass

        for label, option_name in (
            ("Branch", branch_name),
            ("Supplier", supplier_name),
        ):
            control = self.page.locator("label.form-label").filter(
                has_text=re.compile(rf"^{label}\s*$", re.I)
            ).locator("xpath=..").locator(".react-select__control").first
            control.wait_for(state="visible", timeout=10000)
            control.click()
            self.page.get_by_role("option", name=option_name, exact=True).click()

        self.page.get_by_role("button", name="Filter", exact=True).click()
        self.page.wait_for_load_state("networkidle")

    def verify_return_details(
        self,
        product_name: str,
        supplier_name: str,
        branch_name: str,
        quantity: str,
        price: str,
        total_amount: str,
    ) -> bool:
        row = self.page.locator("table tbody tr").filter(
            has_text=product_name
        ).filter(has_text=supplier_name).first
        row.wait_for(state="visible", timeout=10000)
        row_text = row.inner_text()
        assert branch_name.casefold() in row_text.casefold(), row_text
        assert total_amount in row_text.replace(",", ""), row_text

        row.get_by_title("view").first.click()
        dialog = self.page.get_by_role("dialog").filter(
            has_text="View Purchase Return"
        ).first
        dialog.wait_for(state="visible", timeout=10000)
        try:
            dialog.get_by_text(supplier_name, exact=True).first.wait_for(
                state="visible", timeout=10000
            )
            content = dialog.inner_text()
            for expected in (product_name, supplier_name, branch_name):
                assert expected.casefold() in content.casefold(), content

            item_row = dialog.locator("tbody tr").filter(has_text=product_name).first
            item_row.wait_for(state="visible", timeout=5000)
            item_text = item_row.inner_text().replace(",", "")
            assert str(quantity) in item_text, item_text
            assert str(price) in item_text or str(total_amount) in item_text, item_text
            return True
        finally:
            close = dialog.locator(".btn-close").first
            if close.count() and close.is_visible():
                close.click()
