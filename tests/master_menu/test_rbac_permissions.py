from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import pytest
from playwright.sync_api import Browser, Page

from pages.auth.login_page import LoginPage
from pages.master_menu.branches_page import BranchesPage
from pages.master_menu.roles_page import RolesPage
from pages.master_menu.users_page import UsersPage
from utils.constants import BRANCHES_URL, CITY_URL, ROLES_URL, USERS_URL
from utils.random_data import (
    generate_random_email,
    generate_random_name,
    generate_random_password,
)


VIEW_PERMISSIONS = [
    "view_branches",
    "view_cities",
    "view_roles",
    "view_users",
]


@dataclass(frozen=True)
class ModuleAccess:
    name: str
    url: str
    api_url: str
    add_button: str


@dataclass(frozen=True)
class RbacState:
    view_email: str
    view_password: str
    branch_email: str
    branch_password: str
    modules: tuple[ModuleAccess, ...]


def _list_response(module_path: str):
    pattern = re.compile(rf"/{re.escape(module_path)}(?:\?|$)")
    return lambda response: (
        response.request.method == "GET"
        and response.request.resource_type in {"fetch", "xhr"}
        and pattern.search(response.url) is not None
    )


def _without_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _capture_module(
    page: Page,
    *,
    name: str,
    ui_url: str,
    api_path: str,
    add_button: str,
) -> ModuleAccess:
    with page.expect_response(_list_response(api_path), timeout=15000) as info:
        page.goto(ui_url)
    return ModuleAccess(
        name=name,
        url=ui_url,
        api_url=_without_query(info.value.url),
        add_button=add_button,
    )


def _login(browser: Browser, email: str, password: str) -> Page:
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    login = LoginPage(page)
    login.navigate()
    login.login(email, password)
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    return page


def _token(page: Page) -> str:
    token = page.evaluate("localStorage.getItem('access_token')")
    assert token, "Expected an authenticated access token"
    return token


def _authorized_headers(page: Page) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {_token(page)}",
    }


def _application_headers(page: Page, module: ModuleAccess) -> dict[str, str]:
    api_path = urlsplit(module.api_url).path.rsplit("/", 1)[-1]
    with page.expect_response(_list_response(api_path), timeout=15000) as info:
        page.goto(module.url)

    request_headers = info.value.request.all_headers()
    allowed_names = {
        "accept",
        "authorization",
        "x-tenant-id",
        "x-financial-year-id",
        "x-fy-start-date",
        "x-fy-end-date",
        "x-fy-mode",
    }
    headers = {
        name: value
        for name, value in request_headers.items()
        if name.lower() in allowed_names
    }
    ui_parts = urlsplit(module.url)
    origin = f"{ui_parts.scheme}://{ui_parts.netloc}"
    headers["Origin"] = origin
    headers["Referer"] = f"{origin}/"
    headers.update(_authorized_headers(page))
    return headers


@pytest.fixture(scope="module")
def rbac_state(module_page: Page) -> RbacState:
    branches = BranchesPage(module_page)
    roles = RolesPage(module_page)
    users = UsersPage(module_page)

    branches.navigate()
    branch_name = branches.add_branch()

    view_role = generate_random_name("rbac_view")
    branch_role = generate_random_name("rbac_branch")

    roles.navigate()
    roles.add_role_with_permissions(view_role, VIEW_PERMISSIONS)
    roles.navigate()
    roles.add_role_with_permissions(branch_role, ["view_branches"])

    view_email = generate_random_email("rbac_view")
    view_password = generate_random_password()
    view_user = generate_random_name("rbac_view_user")
    branch_email = generate_random_email("rbac_branch")
    branch_password = generate_random_password()
    branch_user = generate_random_name("rbac_branch_user")

    users.navigate()
    users.add_user(
        name=view_user,
        email=view_email,
        password=view_password,
        branch_name=branch_name,
        role_name=view_role,
    )
    users.navigate()
    users.add_user(
        name=branch_user,
        email=branch_email,
        password=branch_password,
        branch_name=branch_name,
        role_name=branch_role,
    )

    modules = (
        _capture_module(
            module_page,
            name="Branches",
            ui_url=BRANCHES_URL,
            api_path="branches",
            add_button="Add Branch",
        ),
        _capture_module(
            module_page,
            name="Cities",
            ui_url=CITY_URL,
            api_path="cities",
            add_button="Add City",
        ),
        _capture_module(
            module_page,
            name="Roles",
            ui_url=ROLES_URL,
            api_path="roles",
            add_button="Add Role",
        ),
        _capture_module(
            module_page,
            name="Users",
            ui_url=USERS_URL,
            api_path="users",
            add_button="Add User",
        ),
    )

    yield RbacState(
        view_email=view_email,
        view_password=view_password,
        branch_email=branch_email,
        branch_password=branch_password,
        modules=modules,
    )

    for user_name in (view_user, branch_user):
        try:
            users.navigate()
            if users.search_user(user_name):
                users.delete_user(user_name)
        except Exception as exc:
            print(f"RBAC teardown: failed to delete user {user_name}: {exc}")

    for role_name in (view_role, branch_role):
        try:
            roles.navigate()
            if roles.search_roles(role_name) and roles.is_role_active(role_name):
                roles.delete_role(role_name)
        except Exception as exc:
            print(f"RBAC teardown: failed to delete role {role_name}: {exc}")

    try:
        branches.navigate()
        if branches.search_branch(branch_name):
            branches.delete_branch(branch_name)
    except Exception as exc:
        print(f"RBAC teardown: failed to delete branch {branch_name}: {exc}")
    branches.cleanup_auto_city(branch_name)


