from __future__ import annotations

import re
import os

def clean_currency(value_str: str) -> float:
    """Removes currency symbols ($, Rs., rupee, ₹, etc.) and commas from a string,
    returning a clean float representation for mathematical assertions."""
    if not value_str:
        return 0.0
    cleaned = re.sub(r"[^\d\.]", "", value_str)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def remove_file_safely(file_path: str) -> bool:
    """Safely deletes a local file if it exists, catching any permissions/IO exceptions."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception:
            pass
    return False
