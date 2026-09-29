from __future__ import annotations

import re

from playwright.sync_api import Locator


class FormHelpers:
    """Reusable form validation helpers for page objects.

    Methods are static so they can be called without instantiation.
    Import either the class or the bare function aliases at module level.
    """

    @staticmethod
    def has_validation_feedback(container: Locator, *patterns: str, timeout: int = 5000) -> bool:
        """Return True when any expected validation message becomes visible."""
        if not patterns:
            return False
        # One combined wait: short-lived toasts vanish before a pattern-by-pattern loop reaches later patterns.
        combined = re.compile("|".join(f"(?:{pattern})" for pattern in patterns), re.IGNORECASE)
        try:
            container.get_by_text(combined).first.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return False

    @staticmethod
    def has_required_field_feedback(container: Locator, timeout: int = 3000) -> bool:
        """Return True for visible native, ARIA, or rendered required-field feedback."""
        feedback = container.locator(
            '[aria-invalid="true"], input:invalid:not([type="hidden"]), '
            'textarea:invalid, select:invalid, .invalid-feedback, .text-danger, '
            '.error-message'
        ).first
        try:
            feedback.wait_for(state="visible", timeout=timeout)
            return True
        except Exception:
            return FormHelpers.has_validation_feedback(
                container,
                r"(?:required|mandatory)",
                r"must be (?:selected|provided|entered)",
                timeout=timeout,
            )


# Backward-compatible bare function aliases so existing imports keep working:
# from pages.common.form_page import has_validation_feedback, has_required_field_feedback
has_validation_feedback = FormHelpers.has_validation_feedback
has_required_field_feedback = FormHelpers.has_required_field_feedback
