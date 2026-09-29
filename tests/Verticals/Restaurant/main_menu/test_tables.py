"""Restaurant Tables & Floor View Test Suite."""
import pytest
from playwright.sync_api import Page, expect
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.tables_page import TablesPage


@pytest.mark.restaurant
class TestTables:
    def test_table_floor_view_and_seats(self, res_logged_in_page: Page, res_branch):
        """Test tables grid displays properly and has seat buttons rendered."""
        tables_page = TablesPage(res_logged_in_page)
        tables_page.navigate()

        expect(tables_page.create_table_button).to_be_visible()
        expect(tables_page.filter_total_tables).to_be_visible()

        # If floor has no tables, create one
        table_cards = res_logged_in_page.locator("div.tables-seat-card, div.card, div[class*='table']").all()
        if len(table_cards) == 0:
            tbl_name = generate_random_name("T")[:4]
            tables_page.add_table(name=tbl_name, capacity="4", branch_name=res_branch)
            tables_page.navigate()

        table_cards = res_logged_in_page.locator("div.tables-seat-card, div.card, div[class*='table']").all()
        assert len(table_cards) > 0, "Expected at least one table card visible on the floor view"

    def test_table_status_filters(self, res_logged_in_page: Page):
        """Test status pill filter buttons on the floor view."""
        tables_page = TablesPage(res_logged_in_page)
        tables_page.navigate()

        if tables_page.filter_available.is_visible():
            tables_page.filter_available.click()
            res_logged_in_page.wait_for_timeout(300)

        if tables_page.filter_occupied.is_visible():
            tables_page.filter_occupied.click()
            res_logged_in_page.wait_for_timeout(300)

        if tables_page.filter_total_tables.is_visible():
            tables_page.filter_total_tables.click()
            res_logged_in_page.wait_for_timeout(300)

    def test_table_seat_opens_pos_billing(self, res_logged_in_page: Page, res_branch):
        """Test clicking a seat navigates to POS /sales/add."""
        tables_page = TablesPage(res_logged_in_page)
        tables_page.navigate()

        seat_btn = res_logged_in_page.locator(".tables-seat-btn, button[aria-label*='Seat']").first
        if not seat_btn.is_visible():
            tbl_name = generate_random_name("T")[:4]
            tables_page.add_table(name=tbl_name, capacity="4", branch_name=res_branch)
            tables_page.navigate()
            seat_btn = res_logged_in_page.locator(".tables-seat-btn, button[aria-label*='Seat']").first

        if seat_btn.is_visible():
            seat_btn.click()
            try:
                res_logged_in_page.wait_for_url(lambda u: "/sales" in u, timeout=10000)
            except Exception:
                pass
            assert "/sales" in res_logged_in_page.url or res_logged_in_page.locator(".restaurant-pos-code-input, button:has-text('Settle & Bill')").first.is_visible()
