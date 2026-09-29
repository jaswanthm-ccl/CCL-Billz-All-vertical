from __future__ import annotations

import json
import requests
from utils.constants import BASE_URL

class ApiHelper:
    def __init__(self, storage_state_path: str = "auth_state.json") -> None:
        # The staging backend usually runs on the /api or similar sub-path; fallback to BASE_URL
        self.base_url: str = BASE_URL.rstrip("/") + "/api"
        self.session: requests.Session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })
        self._load_auth_state(storage_state_path)

    def _load_auth_state(self, path: str) -> None:
        """Extracts saved cookies and localStorage tokens from Playwright storage state
        and applies them to the requests Session for authenticated HTTP calls."""
        try:
            with open(path, "r") as f:
                state = json.load(f)
                
                # Apply cookies to session
                for cookie in state.get("cookies", []):
                    self.session.cookies.set(
                        name=cookie["name"],
                        value=cookie["value"],
                        domain=cookie["domain"],
                        path=cookie.get("path", "/")
                    )
                
                # Try loading Bearer token from localStorage origins
                origins = state.get("origins", [])
                for origin in origins:
                    local_storage = origin.get("localStorage", [])
                    for item in local_storage:
                        if "token" in item["name"].lower():
                            token_val = item["value"]
                            # Clean up quotes if stringified JSON
                            if token_val.startswith('"') and token_val.endswith('"'):
                                token_val = token_val[1:-1]
                            self.session.headers.update({"Authorization": f"Bearer {token_val}"})
        except Exception:
            pass  # Fallback to unauthenticated calls if auth_state.json is missing

    def get(self, endpoint: str, params: dict | None = None) -> requests.Response:
        url: str = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.session.get(url, params=params)

    def post(self, endpoint: str, json_data: dict | None = None) -> requests.Response:
        url: str = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.session.post(url, json=json_data)

    def put(self, endpoint: str, json_data: dict | None = None) -> requests.Response:
        url: str = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.session.put(url, json=json_data)

    def delete(self, endpoint: str) -> requests.Response:
        url: str = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.session.delete(url)
