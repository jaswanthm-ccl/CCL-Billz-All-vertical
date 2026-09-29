"""Restaurant Monthly Incentive Report integration coverage."""

import pytest

from pages.Verticals.Restaurant.accounting.monthly_incentive_report_page import (
    MonthlyIncentiveReportPage,
)


pytestmark = pytest.mark.restaurant


def test_restaurant_monthly_incentive_report_shows_eligible_sale(
    res_logged_in_page, res_incentive_sale
):
    report = MonthlyIncentiveReportPage(res_logged_in_page)
    report.navigate()
    state = res_incentive_sale
    data = report.filter_report(
        from_date=state["date"],
        to_date=state["date"],
        staff_name=state["employee"],
    )

    assert len(data["rows"]) == 1, data
    row = data["rows"][0]
    assert row["month"] == state["month"]
    assert report.amount(row["sales_amount"]) == state["sales"]
    assert report.amount(row["incentive_amount"]) == state["incentive"]
    assert any(
        state["month"] in " ".join(cells) for cells in report.get_table_rows()
    )
