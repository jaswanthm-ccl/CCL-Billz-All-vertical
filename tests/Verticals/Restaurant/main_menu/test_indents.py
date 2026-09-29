"""Restaurant Indents Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.indents_page import IndentsPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage
from pages.Verticals.Restaurant.main_menu.purchases_page import PurchasesPage
from pages.Verticals.Restaurant.main_menu.recipes_page import RecipesPage


@pytest.fixture
def indent_cleanup(res_logged_in_page):
    created_indents = []
    created_prods = []
    created_recipes = []
    yield {
        "indents": created_indents,
        "prods": created_prods,
        "recipes": created_recipes,
    }

    page = res_logged_in_page
    ind_page = IndentsPage(page)
    ind_page.navigate()
    for indent_id in list(created_indents):
        try:
            if ind_page.delete_indent(indent_id):
                created_indents.remove(indent_id)
        except Exception as e:
            print(f"Teardown: could not delete indent {indent_id}: {e}")

    rec_page = RecipesPage(page)
    rec_page.navigate()
    for rec_name in list(created_recipes):
        try:
            if rec_page.delete_recipe(rec_name):
                created_recipes.remove(rec_name)
        except Exception:
            pass

    prod_page = ProductsPage(page)
    prod_page.navigate()
    for prod_name in list(created_prods):
        try:
            if prod_page.delete_product(prod_name):
                created_prods.remove(prod_name)
        except Exception:
            pass


@pytest.mark.restaurant
def test_restaurant_indent_manual_draft_crud_lifecycle(
    res_logged_in_page, indent_cleanup, res_branch, res_department, res_category, res_unit_type
):
    """Test creating a manual draft indent, editing, viewing, and soft-deleting it."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    ind_page = IndentsPage(page)

    prod_page.navigate()
    raw_name = generate_random_name("auto_raw_ind")
    indent_cleanup["prods"].append(raw_name)
    prod_page.add_product(
        name=raw_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        product_type="Raw material",
    )

    ind_page.navigate()
    indent_id = ind_page.create_indent(
        branch_name=res_branch,
        department_name=res_department,
        mode="Manual",
        items=[{"name": raw_name, "quantity": "5"}],
        approve_immediately=False,
    )
    assert indent_id, "Failed to create draft indent"
    indent_cleanup["indents"].append(indent_id)

    assert ind_page.search_indent(indent_id), f"Indent {indent_id} not found in search"
    view_data = ind_page.view_indent(indent_id)
    assert indent_id in view_data["content"], f"Indent ID {indent_id} missing from view dialog"

    assert ind_page.edit_indent(indent_id, new_quantity="8"), f"Failed to edit indent {indent_id}"
    assert ind_page.delete_indent(indent_id), f"Failed to delete indent {indent_id}"
    indent_cleanup["indents"].remove(indent_id)


@pytest.mark.restaurant
def test_restaurant_indent_template_and_auto_computation_lifecycle(
    res_logged_in_page, indent_cleanup, res_branch, res_department, res_category, res_unit_type
):
    """Test 'Save as Template' checkbox and template-based indent workflow."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    rec_page = RecipesPage(page)
    ind_page = IndentsPage(page)

    dish_name = generate_random_name("auto_dish_tmp")
    raw_name = generate_random_name("auto_raw_tmp")
    template_title = generate_random_name("auto_tmpl")
    indent_cleanup["prods"].extend([dish_name, raw_name])
    indent_cleanup["recipes"].append(dish_name)

    prod_page.navigate()
    prod_page.add_product(name=dish_name, category_name=res_category, department_name=res_department, unit_type=res_unit_type, price="150", product_type="Finished good")
    prod_page.add_product(name=raw_name, category_name=res_category, department_name=res_department, unit_type=res_unit_type, product_type="Raw material")

    rec_page.navigate()
    rec_page.add_recipe(dish_name=dish_name, ingredient_name=raw_name, servings="1", quantity="2")

    ind_page.navigate()
    indent_1_id = ind_page.create_indent(
        branch_name=res_branch,
        department_name=res_department,
        mode="Manual",
        items=[{"name": raw_name, "quantity": "10"}],
        save_as_template=True,
        new_template_title=template_title,
        approve_immediately=False,
    )
    assert indent_1_id, "Failed to create first indent with template"
    indent_cleanup["indents"].append(indent_1_id)

    assert ind_page.search_indent(indent_1_id)
    assert ind_page.delete_indent(indent_1_id)
    indent_cleanup["indents"].remove(indent_1_id)


@pytest.mark.restaurant
def test_restaurant_indent_approval_and_reversal_lifecycle(
    res_logged_in_page,
    indent_cleanup,
    res_branch,
    res_department,
    res_category,
    res_unit_type,
    res_supplier,
):
    """Test Create & Approve workflow and Reversal of an approved indent."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    purchases_page = PurchasesPage(page)
    ind_page = IndentsPage(page)

    raw_name = generate_random_name("auto_raw_appr")
    indent_cleanup["prods"].append(raw_name)

    # 1. Create Raw Material Product
    prod_page.navigate()
    prod_page.add_product(name=raw_name, category_name=res_category, department_name=res_department, unit_type=res_unit_type, product_type="Raw material")

    # 2. Create a real FIFO batch through Purchase; indent approval consumes batches.
    purchase_reference = generate_random_name("IND_STOCK")
    purchases_page.add_purchase(
        supplier=res_supplier,
        branch=res_branch,
        reference_no=purchase_reference,
        paid_amount="0",
        purchase_type="Credit",
        products_data=[{"product": raw_name, "quantity": 20, "price": "10"}],
    )

    # 3. Create & Approve Indent
    ind_page.navigate()
    indent_id = ind_page.create_indent(
        branch_name=res_branch,
        department_name=res_department,
        mode="Manual",
        items=[{"name": raw_name, "quantity": "5"}],
        approve_immediately=True,
    )
    assert indent_id, "Failed to create & approve indent"

    assert ind_page.search_indent(indent_id)
    status = ind_page.get_indent_status(indent_id)
    assert "approved" in status.lower(), f"Expected approved status, got '{status}'"

    # 4. Reverse Indent
    assert ind_page.reverse_indent(indent_id), f"Failed to reverse indent {indent_id}"
    status_rev = ind_page.get_indent_status(indent_id)
    assert "reversed" in status_rev.lower(), f"Expected reversed status, got '{status_rev}'"
