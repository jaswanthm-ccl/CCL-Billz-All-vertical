"""Galaxy smoke for masters that behave like retail: page loads, create, search, delete.

Deep coverage for these screens lives in the retail suite.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

import pytest

from pages.master_menu.account_groups_page import AccountGroupsPage
from pages.master_menu.bank_accounts_page import BankAccountPage
from pages.master_menu.brands_page import BrandsPage
from pages.master_menu.categories_page import CategoriesPage
from pages.master_menu.expense_categories_page import ExpenseCategoriesPage
from pages.master_menu.racks_page import RacksPage
from pages.master_menu.roles_page import RolesPage
from pages.master_menu.sac_hsn_code_page import SacHsnCodePage
from pages.master_menu.unit_types_page import UnitTypesPage
from pages.master_menu.users_page import UsersPage
from pages.master_menu.voucher_types_page import VoucherTypesPage
from utils.random_data import (
    generate_random_code,
    generate_random_description,
    generate_random_name,
    generate_random_unit,
)

pytestmark = pytest.mark.smoke

GALAXY_BRANCH = "galaxy Mobile"
ACTIVE_DELETE_ICON = 'button[title="delete"]:has(i.bi-trash)'


@dataclass(frozen=True)
class MasterSpec:
    page_cls: type
    create: Callable[[object], str]
    search: str
    delete: str


def _create_named(method: str, **kwargs) -> Callable[[object], str]:
    def create(page_obj) -> str:
        name = generate_random_name("galaxy")
        getattr(page_obj, method)(name, **kwargs)
        return name
    return create


def _create_unit_type(page_obj) -> str:
    name = generate_random_name("galaxy_unit")
    assert page_obj.add_unit_type(name, generate_random_unit(), generate_random_description("unit"))
    return name


def _create_sac_hsn(page_obj) -> str:
    code = str(random.randint(100000, 999999))
    response = page_obj.add_sac_hsn_code("SAC", code)
    assert response.status in (200, 201), f"SAC/HSN create API returned {response.status}"
    return code


def _create_bank_account(page_obj) -> str:
    bank_name = generate_random_name("galaxy_bank")
    page_obj.add_bank_account(
        bank_name,
        generate_random_name("branch"),
        str(random.randint(100000000000, 999999999999)),
        "IDFC0000899",
    )
    return bank_name


def _create_rack(page_obj) -> str:
    name = generate_random_name("galaxy_rack")
    page_obj.add_rack(name, generate_random_code("RK"), branch_name=GALAXY_BRANCH)
    return name


MASTERS = {
    "roles": MasterSpec(RolesPage, lambda p: p.add_roles()["name"], "search_roles", "delete_role"),
    "categories": MasterSpec(CategoriesPage, _create_named("add_category"), "search_category", "delete_category"),
    "brands": MasterSpec(
        BrandsPage, _create_named("add_brand", description=generate_random_description("brand")),
        "search_brand", "delete_brand",
    ),
    "unit_types": MasterSpec(UnitTypesPage, _create_unit_type, "search_unit_type", "delete_unit_type"),
    "sac_hsn": MasterSpec(SacHsnCodePage, _create_sac_hsn, "search_sac_hsn_code", "delete_sac_hsn_code"),
    "bank_accounts": MasterSpec(BankAccountPage, _create_bank_account, "search_bank_account", "delete_bank_account"),
    "expense_categories": MasterSpec(
        ExpenseCategoriesPage, _create_named("add_expense_category"),
        "search_expense_category", "delete_expense_category",
    ),
    "racks": MasterSpec(RacksPage, _create_rack, "search_rack", "delete_rack"),
    "account_groups": MasterSpec(
        AccountGroupsPage, _create_named("add_account_group"), "search_account_group", "delete_account_group",
    ),
}


def _ensure_deleted(page_obj, spec: MasterSpec, key: str) -> bool:
    page_obj.navigate()
    if not getattr(page_obj, spec.search)(key):
        return True
    row = page_obj.page.locator("tbody tr").filter(has=page_obj.page.get_by_text(key, exact=True)).first
    if row.locator(ACTIVE_DELETE_ICON).count() == 0:
        return True
    return getattr(page_obj, spec.delete)(key)


@pytest.mark.parametrize("master", list(MASTERS))
def test_master_create_search_delete(master, galaxy_logged_in_page, tenant, cleanup):
    spec = MASTERS[master]
    page_obj = spec.page_cls(galaxy_logged_in_page, tenant)
    page_obj.navigate()

    key = spec.create(page_obj)
    cleanup(f"{master} {key}", lambda: _ensure_deleted(page_obj, spec, key))

    page_obj.navigate()
    assert getattr(page_obj, spec.search)(key), f"{master}: '{key}' not found after create"
    assert getattr(page_obj, spec.delete)(key), f"{master}: '{key}' delete did not succeed"


def test_users_page_loads(galaxy_logged_in_page, tenant):
    users_page = UsersPage(galaxy_logged_in_page, tenant)
    users_page.navigate()

    assert users_page.is_user_visible()


def test_voucher_types_page_loads(galaxy_logged_in_page, tenant):
    voucher_types_page = VoucherTypesPage(galaxy_logged_in_page, tenant)
    voucher_types_page.navigate()

    assert voucher_types_page.is_voucher_types_visible()
