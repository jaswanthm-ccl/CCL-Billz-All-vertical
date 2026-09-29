"""Restaurant Products (Dishes & Raw Materials) Test Suite."""
import pytest
from utils.random_data import generate_random_name
from utils.xlsx_factory import create_restaurant_product_import_xlsx
from pages.Verticals.Restaurant.main_menu.products_page import ProductsPage


@pytest.fixture
def product_cleanup(res_logged_in_page):
    created_prods = []
    yield created_prods

    page = res_logged_in_page
    prod_page = ProductsPage(page)
    prod_page.navigate()
    for name in list(created_prods):
        try:
            if prod_page.delete_product(name):
                created_prods.remove(name)
        except Exception as e:
            print(f"Teardown: could not delete product {name}: {e}")


@pytest.mark.restaurant
def test_restaurant_product_crud_lifecycle(res_logged_in_page, product_cleanup, res_category, res_department, res_unit_type):
    """Test full CRUD lifecycle for Finished Dish and Raw Material items."""
    page = res_logged_in_page
    prod_page = ProductsPage(page)
    prod_page.navigate()

    dish_name = generate_random_name("auto_dish")
    new_dish_name = generate_random_name("auto_dish_edit")
    product_cleanup.append(dish_name)

    # 1. Create Finished Good Dish
    item_code = prod_page.add_product(
        name=dish_name,
        category_name=res_category,
        department_name=res_department,
        unit_type=res_unit_type,
        price="180",
        product_type="Finished good",
    )
    assert item_code, "Failed to create finished good product"
    assert prod_page.search_product(dish_name), f"Dish '{dish_name}' was not found in table"

    # 2. Edit Dish Name
    assert prod_page.edit_product(dish_name, new_dish_name), f"Failed to edit dish '{dish_name}'"
    product_cleanup.remove(dish_name)
    product_cleanup.append(new_dish_name)
    assert prod_page.search_product(new_dish_name), f"Edited dish '{new_dish_name}' was not found in table"

    # 3. Soft-delete Dish
    assert prod_page.delete_product(new_dish_name), f"Failed to delete dish '{new_dish_name}'"
    product_cleanup.remove(new_dish_name)


@pytest.mark.restaurant
def test_restaurant_product_bulk_import(
    res_logged_in_page,
    product_cleanup,
    res_category,
    res_department,
    res_unit_type,
    tmp_path,
):
    """Import a finished good and raw material from one generated workbook."""
    prod_page = ProductsPage(res_logged_in_page)
    prod_page.navigate()

    dish_name = generate_random_name("bulk_dish")
    raw_name = generate_random_name("bulk_raw")
    item_code = generate_random_name("BULK").replace("_", "-").upper()
    product_cleanup.extend([dish_name, raw_name])

    workbook_path = create_restaurant_product_import_xlsx(
        tmp_path / "restaurant_products.xlsx",
        [
            {
                "Product Name": dish_name,
                "Category Name": res_category,
                "Selling Price": 180,
                "Incentive %": 5,
                "GST Percentage": 5,
                "Product Type": "goods",
                "Menu Product Type": "finished_good",
                "Item Code": item_code,
                "Department": res_department,
                "Unit Type": res_unit_type,
                "Cost Price": 100,
                "Expiry (in days)": 0,
                "Description": "Automated bulk-import finished good",
                "Low Stock": 5,
            },
            {
                "Product Name": raw_name,
                "Category Name": res_category,
                "Selling Price": 0,
                "GST Percentage": 5,
                "Product Type": "goods",
                "Menu Product Type": "raw_material",
                "Unit Type": res_unit_type,
                "Cost Price": 60,
                "Expiry (in days)": 0,
                "Description": "Automated bulk-import raw material",
                "Low Stock": 5,
            },
        ],
    )

    prod_page.import_products(workbook_path)
    assert prod_page.search_product(dish_name), "Imported finished good is missing"
    assert prod_page.search_product(raw_name), "Imported raw material is missing"
