import filecmp

from jobwatcher import build
from jobwatcher.build import COLUMNS, build_history, write_history
from jobwatcher.rawio import write_raw

from conftest import cfg, posting


def by_id(rows):
    return {r["posting_id"]: r for r in rows}


def test_first_seen_and_last_seen(raw):
    raw("2026-11-01", ["a", "b"])
    raw("2026-11-02", ["a", "b", "c"])
    raw("2026-11-03", ["a", "c"])
    rows = by_id(build_history(raw.dir))
    assert rows["acme:a"]["first_seen"] == "2026-11-01"
    assert rows["acme:a"]["last_seen"] == "2026-11-03"
    assert rows["acme:c"]["first_seen"] == "2026-11-02"
    assert rows["acme:c"]["last_seen"] == "2026-11-03"
    assert rows["acme:a"]["status"] == "open" and rows["acme:a"]["removed_date"] == ""


def test_posting_no_longer_listed_is_removed_with_that_days_date(raw):
    raw("2026-11-01", ["a", "b"])
    raw("2026-11-02", ["a"])
    raw("2026-11-03", ["a"])
    b = by_id(build_history(raw.dir))["acme:b"]
    assert b["status"] == "removed"
    assert b["removed_date"] == "2026-11-02"  # the first day it was missing
    assert b["last_seen"] == "2026-11-01"


def test_removed_date_is_not_moved_on_later_days(raw):
    raw("2026-11-01", ["a", "b"])
    raw("2026-11-02", ["a"])
    raw("2026-11-05", ["a"])
    assert by_id(build_history(raw.dir))["acme:b"]["removed_date"] == "2026-11-02"


def test_reappearing_posting_becomes_open_again(raw):
    raw("2026-11-01", ["a", "b"])
    raw("2026-11-02", ["a"])
    raw("2026-11-03", ["a", "b"])
    b = by_id(build_history(raw.dir))["acme:b"]
    assert b["status"] == "open"
    assert b["removed_date"] == ""
    assert b["first_seen"] == "2026-11-01"  # unchanged
    assert b["last_seen"] == "2026-11-03"


def test_failed_source_day_changes_nothing(raw):
    """A source with no raw file on a day must not have its postings marked removed."""
    raw("2026-11-01", ["a"], source="acme")
    raw("2026-11-01", ["x"], source="beta")
    raw("2026-11-02", ["x"], source="beta")  # acme failed: no file
    raw("2026-11-03", ["a"], source="acme")
    raw("2026-11-03", ["x"], source="beta")
    rows = by_id(build_history(raw.dir))
    assert rows["acme:a"]["status"] == "open"
    assert rows["acme:a"]["removed_date"] == ""
    assert rows["acme:a"]["last_seen"] == "2026-11-03"


def test_removal_in_one_source_does_not_touch_another(raw):
    raw("2026-11-01", ["a"], source="acme")
    raw("2026-11-01", ["x"], source="beta")
    raw("2026-11-02", [], source="acme")
    raw("2026-11-02", ["x"], source="beta")
    rows = by_id(build_history(raw.dir))
    assert rows["acme:a"]["status"] == "removed"
    assert rows["beta:x"]["status"] == "open"


def test_first_run_marks_postings_in_the_first_raw_file_of_each_source(raw):
    raw("2026-11-01", ["a"], source="acme")
    raw("2026-11-02", ["a", "b"], source="acme")
    raw("2026-11-02", ["x"], source="beta")  # beta starts watching a day later
    raw("2026-11-03", ["x", "y"], source="beta")
    rows = by_id(build_history(raw.dir))
    assert rows["acme:a"]["first_run"] == "true"
    assert rows["acme:b"]["first_run"] == "false"
    assert rows["beta:x"]["first_run"] == "true"
    assert rows["beta:y"]["first_run"] == "false"


def test_posting_that_comes_back_after_first_run_stays_first_run(raw):
    raw("2026-11-01", ["a"])
    raw("2026-11-02", [])
    raw("2026-11-03", ["a"])
    assert by_id(build_history(raw.dir))["acme:a"]["first_run"] == "true"


def test_rows_sorted_by_posting_id_and_columns_complete(raw):
    raw("2026-11-01", ["c", "a", "b"], source="zeta")
    raw("2026-11-01", ["m"], source="acme")
    rows = build_history(raw.dir)
    ids = [r["posting_id"] for r in rows]
    assert ids == sorted(ids)
    assert all(list(r) and set(r) == set(COLUMNS) for r in rows)


def test_duplicate_ids_in_one_file_count_once(tmp_path):
    write_raw(tmp_path, "2026-11-01", cfg(), [posting("a"), posting("a"), posting("b")])
    assert len(build_history(tmp_path)) == 2


def test_rebuilding_gives_the_same_file(raw, tmp_path_factory):
    raw("2026-11-01", ["a", "b"])
    raw("2026-11-02", ["a", "c"])
    out = tmp_path_factory.mktemp("out")
    write_history(build_history(raw.dir), out / "one.csv")
    write_history(build_history(raw.dir), out / "two.csv")
    assert filecmp.cmp(out / "one.csv", out / "two.csv", shallow=False)


def test_a_rule_change_applies_to_every_day_of_the_history(raw, monkeypatch):
    raw("2026-11-01", ["a"], titles={"a": "Financial Analyst"})
    raw("2026-11-02", ["a"], titles={"a": "Financial Analyst"})
    assert by_id(build_history(raw.dir))["acme:a"]["in_role"] == "true"
    monkeypatch.setattr(build, "in_role", lambda title: False)
    assert by_id(build_history(raw.dir))["acme:a"]["in_role"] == "false"


def test_latest_title_wins_and_in_role_follows_it(raw):
    raw("2026-11-01", ["a"], titles={"a": "Senior Financial Analyst"})
    raw("2026-11-02", ["a"], titles={"a": "Financial Analyst"})
    row = by_id(build_history(raw.dir))["acme:a"]
    assert row["title"] == "Financial Analyst" and row["in_role"] == "true"


def test_empty_raw_dir_gives_empty_history(tmp_path):
    assert build_history(tmp_path / "missing") == []


def test_csv_round_trip_keeps_commas_and_quotes(tmp_path):
    write_raw(tmp_path / "raw", "2026-11-01", cfg(),
              [posting("a", title='Analyst, "FP&A", Wealth')])
    rows = build_history(tmp_path / "raw")
    write_history(rows, tmp_path / "h.csv")
    assert build.read_history(tmp_path / "h.csv")[0]["title"] == 'Analyst, "FP&A", Wealth'
