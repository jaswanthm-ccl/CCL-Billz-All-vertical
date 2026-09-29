import os
import utils.constants  # Ensures .env is loaded into os.environ

# Credentials & base URL
RESTAURANT_BASE_URL: str = os.getenv("RESTAURANT_BASE_URL", "https://auto-res.devccl-billzweb.crystalbillz.com")
RESTAURANT_USER_1_EMAIL: str = os.getenv("RESTAURANT_USER_1_EMAIL")
RESTAURANT_USER_1_PASSWORD: str = os.getenv("RESTAURANT_USER_1_PASSWORD")

# Restaurant-specific URLs
RES_DASHBOARD_URL: str = f"{RESTAURANT_BASE_URL}/dashboard"
RES_DEPARTMENTS_URL: str = f"{RESTAURANT_BASE_URL}/departments"
RES_TABLES_URL: str = f"{RESTAURANT_BASE_URL}/tables"
RES_RECIPES_URL: str = f"{RESTAURANT_BASE_URL}/recipes"
RES_INDENTS_URL: str = f"{RESTAURANT_BASE_URL}/indents"
RES_GRN_URL: str = f"{RESTAURANT_BASE_URL}/grn"
RES_OUTDOOR_BILLING_URL: str = f"{RESTAURANT_BASE_URL}/outdoor-billing"
RES_PRODUCTS_URL: str = f"{RESTAURANT_BASE_URL}/products"
RES_BILLING_URL: str = f"{RESTAURANT_BASE_URL}/sales/add"

# Shared URLs (same routes, different base)
RES_INVENTORIES_URL: str = f"{RESTAURANT_BASE_URL}/inventories"
RES_CUSTOMERS_URL: str = f"{RESTAURANT_BASE_URL}/customers"
RES_SUPPLIERS_URL: str = f"{RESTAURANT_BASE_URL}/suppliers"
RES_PURCHASES_URL: str = f"{RESTAURANT_BASE_URL}/purchases"
RES_PURCHASE_REQUESTS_URL: str = f"{RESTAURANT_BASE_URL}/purchase-requests"
RES_EXPENSES_URL: str = f"{RESTAURANT_BASE_URL}/expenses"
RES_SALES_URL: str = f"{RESTAURANT_BASE_URL}/sales"
RES_DAILY_CLOSING_URL: str = f"{RESTAURANT_BASE_URL}/reports/daily-closing"
RES_DAY_BOOK_URL: str = f"{RESTAURANT_BASE_URL}/day-book"
RES_PAYMENT_VOUCHER_URL: str = f"{RESTAURANT_BASE_URL}/vouchers/payment/create"
RES_PROFIT_LOSS_URL: str = f"{RESTAURANT_BASE_URL}/reports/profit-loss"
RES_OUTSTANDING_BILLS_URL: str = f"{RESTAURANT_BASE_URL}/vouchers/outstanding"
RES_CUSTOMER_OUTSTANDING_URL: str = f"{RESTAURANT_BASE_URL}/reports/customer-outstanding"
RES_SUPPLIER_OUTSTANDING_URL: str = f"{RESTAURANT_BASE_URL}/reports/supplier-outstanding"
RES_MDR_SETTLEMENT_URL: str = f"{RESTAURANT_BASE_URL}/vouchers/mdr/create"
RES_MDR_REPORT_URL: str = f"{RESTAURANT_BASE_URL}/reports/mdr-report"
RES_GSTR1_B2B_URL: str = f"{RESTAURANT_BASE_URL}/reports/gstr1-b2b"
RES_GSTR1_B2C_URL: str = f"{RESTAURANT_BASE_URL}/reports/gstr1-b2c"
RES_STOCK_SUMMARY_URL: str = f"{RESTAURANT_BASE_URL}/reports/stock-summary"

RESTAURANT_TEST_TABLE: str = os.getenv("RESTAURANT_TEST_TABLE", "QA AUTO TABLE")

# ... add more as needed

# Reuse timeouts from default constants
from utils.constants import SEARCH_DEBOUNCE_MS, LIST_TIMEOUT, UI_TIMEOUT, SETTLED_TIMEOUT
