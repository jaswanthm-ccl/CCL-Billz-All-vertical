import pytest
from pages.main_menu.enquiry_page import EnquiryPage
from pages.master_menu.branches_page import BranchesPage
from utils.random_data import generate_random_name, generate_random_phone


@pytest.fixture(scope="module")
def module_enquiry_type(module_page):
    """Create an enquiry type and a workflow with a default stage.

    Full setup chain:
    1. Create an enquiry type
    2. Create a stage workflow scoped to that type
    3. Navigate to workflow detail and add a default stage
    """
    from pages.master_menu.enquiry_types_page import EnquiryTypesPage
    from pages.master_menu.enquiry_stage_workflows_page import EnquiryStageWorkflowsPage

    # 1. Create enquiry type
    types_page = EnquiryTypesPage(module_page)
    types_page.navigate()
    type_name = generate_random_name("enq_type")
    types_page.add_enquiry_type(type_name, notes="auto test")
    module_page.wait_for_timeout(1000)

    # 2. Create stage workflow (scope: Enquiry Type Override)
    wf_page = EnquiryStageWorkflowsPage(module_page)
    wf_page.navigate()
    module_page.wait_for_load_state("networkidle")
    module_page.wait_for_timeout(1000)

    wf_name = generate_random_name("enq_wf")
    module_page.get_by_role("button", name="Add Workflow").click()
    modal = module_page.get_by_role("dialog")
    modal.wait_for(state="visible", timeout=10000)

    # Scope = "Enquiry Type Override"
    modal.locator(".react-select__input-container").first.click()
    module_page.wait_for_timeout(500)
    module_page.get_by_role("option", name="Enquiry Type Override").click()
    module_page.wait_for_timeout(500)

    # Select our enquiry type
    modal.locator(".react-select__input-container").nth(1).click()
    module_page.wait_for_timeout(500)
    module_page.get_by_role("option", name=type_name).click()
    module_page.wait_for_timeout(300)

    # Workflow name
    modal.locator("input[name='workflow_name']").fill(wf_name)

    # Create
    modal.get_by_role("button", name="Create").click()
    module_page.wait_for_load_state("networkidle")
    module_page.wait_for_timeout(2000)

    # 3. Navigate to the workflow detail and add a stage
    # Find our workflow and click "manage" to go to detail page
    wf_page.navigate()
    module_page.wait_for_load_state("networkidle")
    module_page.wait_for_timeout(1000)

    # Search for our workflow
    row = module_page.locator("table tbody tr").filter(has_text=wf_name).first
    row.wait_for(state="visible", timeout=5000)
    row.get_by_title("manage").click()
    module_page.wait_for_load_state("networkidle")
    module_page.wait_for_timeout(2000)

    # Now on the workflow detail page — add 3 required stages
    stages = [
        {"name": "New Lead", "order": "1", "check": "is_default_stage"},
        {"name": "Converted", "order": "2", "check": "is_converted_stage"},
        {"name": "Cancelled", "order": "3", "check": "is_cancelled_stage"},
    ]

    for stage in stages:
        module_page.get_by_role("button", name="Add Stage").click()
        stage_modal = module_page.get_by_role("dialog")
        stage_modal.wait_for(state="visible", timeout=10000)

        stage_modal.locator("input[name='stage_name']").fill(stage["name"])
        stage_modal.locator("input[name='sort_order']").fill(stage["order"])
        stage_modal.locator(f"input[name='{stage['check']}']").check()
        stage_modal.get_by_role("button", name="Create").click()
        module_page.wait_for_timeout(2000)
        # Modal should close after each stage creation
        try:
            stage_modal.wait_for(state="hidden", timeout=5000)
        except Exception:
            pass

    yield type_name

    # Teardown: delete the workflow (which cascades) and the type
    try:
        wf_page.navigate()
        wf_page.delete_workflow(wf_name)
    except Exception as e:
        print(f"Teardown: Failed to delete workflow {wf_name}: {e}")
    try:
        types_page.navigate()
        if types_page.search_enquiry_type(type_name):
            types_page.delete_enquiry_type(type_name)
    except Exception as e:
        print(f"Teardown: Failed to delete enquiry type {type_name}: {e}")


