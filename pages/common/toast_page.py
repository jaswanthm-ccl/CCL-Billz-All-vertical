import re

class ToastPage:
    def __init__(self, page):
        self.page = page

    def wait_for_toast(self, message_pattern, timeout=10000):
        """Waits for a toast message to become visible on the screen."""
        if isinstance(message_pattern, str):
            locator = self.page.get_by_text(re.compile(re.escape(message_pattern), re.IGNORECASE))
        else:
            locator = self.page.get_by_text(message_pattern)
        locator.wait_for(state="visible", timeout=timeout)
        return locator

    def wait_for_toast_hidden(self, message_pattern, timeout=5000):
        """Waits for a toast message to disappear from the screen."""
        if isinstance(message_pattern, str):
            locator = self.page.get_by_text(re.compile(re.escape(message_pattern), re.IGNORECASE))
        else:
            locator = self.page.get_by_text(message_pattern)
        try:
            locator.wait_for(state="hidden", timeout=timeout)
            return True
        except Exception:
            return False
