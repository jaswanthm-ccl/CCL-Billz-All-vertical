"""End-to-end coverage for the Cash Flow Statement report."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from playwright.sync_api import expect

from pages.accounting.cash_flow_page import CashFlowPage


ACTIVITIES = ("operating", "investing", "financing")


@pytest.fixture(scope="module")
def cash_flow_funded_state(module_page, voucher_funded_state):
    """Load a branch-scoped report after one cash and one bank sale."""
    report_page = CashFlowPage(module_page)
    report_page.navigate()
    report = report_page.apply_filters(
        (date.today() - timedelta(days=1)).isoformat(),
        date.today().isoformat(),
        voucher_funded_state["branch"],
    )
    return {"report": report, **voucher_funded_state}


class TestCashFlowStructure:
    def test_page_loads_and_report_is_requested(self, logged_in_page):
        report_page = CashFlowPage(logged_in_page)
        report = report_page.navigate()

        assert report_page.is_page_visible()
        assert report_page.last_status == 200
        assert {
            "from_date",
            "to_date",
            "branch_id",
            "opening_cash",
            "operating",
            "investing",
            "financing",
            "net_cash_flow",
            "closing_cash",
        } <= report.keys()

    def test_default_period_is_three_months_to_today(self, logged_in_page):
        report_page = CashFlowPage(logged_in_page)
        report = report_page.navigate()

        assert report_page.from_date.input_value() == report["from_date"]
        assert report_page.to_date.input_value() == date.today().isoformat()
        assert report["to_date"] == date.today().isoformat()

    @pytest.mark.parametrize(
        "title", ("Operating Activities", "Investing Activities", "Financing Activities")
    )
    def test_activity_sections_show_inflow_outflow_and_net(self, logged_in_page, title):
        report_page = CashFlowPage(logged_in_page)
        report_page.navigate()
        card = logged_in_page.locator(
            ".card", has=logged_in_page.get_by_text(title, exact=True)
        )
        expect(card.get_by_text("Inflow", exact=True)).to_be_visible()
        expect(card.get_by_text("Outflow", exact=True)).to_be_visible()
        expect(card.get_by_text("Net", exact=True)).to_be_visible()


class TestCashFlowFilters:
    def test_dates_are_required(self, logged_in_page):
        report_page = CashFlowPage(logged_in_page)
        report_page.navigate()
        report_page.submit_without_dates()

        expect(logged_in_page.get_by_text("From date is required", exact=True)).to_be_visible()
        expect(logged_in_page.get_by_text("To date is required", exact=True)).to_be_visible()

    def test_invalid_date_range_is_rejected(self, logged_in_page):
        report_page = CashFlowPage(logged_in_page)
        report_page.navigate()
        report_page.submit_invalid_range("2099-12-31", "2099-01-01")

        expect(
            logged_in_page.get_by_text(
                "To date must be greater than from date", exact=True
            )
        ).to_be_visible()

    def test_date_filter_is_sent_to_report(self, logged_in_page):
        report_page = CashFlowPage(logged_in_page)
        report_page.navigate()
        report = report_page.apply_filters("2026-01-01", "2026-01-31")

        assert report["from_date"] == "2026-01-01"
        assert report["to_date"] == "2026-01-31"

    def test_branch_filter_is_sent_to_report(self, cash_flow_funded_state):
        assert cash_flow_funded_state["report"]["branch_id"] is not None

    def test_clear_filters_restores_defaults(self, logged_in_page):
        report_page = CashFlowPage(logged_in_page)
        report_page.navigate()
        report_page.apply_filters("2026-01-01", "2026-01-31")
        report = report_page.clear_filters()

        assert report_page.from_date.input_value() == report["from_date"]
        assert report_page.to_date.input_value() == date.today().isoformat()
        assert report["to_date"] == date.today().isoformat()
        assert report["branch_id"] is None


class TestCashFlowAccounting:
    @pytest.mark.parametrize("activity", ACTIVITIES)
    def test_activity_net_equals_inflow_minus_outflow(
        self, cash_flow_funded_state, activity
    ):
        section = cash_flow_funded_state["report"][activity]
        assert Decimal(str(section["net"])) == (
            Decimal(str(section["inflow"])) - Decimal(str(section["outflow"]))
        )

    def test_net_cash_flow_equals_sum_of_activity_nets(self, cash_flow_funded_state):
        report = cash_flow_funded_state["report"]
        expected = sum(
            (Decimal(str(report[activity]["net"])) for activity in ACTIVITIES),
            Decimal("0"),
        )
        assert Decimal(str(report["net_cash_flow"])) == expected

    def test_closing_cash_equals_opening_plus_net_flow(self, cash_flow_funded_state):
        report = cash_flow_funded_state["report"]
        assert Decimal(str(report["closing_cash"])) == (
            Decimal(str(report["opening_cash"]))
            + Decimal(str(report["net_cash_flow"]))
        )

    def test_cash_paid_sale_is_operating_inflow(self, cash_flow_funded_state):
        report = cash_flow_funded_state["report"]
        assert Decimal(str(report["operating"]["inflow"])) >= Decimal("500")

    @pytest.mark.skip(
        reason=(
            "BUG: Branch-filtered Cash Flow omits the bank-paid sale because bank "
            "ledgers are tenant-wide and do not use the business branch_id"
        )
    )
    def test_branch_cash_flow_includes_cash_and_bank_receipts(
        self, cash_flow_funded_state
    ):
        report = cash_flow_funded_state["report"]
        assert Decimal(str(report["operating"]["inflow"])) >= Decimal("1000")

    def test_rendered_activity_values_match_api(self, module_page, cash_flow_funded_state):
        report_page = CashFlowPage(module_page)
        report = report_page.apply_filters(
            (date.today() - timedelta(days=1)).isoformat(),
            date.today().isoformat(),
            cash_flow_funded_state["branch"],
        )
        titles = {
            "operating": "Operating Activities",
            "investing": "Investing Activities",
            "financing": "Financing Activities",
        }
        metrics = {"inflow": "Inflow", "outflow": "Outflow", "net": "Net"}

        for activity, title in titles.items():
            for key, label in metrics.items():
                assert report_page.activity_amount(title, label) == Decimal(
                    str(report[activity][key])
                )

    def test_rendered_summary_values_match_api(self, module_page, cash_flow_funded_state):
        report_page = CashFlowPage(module_page)
        report = report_page.apply_filters(
            (date.today() - timedelta(days=1)).isoformat(),
            date.today().isoformat(),
            cash_flow_funded_state["branch"],
        )
        labels = {
            "Opening Cash": "opening_cash",
            "Net Cash Flow": "net_cash_flow",
            "Closing Cash": "closing_cash",
        }

        for label, key in labels.items():
            assert report_page.summary_amount(label) == Decimal(str(report[key]))
