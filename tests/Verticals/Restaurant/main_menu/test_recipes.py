"""Restaurant Recipes Test Suite."""
import pytest
from utils.random_data import generate_random_name
from pages.Verticals.Restaurant.main_menu.recipes_page import RecipesPage
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage


@pytest.fixture
def recipe_cleanup(res_logged_in_page):
    created_recipes = []
    created_products = []
    yield {"recipes": created_recipes, "products": created_products}

    page = res_logged_in_page
    rec_page = RecipesPage(page)
    rec_page.navigate()
    for name in list(created_recipes):
        try:
            if rec_page.delete_recipe(name):
                created_recipes.remove(name)
        except Exception as e:
            print(f"Teardown: could not delete recipe {name}: {e}")

    prod_page = ProductsPage(page)
    prod_page.navigate()
    for name in list(created_products):
        try:
            if prod_page.delete_product(name):
                created_products.remove(name)
        except Exception as e:
            print(f"Teardown: could not delete product {name}: {e}")


@pytest.mark.restaurant
def test_restaurant_recipe_crud_lifecycle(res_logged_in_page, recipe_cleanup, res_category, res_department, res_unit_type):
    """Test creating, viewing, editing, and deleting a recipe linking a finished dish to raw ingredients."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    rec_page = RecipesPage(page)

    prod_page.navigate()
    dish_name = generate_random_name("auto_dish_rec")
    raw_name = generate_random_name("auto_raw_rec")
    recipe_cleanup["products"].extend([dish_name, raw_name])

    # Create Finished Good Dish
    prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="220",
        product_type="Finished good",
    )

    # Create Raw Material Ingredient
    prod_page.add_product(
        name=raw_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        product_type="Raw material",
    )

    # Recipe Workflow
    rec_page.navigate()
    recipe_cleanup["recipes"].append(dish_name)

    assert rec_page.add_recipe(dish_name=dish_name, ingredient_name=raw_name, servings="2", quantity="1"), "Failed to add recipe"
    assert rec_page.search_recipe(dish_name), f"Recipe for '{dish_name}' was not found in table"

    assert rec_page.view_recipe(dish_name), f"Failed to view recipe for '{dish_name}'"
    assert rec_page.edit_recipe(dish_name, new_quantity="3"), f"Failed to edit recipe for '{dish_name}'"
    assert rec_page.delete_recipe(dish_name), f"Failed to delete recipe for '{dish_name}'"
    recipe_cleanup["recipes"].remove(dish_name)
