import pytest

from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.enquiry_stage_workflows_page import EnquiryStageWorkflowsPage
from pages.master_menu.enquiry_types_page import EnquiryTypesPage
from utils.random_data import generate_random_name


@pytest.fixture(scope="module")
def workflow_data(module_page):
    enquiry_types_page = EnquiryTypesPage(module_page)
    type_names = []
    for index in range(7):
        enquiry_types_page.navigate()
        name = generate_random_name(f"wf_type_{index}")
        enquiry_types_page.add_enquiry_type(name)
        type_names.append(name)

    branches_page = BranchesPage(module_page)
    branch_names = []
    for _ in range(2):
        branches_page.navigate()
        branch_name = branches_page.add_branch()
        branches_page.page.get_by_text("Branch created successfully.").wait_for(
            state="visible", timeout=5000
        )
        branch_names.append(branch_name)

    data = {"types": type_names, "branches": branch_names, "workflows": []}
    yield data

    workflows_page = EnquiryStageWorkflowsPage(module_page)
    for workflow_name in reversed(data["workflows"]):
        try:
            workflows_page.navigate()
            if workflows_page.search_workflow(workflow_name):
                workflows_page.delete_workflow(workflow_name)
        except Exception as exc:
            print(f"Teardown: failed to delete workflow {workflow_name}: {exc}")

    for type_name in type_names:
        try:
            enquiry_types_page.navigate()
            if enquiry_types_page.search_enquiry_type(type_name):
                enquiry_types_page.delete_enquiry_type(type_name)
        except Exception as exc:
            print(f"Teardown: failed to delete enquiry type {type_name}: {exc}")

    for branch_name in branch_names:
        try:
            branches_page.navigate()
            if branches_page.search_branch(branch_name):
                row = module_page.locator(
                    "tr", has=module_page.get_by_text(branch_name, exact=True)
                )
                row.get_by_title("delete").click()
                module_page.get_by_role("button", name="Delete Branch").click()
                module_page.get_by_text("Deleted successfully.").first.wait_for(
                    state="visible", timeout=5000
                )
        except Exception as exc:
            print(f"Teardown: failed to delete branch {branch_name}: {exc}")
        branches_page.cleanup_auto_city(branch_name)


def test_enquiry_stage_workflows_page_loads(logged_in_page):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    assert workflows_page.is_workflows_visible()


@pytest.mark.parametrize(
    ("scope", "shows_type", "shows_branch"),
    [
        ("type", True, False),
        ("branch", False, True),
        ("branch_type", True, True),
    ],
)
def test_workflow_scope_shows_only_relevant_fields(
    logged_in_page, scope, shows_type, shows_branch
):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    modal = workflows_page.open_add_form()
    workflows_page.select_scope(modal, scope)

    assert modal.locator("input[name='enquiry_type_id']").count() == int(shows_type)
    assert modal.locator("input[name='branch_id']").count() == int(shows_branch)
    assert modal.locator("input[name='workflow_name']").is_visible()
    workflows_page.close_form(modal)


def test_global_scope_is_singleton_option(logged_in_page):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    modal = workflows_page.open_add_form()
    modal.locator("input[name='scope']").locator("xpath=..").locator(
        ".react-select__input-container"
    ).click()

    global_option = logged_in_page.get_by_role(
        "option", name="Global Default", exact=False
    )
    assert global_option.count() == 1
    assert global_option.inner_text() in (
        "Global Default",
        "Global Default (already exists)",
    )
    logged_in_page.keyboard.press("Escape")


@pytest.mark.parametrize(
    ("scope", "type_index", "branch_index", "expected_scope"),
    [
        ("type", 0, None, "Enquiry Type Override"),
        ("branch", None, 0, "Branch Override"),
        ("branch_type", 1, 0, "Branch + Type Override"),
    ],
)
def test_create_each_workflow_override_scope(
    logged_in_page,
    workflow_data,
    scope,
    type_index,
    branch_index,
    expected_scope,
):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    workflow_name = generate_random_name(f"wf_{scope}")
    enquiry_type = (
        workflow_data["types"][type_index] if type_index is not None else None
    )
    branch = (
        workflow_data["branches"][branch_index]
        if branch_index is not None
        else None
    )

    workflows_page.add_workflow(
        scope,
        workflow_name,
        enquiry_type=enquiry_type,
        branch=branch,
    )
    workflow_data["workflows"].append(workflow_name)
    assert workflows_page.search_workflow(workflow_name)

    row = workflows_page.get_workflow_row_data(workflow_name)
    assert row["scope"] == expected_scope
    assert row["enquiry_type"] == (enquiry_type or "-")
    assert row["branch"] == (
        branch if branch else "All Branches"
    )
    assert row["active"] == "Yes"