@pytest.fixture(scope="module")
def view_only_page(browser: Browser, rbac_state: RbacState):
    page = _login(browser, rbac_state.view_email, rbac_state.view_password)
    yield page
    page.context.close()


@pytest.fixture(scope="module")
def branch_only_page(browser: Browser, rbac_state: RbacState):
    page = _login(browser, rbac_state.branch_email, rbac_state.branch_password)
    yield page
    page.context.close()


@pytest.mark.parametrize(
    "module_index",
    [
        0,
        pytest.param(
            1,
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    "Known UI permission bug: Add City is visible without "
                    "create_cities; the API correctly returns 403"
                ),
            ),
        ),
        2,
        3,
    ],
)
def test_view_only_role_can_list_but_has_no_write_actions(
    view_only_page: Page,
    rbac_state: RbacState,
    module_index: int,
):
    module = rbac_state.modules[module_index]
    with view_only_page.expect_response(
        _list_response(urlsplit(module.api_url).path.rsplit("/", 1)[-1]),
        timeout=15000,
    ) as info:
        view_only_page.goto(module.url)

    assert info.value.status == 200
    assert view_only_page.get_by_role(
        "button", name=module.add_button
    ).count() == 0
    assert view_only_page.locator('button[title="edit"]').count() == 0
    assert view_only_page.locator(
        'button[title="delete"]:has(i.bi-trash)'
    ).count() == 0


@pytest.mark.parametrize("module_index", range(4))
def test_view_only_role_write_apis_are_forbidden(
    view_only_page: Page,
    rbac_state: RbacState,
    module_index: int,
):
    module = rbac_state.modules[module_index]
    headers = _application_headers(view_only_page, module)

    create_response = view_only_page.request.post(
        module.api_url,
        headers=headers,
        data={},
    )
    update_response = view_only_page.request.put(
        f"{module.api_url}/1",
        headers=headers,
        data={},
    )
    delete_response = view_only_page.request.delete(
        f"{module.api_url}/1",
        headers=headers,
    )

    assert create_response.status == 403, create_response.text()
    assert update_response.status == 403, update_response.text()
    assert delete_response.status == 403, delete_response.text()


@pytest.mark.parametrize("module_index", [1, 2, 3])
def test_branch_only_role_cannot_access_unassigned_modules(
    branch_only_page: Page,
    rbac_state: RbacState,
    module_index: int,
):
    module = rbac_state.modules[module_index]
    headers = _application_headers(branch_only_page, rbac_state.modules[0])
    response = branch_only_page.request.get(
        module.api_url,
        headers=headers,
    )
    assert response.status == 403

    branch_only_page.goto(module.url)
    branch_only_page.wait_for_load_state("domcontentloaded")
    assert branch_only_page.get_by_role(
        "button", name=module.add_button
    ).count() == 0


def test_branch_only_role_can_access_assigned_branch_module(
    branch_only_page: Page,
    rbac_state: RbacState,
):
    module = rbac_state.modules[0]
    headers = _application_headers(branch_only_page, module)
    response = branch_only_page.request.get(
        module.api_url,
        headers=headers,
    )
    assert response.status == 200

    branch_only_page.goto(module.url)
    branch_only_page.wait_for_load_state("domcontentloaded")
    assert branch_only_page.get_by_role("button", name="Add Branch").count() == 0
