"""Restaurant GSTR-1 B2C Report Test Suite.

Route: /reports/gstr1-b2c
Verifies:
  1. Page loading, heading, and table headers
  2. API contract (meta, rows, totals, warnings, validation_errors)
  3. Totals reconciliation with rendered rows
  4. Each invoice row tax integrity: Total == Taxable + CGST + SGST + IGST
  5. Custom date range filtering
  6. Mode switching (Invoice Wise vs Summary Wise)
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from pages.Verticals.Restaurant.report.gstr_1_b2c_page import Gstr1B2cPage

pytestmark = pytest.mark.restaurant


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _assert_contract(data: dict, mode: str = "invoice_wise") -> list[dict]:
    assert isinstance(data, dict), "B2C report did not return a valid data dictionary"
    assert {"meta", "rows", "totals", "warnings", "validation_errors"} <= data.keys()
    assert data["meta"]["classification"] == "b2c"
    assert data["meta"]["mode"] == mode
    assert isinstance(data["rows"], list)
    assert isinstance(data["totals"], dict)
    return data["rows"]


# ── Tier 1: Structure & Page Load ─────────────────────────────────────────────

class TestResGstr1B2cStructure:
    """Verify page load and API contract."""

    def test_gstr1_b2c_page_loads_real_report(self, res_logged_in_page):
        page = res_logged_in_page
        report = Gstr1B2cPage(page)
        data = report.navigate()

        assert report.heading_visible(), "GSTR-1 B2C heading should be visible"
        _assert_contract(data)

    def test_table_headers_present(self, res_logged_in_page):
        page = res_logged_in_page
        report = Gstr1B2cPage(page)
        report.navigate()

        headers = report.headers()
        assert len(headers) >= 5, f"Expected at least 5 table headers, got {len(headers)}: {headers}"
        header_text = " ".join(headers).upper()
        assert "INVOICE" in header_text, f"Missing INVOICE column: {headers}"
        assert "GST" in header_text or "TAX" in header_text, f"Missing GST/TAX column: {headers}"

    def test_rendered_row_count_matches_api(self, res_logged_in_page):
        page = res_logged_in_page
        report = Gstr1B2cPage(page)
        data = report.navigate()

        rows = data.get("rows", [])
        assert len(report.rows()) == len(rows)


# ── Tier 2: Totals and Calculations ───────────────────────────────────────────

class TestResGstr1B2cCalculations:
    """Verify tax calculations and totals reconciliation."""

    def test_b2c_totals_equal_rendered_invoice_rows(self, res_logged_in_page):
        page = res_logged_in_page
        report = Gstr1B2cPage(page)
        data = report.navigate()

        rows = _assert_contract(data)
        totals = data["totals"]

        # DOM rendered rows must match the rows array returned by API
        assert len(report.rows()) == len(rows)

        # Grand total invoice count across all pages is >= current page rows
        total_count = int(totals.get("invoice_count", 0))
        assert total_count >= len(rows), f"Grand total {total_count} should be >= page rows {len(rows)}"

        for key in ("taxable_value", "cgst_amount", "sgst_amount", "igst_amount"):
            if key in totals:
                page_sum = sum((_money(row[key]) for row in rows if key in row), Decimal("0.00"))
                if total_count == len(rows):
                    assert _money(totals[key]) == page_sum, (
                        f"Mismatch in total {key}: expected {page_sum}, got {totals[key]}"
                    )
                else:
                    assert _money(totals[key]) >= page_sum, (
                        f"Grand total {key} ({totals[key]}) should be >= page sum ({page_sum})"
                    )

    def test_invoice_rows_tax_calculation_integrity(self, res_logged_in_page):
        page = res_logged_in_page
        report = Gstr1B2cPage(page)
        data = report.navigate()

        rows = _assert_contract(data)
        if not rows:
            pytest.skip("No B2C invoices present to verify individual row tax calculations")

        for row in rows:
            assert row.get("classification") == "b2c"
            taxable = _money(row.get("taxable_value", 0))
            cgst = _money(row.get("cgst_amount", 0))
            sgst = _money(row.get("sgst_amount", 0))
            igst = _money(row.get("igst_amount", 0))
            total_val = _money(row.get("total_invoice_value", 0))

            expected_total = taxable + cgst + sgst + igst
            assert abs(total_val - expected_total) <= Decimal("0.05"), (
                f"Row tax formula broken for {row.get('invoice_number')}: "
                f"{total_val} != {taxable} + {cgst} + {sgst} + {igst}"
            )


# ── Tier 3: Filters & Display Modes ───────────────────────────────────────────

class TestResGstr1B2cFilters:
    """Verify date filtering and summary/invoice view modes."""

    def test_b2c_custom_date_filter_sends_exact_parameters(self, res_logged_in_page):
        page = res_logged_in_page
        report = Gstr1B2cPage(page)
        report.navigate()

        data = report.apply_filters(
            from_date=report.month_start(),
            to_date=report.today(),
            mode="invoice_wise",
        )

        _assert_contract(data)
        assert data["meta"]["start_date"] == report.month_start()
        assert data["meta"]["end_date"] == report.today()

    def test_b2c_summary_mode_switch(self, res_logged_in_page):
        page = res_logged_in_page
        report = Gstr1B2cPage(page)
        report.navigate()

        summary_data = report.apply_filters(
            from_date=report.month_start(),
            to_date=report.today(),
            mode="summary_wise",
        )

        _assert_contract(summary_data, mode="summary_wise")
        assert summary_data["meta"]["mode"] == "summary_wise"