def test_duplicate_type_override_is_rejected(logged_in_page, workflow_data):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    enquiry_type = workflow_data["types"][2]
    first_name = generate_random_name("wf_unique_type")
    workflows_page.add_workflow("type", first_name, enquiry_type=enquiry_type)
    workflow_data["workflows"].append(first_name)

    modal = workflows_page.open_add_form()
    workflows_page.select_scope(modal, "type")
    workflows_page.select_form_option(modal, "enquiry_type_id", enquiry_type)
    modal.locator("input[name='workflow_name']").fill(generate_random_name("wf_duplicate"))
    modal.get_by_role("button", name="Create", exact=True).click()

    error = modal.get_by_text(
        "An enquiry type override workflow already exists for this type.",
        exact=True,
    )
    error.wait_for(state="visible", timeout=5000)
    assert modal.is_visible(), "Duplicate scope unexpectedly created a workflow"
    workflows_page.close_form(modal)


def test_scope_cannot_be_changed_during_edit(logged_in_page, workflow_data):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    workflow_name = generate_random_name("wf_locked_scope")
    workflows_page.add_workflow(
        "type", workflow_name, enquiry_type=workflow_data["types"][3]
    )
    workflow_data["workflows"].append(workflow_name)

    modal = workflows_page.open_edit_form(workflow_name)
    assert modal.locator(".react-select__control--is-disabled").count() == 1
    workflows_page.close_form(modal)


def test_workflow_and_stage_lifecycle_persistence(
    logged_in_page, workflow_data
):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    enquiry_type = workflow_data["types"][0]
    branch = workflow_data["branches"][1]
    workflow_name = generate_random_name("wf_lifecycle")
    workflows_page.add_workflow(
        "branch_type",
        workflow_name,
        enquiry_type=enquiry_type,
        branch=branch,
    )
    workflow_data["workflows"].append(workflow_name)

    updated_name = generate_random_name("wf_lifecycle_updated")
    assert workflows_page.edit_workflow(
        workflow_name, updated_name, active=False
    )
    workflow_data["workflows"].remove(workflow_name)
    workflow_data["workflows"].append(updated_name)
    assert workflows_page.get_workflow_edit_values(updated_name) == {
        "workflow_name": updated_name,
        "active": False,
        "enquiry_type": enquiry_type,
        "branch": branch,
    }
    assert workflows_page.get_workflow_row_data(updated_name)["active"] == "No"

    workflows_page.manage_workflow(updated_name)
    default_stage = generate_random_name("stage_default")
    converted_stage = generate_random_name("stage_converted")
    cancelled_stage = generate_random_name("stage_cancelled")
    neutral_stage = generate_random_name("stage_neutral")

    assert workflows_page.add_stage(
        default_stage, 1, default=True
    ).status in {200, 201}
    assert workflows_page.add_stage(
        converted_stage, 2, final=True, converted=True
    ).status in {200, 201}
    assert workflows_page.add_stage(
        cancelled_stage, 3, final=True, cancelled=True
    ).status in {200, 201}
    assert workflows_page.add_stage(
        neutral_stage, 4, description="Temporary neutral stage"
    ).status in {200, 201}

    logged_in_page.get_by_text("Workflow is complete.", exact=False).wait_for(
        state="visible", timeout=5000
    )
    replacement_default = generate_random_name("replacement_default")
    assert workflows_page.add_replacement_default_stage(
        replacement_default, 5
    )
    assert workflows_page.get_stage_row_data(default_stage)["default"] == "No"
    assert workflows_page.get_stage_row_data(replacement_default)["default"] == "Yes"

    updated_stage = generate_random_name("stage_updated")
    assert workflows_page.edit_stage(
        neutral_stage,
        updated_stage,
        sort_order=6,
        description="Persisted stage description",
    )
    assert workflows_page.get_stage_edit_values(updated_stage) == {
        "name": updated_stage,
        "sort_order": "6",
        "description": "Persisted stage description",
    }
    stage_row = workflows_page.get_stage_row_data(updated_stage)
    assert stage_row["sort_order"] == "6"
    assert stage_row["active"] == "Yes"
    assert stage_row["default"] == "No"

    assert workflows_page.delete_stage(updated_stage)
    assert workflows_page.restore_stage(updated_stage)
    assert workflows_page.stage_row(updated_stage).is_visible()


