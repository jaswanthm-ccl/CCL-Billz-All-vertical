"""One Tenant per vertical. Page objects build every URL from the tenant they are given."""
from __future__ import annotations

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
