# Crystal Billz Test Automation Framework

A professional, enterprise-grade test automation suite built with **Playwright (Python)** and **pytest** for verifying the functionality of the **Crystal Billz** application. This framework is designed to be highly reliable, maintainable, and readable for development and QA teams.

---

## 🏗️ Architectural Design & Design Rationale

The framework utilizes the **Page Object Model (POM)** pattern. This architectural choice is driven by the following principles:

### 1. Separation of Concerns (POM vs. Tests)

- **Pages (`pages/`)**: Handle **how** to interact with the UI. They contain element selectors and wrapper functions for UI workflows (e.g., clicking dropdowns, filling inputs). They do not perform assertions.
- **Tests (`tests/`)**: Handle **what** to assert. They use page object methods to perform actions and assert results (e.g., verifying a toast message appears).
- _Rationale_: If a UI selector changes (e.g., an input ID changes), only the page object needs an update. The tests themselves remain unchanged.

### 2. Module-Based Test Classification

- Test directories match the main sections of the Billz application (`master_menu`, `main_menu`, `accounting`).
- _Rationale_: Grouping tests by menu module allows targeting specific sections of the app (e.g., running Setup configuration tests independently from daily Transaction flows).

### 3. Stateless Test Execution & Custom Rollbacks

- Staging and development database environments are shared. Hardcoding data or leaving test records in the database leads to duplicate name errors and database clutter.
- _Rationale_: Every test module uses custom teardown fixtures that dynamically identify and delete created records (active or soft-deleted) at the end of the execution, leaving the database exactly as it was.

---

## 📁 File Structure & Component Overview

Below is the detailed file structure mapping out the repository and the purpose of each component:

