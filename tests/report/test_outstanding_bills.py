import pytest

from pages.accounting.create_voucher_page import CreateVoucherPage
from pages.report.outstanding_bills_page import OutstandingBillsPage


EXPECTED_SALES_HEADERS = [
    "Invoice No.", "Customer", "Total", "Settled", "Outstanding", "Status"
]
EXPECTED_PURCHASE_HEADERS = [
    "Invoice No.", "Supplier", "Total", "Settled", "Outstanding", "Status"
]


def _open(page, bill_type="sales"):
    report = OutstandingBillsPage(page)
    data = report.navigate(bill_type)
    assert "items" in data and "pagination" in data, data
    return report, data


def test_outstanding_bills_page_loads(logged_in_page):
    report, _ = _open(logged_in_page)
    assert report.heading_visible()


def test_sales_is_default_bill_type(logged_in_page):
    report, _ = _open(logged_in_page)
    assert report.selected_type() == "sales"
    assert report.headers() == EXPECTED_SALES_HEADERS


def test_purchase_query_loads_supplier_columns(logged_in_page):
    report, data = _open(logged_in_page, "purchases")
    assert report.selected_type() == "purchases"
    assert report.headers() == EXPECTED_PURCHASE_HEADERS
    assert all(item["type"] == "purchase" for item in data["items"])