def test_stage_required_field_validation(logged_in_page, workflow_data):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    workflow_name = generate_random_name("wf_stage_validation")
    workflows_page.add_workflow(
        "type", workflow_name, enquiry_type=workflow_data["types"][4]
    )
    workflow_data["workflows"].append(workflow_name)
    workflows_page.manage_workflow(workflow_name)

    logged_in_page.get_by_role("button", name="Add Stage").click()
    drawer = logged_in_page.get_by_role("dialog", name="Add Stage")
    drawer.get_by_role("button", name="Create", exact=True).click()
    drawer.get_by_text("Stage name is required", exact=True).wait_for(
        state="visible", timeout=5000
    )
    drawer.get_by_text("Sort order is required", exact=True).wait_for(
        state="visible", timeout=5000
    )
    assert drawer.is_visible()
    drawer.get_by_role("button", name="Cancel", exact=True).click()


def test_workflow_resolution_uses_most_specific_scope(logged_in_page, workflow_data):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    enquiry_type = workflow_data["types"][5]
    fallback_type = workflow_data["types"][6]
    branch = workflow_data["branches"][1]

    type_workflow = generate_random_name("wf_priority_type")
    branch_workflow = generate_random_name("wf_priority_branch")
    branch_type_workflow = generate_random_name("wf_priority_both")

    workflows_page.add_workflow("type", type_workflow, enquiry_type=enquiry_type)
    workflow_data["workflows"].append(type_workflow)
    workflows_page.manage_workflow(type_workflow)
    workflows_page.add_complete_stage_set("Type")
    logged_in_page.get_by_role("link", name="Back to Workflows").click()

    workflows_page.add_workflow("branch", branch_workflow, branch=branch)
    workflow_data["workflows"].append(branch_workflow)
    workflows_page.manage_workflow(branch_workflow)
    workflows_page.add_complete_stage_set("Branch")
    logged_in_page.get_by_role("link", name="Back to Workflows").click()

    workflows_page.add_workflow(
        "branch_type",
        branch_type_workflow,
        enquiry_type=enquiry_type,
        branch=branch,
    )
    workflow_data["workflows"].append(branch_type_workflow)
    workflows_page.manage_workflow(branch_type_workflow)
    workflows_page.add_complete_stage_set("Both")
    logged_in_page.get_by_role("link", name="Back to Workflows").click()

    type_id = workflows_page.get_dropdown_id("enquiry-types", enquiry_type)
    fallback_type_id = workflows_page.get_dropdown_id("enquiry-types", fallback_type)
    branch_id = workflows_page.get_dropdown_id("branches", branch)

    exact_result = workflows_page.resolve_workflow(type_id, branch_id)
    assert exact_result["workflow"]["workflow_name"] == branch_type_workflow

    type_result = workflows_page.resolve_workflow(type_id)
    assert type_result["workflow"]["workflow_name"] == type_workflow

    branch_result = workflows_page.resolve_workflow(fallback_type_id, branch_id)
    assert branch_result["workflow"]["workflow_name"] == branch_workflow


def test_delete_and_restore_workflow(logged_in_page, workflow_data):
    workflows_page = EnquiryStageWorkflowsPage(logged_in_page)
    workflows_page.navigate()
    workflow_name = generate_random_name("wf_restore")
    workflows_page.add_workflow(
        "branch_type",
        workflow_name,
        enquiry_type=workflow_data["types"][4],
        branch=workflow_data["branches"][1],
    )
    workflow_data["workflows"].append(workflow_name)

    assert workflows_page.delete_workflow(workflow_name)
    assert workflows_page.restore_workflow(workflow_name)
    assert workflows_page.search_workflow(workflow_name)
