"""GSTR-1 B2B report contract, tax calculation, filters, and exports."""

from decimal import Decimal

import pytest

from pages.report.gstr_1_b2b_page import Gstr1B2bPage

pytestmark = pytest.mark.usefixtures("gstr_b2b_sale")


def _open(page):
    report = Gstr1B2bPage(page)
    return report, report.navigate()


def _assert_contract(data: dict, mode: str = "invoice_wise") -> list[dict]:
    assert isinstance(data, dict), "B2B preview did not return a data object"
    assert {"meta", "rows", "totals", "warnings", "validation_errors"} <= data.keys()
    assert data["meta"]["classification"] == "b2b"
    assert data["meta"]["mode"] == mode
    assert isinstance(data["rows"], list)
    assert isinstance(data["totals"], dict)
    return data["rows"]


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def test_gstr1_b2b_page_loads_real_report(logged_in_page):
    report, data = _open(logged_in_page)

    assert report.heading_visible()
    _assert_contract(data)
    assert set(report.EXPECTED_HEADERS) <= set(report.headers())


def test_b2b_invoice_rows_have_gstin_and_balanced_tax(
    logged_in_page, gstr_b2b_sale
):
    _, data = _open(logged_in_page)
    rows = _assert_contract(data)

    assert rows, "B2B report has no invoice rows; controlled B2B test data is required"
    for row in rows:
        assert row["classification"] == "b2b"
        assert str(row["customer_gstin"]).strip(), row["invoice_number"]
        expected_total = sum(
            _money(row[key])
            for key in ("taxable_value", "cgst_amount", "sgst_amount", "igst_amount")
        )
        assert abs(_money(row["total_invoice_value"]) - expected_total) <= Decimal("0.01")
        if row["is_same_state"]:
            assert _money(row["igst_amount"]) == Decimal("0.00")
        else:
            assert _money(row["cgst_amount"]) == Decimal("0.00")
            assert _money(row["sgst_amount"]) == Decimal("0.00")

    controlled = next(
        row
        for row in rows
        if row["customer_name"] == gstr_b2b_sale["customer_name"]
    )
    assert controlled["customer_gstin"] == gstr_b2b_sale["gstin"]
    assert _money(controlled["taxable_value"]) == _money(gstr_b2b_sale["taxable_value"])
    assert _money(controlled["cgst_amount"]) == _money(gstr_b2b_sale["cgst"])
    assert _money(controlled["sgst_amount"]) == _money(gstr_b2b_sale["sgst"])
    assert _money(controlled["igst_amount"]) == _money(gstr_b2b_sale["igst"])
    assert _money(controlled["total_invoice_value"]) == _money(gstr_b2b_sale["invoice_total"])


def test_b2b_totals_equal_rendered_invoice_rows(logged_in_page):
    report, data = _open(logged_in_page)
    rows = _assert_contract(data)
    totals = data["totals"]

    assert len(report.rows()) == len(rows)
    assert int(totals["invoice_count"]) == len(rows)
    for key in ("taxable_value", "cgst_amount", "sgst_amount", "igst_amount"):
        assert _money(totals[key]) == sum((_money(row[key]) for row in rows), Decimal("0.00"))


def test_b2b_custom_date_filter_sends_exact_parameters(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.apply_filters(
        from_date=report.month_start(),
        to_date=report.today(),
        mode="invoice_wise",
    )

    _assert_contract(data)
    assert data["meta"]["start_date"] == report.month_start()
    assert data["meta"]["end_date"] == report.today()


def test_b2b_summary_mode_uses_same_totals(logged_in_page):
    report, _ = _open(logged_in_page)
    invoice_data = report.apply_filters(
        from_date=report.month_start(),
        to_date=report.today(),
        mode="invoice_wise",
    )
    summary_data = report.apply_filters(
        from_date=report.month_start(),
        to_date=report.today(),
        mode="summary_wise",
    )

    _assert_contract(summary_data, mode="summary_wise")
    for key in ("taxable_value", "cgst_amount", "sgst_amount", "igst_amount", "invoice_count"):
        assert _money(summary_data["totals"][key]) == _money(invoice_data["totals"][key])


def test_b2b_reset_restores_financial_year_mode(logged_in_page):
    report, _ = _open(logged_in_page)
    report.apply_filters(
        from_date=report.month_start(),
        to_date=report.today(),
        mode="summary_wise",
    )

    data = report.clear_filters()

    _assert_contract(data)
    assert report.selected_filter_label("period_type") == "Financial Year"
    assert report.selected_filter_label("mode") == "Invoice Wise"


def test_b2b_xlsx_export_is_valid(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.apply_filters(
        from_date=report.today(),
        to_date=report.today(),
    )
    assert _assert_contract(data), "B2B export requires at least one report row"

    xlsx_path = report.downloaded_path(report.export("xlsx"))
    report.assert_valid_xlsx(xlsx_path, report.REPORT_NAME)


def test_b2b_pdf_export_is_valid(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.apply_filters(
        from_date=report.today(),
        to_date=report.today(),
    )
    assert _assert_contract(data), "B2B export requires at least one report row"

    pdf_path = report.downloaded_path(report.export("pdf"))
    report.assert_valid_pdf(pdf_path)
