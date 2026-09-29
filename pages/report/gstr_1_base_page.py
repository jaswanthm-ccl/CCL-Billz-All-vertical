from __future__ import annotations

import re
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Download, Page, Response


class Gstr1ReportPage:
    """Shared strict interactions for GSTR-1 preview, filters, and exports."""

    REPORT_NAME = ""
    API_PATH_SUFFIX = ""
    REPORT_URL = ""
    EXPECTED_HEADERS: list[str] = []

    def __init__(self, page: Page) -> None:
        self.page = page
        self.url = self.REPORT_URL
        self.last_data: dict[str, Any] | None = None

    @staticmethod
    def month_start() -> str:
        today = date.today()
        return today.replace(day=1).isoformat()

    @staticmethod
    def today() -> str:
        return date.today().isoformat()

    @staticmethod
    def _query(response: Response) -> dict[str, list[str]]:
        return parse_qs(urlparse(response.url).query)

    @classmethod
    def _is_report_response(cls, response: Response) -> bool:
        path = urlparse(response.url).path.rstrip("/")
        return (
            response.request.method == "GET"
            and path.endswith(cls.API_PATH_SUFFIX)
        )

    @classmethod
    def _matches_params(cls, response: Response, **params: object) -> bool:
        if not cls._is_report_response(response):
            return False
        query = cls._query(response)
        return all(query.get(key, [None])[-1] == str(value) for key, value in params.items())

    def _capture(
        self,
        action: Callable[[], None],
        predicate: Callable[[Response], bool] | None = None,
    ) -> dict[str, Any]:
        matcher = predicate or self._is_report_response
        with self.page.expect_response(matcher, timeout=20_000) as response_info:
            action()

        response = response_info.value
        if not response.ok:
            try:
                detail = response.text()
            except Exception:
                detail = "<response body unavailable>"
            raise AssertionError(
                f"{self.REPORT_NAME} API failed with HTTP {response.status}: {detail}"
            )

        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise AssertionError(
                f"{self.REPORT_NAME} API returned an invalid payload: {payload!r}"
            )

        self.last_data = data
        overlay = self.page.locator(".loading-state-modern--overlay")
        if overlay.count():
            overlay.wait_for(state="hidden", timeout=10_000)
        return data

    def navigate(self) -> dict[str, Any]:
        return self._capture(
            lambda: self.page.goto(self.url, wait_until="domcontentloaded")
        )

    def expand_filters(self) -> None:
        button = self.page.get_by_role("button", name="Expand filters")
        if button.count() and button.is_visible():
            button.click()

    def _select_filter(self, name: str, option: str) -> None:
        hidden_input = self.page.locator(f"input[name='{name}']")
        hidden_input.wait_for(state="attached", timeout=10_000)
        control = hidden_input.locator("xpath=..").locator(".react-select__control")
        control.click()
        self.page.get_by_role("option", name=option, exact=True).click()

    def selected_filter_label(self, name: str) -> str:
        hidden_input = self.page.locator(f"input[name='{name}']")
        value = hidden_input.locator("xpath=..").locator(
            ".react-select__single-value"
        )
        return value.inner_text().strip()

    def apply_filters(
        self,
        *,
        from_date: str,
        to_date: str,
        branch_name: str | None = None,
        mode: str = "invoice_wise",
    ) -> dict[str, Any]:
        self.expand_filters()
        self._select_filter("period_type", "Custom Date Range")
        self.page.locator("input[name='start_date']").fill(from_date)
        self.page.locator("input[name='end_date']").fill(to_date)

        expected_params: dict[str, object] = {
            "start_date": from_date,
            "end_date": to_date,
            "mode": mode,
        }
        if branch_name:
            self._select_filter("branch_id", branch_name)
            branch_id = self.page.locator("input[name='branch_id']").input_value()
            expected_params["branch_id"] = branch_id

        mode_label = "Summary Wise" if mode == "summary_wise" else "Invoice Wise"
        self._select_filter("mode", mode_label)

        button = self.page.get_by_role("button", name="Generate", exact=True)
        return self._capture(
            lambda: button.click(),
            lambda response: self._matches_params(response, **expected_params),
        )

    def clear_filters(self) -> dict[str, Any]:
        self.expand_filters()
        button = self.page.get_by_role(
            "button", name=re.compile(r"Reset", re.IGNORECASE)
        )
        return self._capture(lambda: button.click())

    def export(self, file_format: str) -> Download:
        normalized = file_format.lower()
        if normalized not in {"xlsx", "pdf"}:
            raise ValueError("GSTR-1 exports support only XLSX and PDF")

        button = self.page.get_by_role(
            "button", name=f"Download {normalized.upper()}", exact=True
        )
        if button.is_disabled():
            raise AssertionError(
                f"{self.REPORT_NAME} {normalized.upper()} export is disabled"
            )

        downloads: list[Download] = []

        def capture_download(download: Download) -> None:
            downloads.append(download)

        self.page.once("download", capture_download)
        export_suffix = f"{self.API_PATH_SUFFIX}/export"
        try:
            with self.page.expect_response(
                lambda response: (
                    response.request.method == "GET"
                    and urlparse(response.url).path.rstrip("/").endswith(export_suffix)
                    and self._query(response).get("format", [None])[-1] == normalized
                ),
                timeout=90_000,
            ) as response_info:
                button.click()
            response = response_info.value
        except Exception:
            self.page.remove_listener("download", capture_download)
            raise

        if not response.ok:
            self.page.remove_listener("download", capture_download)
            try:
                detail = response.text()
            except Exception:
                detail = "<response body unavailable>"
            raise AssertionError(
                f"{self.REPORT_NAME} {normalized.upper()} export API failed "
                f"with HTTP {response.status}: {detail}"
            )

        deadline = time.monotonic() + 10
        while not downloads and time.monotonic() < deadline:
            self.page.wait_for_timeout(100)
        if not downloads:
            self.page.remove_listener("download", capture_download)
            raise AssertionError(
                f"{self.REPORT_NAME} {normalized.upper()} API succeeded but no download started"
            )

        download = downloads[0]
        if download.failure():
            raise AssertionError(
                f"{self.REPORT_NAME} export failed: {download.failure()}"
            )
        return download

    def heading_visible(self) -> bool:
        return self.page.get_by_role(
            "heading", name=self.REPORT_NAME, exact=False
        ).is_visible()

    def headers(self) -> list[str]:
        return [
            value.strip()
            for value in self.page.locator("table thead th").all_text_contents()
        ]

    def rows(self) -> list[list[str]]:
        result: list[list[str]] = []
        for row in self.page.locator("table tbody tr").all():
            cells = [value.strip() for value in row.locator("td").all_text_contents()]
            if len(cells) > 1:
                result.append(cells)
        return result

    @staticmethod
    def downloaded_path(download: Download) -> Path:
        path = download.path()
        if not path:
            raise AssertionError("Export download has no local path")
        result = Path(path)
        if not result.is_file() or result.stat().st_size == 0:
            raise AssertionError("Export download is empty")
        return result

    @staticmethod
    def assert_valid_xlsx(path: Path, report_name: str) -> None:
        if not zipfile.is_zipfile(path):
            raise AssertionError("Downloaded XLSX is not a valid Office archive")
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            required = {"[Content_Types].xml", "xl/workbook.xml"}
            if not required <= names:
                raise AssertionError("Downloaded XLSX is missing workbook files")
            xml_content = b"".join(
                archive.read(name)
                for name in names
                if name.endswith(".xml")
            )
        if report_name.encode("utf-8") not in xml_content:
            raise AssertionError(
                f"Downloaded XLSX does not identify the {report_name} report"
            )

    @staticmethod
    def assert_valid_pdf(path: Path) -> None:
        with path.open("rb") as file:
            if file.read(5) != b"%PDF-":
                raise AssertionError("Downloaded PDF has an invalid signature")
