"""One Tenant per vertical. Page objects build every URL from the tenant they are given.

Shared pages default to the *active* tenant, chosen per run with `pytest --tenant <name>`
or the BILLZ_TENANT environment variable (default: retail).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from utils.constants import ADMIN_EMAIL, ADMIN_PASSWORD, BASE_URL
from utils.galaxy_constants import GALAXY_BASE_URL, GALAXY_USER_EMAIL, GALAXY_USER_PASSWORD
from utils.res_constants import (
    RESTAURANT_BASE_URL,
    RESTAURANT_USER_1_EMAIL,
    RESTAURANT_USER_1_PASSWORD,
)


@dataclass(frozen=True)
class Tenant:
    name: str
    base_url: str
    email: str | None
    password: str | None
    marker: str

    def url(self, path: str = "") -> str:
        if not path:
            return self.base_url.rstrip("/")
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"


RETAIL = Tenant("retail", BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, "default_vertical")
RESTAURANT = Tenant(
    "restaurant",
    RESTAURANT_BASE_URL,
    RESTAURANT_USER_1_EMAIL,
    RESTAURANT_USER_1_PASSWORD,
    "restaurant",
)
GALAXY = Tenant("galaxy", GALAXY_BASE_URL, GALAXY_USER_EMAIL, GALAXY_USER_PASSWORD, "galaxy")

TENANTS: dict[str, Tenant] = {t.name: t for t in (RETAIL, GALAXY, RESTAURANT)}

_active: Tenant = TENANTS.get(os.getenv("BILLZ_TENANT", "retail").lower(), RETAIL)


def get_tenant(name: str) -> Tenant:
    try:
        return TENANTS[name.lower()]
    except KeyError:
        raise ValueError(f"Unknown tenant '{name}'. Choose one of: {', '.join(TENANTS)}") from None


def set_active_tenant(name: str) -> Tenant:
    global _active
    _active = get_tenant(name)
    return _active


def active_tenant() -> Tenant:
    return _active
