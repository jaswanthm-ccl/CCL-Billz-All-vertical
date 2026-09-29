"""Restaurant Daily Incentive Report integration coverage."""

import pytest

from pages.Verticals.Restaurant.accounting.daily_incentive_report_page import (
    DailyIncentiveReportPage,
)


pytestmark = pytest.mark.restaurant


def test_restaurant_daily_incentive_report_shows_eligible_sale(
    res_logged_in_page, res_incentive_sale
):
    report = DailyIncentiveReportPage(res_logged_in_page)
    report.navigate()
    state = res_incentive_sale
    data = report.filter_report(
        from_date=state["date"],
        to_date=state["date"],
        staff_name=state["employee"],
    )

    assert len(data["rows"]) == 1, data
    row = data["rows"][0]
    assert row["bills"] == state["bills"]
    assert report.amount(row["sales_amount"]) == state["sales"]
    assert report.amount(row["incentive_amount"]) == state["incentive"]
    assert data["totals"]["bills"] == state["bills"]
    assert report.get_table_rows(), "Daily Incentive UI did not render the API row"
