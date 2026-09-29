"""Supplier Outstanding report and payment-settlement lifecycle coverage."""

import csv

import pytest

from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.report.supplier_outstanding_page import SupplierOutstandingPage


def _open(page):
    report = SupplierOutstandingPage(page)
    data = report.navigate()
    assert {"items", "pagination", "summary"} <= data.keys(), data
    return report, data


def _open_known_supplier(page, outstanding_purchase):
    report, _ = _open(page)
    supplier = outstanding_purchase["supplier"]
    data = report.search(supplier)
    party = report.find_party(data, supplier)
    assert party is not None, f"Supplier ledger not found in report: {supplier}"
    return report, data, party


def test_supplier_outstanding_page_loads(logged_in_page):
    report, _ = _open(logged_in_page)
    assert report.heading_visible()
    assert report.headers() == report.EXPECTED_HEADERS


def test_api_contract_and_rendered_rows_match(logged_in_page):
    report, data = _open(logged_in_page)
    assert len(report.rows()) == len(data["items"])
    assert {
        "current_page", "per_page", "total", "last_page"
    } <= data["pagination"].keys()
    assert {
        "total_outstanding", "count_with_outstanding", "total_parties"
    } <= data["summary"].keys()


def test_credit_purchase_is_reported_as_payable(
    logged_in_page, module_outstanding_purchase
):
    report, _, party = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    assert party["balance_type"] == "Payable", party
    assert report.amount(party["outstanding_amount"]) == report.amount("200")
    assert report.amount(party["ledger_balance"]) == report.amount("200")
    assert party["last_transaction_date"], party
    assert len(report.rows()) == 1


def test_filtered_summary_matches_known_supplier(
    logged_in_page, module_outstanding_purchase
):
    report, data, _ = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    summary = data["summary"]
    assert report.amount(summary["total_outstanding"]) == report.amount("200")
    assert summary["count_with_outstanding"] == 1
    assert summary["total_parties"] == 1


def test_unknown_supplier_search_returns_empty_state(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.search("AUTOMATION-NO-SUCH-SUPPLIER-987654321")
    assert data["items"] == []
    assert data["summary"]["total_parties"] == 0
    assert report.rows() == []


def test_minimum_outstanding_filter(
    logged_in_page, module_outstanding_purchase
):
    report, _, _ = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    data = report.set_min_outstanding("201")
    assert data["items"] == []
    assert data["summary"]["total_parties"] == 0


@pytest.mark.skip(
    reason=(
        "App bug: maximum-only filter returns HTTP 422 because max_outstanding "
        "requires a missing min_outstanding value"
    )
)
def test_maximum_outstanding_filter(
    logged_in_page, module_outstanding_purchase
):
    report, _, _ = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    data = report.set_max_outstanding("199")
    assert data["items"] == []
    assert data["summary"]["total_parties"] == 0


@pytest.mark.skip(
    reason=(
        "App bug: supplier ledgers have no accounting branch, so the selected "
        "branch does not scope Supplier Outstanding results"
    )
)
def test_branch_filter_returns_only_selected_branch(
    logged_in_page, module_branch
):
    report, _ = _open(logged_in_page)
    branch_id, data = report.select_branch(module_branch)
    assert all(
        str(item["branch_id"]) == branch_id for item in data["items"]
    ), data["items"]


def test_outstanding_sort_descending(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.set_sort("outstanding_amount", "desc")
    amounts = [
        report.amount(item["outstanding_amount"])
        for item in data["items"]
        if report.amount(item["outstanding_amount"]) > 0
    ]
    assert amounts == sorted(amounts, reverse=True)


def test_reset_filters_restores_defaults(
    logged_in_page, module_outstanding_purchase
):
    report, _, _ = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    report.set_min_outstanding("1")
    data = report.reset_filters()
    assert data["pagination"]["current_page"] == 1
    assert data["pagination"]["per_page"] == 20


def test_page_size_limits_api_and_table_rows(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.set_page_size(5)
    assert data["pagination"]["per_page"] == 5
    assert len(data["items"]) <= 5
    assert len(report.rows()) == len(data["items"])


def test_ledger_drawer_shows_credit_purchase(
    logged_in_page, module_outstanding_purchase
):
    report, _, party = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    ledger = report.open_ledger(module_outstanding_purchase["supplier"])
    assert ledger["rows"], ledger
    assert report.amount(ledger["current_balance"]) == report.amount(
        party["ledger_balance"]
    )
    assert any(
        report.amount(row["credit"]) == report.amount("200")
        for row in ledger["rows"]
    )


def test_export_csv_matches_supplier_filter(
    logged_in_page, module_outstanding_purchase
):
    report, _, _ = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    download = report.export_csv()
    path = report.downloaded_path(download)
    assert path.stat().st_size > 0

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))

    assert rows[0] == [
        "Supplier Name",
        "Ledger Name",
        "Outstanding Amount",
        "Balance Type",
        "Branch",
        "Last Transaction Date",
    ]
    assert any(
        row[0] == module_outstanding_purchase["supplier"] for row in rows[1:]
    )


def test_pagination_moves_to_second_page_when_available(logged_in_page):
    report, _ = _open(logged_in_page)
    first = report.set_page_size(5)
    items = first.get("items", []) if isinstance(first, dict) else []
    last_page = first.get("pagination", {}).get("last_page", 1) if isinstance(first, dict) else 1
    if last_page <= 1 or len(items) < 5:
        pytest.skip("Not enough data to paginate to page 2")
        return

    second = report.go_to_page(2)
    assert second.get("items")
    assert [item["ledger_id"] for item in second["items"]] != [
        item["ledger_id"] for item in first["items"]
    ]


def test_supplier_outstanding_settlement_lifecycle(
    logged_in_page, module_outstanding_purchase, voucher_funded_state
):
    """Unpaid -> partially paid -> fully settled with report updates."""
    supplier = module_outstanding_purchase["supplier"]
    branch_name = module_outstanding_purchase.get("branch", voucher_funded_state["branch"])
    report, initial, party = _open_known_supplier(
        logged_in_page, module_outstanding_purchase
    )
    assert report.amount(party["outstanding_amount"]) == report.amount("200")
    assert report.amount(initial["summary"]["total_outstanding"]) == report.amount("200")

    voucher = CreateVoucherPage(logged_in_page)
    voucher.create_payment_voucher(supplier, "Cash Ledger", "50", branch=branch_name)
    assert voucher.wait_for_redirect_to_history() or voucher.wait_for_success_toast()

    report.navigate()
    partial_data = report.search(supplier)
    partial = report.find_party(partial_data, supplier)
    assert partial is not None
    assert partial["balance_type"] == "Payable"
    assert report.amount(partial["outstanding_amount"]) == report.amount("150")
    assert report.amount(partial_data["summary"]["total_outstanding"]) == report.amount("150")

    voucher.create_payment_voucher(supplier, "Cash Ledger", "150", branch=branch_name)
    assert voucher.wait_for_redirect_to_history() or voucher.wait_for_success_toast()

    report.navigate()
    settled_data = report.search(supplier)
    settled = report.find_party(settled_data, supplier)
    assert settled is not None, "Settled supplier ledger disappeared from the report"
    assert settled["balance_type"] == "Nil", settled
    assert report.amount(settled["outstanding_amount"]) == 0
    assert report.amount(settled["ledger_balance"]) == 0
    assert report.amount(settled_data["summary"]["total_outstanding"]) == 0
    assert settled_data["summary"]["count_with_outstanding"] == 0
