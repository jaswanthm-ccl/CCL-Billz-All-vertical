"""Fixtures for accounting/voucher tests.

Provides module-scoped dependencies:
- module_branch: dedicated branch for isolation
- module_bank_account: bank account linked to the branch
- module_customer / module_supplier: for receipt/payment vouchers
- module_product: for creating sales/purchases
- voucher_funded_state: seeds cash + bank balances via sales
- module_outstanding_sale: creates an unpaid sale for receipt allocation
- module_outstanding_purchase: creates an unpaid purchase for payment allocation
"""
import pytest
import random
from datetime import date, timedelta

from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.bank_accounts_page import BankAccountPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.brands_page import BrandPage
from pages.master_menu.unit_types_page import UnitTypesPage
from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from pages.master_menu.cities_page import CitiesPage
from pages.main_menu.products_page import ProductsPage
from pages.main_menu.customers_page import CustomersPage
from pages.main_menu.suppliers_page import SuppliersPage
from pages.main_menu.sales_page import SalesPage
from pages.main_menu.purchases_page import PurchasesPage
from pages.main_menu.chits_page import ChitsPage
from pages.accounting.create_voucher_page import CreateVoucherPage
from utils.random_data import (
    generate_random_name,
    generate_random_email,
    generate_random_phone,
    generate_random_gst,
    generate_random_postal_code,
)


