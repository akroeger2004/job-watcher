from datetime import date

import pytest

from jobwatcher import sources
from jobwatcher.sources import CONVERTED, SOURCES, convert, workday_posted_date

RUN = date(2026, 11, 13)

WORKDAY = {"tenant": "tysonfoods", "wd": 5, "site": "TSN"}
ORACLE = {"host": "fa-exvu-saasfaprod1.fa.ocs.oraclecloud.com", "site": "CX_1"}
ULTIPRO = {"base": "https://recruiting.ultipro.com/WEL1008WLLT/JobBoard/abc"}
JIBE = {"host": "jobs.firstcitizens.com"}


def test_workday_conversion():
    posting = {
        "title": "Manager Procurement - Energy",
        "externalPath": "/job/Corporate---Springdale-Arkansas/Manager-Procurement---Energy_R0493843",
        "locationsText": "Corporate - Springdale, Arkansas",
        "postedOn": "Posted Yesterday",
        "bulletFields": ["R0493843"],
    }
    row = convert("workday", posting, WORKDAY, RUN)
    assert row == {
        "source_id": "R0493843",
        "title": "Manager Procurement - Energy",
        "location": "Corporate - Springdale, Arkansas",
        "department": "",
        "posted_date": "2026-11-12",
        "url": "https://tysonfoods.wd5.myworkdayjobs.com/en-US/TSN/job/"
               "Corporate---Springdale-Arkansas/Manager-Procurement---Energy_R0493843",
    }


