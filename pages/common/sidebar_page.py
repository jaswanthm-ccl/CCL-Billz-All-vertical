import re

class SidebarPage:
    def __init__(self, page):
        self.page = page

    def click_sidebar_link(self, name):
        """Clicks a link in the sidebar menu."""
        link = self.page.get_by_role("link", name=re.compile(rf"^\s*{re.escape(name)}", re.IGNORECASE))
        link.wait_for(state="visible", timeout=5000)
        link.click()
        self.page.wait_for_load_state("networkidle")