def test_bill_type_filter_switches_to_purchases(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.set_bill_type("purchases")
    assert report.headers() == EXPECTED_PURCHASE_HEADERS
    assert all(item["type"] == "purchase" for item in data["items"])


def test_pending_status_filter(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.set_status("pending")
    assert report.selected_status() == "pending"
    assert all(item["payment_status"] == "pending" for item in data["items"])


def test_partial_status_filter(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.set_status("partial")
    assert report.selected_status() == "partial"
    assert all(item["payment_status"] == "partial" for item in data["items"])


def test_clear_resets_type_and_status(logged_in_page):
    report, _ = _open(logged_in_page)
    report.set_bill_type("purchases")
    report.set_status("partial", "purchases")
    report.clear_filters("sales")
    assert report.selected_type() == "sales"
    assert report.selected_status() == ""


def test_known_invoice_search(logged_in_page):
    report, data = _open(logged_in_page)
    assert data["items"], "Test environment has no outstanding sales bill to search"
    invoice = str(data["items"][0]["invoice_no"])
    filtered = report.search(invoice)
    assert filtered["items"], f"Invoice search returned no result for {invoice}"
    assert all(invoice.lower() in str(item["invoice_no"]).lower() for item in filtered["items"])


def test_unknown_invoice_search_shows_empty_state(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.search("AUTOMATION-NO-SUCH-INVOICE-987654321")
    assert data["items"] == []
    assert report.rows() == []
    assert logged_in_page.get_by_text("No outstanding bills.", exact=True).is_visible()


def test_page_size_limits_api_and_table_rows(logged_in_page):
    report, _ = _open(logged_in_page)
    data = report.set_page_size(5)
    assert len(data["items"]) <= 5
    assert len(report.rows()) == len(data["items"])


def test_rendered_row_count_matches_api(logged_in_page):
    report, data = _open(logged_in_page)
    assert len(report.rows()) == len(data["items"])


def test_each_bill_amount_reconciles(logged_in_page):
    report, data = _open(logged_in_page)
    assert data["items"], "Test environment has no outstanding sales bills"
    for item in data["items"]:
        total = report.amount(item["invoice_amount"])
        settled = report.amount(item["settled_amount"])
        outstanding = report.amount(item["outstanding_amount"])
        assert total == settled + outstanding, item


def test_only_positive_unpaid_balances_are_listed(logged_in_page):
    report, data = _open(logged_in_page)
    assert data["items"], "Test environment has no outstanding sales bills"
    for item in data["items"]:
        assert report.amount(item["outstanding_amount"]) > 0, item
        assert item["payment_status"] in {"pending", "partial"}, item


def test_payment_status_matches_settlement_amount(logged_in_page):
    report, data = _open(logged_in_page)
    assert data["items"], "Test environment has no outstanding sales bills"
    for item in data["items"]:
        settled = report.amount(item["settled_amount"])
        if item["payment_status"] == "pending":
            assert settled == 0, item
        elif item["payment_status"] == "partial":
            assert settled > 0, item


def test_standalone_report_has_no_settle_action(logged_in_page):
    report, _ = _open(logged_in_page)
    assert report.headers() == EXPECTED_SALES_HEADERS
    assert logged_in_page.get_by_role("button", name="Settle", exact=True).count() == 0


def test_pagination_moves_to_second_page_when_available(logged_in_page):
    report, first = _open(logged_in_page)
    first = report.set_page_size(5)
    items = first.get("items", []) if isinstance(first, dict) else []
    last_page = first.get("pagination", {}).get("last_page", 1) if isinstance(first, dict) else 1
    if last_page <= 1 or len(items) < 5:
        pytest.skip("At least six outstanding sales bills are required to verify pagination")
    second = report.go_to_page(2)
    assert second.get("items")
    assert [item["id"] for item in second["items"]] != [
        item["id"] for item in first["items"]
    ]


def test_sale_outstanding_bill_lifecycle(
    logged_in_page, module_outstanding_sale, voucher_funded_state
):
    """Create an unpaid Sale, partially receive it, then settle it fully."""
    customer = module_outstanding_sale["customer"]
    invoice_no = (module_outstanding_sale.get("invoice_no") or "").lstrip("#").strip()
    branch_name = module_outstanding_sale.get("branch", voucher_funded_state["branch"])
    report = OutstandingBillsPage(logged_in_page)

    initial = report.load_all("sales")
    bill = report.find_bill(initial, party_name=customer)
    if bill is None and invoice_no:
        search_data = report.search(invoice_no, "sales")
        bill = report.find_bill(search_data, party_name=customer)
    if bill is None:
        search_data = report.search(customer, "sales")
        bill = report.find_bill(search_data, party_name=customer)
    assert bill is not None, f"New unpaid Sale was not listed in Outstanding Bills. Customer={customer}, invoice={invoice_no}"
    assert bill["payment_status"] == "pending", bill
    assert report.amount(bill["invoice_amount"]) == report.amount("300")
    assert report.amount(bill["settled_amount"]) == 0
    assert report.amount(bill["outstanding_amount"]) == report.amount("300")

    voucher = CreateVoucherPage(logged_in_page)
    voucher.create_receipt_voucher(customer, "Cash Ledger", "100", branch=branch_name)
    assert voucher.wait_for_redirect_to_history() or voucher.wait_for_success_toast()

    partial_data = report.load_all("sales")
    partial = report.find_bill(partial_data, party_name=customer, bill_id=bill["id"])
    if partial is None and invoice_no:
        search_data = report.search(invoice_no, "sales")
        partial = report.find_bill(search_data, party_name=customer, bill_id=bill["id"])
    if partial is None:
        search_data = report.search(customer, "sales")
        partial = report.find_bill(search_data, party_name=customer, bill_id=bill["id"])
    assert partial is not None, "Partially settled Sale disappeared from the report"
    assert partial["payment_status"] == "partial", partial
    assert report.amount(partial["settled_amount"]) == report.amount("100")
    assert report.amount(partial["outstanding_amount"]) == report.amount("200")

    voucher.create_receipt_voucher(customer, "Cash Ledger", "200", branch=branch_name)
    assert voucher.wait_for_redirect_to_history() or voucher.wait_for_success_toast()

    settled_data = report.load_all("sales")
    if invoice_no:
        search_settled = report.search(invoice_no, "sales")
        assert report.find_bill(
            search_settled, party_name=customer, bill_id=bill["id"]
        ) is None, "Fully settled Sale still appears in Outstanding Bills"
    else:
        assert report.find_bill(
            settled_data, party_name=customer, bill_id=bill["id"]
        ) is None, "Fully settled Sale still appears in Outstanding Bills"


def test_purchase_outstanding_bill_lifecycle(
    logged_in_page, module_outstanding_purchase, voucher_funded_state
):
    """Create an unpaid Purchase, partially pay it, then settle it fully."""
    supplier = module_outstanding_purchase["supplier"]
    ref_no = module_outstanding_purchase.get("reference_no")
    branch_name = module_outstanding_purchase.get("branch", voucher_funded_state["branch"])
    report = OutstandingBillsPage(logged_in_page)

    initial = report.load_all("purchases")
    bill = report.find_bill(initial, party_name=supplier)
    if bill is None and ref_no:
        search_data = report.search(ref_no, "purchases")
        bill = report.find_bill(search_data, party_name=supplier)
    if bill is None:
        search_data = report.search(supplier, "purchases")
        bill = report.find_bill(search_data, party_name=supplier)
    assert bill is not None, f"New unpaid Purchase was not listed in Outstanding Bills. Supplier={supplier}, ref={ref_no}"
    assert bill["payment_status"] == "pending", bill
    assert report.amount(bill["invoice_amount"]) == report.amount("200")
    assert report.amount(bill["settled_amount"]) == 0
    assert report.amount(bill["outstanding_amount"]) == report.amount("200")

    voucher = CreateVoucherPage(logged_in_page)
    voucher.create_payment_voucher(supplier, "Cash Ledger", "50", branch=branch_name)
    assert voucher.wait_for_redirect_to_history() or voucher.wait_for_success_toast()

    partial_data = report.load_all("purchases")
    partial = report.find_bill(partial_data, party_name=supplier, bill_id=bill["id"])
    if partial is None and ref_no:
        search_data = report.search(ref_no, "purchases")
        partial = report.find_bill(search_data, party_name=supplier, bill_id=bill["id"])
    if partial is None:
        search_data = report.search(supplier, "purchases")
        partial = report.find_bill(search_data, party_name=supplier, bill_id=bill["id"])
    assert partial is not None, "Partially settled Purchase disappeared from the report"
    assert partial["payment_status"] == "partial", partial
    assert report.amount(partial["settled_amount"]) == report.amount("50")
    assert report.amount(partial["outstanding_amount"]) == report.amount("150")

    voucher.create_payment_voucher(supplier, "Cash Ledger", "150", branch=branch_name)
    assert voucher.wait_for_redirect_to_history() or voucher.wait_for_success_toast()

    settled_data = report.load_all("purchases")
    assert report.find_bill(
        settled_data, party_name=supplier, bill_id=bill["id"]
    ) is None, "Fully settled Purchase still appears in Outstanding Bills"
