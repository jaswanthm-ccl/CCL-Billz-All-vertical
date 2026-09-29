"""Fixtures and isolation setup for Restaurant Vertical Regression Flows."""

import pytest
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.suppliers_page import SuppliersPage
from pages.Verticals.Restaurant.main_menu.customers_page import CustomersPage
from pages.Verticals.Restaurant.main_menu.indents_page import IndentsPage
from pages.Verticals.Restaurant.main_menu.recipes_page import RecipesPage
from pages.Verticals.Restaurant.master_menu.users_page import UsersPage
from pages.Verticals.Restaurant.master_menu.roles_page import RolesPage


@pytest.fixture
def res_regression_cleanup(res_logged_in_page):
    """Tracks dynamic entities created during regression flows and soft-deletes them."""
    created_indents: list[str] = []
    created_products: list[str] = []
    created_suppliers: list[str] = []
    created_customers: list[str] = []
    created_recipes: list[str] = []
    created_users: list[str] = []
    created_roles: list[str] = []

    yield {
        "indents": created_indents,
        "products": created_products,
        "suppliers": created_suppliers,
        "customers": created_customers,
        "recipes": created_recipes,
        "users": created_users,
        "roles": created_roles,
    }

    page = res_logged_in_page

    # 1. Clean up Indents
    if created_indents:
        ind_page = IndentsPage(page)
        ind_page.navigate()
        for indent_id in list(created_indents):
            try:
                if ind_page.delete_indent(indent_id):
                    created_indents.remove(indent_id)
            except Exception as e:
                print(f"Teardown warning (indent {indent_id}): {e}")

    # 2. Clean up Recipes
    if created_recipes:
        rec_page = RecipesPage(page)
        rec_page.navigate()
        for rec_name in list(created_recipes):
            try:
                if rec_page.delete_recipe(rec_name):
                    created_recipes.remove(rec_name)
            except Exception as e:
                print(f"Teardown warning (recipe {rec_name}): {e}")

    # 3. Clean up Products
    if created_products:
        prod_page = ProductsPage(page)
        prod_page.navigate()
        for prod_name in list(created_products):
            try:
                if prod_page.delete_product(prod_name):
                    created_products.remove(prod_name)
            except Exception as e:
                print(f"Teardown warning (product {prod_name}): {e}")

    # 4. Clean up Suppliers
    if created_suppliers:
        sup_page = SuppliersPage(page)
        sup_page.navigate()
        for sup_name in list(created_suppliers):
            try:
                if sup_page.delete_supplier(sup_name):
                    created_suppliers.remove(sup_name)
            except Exception as e:
                print(f"Teardown warning (supplier {sup_name}): {e}")

    # 5. Clean up Customers
    if created_customers:
        cust_page = CustomersPage(page)
        cust_page.navigate()
        for cust_name in list(created_customers):
            try:
                if cust_page.delete_customer(cust_name):
                    created_customers.remove(cust_name)
            except Exception as e:
                print(f"Teardown warning (customer {cust_name}): {e}")

    # 6. Clean up Users
    if created_users:
        try:
            users_page = UsersPage(page)
            users_page.navigate()
            for user_name in list(created_users):
                try:
                    if users_page.delete_user(user_name):
                        created_users.remove(user_name)
                except Exception as e:
                    print(f"Teardown warning (user {user_name}): {e}")
        except Exception as exc:
            print(f"Teardown warning (users navigation): {exc}")

    # 7. Clean up Roles
    if created_roles:
        try:
            roles_page = RolesPage(page)
            roles_page.navigate()
            for role_name in list(created_roles):
                try:
                    if roles_page.delete_role(role_name):
                        created_roles.remove(role_name)
                except Exception as e:
                    print(f"Teardown warning (role {role_name}): {e}")
        except Exception as exc:
            print(f"Teardown warning (roles navigation): {exc}")
