"""Restaurant Purchase page object."""

from playwright.sync_api import Locator
from urllib.parse import urlparse

from pages.main_menu.purchases_page import PurchasesPage as DefaultPurchasesPage
from utils.res_constants import RES_PURCHASES_URL, SEARCH_DEBOUNCE_MS


class PurchasesPage(DefaultPurchasesPage):
    """Use the shared Purchase contract against the Restaurant tenant."""

    def __init__(self, page) -> None:
        super().__init__(page)
        self.url = RES_PURCHASES_URL
        self.last_created_purchase: dict = {}
        self._purchase_submission_in_progress = False

    def navigate(self) -> None:
        # The shared helper navigates after submitting. Keep an invalid form open
        # so its validation errors can be reported instead of masked as success.
        if self._purchase_submission_in_progress and "/purchases/add" in self.page.url:
            return
        super().navigate()

    def add_purchase(self, *args, **kwargs):
        responses = []
        submitted_posts = []

        def capture(response) -> None:
            path = urlparse(response.url).path.rstrip("/")
            if response.request.method == "POST":
                submitted_posts.append(response.url)
                if path.endswith("/purchases") or path.endswith("/purchase"):
                    try:
                        body = response.json()
                    except Exception:
                        body = {}
                    responses.append(
                        {
                            "ok": response.ok,
                            "status": response.status,
                            "body": body,
                            "payload": response.request.post_data,
                        }
                    )

        self.page.on("response", capture)
        self._purchase_submission_in_progress = True
        try:
            result = super().add_purchase(*args, **kwargs)
        finally:
            self._purchase_submission_in_progress = False
            self.page.remove_listener("response", capture)

        validation_text = " | ".join(
            text.strip()
            for text in self.page.locator(
                ".invalid-feedback:visible, .text-danger:visible, [role='alert']:visible"
            ).all_inner_texts()
            if text.strip()
        )
        assert responses, (
            "Purchase form did not submit a Purchase POST request. "
            f"Validation: {validation_text or 'none shown'}. "
            f"Observed POST requests: {submitted_posts}"
        )
        response = responses[-1]
        body = response["body"]
        assert response["ok"], (
            f"Purchase creation failed: HTTP {response['status']}, {body}. "
            f"Payload: {response['payload']}"
        )
        self.last_created_purchase = body.get("data") or {}
        return result

    @property
    def search_input(self) -> Locator:
        return self.page.get_by_placeholder("Search Purchases...").or_(
            self.page.get_by_placeholder("Search...")
        ).first

    def search_purchase(self, reference_no: str) -> bool:
        self.search_input.wait_for(state="visible", timeout=10000)
        self.search_input.fill(reference_no)
        self.search_input.press("Enter")
        self.page.wait_for_timeout(SEARCH_DEBOUNCE_MS + 300)
        try:
            self.page.locator("table tbody tr").filter(
                has_text=reference_no
            ).first.wait_for(state="visible", timeout=10000)
            return True
        except Exception:
            return False