def test_workday_falls_back_to_path_id_and_collapses_multiple_locations():
    posting = {"title": "Analyst", "externalPath": "/job/x/Analyst_R77-1",
               "locationsText": "3 Locations", "postedOn": "Posted 30+ Days Ago"}
    row = convert("workday", posting, WORKDAY, RUN)
    assert row["source_id"] == "R77-1"
    assert row["location"] == "Multiple locations"
    assert row["posted_date"] == ""  # 30+ days has no usable date


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Posted Today", "2026-11-13"),
        ("Posted Yesterday", "2026-11-12"),
        ("Posted 5 Days Ago", "2026-11-08"),
        ("Posted 30+ Days Ago", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_workday_posted_date(text, expected):
    assert workday_posted_date(text, RUN) == expected


def test_oracle_conversion():
    posting = {"Id": "261069", "Title": "Sr Financial Analyst - Financial Reporting",
               "PostedDate": "2026-11-12", "PrimaryLocation": "Fort Worth, TX, United States",
               "JobFamily": None, "Department": None}
    row = convert("oracle", posting, ORACLE, RUN)
    assert row["source_id"] == "261069"
    assert row["location"] == "Fort Worth, TX, United States"
    assert row["department"] == ""
    assert row["posted_date"] == "2026-11-12"
    assert row["url"] == ("https://fa-exvu-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/"
                          "CandidateExperience/en/sites/CX_1/job/261069")


def test_oracle_uses_job_family_as_department():
    posting = {"Id": 5, "Title": "Analyst", "PrimaryLocation": "New York, NY",
               "JobFamily": "Finance", "PostedDate": "2026-11-13"}
    assert convert("oracle", posting, ORACLE, RUN)["department"] == "Finance"


def test_ultipro_conversion_joins_distinct_locations():
    posting = {
        "Id": "e3acb0c3", "Title": "Human Capital Technology Analyst",
        "JobCategoryName": "Indiv Contributor-Slry", "PostedDate": "2026-11-13T17:21:20.021Z",
        "Locations": [
            {"Address": {"City": "Frisco", "State": {"Code": "TX"}}},
            {"Address": {"City": "Frisco", "State": {"Code": "TX"}}},
            {"Address": {"City": "Toledo", "State": {"Code": "OH"}}},
        ],
    }
    row = convert("ultipro", posting, ULTIPRO, RUN)
    assert row["location"] == "Frisco, TX; Toledo, OH"
    assert row["department"] == "Indiv Contributor-Slry"
    assert row["posted_date"] == "2026-11-13"
    assert row["url"].endswith("/OpportunityDetail?opportunityId=e3acb0c3")


def test_jibe_conversion():
    posting = {"data": {
        "slug": "36596", "req_id": "36596", "title": "Sales & Service Representative (Teller)",
        "full_location": "Florence, South Carolina", "categories": [{"name": "Branch Sales"}],
        "department": "", "posted_date": "2026-11-13T19:52:00+0000"}}
    row = convert("jibe", posting, JIBE, RUN)
    assert row == {
        "source_id": "36596",
        "title": "Sales & Service Representative (Teller)",
        "location": "Florence, South Carolina",
        "department": "Branch Sales",
        "posted_date": "2026-11-13",
        "url": "https://jobs.firstcitizens.com/jobs/36596",
    }


def test_missing_optional_columns_are_empty_strings():
    row = convert("jibe", {"data": {"slug": "9", "title": "Analyst"}}, JIBE, RUN)
    assert row["location"] == "" and row["department"] == "" and row["posted_date"] == ""


@pytest.mark.parametrize("ats", sorted(sources.CONVERTERS))
def test_every_converter_returns_exactly_the_common_columns(ats):
    sample = {
        "workday": {"title": "A", "externalPath": "/job/a/A_R1"},
        "oracle": {"Id": 1, "Title": "A"},
        "ultipro": {"Id": "u1", "Title": "A"},
        "jibe": {"data": {"slug": "1", "title": "A"}},
    }[ats]
    params = {"workday": WORKDAY, "oracle": ORACLE, "ultipro": ULTIPRO, "jibe": JIBE}[ats]
    assert tuple(convert(ats, sample, params, RUN)) == CONVERTED


def test_source_list_meets_the_assignment_minimums():
    assert len(SOURCES) >= 15
    assert len({s["name"] for s in SOURCES}) == len(SOURCES)
    assert len({s["ats"] for s in SOURCES}) >= 2
    assert {s["ats"] for s in SOURCES} <= set(sources.FETCHERS)


def test_fetch_workday_pages_until_total_and_dedupes(monkeypatch):
    pages = {
        0: {"total": 25, "jobPostings": [{"externalPath": "/a"}, {"externalPath": "/b"}]},
        20: {"total": 0, "jobPostings": [{"externalPath": "/b"}, {"externalPath": "/c"}]},
    }
    seen_offsets = []

    def fake(url, body=None, **kw):
        seen_offsets.append(body["offset"])
        return pages[body["offset"]]

    monkeypatch.setattr(sources, "http_json", fake)
    rows = sources.fetch_workday(WORKDAY)
    assert [r["externalPath"] for r in rows] == ["/a", "/b", "/c"]
    assert seen_offsets == [0, 20]  # total came from the first page only


def test_fetch_oracle_drops_description_and_pages(monkeypatch):
    def fake(url, **kw):
        assert "limit=200" in url
        return {"items": [{"TotalJobsCount": 1, "requisitionList": [
            {"Id": "1", "Title": "A", "ShortDescriptionStr": "x" * 1000}]}]}

    monkeypatch.setattr(sources, "http_json", fake)
    rows = sources.fetch_oracle(ORACLE)
    assert rows == [{"Id": "1", "Title": "A"}]


def test_fetch_oracle_searches_each_term(monkeypatch):
    urls = []

    def fake(url, **kw):
        urls.append(url)
        n = "1" if "keyword=analyst" in url else "2"
        return {"items": [{"TotalJobsCount": 1, "requisitionList": [{"Id": n, "Title": "T"}]}]}

    monkeypatch.setattr(sources, "http_json", fake)
    rows = sources.fetch_oracle({**ORACLE, "terms": ["analyst", "associate"]})
    assert sorted(r["Id"] for r in rows) == ["1", "2"]
    assert any("keyword=associate" in u for u in urls)