@pytest.fixture(scope="module")
def module_branch(module_page):
    """Create a branch for enquiry tests."""
    branches_page = BranchesPage(module_page)
    branches_page.navigate()
    branch_name = branches_page.add_branch()
    branches_page.page.get_by_text("Branch created successfully.").wait_for(
        state="visible", timeout=5000
    )
    yield branch_name
    try:
        branches_page.navigate()
        if branches_page.search_branch(branch_name):
            branches_page.delete_branch(branch_name)
    except Exception as e:
        print(f"Teardown: Failed to delete branch {branch_name}: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_enquiry_page_loads(logged_in_page):
    """Verify the enquiry page loads correctly."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()
    assert enquiry_page.is_enquiry_visible(), "Enquiry page did not load"


def test_add_enquiry(logged_in_page, module_enquiry_type, module_branch):
    """Create a new enquiry and verify it appears in the list."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    enq_name = generate_random_name("enq_lead")
    phone = generate_random_phone()

    enquiry_page.add_enquiry(
        enquiry_type=module_enquiry_type,
        branch=module_branch,
        name=enq_name,
        phone=phone,
        assigned_to="Developer",  # Admin user from the system
        description="Automated test enquiry",
    )

    # Verify it appears via search
    enquiry_page.navigate()
    assert enquiry_page.search_enquiry(enq_name), (
        f"Enquiry '{enq_name}' not found after creation"
    )


def test_search_enquiry(logged_in_page, module_enquiry_type, module_branch):
    """Create an enquiry with a unique name, then search for it."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    unique_name = generate_random_name("search_enq")
    enquiry_page.add_enquiry(
        enquiry_type=module_enquiry_type,
        branch=module_branch,
        name=unique_name,
        phone=generate_random_phone(),
        assigned_to="Developer",
        description="Search test enquiry",
    )

    enquiry_page.navigate()
    assert enquiry_page.search_enquiry(unique_name), (
        f"Enquiry '{unique_name}' not found in search"
    )


def test_view_enquiry(logged_in_page, module_enquiry_type, module_branch):
    """Create an enquiry, then view its details in the drawer."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    view_name = generate_random_name("view_enq")
    enquiry_page.add_enquiry(
        enquiry_type=module_enquiry_type,
        branch=module_branch,
        name=view_name,
        phone=generate_random_phone(),
        assigned_to="Developer",
        description="View test enquiry",
    )

    enquiry_page.navigate()
    assert enquiry_page.view_enquiry(view_name), (
        f"Could not open detail drawer for enquiry '{view_name}'"
    )
    enquiry_page.close_drawer()


def test_enquiry_required_field_validation(logged_in_page):
    """Required fields should block an empty Enquiry submission."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    errors = enquiry_page.submit_empty_form()

    expected_errors = {
        "Enquiry Type is required",
        "Branch is required",
        "Stage is required",
        "Name is required",
        "Either phone or email is required",
        "Description is required",
        "Assigned user is required",
    }
    missing = expected_errors.difference(errors)
    assert not missing, f"Missing Enquiry validation messages: {sorted(missing)}"


def test_default_stage_and_initial_followup(
    logged_in_page, module_enquiry_type, module_branch
):
    """Creating an Enquiry should assign its default stage and pending follow-up."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    enquiry_name = generate_random_name("flow_enq")
    created = enquiry_page.add_enquiry(
        enquiry_type=module_enquiry_type,
        branch=module_branch,
        name=enquiry_name,
        phone=generate_random_phone(),
        assigned_to="Developer",
        description="Default stage and initial follow-up test",
    )

    assert created.get("id"), "Create response did not contain an Enquiry ID"
    assert created.get("stage", {}).get("stage_name") == "New Lead", (
        f"Expected default stage 'New Lead', received: {created.get('stage')}"
    )

    enquiry_page.navigate()
    assert enquiry_page.view_enquiry(enquiry_name), (
        f"Could not open Enquiry '{enquiry_name}' after creation"
    )
    assert enquiry_page.has_pending_followup(), (
        "The automatically created pending follow-up was not visible"
    )
    enquiry_page.close_drawer()


@pytest.mark.skip(
    reason=(
        "Phone is marked mandatory in the Enquiry form, but the application "
        "accepts an email-only Enquiry without Phone."
    )
)
def test_reject_enquiry_without_mandatory_phone():
    """An Enquiry must not be created when its mandatory Phone is empty."""


def test_filter_enquiries_by_type(
    logged_in_page, module_enquiry_type, module_branch
):
    """The Enquiry Type filter should return only matching Enquiries."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    enquiry_name = generate_random_name("filter_enq")
    enquiry_page.add_enquiry(
        enquiry_type=module_enquiry_type,
        branch=module_branch,
        name=enquiry_name,
        phone=generate_random_phone(),
        assigned_to="Developer",
        description="Enquiry type filter test",
    )

    enquiry_page.navigate()
    rows = enquiry_page.filter_by_enquiry_type(module_enquiry_type)

    assert rows, "Enquiry Type filter returned no rows"
    assert any(enquiry_name in row for row in rows), (
        f"Filtered results did not contain '{enquiry_name}'"
    )
    assert all(module_enquiry_type in row for row in rows), (
        "Enquiry Type filter returned a row from another type"
    )


@pytest.mark.skip(
    reason=(
        "Application validation accepts a 10-digit phone starting outside 6-9; "
        "Indian mobile-number validation is missing."
    )
)
def test_reject_enquiry_phone_with_invalid_start_digit():
    """Enquiry phone numbers should begin with 6, 7, 8, or 9."""


@pytest.mark.skip(
    reason=(
        "Enquiry list/delete branch authorization is missing in the backend; "
        "a restricted-user credential fixture is also required."
    )
)
def test_restricted_user_cannot_access_other_branch_enquiry():
    """A branch-restricted user must not list, view, delete, or restore other-branch Enquiries."""


@pytest.mark.skip(
    reason=(
        "Changing Enquiry Type or Branch keeps the original workflow snapshot, "
        "which can reject or misassign the newly resolved stage."
    )
)
def test_edit_type_or_branch_re_resolves_enquiry_workflow():
    """Changing Type or Branch should bind the Enquiry to the newly resolved workflow."""


def test_delete_enquiry(logged_in_page, module_enquiry_type, module_branch):
    """Create an enquiry, then delete it."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    del_name = generate_random_name("del_enq")
    enquiry_page.add_enquiry(
        enquiry_type=module_enquiry_type,
        branch=module_branch,
        name=del_name,
        phone=generate_random_phone(),
        assigned_to="Developer",
        description="Delete test enquiry",
    )

    enquiry_page.navigate()
    assert enquiry_page.delete_enquiry(del_name), (
        f"Failed to delete enquiry '{del_name}'"
    )


def test_retrieve_enquiry(logged_in_page, module_enquiry_type, module_branch):
    """Create an enquiry, delete it, then restore it."""
    enquiry_page = EnquiryPage(logged_in_page)
    enquiry_page.navigate()

    ret_name = generate_random_name("ret_enq")
    enquiry_page.add_enquiry(
        enquiry_type=module_enquiry_type,
        branch=module_branch,
        name=ret_name,
        phone=generate_random_phone(),
        assigned_to="Developer",
        description="Retrieve test enquiry",
    )

    # Delete it first
    enquiry_page.navigate()
    assert enquiry_page.delete_enquiry(ret_name), (
        f"Failed to delete enquiry '{ret_name}'"
    )

    # Now retrieve it
    enquiry_page.navigate()
    assert enquiry_page.retrieve_enquiry(ret_name), (
        f"Failed to retrieve enquiry '{ret_name}'"
    )