````
playwright-python-tests/
│
├── pages/                                # PAGE OBJECTS LAYER ("how" to interact with the UI)
│   ├── auth/                             # Authentication page wrappers
│   │   └── login_page.py                 # Handles login fields, error messages, and password toggle
│   │
│   ├── common/                           # Shared Page Components
│   │   ├── base_page.py                  # Base class with shared page actions
│   │   ├── form_page.py                  # Reusable form-field interactions
│   │   ├── table_page.py                 # Reusable table/list helpers
│   │   ├── sidebar_page.py               # App sidebar / navigation helpers
│   │   └── toast_page.py                 # Toast / notification assertions
│   │
│   ├── master_menu/                      # Master Settings pages (Setup configurations)
│   │   ├── branches_page.py              # Selects and inputs branch details
│   │   ├── roles_page.py                 # Configures user roles and system privileges
│   │   ├── users_page.py                 # Selects branches/roles via custom react-select controls
│   │   ├── bank_accounts_page.py         # Configures company bank account details
│   │   ├── account_groups_page.py        # Manages accounting groups with Tree/Table view toggle
│   │   ├── voucher_types_page.py         # Updates seeded voucher definitions (automatic/manual)
│   │   ├── brands_page.py                # Brand creation, search, and deletion
│   │   ├── categories_page.py            # Product category management
│   │   ├── unit_types_page.py            # Unit type management
│   │   ├── racks_page.py                 # Rack / storage location management
│   │   ├── cities_page.py                # City master management
│   │   ├── expense_categories_page.py    # Expense category management
│   │   ├── product_attributes_page.py    # Product attribute definitions
│   │   ├── attribute_keys_page.py        # Attribute key management
│   │   ├── attribute_values_page.py      # Attribute value management
│   │   ├── sac_hsn_code_page.py          # SAC/HSN code management (list, search, add, edit, delete, restore)
│   │   ├── enquiry_types_page.py         # Enquiry type management
│   │   └── enquiry_stage_workflows_page.py # Workflow & Stage management
│   │
│   ├── main_menu/                        # Transactions, inventory, and inventory batch pages
│   │   ├── products_page.py              # Product creation, view, edit, delete, stock
│   │   ├── batches_page.py               # Inventory batch management
│   │   ├── inventories_page.py            # Inventory listing and adjustments
│   │   ├── customers_page.py             # Customer master
│   │   ├── suppliers_page.py             # Supplier master
│   │   ├── sales_page.py                 # Sales transactions
│   │   ├── sales_quotes_page.py          # Sales quotation workflows
│   │   ├── sale_returns_page.py          # Sales return workflows
│   │   ├── purchases_page.py             # Purchase transactions
│   │   ├── purchase_returns_page.py      # Purchase return workflows
│   │   ├── purchase_request_page.py      # Purchase request workflows
│   │   ├── payments_page.py              # Payment entries
│   │   ├── expenses_page.py              # Expense entries
│   │   ├── ledgers_page.py               # Ledger entries
│   │   ├── chits_page.py                 # Chit management
│   │   └── enquiry_page.py               # Enquiry management
│   │
│   ├── accounting/                       # Accounting / ledger pages
│   │   ├── create_voucher_page.py        # Voucher creation
│   │   ├── day_book_page.py              # Day book view
│   │   ├── ledger_statement_page.py      # Ledger statement view
│   │   ├── trial_balance_page.py         # Trial balance view
│   │   ├── profit_loss_page.py           # Profit & Loss statement
│   │   ├── balance_sheet_page.py         # Balance sheet view
│   │   ├── cash_flow_page.py             # Cash flow statement
│   │   └── voucher_history_page.py       # Voucher history view
│   │
│   ├── reports/                          # Reporting pages
│   │   ├── stock_summary_page.py         # Stock summary report
│   │   └── mdr_report_page.py            # MDR report
│   │
│   └── dashboard_page.py                 # App dashboard / home page
│
├── tests/                                # TESTS LAYER ("what" to assert, controls workflows)
│   ├── test_auth.py                       # Authentication flow tests
│   ├── test_dashboard.py                  # Dashboard tests
│   │
│   ├── master_menu/                      # Master Menu automated validation test suites
│   │   ├── test_branches.py              # Verifies branch visibility, creation, edit, and cleanup
│   │   ├── test_account_groups.py        # Validates group additions, tree lists, and deletions
│   │   ├── test_voucher_types.py         # Tests seeded voucher edits and verifies rollback
│   │   ├── test_roles.py                 # Role management tests
│   │   ├── test_users.py                 # User management tests
│   │   ├── test_bank_accounts.py         # Bank account tests
│   │   ├── test_brands.py                # Brand tests
│   │   ├── test_categories.py            # Category tests
│   │   ├── test_unit_types.py            # Unit type tests
│   │   ├── test_racks.py                 # Rack tests
│   │   ├── test_cities.py                # City tests
│   │   ├── test_expense_categories.py    # Expense category tests
│   │   ├── test_product_attributes.py    # Product attribute tests
│   │   ├── test_attribute_keys.py        # Attribute key tests
│   │   ├── test_attribute_values.py      # Attribute value tests
│   │   ├── test_sac_hsn.py               # SAC/HSN code tests
│   │   ├── test_enquiry_types.py         # Enquiry type tests
│   │   └── test_enquiry_stage_workflows.py # Workflow & stage tests
│   │
│   ├── main_menu/                        # Transactions, inventory, and inventory batch tests
│   │   ├── test_products.py              # Product lifecycle tests
│   │   ├── test_batches.py               # Batch tests
│   │   ├── test_inventories.py           # Inventory tests
│   │   ├── test_customers.py             # Customer tests
│   │   ├── test_suppliers.py             # Supplier tests
│   │   ├── test_sales.py                 # Sales tests
│   │   ├── test_sales_quotes.py          # Sales quote tests
│   │   ├── test_sale_returns.py          # Sale return tests
│   │   ├── test_purchases.py             # Purchase tests
│   │   ├── test_purchase_returns.py      # Purchase return tests
│   │   ├── test_purchase_request.py      # Purchase request tests
│   │   ├── test_payments.py              # Payment tests
│   │   ├── test_expenses.py             # Expense tests
│   │   ├── test_ledgers.py              # Ledger tests
│   │   ├── test_chits.py                # Chit tests
│   │   └── test_enquiry.py              # Enquiry tests
│   │
│   ├── accounting/                       # Ledger, Profit & Loss, and Balance Sheet tests
│   │   ├── test_create_voucher.py        # Voucher creation tests
│   │   ├── test_day_book.py              # Day book tests
│   │   ├── test_ledger_statement.py      # Ledger statement tests
│   │   ├── test_trial_balance.py         # Trial balance tests
│   │   ├── test_profit_loss.py           # Profit & Loss tests
│   │   ├── test_balance_sheet.py         # Balance sheet tests
│   │   ├── test_cash_flow.py             # Cash flow tests
│   │   └── test_voucher_history.py       # Voucher history tests
│   │
│   └── reports/                          # Reporting tests
│       ├── test_stock_summary.py         # Stock summary report tests
│       └── test_mdr_report.py            # MDR report tests
│
├── utils/                                # SHARED UTILITIES LAYER
│   ├── constants.py                      # Stores system URL constants and handles .env loader
│   ├── helpers.py                        # Common action helpers (e.g., navigation delays)
│   ├── random_data.py                    # Generates unique, non-colliding emails, passwords, and names
│   └── api_helper.py                     # Shared API/HTTP helpers



