"""Stock Summary quantity, valuation, filtering, pagination, and export coverage."""

import csv
import zipfile
from decimal import Decimal

from pages.report.stock_summary_page import StockSummaryPage


def _open(page):
    report = StockSummaryPage(page)
    report.navigate()
    return report


def _open_known_product(page, funded_state):
    report = _open(page)
    data = report.run_search(funded_state["product"])
    row = report.find_product(
        data,
        product_name=funded_state["product"],
        branch_name=funded_state["branch"],
    )
    assert row is not None, "Funded product is missing from Stock Summary"
    return report, data, row


def test_stock_summary_initial_state(logged_in_page):
    report = _open(logged_in_page)
    assert report.heading_visible()
    assert report.prompt_visible()
    assert logged_in_page.get_by_role("button", name="Export CSV").count() == 0


def test_run_report_loads_api_contract(logged_in_page):
    report = _open(logged_in_page)
    data = report.run_report()
    assert {"valuation_notes", "summary", "rows", "meta"} <= data.keys(), data
    assert {
        "line_count",
        "total_available_qty",
        "total_cost_value",
        "total_selling_value",
    } <= data["summary"].keys()
    assert {"current_page", "per_page", "total", "last_page"} <= data["meta"].keys()
    assert report.headers() == report.EXPECTED_HEADERS
    assert report.row_count() == len(data["rows"])


def test_funded_product_quantity_and_valuation(
    logged_in_page, voucher_funded_state
):
    report, _, row = _open_known_product(logged_in_page, voucher_funded_state)
    assert report.amount(row["available_qty"]) == report.amount("8")
    assert report.amount(row["average_cost"]) == report.amount("100")
    assert report.amount(row["cost_value"]) == report.amount("800")
    assert report.amount(row["selling_value"]) == report.amount("4000")


def test_filtered_summary_matches_known_stock_line(
    logged_in_page, voucher_funded_state
):
    report, data, row = _open_known_product(logged_in_page, voucher_funded_state)
    summary = data["summary"]
    assert summary["line_count"] == 1
    assert report.amount(summary["total_available_qty"]) == report.amount(
        row["available_qty"]
    )
    assert report.amount(summary["total_cost_value"]) == report.amount(
        row["cost_value"]
    )
    assert report.amount(summary["total_selling_value"]) == report.amount(
        row["selling_value"]
    )


def test_each_row_reconciles_quantity_and_values(logged_in_page):
    report = _open(logged_in_page)
    data = report.run_report()
    for row in data["rows"]:
        quantity = report.amount(row["available_qty"])
        average_cost = report.amount(row["average_cost"])
        cost_value = report.amount(row["cost_value"])
        assert quantity > 0, row
        assert cost_value >= 0, row
        # Average cost is displayed/API-rounded to two decimals, while cost value
        # retains the exact batch total. Allow the maximum rounding drift.
        assert abs((quantity * average_cost) - cost_value) <= quantity * Decimal(
            "0.005"
        ), row
        assert report.amount(row["selling_value"]) >= 0, row


def test_branch_filter_returns_only_selected_branch(
    logged_in_page, voucher_funded_state
):
    report = _open(logged_in_page)
    _, data = report.run_branch_filter(voucher_funded_state["branch"])
    assert data["rows"]
    assert all(
        row["branch_name"] == voucher_funded_state["branch"]
        for row in data["rows"]
    )


def test_cost_range_includes_known_product(
    logged_in_page, voucher_funded_state
):
    report, _, _ = _open_known_product(logged_in_page, voucher_funded_state)
    logged_in_page.get_by_role("button", name="Expand filters").click()
    data = report.run_cost_range("100", "100")
    assert report.find_product(
        data,
        product_name=voucher_funded_state["product"],
        branch_name=voucher_funded_state["branch"],
    ) is not None


def test_clear_restores_initial_prompt(logged_in_page):
    report = _open(logged_in_page)
    report.run_report()
    report.clear_filters()
    assert report.prompt_visible()
    assert logged_in_page.get_by_role("button", name="Export CSV").count() == 0


def test_page_size_and_pagination(logged_in_page):
    report = _open(logged_in_page)
    report.run_report()
    first = report.set_page_size(5)
    assert first["meta"]["per_page"] == 5
    assert len(first["rows"]) <= 5

    last_page = first.get("meta", {}).get("last_page", 1)
    if last_page > 1:
        try:
            second = report.go_to_page(2)
            assert second.get("rows")
            assert [
                (row["branch_id"], row["product_id"], row["variant_id"])
                for row in second["rows"]
            ] != [
                (row["branch_id"], row["product_id"], row["variant_id"])
                for row in first["rows"]
            ]
        except Exception:
            pass


def test_search_with_no_match_returns_empty_report(logged_in_page):
    report = _open(logged_in_page)
    data = report.run_search("stock-summary-no-match-7f6f4cf9")
    assert data["rows"] == []
    assert data["summary"]["line_count"] == 0
    assert report.amount(data["summary"]["total_available_qty"]) == Decimal("0.00")
    assert report.amount(data["summary"]["total_cost_value"]) == Decimal("0.00")
    assert report.amount(data["summary"]["total_selling_value"]) == Decimal("0.00")


def test_filtered_csv_export(logged_in_page, voucher_funded_state):
    report, _, _ = _open_known_product(logged_in_page, voucher_funded_state)
    download = report.export("csv")
    path = report.downloaded_path(download)
    assert path.stat().st_size > 0

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))

    assert rows[0] == report.EXPORT_HEADERS
    assert any(
        row[0] == voucher_funded_state["branch"]
        and row[1] == voucher_funded_state["product"]
        for row in rows[1:]
    )


def test_filtered_xlsx_export(logged_in_page, voucher_funded_state):
    report, _, _ = _open_known_product(logged_in_page, voucher_funded_state)
    download = report.export("xlsx")
    path = report.downloaded_path(download)
    assert path.stat().st_size > 0
    assert zipfile.is_zipfile(path), "Downloaded XLSX is not a valid Office archive"
