import pytest
import random
from pages.main_menu.batches_page import BatchesPage
from pages.main_menu.purchases_page import PurchasesPage


def test_batches_integration_flow(
    logged_in_page, module_branch, module_supplier, module_product
):
    purchases_page = PurchasesPage(logged_in_page)
    batches_page = BatchesPage(logged_in_page)

    # 1. Create a credit Purchase of the product with quantity 10 (triggers automatic batch creation)
    purchases_page.navigate()
    ref_no = "ref_" + str(random.randint(100000, 999999))
    purchases_page.add_purchase(
        supplier=module_supplier,
        branch=module_branch,
        reference_no=ref_no,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[
            {"product": module_product, "quantity": 10, "price": "200"}
        ]
    )
    assert purchases_page.search_purchase(ref_no)

    # 2. Go to /batches and verify page loaded
    batches_page.navigate()
    assert batches_page.is_batches_visible()

    # 3. Search for product name and verify batch row details
    assert batches_page.verify_batch_row_details(
        product_name=module_product,
        expected_quantity_str="10 / 10"
    )

    # 4. Open traceability drawer and close it
    assert batches_page.open_batch_trace(product_name=module_product)