---

## 📜 Coding Conventions & Naming Standards

To maintain a clean and standardized codebase, developers must adhere to the following rules:
- **PEP 8 Compliance**: Follow standard Python conventions (snake_case for variables/functions, PascalCase for classes).
- **Comment Style**: **Do NOT use `//` comments anywhere** in Python files. Use standard Python `#` comments or multi-line docstrings (`"""`).
- **Data Isolation**: Never use static names for creating test records. Always use `generate_random_name("auto_*")` or similar from the `random_data` utility.
- **Credential Protection**: Hardcoded credentials must not be committed to Git. All secrets must reside in the local, untracked `.env` file.

---

## ⚙️ Setup & Execution

### 1. Installation
Install python dependencies and download Playwright browser binaries:
```bash
pip install -r requirements.txt
playwright install
````

### 2. Configure Local Credentials

Create a `.env` file in the project root:

```env
ADMIN_EMAIL=your_email@domain.com
ADMIN_PASSWORD=your_secure_password
```

### 3. Running Tests

Run the entire Master Menu suite:

```bash
python -m pytest tests/master_menu/
```

Run a specific test in headed mode with visual slowdown:

```bash
python -m pytest tests/master_menu/test_account_groups.py --headed --slowmo 400
```

### 4. Interactive Debugging & Visual Helpers

This framework includes custom helpers to make debugging in headed mode significantly easier:

- **Draggable Playback Control Panel (`--playback` flag or `PLAYBACK_UI=1` env var)**: When running tests with the `--playback` CLI flag (or `$env:PLAYBACK_UI="1"`), a dark, compact control widget is injected into the browser page. 
  - **Draggable & Persistent Position**: You can drag this panel anywhere on the screen by clicking and holding its header bar. Its coordinates are automatically persisted in `sessionStorage` so that the panel stays exactly where you placed it across all page navigations and route changes.
  - **Comprehensive Features**: Contains a label displaying the current test name/active fixture, status (`RUNNING`/`PAUSED`/`STEP`), speed indicator, playback control buttons (Pause, Resume, Step, Next action, Slow, Fast, Run, Prev, Next), and a collapsible action **History** log.
- **Standalone Test Name Banner**: When running headed tests *without* the full Playback UI, a simple click-through yellow banner displaying the test title is shown at the top of the browser page.
- **Interactive Debug Pauses (`debug_pause` fixture)**: Any test can request the `debug_pause` fixture to pause execution.
  - In `--headed` mode, it prints a message and prompts you in the terminal (`Press Enter in terminal to continue...`) to resume. It also updates the title inside the draggable panel/banner to orange with your custom message to indicate the pause.
  - In headless mode, it falls back to a short 2-second sleep to avoid blocking CI test runners.

Example usage inside a test:
```python
def test_some_workflow(logged_in_page, debug_pause):
    # Perform some steps...
    debug_pause(page=logged_in_page, message="Verify page before clicking Delete")
    
    # Rest of the test...
```


