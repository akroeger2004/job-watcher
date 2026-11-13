import pytest

from jobwatcher.role import in_role


@pytest.mark.parametrize(
    "title",
    [
        "Associate, FP&A Tech & Ops",
        "Associate, Financial Planning & Analysis - Private Markets",
        "Financial Planning & Analytics (FP&A) Analyst",
        "Finance (FP&A) Analyst - 12 month fixed-term contract",
        "Financial Analyst (Hybrid - NYC, Newark, NJ, Edgewood, NY)",
        "Wealth Associate",
        "Associate Wealth Advisor - Salal Credit Union",
        "Financial Advisor Development Program",
        "2027 STARs Analyst (Full Time)",
        "Investment Analyst/Associate, Secondaries",
        "Finance Analyst Level 2",
        "Financial Analyst II",
    ],
)
def test_entry_level_fpa_and_wealth_titles_match(title):
    assert in_role(title)


@pytest.mark.parametrize(
    "title",
    [
        "Sr. Finance Analyst-FinOps",
        "Sr Financial Analyst - Financial Reporting",
        "Senior Financial Analyst, GM Energy",
        "Lead Financial Analyst - FP&A",
        "Lead Portfolio Investment Analyst - Equities",
        "Principal Financial Analyst",
        "Manager, Financial Planning & Analysis - Capital One Auto",
        "Vice President, Portfolio Finance - GIP",
        "Associate Regional Consultant, Model Portfolios - US Wealth, AVP",
        "Financial Analyst, Level 3",
        "Finance Analyst Senior - Level 3",
        "Staff Financial Analyst Level 4",
        "Investment Analyst MBA Intern, Robinhood Ventures (Summer 2027)",
        "Intern - Corporate Treasury",
        "Software Engineer, Wealth Platform",
        "Wealth Management Director",
        "Wealth Advisor",
        "Claims Quality Improvement Analyst",
        "Packer Labor 1st shift",
        "",
        None,
    ],
)
def test_senior_unrelated_and_internship_titles_do_not_match(title):
    assert not in_role(title)


def test_rule_is_case_insensitive():
    assert in_role("FINANCIAL ANALYST")
    assert not in_role("SR FINANCIAL ANALYST")


def test_sr_with_period_is_senior():
    # the abbreviation followed by a period and a space must still be caught
    assert not in_role("Sr. Associate, Financial Analyst")
