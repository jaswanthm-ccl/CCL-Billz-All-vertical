"""End-to-end coverage for the Accounting Day Book voucher report."""
from datetime import date, timedelta
from decimal import Decimal
import time

import pytest
from playwright.sync_api import expect

from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.accounting.day_book_page import DayBookPage


@pytest.fixture(scope="module")
def day_book_voucher(module_page, voucher_funded_state):
    marker = f"day book audit {time.time_ns()}"
    voucher = CreateVoucherPage(module_page)
    voucher.navigate_contra()
    with module_page.expect_response(
        lambda response: response.request.method == "POST"
        and "/vouchers" in response.url,
        timeout=15_000,
    ) as response_info:
        voucher.create_contra_preset("cash_to_bank", "20", remarks=marker)

    response = response_info.value
    assert response.ok, f"Known Day Book voucher creation failed with HTTP {response.status}"
    payload = response.json().get("data") or {}
    voucher_no = (payload.get("voucher") or {}).get("voucher_no")
    assert voucher_no, "Voucher creation response did not contain voucher_no"
    assert voucher.wait_for_redirect_to_history()
    return {"voucher_no": voucher_no, "marker": marker, "amount": Decimal("20.00")}


class TestDayBookStructure:
    def test_page_loads(self, logged_in_page):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        assert day_book.is_page_visible()

    def test_default_dates_are_today(self, logged_in_page):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        today = date.today().isoformat()
        expect(day_book.from_date).to_have_value(today)
        expect(day_book.to_date).to_have_value(today)

    def test_table_headers_match_report_contract(self, logged_in_page):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        assert day_book.headers() == [
            "DATE",
            "VOUCHER NO.",
            "TYPE",
            "NARRATION",
            "DEBIT",
            "CREDIT",
        ]

    def test_initial_state_has_no_rows(self, logged_in_page):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        expect(logged_in_page.get_by_text("Run report to load vouchers.")).to_be_visible()
        assert day_book.get_row_count() == 0


class TestDayBookDateRange:
    def test_future_date_returns_balanced_empty_report(self, logged_in_page):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        report = day_book.run_report("2099-12-31", "2099-12-31")
        assert day_book.last_response_status == 200
        assert report["count"] == 0
        assert report["is_balanced"] is True
        assert day_book.get_row_count() == 0

    def test_reversed_date_range_is_rejected(self, logged_in_page):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        today = date.today()
        day_book.run_report(today.isoformat(), (today - timedelta(days=1)).isoformat())
        assert day_book.last_response_status == 422
        assert day_book.validation_error_is_visible()

    def test_range_boundaries_include_today_voucher(self, logged_in_page, day_book_voucher):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        today = date.today()
        day_book.run_report((today - timedelta(days=1)).isoformat(), today.isoformat())
        assert day_book.row_by_voucher(day_book_voucher["voucher_no"]) is not None

    def test_new_report_replaces_previous_results(self, logged_in_page, day_book_voucher):
        day_book = DayBookPage(logged_in_page)
        day_book.navigate()
        today = date.today().isoformat()
        day_book.run_report(today, today)
        assert day_book.row_by_voucher(day_book_voucher["voucher_no"]) is not None
        day_book.run_report("2099-12-31", "2099-12-31")
        assert day_book.get_row_count() == 0


class TestDayBookAccounting:
    @pytest.fixture(autouse=True)
    def load_today_report(self, logged_in_page, day_book_voucher):
        self.day_book = DayBookPage(logged_in_page)
        self.day_book.navigate()
        today = date.today().isoformat()
        self.report = self.day_book.run_report(today, today)
        self.known_voucher = day_book_voucher

    def test_known_voucher_is_reported_with_exact_values(self):
        row = self.day_book.row_by_voucher(self.known_voucher["voucher_no"])
        assert row is not None
        assert row["date"] == date.today().isoformat()
        assert "Contra" in str(row["type"])
        assert self.known_voucher["marker"] in str(row["narration"])
        assert row["debit"] == self.known_voucher["amount"]
        assert row["credit"] == self.known_voucher["amount"]

    def test_api_count_matches_rendered_row_count(self):
        assert self.report["count"] == self.day_book.get_row_count()
        assert self.report["count"] == len(self.day_book.get_all_rows_data())

    def test_every_voucher_row_is_balanced(self):
        rows = self.day_book.get_all_rows_data()
        assert rows, "Today report unexpectedly contains no vouchers"
        for row in rows:
            assert row["debit"] == row["credit"], (
                f"Voucher {row['voucher_no']} is unbalanced: "
                f"debit={row['debit']}, credit={row['credit']}"
            )

    def test_report_totals_equal_rendered_sums(self):
        rows = self.day_book.get_all_rows_data()
        debit_sum = sum((row["debit"] for row in rows), Decimal("0"))
        credit_sum = sum((row["credit"] for row in rows), Decimal("0"))
        assert debit_sum == Decimal(str(self.report["total_debit"]))
        assert credit_sum == Decimal(str(self.report["total_credit"]))

    def test_report_aggregate_is_balanced(self):
        assert self.report["is_balanced"] is True
        assert Decimal(str(self.report["total_debit"])) == Decimal(
            str(self.report["total_credit"])
        )
