import re

class TablePage:
    def __init__(self, page):
        self.page = page

    def search(self, query, placeholder="Search..."):
        """Fills search box and triggers table filtering."""
        search_box = self.page.get_by_placeholder(re.compile(re.escape(placeholder), re.IGNORECASE))
        search_box.fill(query)
        search_box.press("Enter")
        self.page.wait_for_timeout(2000)  # Wait for search debounce animation

    def get_row(self, row_text):
        """Locates the first table row containing the specified text."""
        return self.page.locator("table tbody tr").filter(has_text=row_text).first

    def click_row_action(self, row_text, action_title):
        """Locates a row containing row_text and clicks the button/icon with the given title."""
        row = self.get_row(row_text)
        row.wait_for(state="visible", timeout=5000)
        row.get_by_title(re.compile(re.escape(action_title), re.IGNORECASE)).first.click()

    def verify_cell_contains(self, row_text, cell_index, expected_value):
        """Asserts that a specific column cell in a row contains the expected value."""
        row = self.get_row(row_text)
        row.wait_for(state="visible", timeout=5000)
        cell = row.locator("td").nth(cell_index)
        cell_text = cell.text_content().strip()
        assert expected_value in cell_text, f"Expected '{expected_value}' in cell text '{cell_text}'"
        return True