@pytest.fixture(scope="module")
def module_branch(module_page):
    """Create a dedicated branch for voucher tests."""
    branches_page = BranchesPage(module_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branches_page.page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    yield branch_name
    try:
        module_page.set_default_timeout(5000)
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete branch {branch_name}: {e}")
    finally:
        module_page.set_default_timeout(30000)


@pytest.fixture(scope="module")
def module_bank_account(module_page):
    """Create a tenant bank account; branch is the bank's physical branch name."""
    bank_page = BankAccountPage(module_page)
    bank_page.navigate()
    bank_name = generate_random_name("v_bank")
    bank_page.add_bank_account(
        bank_name=bank_name,
        branch="Automation Bank Branch",
        account_number=str(random.randint(100000000000, 999999999999)),
        ifsc_code="IDFC0000899",
    )
    yield bank_name
    try:
        bank_page.navigate()
        if bank_page.search_bank_account(bank_name):
            bank_page.delete_bank_account(bank_name)
    except Exception as e:
        print(f"Teardown: Failed to delete bank {bank_name}: {e}")


@pytest.fixture(scope="module")
def transfer_destination_branch(module_page):
    """Create the receiving branch used by branch fund transfer tests."""
    branches_page = BranchesPage(module_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branches_page.page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    yield branch_name
    try:
        module_page.set_default_timeout(5000)
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete destination branch {branch_name}: {e}")
    finally:
        module_page.set_default_timeout(30000)


@pytest.fixture(scope="module")
def transfer_destination_bank(module_page):
    """Create a second bank account for transfer destination scenarios."""
    bank_page = BankAccountPage(module_page)
    bank_page.navigate()
    bank_name = generate_random_name("v_dest_bank")
    bank_page.add_bank_account(
        bank_name=bank_name,
        branch="Automation Destination Bank Branch",
        account_number=str(random.randint(100000000000, 999999999999)),
        ifsc_code="IDFC0000899",
    )
    yield bank_name
    try:
        bank_page.navigate()
        if bank_page.search_bank_account(bank_name):
            bank_page.delete_bank_account(bank_name)
    except Exception as e:
        print(f"Teardown: Failed to delete destination bank {bank_name}: {e}")


@pytest.fixture(scope="module")
def module_customer(module_page):
    """Create a customer for receipt voucher tests."""
    customers_page = CustomersPage(module_page)
    customer_name = generate_random_name("v_cust")
    customers_page.add_customer(name=customer_name)
    yield customer_name
    try:
        customers_page.navigate()
        if customers_page.search_customer(customer_name):
            customers_page.delete_customer(customer_name)
    except Exception as e:
        print(f"Teardown: Failed to delete customer {customer_name}: {e}")


@pytest.fixture(scope="module")
def module_city(module_page):
    """Create a city that is guaranteed to exist in the supplier form."""
    cities_page = CitiesPage(module_page)
    cities_page.navigate()
    city_name = generate_random_name("v_city")
    cities_page.add_city(city_name)
    yield city_name
    try:
        cities_page.navigate()
        if cities_page.search_city(city_name):
            cities_page.delete_city(city_name)
    except Exception as e:
        print(f"Teardown: Failed to delete city {city_name}: {e}")


@pytest.fixture(scope="module")
def module_supplier(module_page, module_city):
    """Create a supplier for payment voucher tests."""
    suppliers_page = SuppliersPage(module_page)
    suppliers_page.navigate()
    supplier_name = generate_random_name("v_supp")
    suppliers_page.add_supplier(
        name=supplier_name,
        contact_person="Voucher Test Contact",
        email=generate_random_email("vsupp"),
        phone=generate_random_phone(),
        gst_number=generate_random_gst(),
        state_name="Tamil Nadu",
        city_name=module_city,
        postal_code=generate_random_postal_code(),
        address="123 Test Street",
    )
    yield supplier_name
    try:
        suppliers_page.navigate()
        if suppliers_page.search_supplier(supplier_name):
            suppliers_page.delete_supplier(supplier_name)
    except Exception as e:
        print(f"Teardown: Failed to delete supplier {supplier_name}: {e}")


@pytest.fixture(scope="module")
def module_chit(module_page, module_branch):
    """Create an open chit for Chit Entry voucher tests."""
    chits_page = ChitsPage(module_page)
    chits_page.navigate()
    chit_name = generate_random_name("v_chit")
    chits_page.add_chit(
        chit_name=chit_name,
        branch=module_branch,
        chit_value="1200",
        tenure_months="12",
        monthly_amount="100",
        foreman_name="Voucher Test Foreman",
    )
    yield chit_name
    try:
        chits_page.navigate()
        chits_page.delete_chit(chit_name)
    except Exception as e:
        print(f"Teardown: Failed to delete chit {chit_name}: {e}")


@pytest.fixture(scope="module")
def module_product_deps(module_page):
    """Create product dependencies: category, brand, unit, HSN code."""
    cat_name = generate_random_name("v_cat")
    brand_name = generate_random_name("v_brand")
    unit_name = generate_random_name("v_unit")
    sac_code = str(random.randint(100000, 999999))

    categories_page = CategoriesPage(module_page)
    categories_page.navigate()
    categories_page.add_category(name=cat_name, description="voucher tests")
    categories_page.page.get_by_text("Category created successfully").wait_for(
        state="visible", timeout=5000
    )

    brand_page = BrandPage(module_page)
    brand_page.navigate()
    brand_page.add_brand(brand_name, "voucher tests")

    unit_page = UnitTypesPage(module_page)
    unit_page.navigate()
    unit_page.add_unit_type(name=unit_name, unit="pcs", description="voucher tests")

    sac_page = SacHsnCodePage(module_page)
    sac_page.navigate()
    sac_page.add_sac_hsn_code("SAC", sac_code, description="voucher tests")

    yield {
        "category": cat_name,
        "brand": brand_name,
        "unit": unit_name,
        "hsn_code": sac_code,
    }


@pytest.fixture(scope="module")
def module_product(module_page, module_product_deps):
    """Create a product for sales/purchases."""
    products_page = ProductsPage(module_page)
    products_page.navigate()
    product_name = generate_random_name("v_prod")
    products_page.add_product(
        name=product_name,
        brand_name=module_product_deps["brand"],
        category_name=module_product_deps["category"],
        hsn_code=module_product_deps["hsn_code"],
        unit_type=module_product_deps["unit"],
        cost_price="100",
        selling_price="500",
        gst_percentage="18%",
    )
    yield product_name


@pytest.fixture(scope="module")
def voucher_funded_state(module_page, module_branch, module_bank_account, module_product, module_customer):
    """Seed cash and bank balances by creating paid sales.

    Creates 2 sales:
    - One paid via bank (₹500) → funds bank account
    - One paid via cash (₹500) → funds cash ledger

    Also adds opening stock.
    """
    products_page = ProductsPage(module_page)
    products_page.navigate()
    products_page.update_opening_stock(
        name=module_product,
        branch_name=module_branch,
        quantity="10",
        cost_price="100",
    )

    sales_page = SalesPage(module_page)

    # Sale via bank
    sales_page.add_sale(
        customer_name=module_customer,
        branch_name=module_branch,
        product_name=module_product,
        price="500",
        paid_amount="500",
        payment_method=module_bank_account,
        sale_date=(date.today() - timedelta(days=1)).isoformat(),
    )

    # Sale via cash
    sales_page.add_sale(
        customer_name=module_customer,
        branch_name=module_branch,
        product_name=module_product,
        price="500",
        paid_amount="500",
        payment_method="Cash",
    )

    yield {
        "branch": module_branch,
        "bank": module_bank_account,
        "customer": module_customer,
        "product": module_product,
        "cash_balance": "500",
        "bank_balance": "500",
    }


@pytest.fixture(scope="module")
def module_outstanding_sale(module_page, module_branch, module_product, module_customer, voucher_funded_state):
    """Create an unpaid sale (₹300 outstanding) for receipt voucher allocation tests."""
    sales_page = SalesPage(module_page)
    res = sales_page.add_sale(
        customer_name=module_customer,
        branch_name=module_branch,
        product_name=module_product,
        price="300",
        paid_amount="0",
        payment_method="Cash",
    )
    yield {
        "customer": module_customer,
        "outstanding": "300",
        "branch": module_branch,
        "invoice_no": getattr(res, "invoice_no", ""),
    }


@pytest.fixture(scope="module")
def module_outstanding_purchase(module_page, module_branch, module_product, module_supplier, voucher_funded_state):
    """Create an unpaid purchase (₹200 outstanding) for payment voucher allocation tests."""
    purchases_page = PurchasesPage(module_page)
    purchases_page.navigate()
    ref_no = generate_random_name("pur_ref")
    purchases_page.add_purchase(
        supplier=module_supplier,
        branch=module_branch,
        reference_no=ref_no,
        paid_amount="0",
        purchase_type="Cash",
        products_data=[{
            "product": module_product,
            "quantity": "1",
            "price": "200",
        }],
    )
    yield {
        "supplier": module_supplier,
        "outstanding": "200",
        "branch": module_branch,
        "reference_no": ref_no,
        "invoice_no": ref_no,
    }
