import pytest

from pages.master_menu.enquiry_types_page import EnquiryTypesPage
from utils.random_data import generate_random_description, generate_random_name


@pytest.fixture
def enquiry_type_cleanup(logged_in_page):
    created_types: list[str] = []
    yield created_types
    page_obj = EnquiryTypesPage(logged_in_page)
    for name in reversed(created_types):
        try:
            page_obj.navigate()
            if page_obj.is_enquiry_type_active(name):
                page_obj.delete_enquiry_type(name)
        except Exception as exc:
            print(f"Teardown: Failed to delete enquiry type {name}: {exc}")


def test_enquiry_type_crud_lifecycle(logged_in_page, enquiry_type_cleanup):
    page_obj = EnquiryTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.is_enquiry_types_visible()

    name = generate_random_name("auto_enq")
    notes = generate_random_description("enquiry_notes")
    response = page_obj.add_enquiry_type(name, notes=notes, sort_order=5)
    assert response.status in {200, 201}
    enquiry_type_cleanup.append(name)
    assert page_obj.search_enquiry_type(name)
    assert page_obj.view_enquiry_type(name, notes, 5)

    new_name = generate_random_name("updated_enq")
    new_notes = generate_random_description("updated_notes")
    assert page_obj.edit_enquiry_type(
        old_name=name,
        new_name=new_name,
        notes=new_notes,
        sort_order=9,
    )
    enquiry_type_cleanup.remove(name)
    enquiry_type_cleanup.append(new_name)
    assert page_obj.get_edit_values(new_name) == {
        "name": new_name,
        "notes": new_notes,
        "sort_order": "9",
    }
    assert page_obj.view_enquiry_type(new_name, new_notes, 9)
    assert page_obj.delete_enquiry_type(new_name)
    assert page_obj.retrieve_enquiry_type(new_name)
    assert page_obj.search_enquiry_type(new_name)


def test_enquiry_type_required_name(logged_in_page):
    page_obj = EnquiryTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_required_name()


def test_enquiry_type_sort_order_minimum(logged_in_page):
    page_obj = EnquiryTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_sort_order_minimum()


def test_enquiry_type_notes_max_length(logged_in_page):
    page_obj = EnquiryTypesPage(logged_in_page)
    page_obj.navigate()
    assert page_obj.validate_notes_max_length()


def test_duplicate_enquiry_type_name(logged_in_page, enquiry_type_cleanup):
    page_obj = EnquiryTypesPage(logged_in_page)
    page_obj.navigate()
    name = generate_random_name("duplicate_enq")
    response = page_obj.add_enquiry_type(name)
    assert response.status in {200, 201}
    enquiry_type_cleanup.append(name)
    assert page_obj.validate_duplicate_name(name)
