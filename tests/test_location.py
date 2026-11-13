"""The history keeps only US-based postings; jobwatcher/location.py decides from the text."""
import pytest

from jobwatcher.build import build_history
from jobwatcher.location import is_us
from jobwatcher.rawio import list_raw, read_raw, write_raw

US = [
    "Fort Worth, TX, United States", "Dallas, Texas", "Frisco, TX", "New York, NY",
    "McLean VA (+3 more)", "FL - Tampa (+8 more)", "PA - Pittsburgh - 15222",
    "Florence, South Carolina", "Corporate - Springdale, Arkansas", "Boston Massachusetts (+3 more)",
    "New York, New York", "Boston", "Dallas", "Tempe", "Fort Mill/Charlotte", "Charlotte",
    "London, KY",            # a US town that shares a foreign name
    "Paris, TX", "Dublin, OH", "Little Rock", "Bentonville, AR", "San Juan, PR",
    "Washington, DC", "Albuquerque, New Mexico", "Georgia", "Atlanta, Georgia",
    "Remote - United States", "Austin, TX, United States", "Ontario, CA",
    "Storm Lake Turkey Plant - Storm Lake, Iowa", "Franklin Building - Chicago (IL016)",
    "SF4-San Francisco - 400 Howard Street", "Fort MillCharlotte (+1 more)",
    "Two PNC Plaza PA374 (+3 more)", "Arlington", "Tysons Corner VA130 (+1 more)",
    "North Dallas Campus",
]
NOT_US = [
    "LONDON, LONDON, United Kingdom", "Mumbai, Maharashtra, India", "Hangzhou, China",
    "Toronto, ON", "Toronto, Ontario", "Nottingham,  Eng", "Bangalore, In", "London - 12 Arthur Street",
    "Cluj-Napoca - 3rd Emile Zola Street", "Singapore, Singapore", "Singapore", "Hong Kong",
    "Tokyo-To, Japan", "Edinburgh, Scotland", "Dublin 2, Ireland", "Mexico City, Mexico",
    "Sao Paulo, SP, Brazil", "Krakow Poland (+1 more)", "Frankfurt a. Main, Germany",
    "Metro Manila, National Capital Region, Philippines", "Sydney, NSW, Australia",
    "Tbilisi, Georgia", "Multiple locations", "", None, "Bengaluru-EPIP Industrial Area",
    "Charlottetown, Prince Edward Island", "ON; BC", "Markham, ON", "Edmonton, Alberta, Canada",
    "Home Location - Ontario (CNH12)", "Toronto, ON, Canada", "Istanbul, Türkiye",
]


@pytest.mark.parametrize("location", US)
def test_us_locations_are_recognised(location):
    assert is_us(location)


@pytest.mark.parametrize("location", NOT_US)
def test_non_us_and_unknown_locations_are_excluded(location):
    assert not is_us(location)


# ------------------------------------------------------- the history build


def jibe(pid, city):
    return {"data": {"slug": pid, "req_id": pid, "title": "Financial Analyst", "full_location": city}}


def source(name="acme"):
    return {"name": name, "employer": name.title(), "ats": "jibe", "params": {"host": f"jobs.{name}.test"}}


def test_history_keeps_only_us_postings_but_the_raw_file_keeps_everything(tmp_path):
    write_raw(tmp_path, "2026-11-01", source(),
              [jibe("a", "Dallas, TX"), jibe("b", "London, United Kingdom"), jibe("c", "Multiple locations")])
    assert [r["source_id"] for r in build_history(tmp_path)] == ["a"]
    kept = read_raw(list_raw(tmp_path)["2026-11-01"]["acme"])["postings"]
    assert len(kept) == 3  # nothing was thrown away at fetch time


def test_non_us_postings_are_never_tracked_so_never_removed(tmp_path):
    write_raw(tmp_path, "2026-11-01", source(), [jibe("a", "Dallas, TX"), jibe("b", "Mumbai, India")])
    write_raw(tmp_path, "2026-11-02", source(), [jibe("a", "Dallas, TX")])
    rows = {r["source_id"]: r for r in build_history(tmp_path)}
    assert set(rows) == {"a"} and rows["a"]["status"] == "open"


def test_a_posting_that_moves_into_the_us_is_tracked_from_that_day(tmp_path):
    write_raw(tmp_path, "2026-11-01", source(), [jibe("a", "Dallas, TX"), jibe("x", "Toronto, ON")])
    write_raw(tmp_path, "2026-11-02", source(), [jibe("a", "Dallas, TX"), jibe("x", "Plano, TX")])
    x = {r["source_id"]: r for r in build_history(tmp_path)}["x"]
    assert x["first_seen"] == "2026-11-02" and x["first_run"] == "false"


def test_changing_the_rule_applies_to_every_day_of_the_history(tmp_path, monkeypatch):
    from jobwatcher import build
    write_raw(tmp_path, "2026-11-01", source(), [jibe("a", "London, United Kingdom")])
    write_raw(tmp_path, "2026-11-02", source(), [jibe("a", "London, United Kingdom")])
    assert build_history(tmp_path) == []
    monkeypatch.setattr(build, "is_us", lambda location: True)
    assert len(build_history(tmp_path)) == 1
