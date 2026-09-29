"""MDR Report settlement, calculation, grouping, and filter coverage."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.report.mdr_report_page import MdrReportPage
from utils.random_data import generate_random_name


@pytest.fixture(scope="module")
def module_mdr_settlement(module_page, voucher_funded_state):
    """Create a deterministic MDR settlement from yesterday's ₹500 bank sale."""
    narration = generate_random_name("mdr_report")
    voucher = CreateVoucherPage(module_page)
    voucher.create_mdr_settlement_voucher(
        bank_ledger=voucher_funded_state["bank"],
        mdr_amount="2",
        remarks=narration,
    )
    assert voucher.wait_for_redirect_to_history() or voucher.wait_for_success_toast()

    yield {
        "bank": voucher_funded_state["bank"],
        "date": date.today().isoformat(),
        "gross": "500",
        "net": "498",
        "mdr": "2",
        "percentage": "0.4",
        "narration": narration,
    }


def _open(page):
    report = MdrReportPage(page)
    data = report.navigate()
    assert {"from_date", "to_date", "summary_by_bank", "entries"} <= data.keys(), data
    return report, data


def _open_known_settlement(page, settlement):
    report, _ = _open(page)
    data = report.apply_filters(
        from_date=settlement["date"],
        to_date=settlement["date"],
        bank_name=settlement["bank"],
    )
    entry = report.find_entry(data, narration=settlement["narration"])
    assert entry is not None, "Created MDR settlement is missing from MDR Report"
    return report, data, entry


def test_mdr_report_page_loads_with_default_period(logged_in_page):
    report, data = _open(logged_in_page)
    assert report.heading_visible()
    assert data["from_date"] == report.month_start()
    assert data["to_date"] == report.today()


def test_created_settlement_appears_with_expected_values(
    logged_in_page, module_mdr_settlement
):
    report, _, entry = _open_known_settlement(
        logged_in_page, module_mdr_settlement
    )
    assert entry["bank_name"] == module_mdr_settlement["bank"]
    assert entry["date"] == module_mdr_settlement["date"]
    assert report.amount(entry["net_settlement"]) == report.amount("498")
    assert report.amount(entry["mdr_charge"]) == report.amount("2")
    assert report.amount(entry["gross"]) == report.amount("500")
    assert Decimal(str(entry["mdr_percentage"])) == Decimal("0.4")
    assert entry["voucher_no"]


def test_report_tables_match_api_rows(logged_in_page, module_mdr_settlement):
    report, data, _ = _open_known_settlement(
        logged_in_page, module_mdr_settlement
    )
    assert report.summary_headers() == report.SUMMARY_HEADERS
    assert report.detail_headers() == report.DETAIL_HEADERS
    assert report.summary_row_count() == len(data["summary_by_bank"])
    assert report.detail_row_count() == len(data["entries"])


def test_each_entry_reconciles_gross_and_percentage(
    logged_in_page, module_mdr_settlement
):
    report, data, _ = _open_known_settlement(
        logged_in_page, module_mdr_settlement
    )
    for entry in data["entries"]:
        net = report.amount(entry["net_settlement"])
        mdr = report.amount(entry["mdr_charge"])
        gross = report.amount(entry["gross"])
        assert gross == net + mdr, entry

        expected_percentage = (
            Decimal("0")
            if gross == 0
            else (mdr / gross * Decimal("100")).quantize(Decimal("0.0001"))
        )
        actual_percentage = Decimal(str(entry["mdr_percentage"])).quantize(
            Decimal("0.0001")
        )
        assert actual_percentage == expected_percentage, entry


def test_bank_summary_reconciles_detail_entries(
    logged_in_page, module_mdr_settlement
):
    report, data, _ = _open_known_settlement(
        logged_in_page, module_mdr_settlement
    )
    summary = report.find_bank_summary(
        data, bank_name=module_mdr_settlement["bank"]
    )
    assert summary is not None

    entries = [
        entry
        for entry in data["entries"]
        if entry["bank_account_id"] == summary["bank_account_id"]
    ]
    assert summary["voucher_count"] == len(entries)
    assert report.amount(summary["total_net_settlement"]) == sum(
        (report.amount(entry["net_settlement"]) for entry in entries),
        Decimal("0"),
    )
    assert report.amount(summary["total_mdr_charge"]) == sum(
        (report.amount(entry["mdr_charge"]) for entry in entries),
        Decimal("0"),
    )
    assert report.amount(summary["total_gross"]) == sum(
        (report.amount(entry["gross"]) for entry in entries),
        Decimal("0"),
    )


def test_bank_filter_returns_only_selected_bank(
    logged_in_page, module_mdr_settlement
):
    report, data, _ = _open_known_settlement(
        logged_in_page, module_mdr_settlement
    )
    assert data["entries"]
    assert all(
        entry["bank_name"] == module_mdr_settlement["bank"]
        for entry in data["entries"]
    )
    assert all(
        summary["bank_name"] == module_mdr_settlement["bank"]
        for summary in data["summary_by_bank"]
    )


def test_period_without_settlement_shows_empty_state(
    logged_in_page, module_mdr_settlement
):
    report, _ = _open(logged_in_page)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    data = report.apply_filters(
        from_date=yesterday,
        to_date=yesterday,
        bank_name=module_mdr_settlement["bank"],
    )
    assert data["entries"] == []
    assert data["summary_by_bank"] == []
    assert report.no_settlements_visible()


def test_clear_filters_restores_default_period(
    logged_in_page, module_mdr_settlement
):
    report, _ = _open(logged_in_page)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    report.apply_filters(
        from_date=yesterday,
        to_date=yesterday,
        bank_name=module_mdr_settlement["bank"],
    )
    data = report.clear_filters()
    assert data["from_date"] == report.month_start()
    assert data["to_date"] == report.today()
    assert report.find_entry(
        data, narration=module_mdr_settlement["narration"]
    ) is not None


def test_detail_voucher_link_targets_created_voucher(
    logged_in_page, module_mdr_settlement
):
    report, _, entry = _open_known_settlement(
        logged_in_page, module_mdr_settlement
    )
    link = report.voucher_link(entry["voucher_id"])
    assert link.count() == 1
    assert link.inner_text().strip() == entry["voucher_no"]


def test_detail_entries_are_chronological(
    logged_in_page, module_mdr_settlement
):
    _, data, _ = _open_known_settlement(
        logged_in_page, module_mdr_settlement
    )
    ordering = [
        (entry["date"] or "", int(entry["voucher_id"]))
        for entry in data["entries"]
    ]
    assert ordering == sorted(ordering)
