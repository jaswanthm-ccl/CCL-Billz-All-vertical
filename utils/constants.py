from __future__ import annotations

import os

env_path: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

BASE_URL: str = os.getenv("BASE_URL", "https://dev-demo-ccl.devccl-billzweb.crystalbillz.com")
ADMIN_EMAIL: str | None = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD: str | None = os.getenv("ADMIN_PASSWORD")

DASHBOARD_URL: str = f"{BASE_URL}/dashboard"
CITY_URL: str = f"{BASE_URL}/cities"
BRANCHES_URL: str = f"{BASE_URL}/branches"
ROLES_URL: str = f"{BASE_URL}/roles"
USERS_URL: str = f"{BASE_URL}/users"
CUSTOMERS_URL: str = f"{BASE_URL}/customers"

CATEGORIES_URL: str = f"{BASE_URL}/categories"
BRANDS_URL: str = f"{BASE_URL}/brands"
UNIT_TYPES_URL: str = f"{BASE_URL}/unit-types"
ATTRIBUTE_KEYS_URL: str = f"{BASE_URL}/attribute-keys"
ATTRIBUTE_VALUES_URL: str = f"{BASE_URL}/attribute-values"
PRODUCT_ATTRIBUTES_URL: str = f"{BASE_URL}/product-unit-attributes"
BANK_ACCOUNTS_URL: str = f"{BASE_URL}/bank-accounts"
ENQUIRY_STAGE_WORKFLOWS_URL: str = f"{BASE_URL}/enquiry-stage-workflows"
ACCOUNT_GROUPS_URL: str = f"{BASE_URL}/account-groups"
EMI_PROVIDERS_URL: str = f"{BASE_URL}/emi-providers"
EXPENSE_CATEGORIES_URL: str = f"{BASE_URL}/expense-categories"
ENQUIRY_TYPES_URL: str = f"{BASE_URL}/enquiry-types"
SAC_HSN_URL: str = f"{BASE_URL}/gst-codes"
RACKS_URL: str = f"{BASE_URL}/racks"
PRODUCTS_URL: str = f"{BASE_URL}/products"
SUPPLIERS_URL: str = f"{BASE_URL}/suppliers"
PURCHASE_REQUESTS_URL: str = f"{BASE_URL}/purchase-requests"
PURCHASES_URL: str = f"{BASE_URL}/purchases"
PURCHASE_RETURNS_URL: str = f"{BASE_URL}/purchase-returns"
SALES_URL: str = f"{BASE_URL}/sales"
SALES_QUOTES_URL: str = f"{BASE_URL}/sales-quotes"
SALE_RETURNS_URL: str = f"{BASE_URL}/sale-returns"
BATCHES_URL: str = f"{BASE_URL}/batches"
INVENTORIES_URL: str = f"{BASE_URL}/inventories"
STOCK_TRANSFERS_URL: str = f"{BASE_URL}/stock-transfers"
DAY_BOOKS_URL: str = f"{BASE_URL}/day-book"
BRANCH_FUND_TRANSFERS_URL: str = f"{BASE_URL}/branch-fund-transfers"
ACCOUNTING_DAY_BOOK_URL: str = f"{BASE_URL}/accounting/day-book"
PROFIT_LOSS_URL: str = f"{BASE_URL}/reports/profit-loss"
TRIAL_BALANCE_URL: str = f"{BASE_URL}/reports/trial-balance"
BALANCE_SHEET_URL: str = f"{BASE_URL}/reports/balance-sheet"
CASH_FLOW_URL: str = f"{BASE_URL}/reports/cash-flow"
OUTSTANDING_BILLS_URL: str = f"{BASE_URL}/vouchers/outstanding"
CUSTOMER_OUTSTANDING_URL: str = f"{BASE_URL}/reports/customer-outstanding"
SUPPLIER_OUTSTANDING_URL: str = f"{BASE_URL}/reports/supplier-outstanding"
MDR_REPORT_URL: str = f"{BASE_URL}/reports/mdr-report"
EMI_RECONCILIATION_URL: str = f"{BASE_URL}/reports/emi-provider-reconciliation"
STOCK_SUMMARY_URL: str = f"{BASE_URL}/reports/stock-summary"
GSTR1_B2B_URL: str = f"{BASE_URL}/reports/gstr1-b2b"
GSTR1_B2C_URL: str = f"{BASE_URL}/reports/gstr1-b2c"


# ── Standard Timeouts (in milliseconds) ──────────────────────────────────────
SEARCH_DEBOUNCE_MS: int = 1000
LIST_TIMEOUT: int = 20000                           # 20,000ms for debounced list / creation API
UI_TIMEOUT: int = 5000                              # 5,000ms for standard UI elements
SETTLED_TIMEOUT: int = 2500                         # 2,500ms for quick row presence checks

