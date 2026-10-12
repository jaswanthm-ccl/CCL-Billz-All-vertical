"""Galaxy invoice: the sale invoice is the customer's warranty proof, so it must name the phone's serial (IMEI)."""
from pypdf import PdfReader

from pages.main_menu.sales_page import SalesPage
from tests.Verticals.Galaxy.data_fixtures import GALAXY_BRANCH

PRICE = "15000"


def test_downloaded_invoice_shows_the_sold_serial(galaxy_logged_in_page, tenant, galaxy_stock, galaxy_customer):
    product, serials, _ = galaxy_stock
    sales_page = SalesPage(galaxy_logged_in_page, tenant)
    sale = sales_page.add_sale(galaxy_customer, GALAXY_BRANCH, PRICE, PRICE, product_name=product, serials=[serials[0]])

    pdf_path = sales_page.download_invoice(sale.invoice_no)
    text = " ".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)

    assert sale.invoice_no in text, f"Invoice {sale.invoice_no} PDF doesn't show its own number"
    assert product in text, f"Invoice {sale.invoice_no} PDF doesn't name the phone {product}"
    assert serials[0] in text, f"Invoice {sale.invoice_no} PDF doesn't show the sold serial {serials[0]}"
    assert serials[1] not in text, f"Invoice {sale.invoice_no} PDF shows the unsold serial {serials[1]}"
