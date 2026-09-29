"""Restaurant Goods Receipt Note (GRN) Page Object.

Route: RES_GRN_URL (/grn)
Handles:
- GRN list searching, filtering, and table assertions
- GRN creation against a Purchase Order (/grn/create/:purchaseRequestId)
- Line item receiving quantities, actual unit pricing, and validation
- GRN approval workflow (/grn/:id) triggering Purchase creation and inventory updates
- Linked Purchase verification (/purchases) and Inventory impact verification (/inventories)
"""
from __future__ import annotations

import re
from typing import Any
from playwright.sync_api import Page, Locator
from utils.res_constants import RES_GRN_URL, RES_PURCHASE_REQUESTS_URL


class GrnPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = RES_GRN_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    # ── Dynamic @property Locators ──────────────────────────────────────────

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search...").or_(
            self.page.locator("input[placeholder*='Search']")
        ).first

    @property
    def modal_dialog(self) -> Locator:
        return self.page.get_by_role("dialog").or_(self.page.locator(".modal-dialog, div[role='dialog']")).first

    @property
    def approve_grn_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Approve GRN", re.I)).first

    @property
    def create_grn_submit_button(self) -> Locator:
        return self.page.get_by_role("button", name=re.compile(r"Create GRN", re.I)).first

    # ── Purchase Order Creation Helper for GRN ───────────────────────────────

    def create_purchase_order_and_open_grn(
        self,
        branch_name: str,
        supplier_name: str,
        product_name: str,
        quantity: str = "10",
    ) -> int:
        """Creates a purchase order in restaurant tenant and clicks the GRN action button to open /grn/create/:id."""
        self.page.goto(f"{RES_PURCHASE_REQUESTS_URL}/add")
        self.page.wait_for_load_state("networkidle")

        # 1. Branch selection (if visible in form)
        branch_ctrl = self.page.locator("input[name='branch_id']").locator("..").locator(".react-select__control").first
        if branch_ctrl.is_visible():
            branch_ctrl.click()
            self.page.wait_for_timeout(200)
            self.page.keyboard.type(branch_name[:10])
            self.page.wait_for_timeout(300)
            opt = self.page.locator(".react-select__option").filter(has_text=branch_name).first
            if opt.is_visible():
                opt.click()
            else:
                self.page.keyboard.press("Enter")

        # 2. Supplier selection
        supp_ctrl = self.page.locator("input[name='supplier_id']").locator("..").locator(".react-select__control").first
        supp_ctrl.wait_for(state="visible", timeout=5000)
        supp_ctrl.click()
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(supplier_name[:10])
        self.page.wait_for_timeout(300)
        opt_s = self.page.locator(".react-select__option").filter(has_text=supplier_name).first
        if opt_s.is_visible():
            opt_s.click()
        else:
            self.page.locator(".react-select__option").first.click()

        # 3. Product line item selection
        prod_ctrl = self.page.locator(".table-sale-item tbody tr .react-select__control").first
        prod_ctrl.wait_for(state="visible", timeout=5000)
        prod_ctrl.click()
        self.page.wait_for_timeout(200)
        self.page.keyboard.type(product_name[:10])
        self.page.wait_for_timeout(300)
        opt_p = self.page.locator(".react-select__option").filter(has_text=product_name).first
        if opt_p.is_visible():
            opt_p.click()
        else:
            self.page.keyboard.press("Enter")

        # 4. Fill Quantity
        qty_inp = self.page.locator(".table-sale-item tbody tr input[type='number']").first
        qty_inp.fill(str(quantity))

        # 5. Submit Create PO
        create_btn = self.page.get_by_role("button", name="Create").first
        with self.page.expect_response(
            lambda r: "/purchase-requests" in r.url and r.request.method == "POST",
            timeout=10000
        ) as resp_info:
            create_btn.click()

        assert resp_info.value.status in (200, 201), f"PO creation failed with HTTP {resp_info.value.status}"
        self.page.wait_for_url(lambda u: "/purchase-requests" in u and "add" not in u, timeout=10000)
        self.page.wait_for_load_state("networkidle")

        # Search for supplier in list table to isolate the created PO
        search_box = self.page.get_by_placeholder("Search...").or_(self.page.locator("input[placeholder*='Search']")).first
        search_box.wait_for(state="visible", timeout=10000)
        search_box.fill(supplier_name)
        search_box.press("Enter")
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(600)

        # Find row and click GRN action button (bi-box-seam)
        row = self.page.locator("table tbody tr").filter(has_text=supplier_name).first
        row.wait_for(state="visible", timeout=10000)

        grn_btn = row.locator("button:has(i.bi-box-seam)").first
        grn_btn.wait_for(state="visible", timeout=5000)
        grn_btn.click()

        self.page.wait_for_url(lambda u: "/grn/create/" in u, timeout=10000)
        self.page.wait_for_load_state("networkidle")

        match = re.search(r"/grn/create/(\d+)", self.page.url)
        return int(match.group(1)) if match else 0

    # ── GRN Workflow Actions ────────────────────────────────────────────────

    def create_grn(
        self,
        purchase_request_id: int,
        unit_price: str = "50",
        received_quantity: str = "10",
    ) -> dict[str, Any]:
        """Fills unit price and receiving qty on /grn/create/:po_id, then submits GRN."""
        if f"/grn/create/{purchase_request_id}" not in self.page.url:
            self.page.goto(f"{self.url}/create/{purchase_request_id}")
            self.page.wait_for_load_state("networkidle")

        # Wait for line items table to finish loading
        self.page.locator("table tbody tr").first.wait_for(state="visible", timeout=10000)

        # 1. Fill Actual Unit Price
        unit_price_inp = self.page.locator("table tbody tr input[placeholder='0.00']").first
        unit_price_inp.wait_for(state="visible", timeout=5000)
        unit_price_inp.click()
        unit_price_inp.fill(str(unit_price))

        # 2. Check Receive Now quantity
        inputs = self.page.locator("table tbody tr input[type='number']").all()
        if len(inputs) >= 2:
            receive_now_inp = inputs[1]
            receive_now_inp.click()
            receive_now_inp.fill(str(received_quantity))

        self.page.wait_for_timeout(300)

        # Check for any validation warnings
        alert = self.page.locator(".alert-warning")
        if alert.is_visible():
            print(f"Validation warning on GRN form: {alert.inner_text()}")

        # 3. Submit Create GRN
        submit_btn = self.create_grn_submit_button
        submit_btn.wait_for(state="visible", timeout=5000)
        assert not submit_btn.is_disabled(), f"Create GRN button is disabled! Alert: {alert.inner_text() if alert.is_visible() else 'none'}"

        with self.page.expect_response(
            lambda r: "/grn" in r.url and r.request.method == "POST", timeout=10000
        ) as resp_info:
            submit_btn.click()

        assert resp_info.value.status in (200, 201), f"Create GRN failed with HTTP {resp_info.value.status}"
        resp_data = resp_info.value.json()
        self.page.wait_for_url(lambda u: "/grn/" in u and "create" not in u, timeout=10000)
        self.page.wait_for_load_state("networkidle")
        return resp_data.get("data", {})

    def get_grn_details(self, grn_id: int) -> dict[str, Any]:
        """Navigates to /grn/:id and returns details card contents."""
        self.page.goto(f"{self.url}/{grn_id}")
        self.page.wait_for_load_state("networkidle")
        content = self.page.content()
        status_badge = self.page.locator(".card-body .badge").first.inner_text().strip()
        return {
            "status": status_badge,
            "html": content,
        }

    def approve_grn(self, grn_id: int) -> bool:
        """Approves a pending GRN on /grn/:id and confirms the approval dialog."""
        self.page.goto(f"{self.url}/{grn_id}")
        self.page.wait_for_load_state("networkidle")

        self.approve_grn_button.wait_for(state="visible", timeout=5000)
        self.approve_grn_button.click()

        # Confirm Modal
        confirm_modal = self.modal_dialog
        confirm_modal.wait_for(state="visible", timeout=5000)
        approve_confirm_btn = confirm_modal.get_by_role("button", name="Approve").first

        with self.page.expect_response(
            lambda r: f"/grn/{grn_id}/approve" in r.url and r.request.method == "POST",
            timeout=10000
        ) as resp_info:
            approve_confirm_btn.click()

        assert resp_info.value.status in (200, 204), f"Approve GRN failed with HTTP {resp_info.value.status}"
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(500)

        # Assert status updated to approved
        status_text = self.page.locator(".card-body .badge").first.inner_text().strip()
        return status_text.lower() == "approved"

    def get_linked_purchase_id(self, grn_id: int) -> int | None:
        """Reads linked purchase ID button from approved GRN detail page."""
        self.page.goto(f"{self.url}/{grn_id}")
        self.page.wait_for_load_state("networkidle")
        btn = self.page.locator("button:has-text('View Purchase #')").first
        if btn.is_visible():
            match = re.search(r"View Purchase #(\d+)", btn.inner_text())
            if match:
                return int(match.group(1))
        return None

    def search_grn_in_list(self, query: str | int) -> bool:
        """Navigates to /grn and verifies GRN ID or PO ID is present in the table."""
        self.navigate()
        try:
            row = self.page.locator("table tbody tr").filter(has_text=str(query)).first
            row.wait_for(state="visible", timeout=10000)
            return True
        except Exception:
            return False
