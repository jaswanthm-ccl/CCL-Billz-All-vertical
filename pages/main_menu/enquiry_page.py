from __future__ import annotations

from typing import Any

from playwright.sync_api import Locator, Page

from utils.constants import BASE_URL

ENQUIRY_URL = f"{BASE_URL}/enquiries"


class EnquiryPage:
    """Page object for the Enquiry module (/enquiries).

    Enquiries are CRM-like leads. Create requires: Enquiry Type, Branch,
    Stage (auto-resolved from type+branch workflow), Name, Phone/Email,
    Assigned user, Follow-up date, Description.

    Table columns: Name, Customer, Enquiry Type, Assigned To, Stage,
                   Next Followup, Due, Description, Actions
    Search: placeholder='Search...' (live, debounced)
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = ENQUIRY_URL

    def navigate(self) -> None:
        self.page.goto(self.url)
        self.page.wait_for_load_state("networkidle")

    def is_enquiry_visible(self) -> bool:
        """Verify the enquiry page loaded."""
        try:
            self.page.get_by_text("Enquiry Management").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            return False

    # ─── Create ────────────────────────────────────────────────────────────────

    def add_enquiry(
        self,
        enquiry_type: str,
        branch: str,
        name: str,
        phone: str,
        assigned_to: str,
        description: str,
        email: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Create a new enquiry.

        Stage is auto-populated based on enquiry_type + branch workflow.
        Follow-up date defaults to now. same_as_follow_up_by is checked by default.
        """
        self.page.get_by_role("button", name="Add Enquiry").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)

        # Enquiry Type
        modal.locator("input[name='enquiry_type_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=enquiry_type).click()
        self.page.wait_for_timeout(500)

        # Branch
        modal.locator("input[name='branch_id']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.get_by_role("option", name=branch).click()
        self.page.wait_for_timeout(1000)  # Wait for stage to auto-resolve

        # Wait for stage to be auto-selected (it resolves from workflow)
        try:
            modal.locator(".react-select__single-value").nth(2).wait_for(
                state="visible", timeout=5000
            )
        except Exception:
            pass  # Stage might already be selected

        # Name
        modal.locator("input[name='name']").fill(name)

        # Phone
        modal.locator("input[name='phone']").fill(phone)

        # Email (optional)
        if email:
            modal.locator("input[name='email']").fill(email)

        # Assigned To
        modal.locator("input[name='assigned_to']").locator(
            "xpath=.."
        ).locator(".react-select__input-container").click()
        self.page.wait_for_timeout(1000)
        requested_user = self.page.get_by_role("option", name=assigned_to, exact=True)
        if requested_user.count() > 0:
            requested_user.click()
        else:
            first_user = self.page.locator(".react-select__option").first
            first_user.wait_for(state="visible", timeout=5000)
            first_user.click()
        self.page.wait_for_timeout(300)

        # Follow-up date defaults to now — leave as is

        # Description
        modal.locator("textarea[name='description']").fill(description)

        # Notes (optional)
        if notes:
            modal.locator("textarea[name='notes']").fill(notes)

        # Submit
        with self.page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.rstrip("/").endswith("/enquiries"),
            timeout=15000,
        ) as response_info:
            modal.get_by_role("button", name="Create").click()

        response = response_info.value
        self.page.wait_for_timeout(2000)

        # Wait for modal to close (success)
        try:
            modal.wait_for(state="hidden", timeout=10000)
        except Exception:
            # Check for visible validation errors
            errors = modal.locator(".text-danger, .invalid-feedback").all()
            visible_errors = [e.text_content().strip() for e in errors if e.is_visible() and e.text_content().strip()]
            if visible_errors:
                raise AssertionError(f"Enquiry creation validation errors: {visible_errors}")
            # Check for toast error
            toast = self.page.locator(".Toastify__toast--error").first
            if toast.is_visible():
                msg = toast.text_content().strip()
                raise AssertionError(f"Enquiry creation failed: {msg}")
            raise

        if not response.ok:
            raise AssertionError(
                f"Enquiry creation API failed with {response.status}: {response.text()}"
            )

        payload = response.json()
        return payload.get("data") or {}

    def open_add_modal(self) -> Locator:
        self.page.get_by_role("button", name="Add Enquiry").click()
        modal = self.page.get_by_role("dialog")
        modal.wait_for(state="visible", timeout=10000)
        return modal

    def submit_empty_form(self) -> list[str]:
        """Submit the create form without data and return visible validation errors."""
        modal = self.open_add_modal()
        modal.get_by_role("button", name="Create").click()
        self.page.wait_for_timeout(500)

        errors = modal.locator(".text-danger, .invalid-feedback")
        return [
            text.strip()
            for text in errors.all_text_contents()
            if text and text.strip()
        ]

    # ─── Search ────────────────────────────────────────────────────────────────

    def search_enquiry(self, query: str) -> bool:
        """Search enquiries (live search, debounced)."""
        search_box = self.page.get_by_placeholder("Search...")
        search_box.fill("")
        self.page.wait_for_timeout(1000)
        search_box.fill(query)
        self.page.wait_for_timeout(2000)
        self.page.wait_for_load_state("networkidle", timeout=10000)
        try:
            first_row = self.page.locator("table tbody tr").first
            first_row.wait_for(state="visible", timeout=5000)
            text = first_row.text_content()
            return "No Enquiries found" not in text
        except Exception:
            return False

    # ─── Table ─────────────────────────────────────────────────────────────────

    def get_row_count(self) -> int:
        """Return visible row count."""
        try:
            self.page.locator("table tbody tr").first.wait_for(
                state="visible", timeout=5000
            )
            return self.page.locator("table tbody tr").count()
        except Exception:
            return 0

    def enquiry_row(self, query: str) -> Locator:
        return self.page.locator("table tbody tr").filter(has_text=query).first

    def enquiry_row_text(self, query: str) -> str:
        if not self.search_enquiry(query):
            return ""

        row = self.enquiry_row(query)
        row.wait_for(state="visible", timeout=5000)
        return row.inner_text()

    def filter_by_enquiry_type(self, enquiry_type: str) -> list[str]:
        """Apply the Enquiry Type list filter and return visible row text."""
        toggle = self.page.get_by_role("button", name="Expand filters")
        if toggle.is_visible():
            toggle.click()

        type_input = self.page.locator("input[name='enquiry_type_id']")
        type_input.locator("xpath=..").locator(
            ".react-select__input-container"
        ).click()
        self.page.get_by_role("option", name=enquiry_type, exact=True).click()

        with self.page.expect_response(
            lambda response: response.request.method == "GET"
            and "/enquiries" in response.url
            and "enquiry_type_id=" in response.url,
            timeout=15000,
        ):
            self.page.get_by_role("button", name="Filter", exact=True).click()

        self.page.wait_for_load_state("networkidle", timeout=10000)
        return [text.strip() for text in self.page.locator("table tbody tr").all_inner_texts()]

    def is_table_empty(self) -> bool:
        """Check if table shows empty state."""
        try:
            self.page.get_by_text("No Enquiries found").wait_for(
                state="visible", timeout=3000
            )
            return True
        except Exception:
            return False

    # ─── View ──────────────────────────────────────────────────────────────────

    def view_enquiry(self, query: str) -> bool:
        """Search for an enquiry and click to open the detail drawer."""
        if not self.search_enquiry(query):
            return False

        # Click the row to open drawer (onRowClick)
        row = self.page.locator("table tbody tr").first
        row.click()
        self.page.wait_for_timeout(1000)

        # Drawer should appear with enquiry details
        try:
            self.page.get_by_text("Enquiry Details").first.wait_for(
                state="visible", timeout=5000
            )
            return True
        except Exception:
            # Try alternate drawer indicator
            try:
                self.page.locator(".offcanvas, .drawer, [class*='drawer']").first.wait_for(
                    state="visible", timeout=3000
                )
                return True
            except Exception:
                return False

    def close_drawer(self) -> None:
        """Close the detail drawer."""
        try:
            self.page.locator(".btn-close").first.click()
            self.page.wait_for_timeout(500)
        except Exception:
            try:
                self.page.keyboard.press("Escape")
            except Exception:
                pass

    def open_followups_tab(self) -> None:
        self.page.get_by_text("Follow-ups", exact=True).first.click()
        self.page.get_by_role("heading", name="Follow-ups").wait_for(
            state="visible", timeout=5000
        )

    def has_pending_followup(self) -> bool:
        """Return whether the open enquiry drawer contains a pending follow-up."""
        self.open_followups_tab()
        try:
            self.page.get_by_text("pending", exact=True).first.wait_for(
                state="visible", timeout=10000
            )
            return True
        except Exception:
            return False

    # ─── Delete ────────────────────────────────────────────────────────────────

    def delete_enquiry(self, query: str) -> bool:
        """Search for an enquiry and delete it."""
        # Navigate fresh to avoid any drawer/state issues
        self.navigate()
        self.page.wait_for_timeout(1000)

        # Search
        search_box = self.page.get_by_placeholder("Search...")
        search_box.fill(query)
        self.page.wait_for_timeout(2000)
        self.page.wait_for_load_state("networkidle", timeout=10000)

        row = self.enquiry_row(query)
        row.wait_for(state="visible", timeout=5000)
        row.get_by_title("delete", exact=True).click()
        self.page.wait_for_timeout(1000)

        # Confirm delete
        self.page.get_by_role("button", name="Delete Enquiry").click()

        try:
            self.page.get_by_text("Enquiry deleted successfully.").wait_for(
                state="visible", timeout=10000
            )
            return True
        except Exception:
            return False

    def retrieve_enquiry(self, query: str) -> bool:
        """Search for a deleted enquiry and restore it."""
        if not self.search_enquiry(query):
            return False

        row = self.enquiry_row(query)
        row.wait_for(state="visible", timeout=5000)
        row.get_by_title("delete", exact=True).click()
        self.page.get_by_role("button", name="Retrieve Enquiry").click()

        try:
            self.page.get_by_text("Enquiry restored successfully.").wait_for(
                state="visible", timeout=10000
            )
            return True
        except Exception:
            return False
