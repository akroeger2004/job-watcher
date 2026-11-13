import json
from datetime import datetime, timezone

from jobwatcher import pipeline
from jobwatcher.build import build_history
from jobwatcher.issue import MAX_BODY, render_issue
from jobwatcher.rawio import list_raw
from jobwatcher.status import make_status

from conftest import cfg, posting

A, B = cfg("acme", "Acme"), cfg("beta", "Beta")


def at(day, hour=12):
    y, m, d = map(int, day.split("-"))
    return datetime(y, m, d, hour, 0, 0, tzinfo=timezone.utc)


def fake_fetcher(table, failing=()):
    def fetch(src):
        if src["name"] in failing:
            raise OSError("boom")
        return [posting(i) for i in table[src["name"]]]
    return fetch


def test_failed_source_writes_no_file_but_run_still_succeeds(tmp_path):
    status = pipeline.run([A, B], fake_fetcher({"acme": ["a"], "beta": ["x"]}, failing={"beta"}),
                          tmp_path, now=at("2026-11-01"))
    assert sorted(list_raw(tmp_path / "raw")["2026-11-01"]) == ["acme"]
    assert status["sources"] == [{"name": "acme", "ok": True, "count": 1},
                                 {"name": "beta", "ok": False, "count": 0}]
    assert (tmp_path / "history.csv").exists() and (tmp_path / "status.json").exists()


def test_status_keys_and_counts(tmp_path):
    pipeline.run([A], fake_fetcher({"acme": ["a", "b"]}), tmp_path, now=at("2026-11-01"))
    pipeline.run([A], fake_fetcher({"acme": ["a", "c", "d"]}), tmp_path, now=at("2026-11-02"))
    status = json.loads((tmp_path / "status.json").read_text())
    assert set(status) == {"run_time", "first_run_date", "days_with_success", "open",
                           "new_today", "removed_today", "sources"}
    assert status["run_time"] == "2026-11-02T12:00:00Z"
    assert status["first_run_date"] == "2026-11-01"
    assert status["days_with_success"] == 2
    assert status["open"] == 3          # a, c, d
    assert status["new_today"] == 2     # c, d (a and b were first-run postings)
    assert status["removed_today"] == 1  # b


def test_first_run_postings_are_not_counted_as_new(tmp_path):
    status = pipeline.run([A], fake_fetcher({"acme": ["a", "b", "c"]}), tmp_path,
                          now=at("2026-11-01"))
    assert status["new_today"] == 0 and status["open"] == 3


def test_second_run_same_day_replaces_files_and_counts_the_day_once(tmp_path):
    pipeline.run([A], fake_fetcher({"acme": ["a"]}), tmp_path, now=at("2026-11-01", 8))
    status = pipeline.run([A], fake_fetcher({"acme": ["a", "b"]}), tmp_path,
                          now=at("2026-11-01", 20))
    assert status["days_with_success"] == 1
    rows = build_history(tmp_path / "raw")
    assert sorted(r["source_id"] for r in rows) == ["a", "b"]
    assert len(list_raw(tmp_path / "raw")["2026-11-01"]) == 1
    assert status["run_time"] == "2026-11-01T20:00:00Z"


def test_rerun_after_a_failure_keeps_the_days_earlier_file(tmp_path):
    pipeline.run([A], fake_fetcher({"acme": ["a"]}), tmp_path, now=at("2026-11-01", 8))
    status = pipeline.run([A], fake_fetcher({"acme": ["a"]}, failing={"acme"}), tmp_path,
                          now=at("2026-11-01", 20))
    assert status["sources"][0]["ok"] is False
    assert "acme" in list_raw(tmp_path / "raw")["2026-11-01"]


def test_history_is_rebuilt_from_raw_files_alone(tmp_path):
    pipeline.run([A], fake_fetcher({"acme": ["a", "b"]}), tmp_path, now=at("2026-11-01"))
    pipeline.run([A], fake_fetcher({"acme": ["a"]}), tmp_path, now=at("2026-11-02"))
    first = (tmp_path / "history.csv").read_bytes()
    (tmp_path / "history.csv").unlink()
    from jobwatcher.build import write_history
    write_history(build_history(tmp_path / "raw"), tmp_path / "history.csv")
    assert (tmp_path / "history.csv").read_bytes() == first


def test_make_status_with_no_raw_files(tmp_path):
    status = make_status([], tmp_path / "raw", "2026-11-01T00:00:00Z", [])
    assert status["days_with_success"] == 0 and status["open"] == 0


# ------------------------------------------------------------------------- issue


def _rows(n_new=2):
    base = {"employer": "Acme", "location": "Dallas, TX", "department": "", "in_role": "false",
            "first_run": "false", "removed_date": "", "status": "open"}
    new = [dict(base, posting_id=f"acme:{i}", title=f"Job [{i}]", url=f"https://x/{i}",
                first_seen="2026-11-02") for i in range(n_new)]
    gone = [dict(base, posting_id="acme:z", title="Gone", url="https://x/z",
                 first_seen="2026-11-01", removed_date="2026-11-02", status="removed")]
    return new + gone


STATUS = {"run_time": "2026-11-02T12:00:00Z", "open": 2, "days_with_success": 2,
          "sources": [{"name": "acme", "ok": True, "count": 3},
                      {"name": "beta", "ok": False, "count": 0}]}


def test_issue_is_titled_with_the_date_and_lists_links():
    title, body = render_issue("2026-11-02", _rows(), STATUS)
    assert title == "2026-11-02"
    assert "## New postings (2)" in body and "## Removed postings (1)" in body
    assert "[Job (0)](https://x/0)" in body  # brackets in titles are neutralised
    assert "[Gone](https://x/z)" in body
    assert "Sources that failed: beta" in body


def test_issue_is_still_produced_on_a_day_with_no_changes():
    title, body = render_issue("2026-11-02", [], STATUS)
    assert title == "2026-11-02"
    assert body.count("None.") == 2


def test_issue_puts_role_postings_first_and_stays_under_the_size_limit():
    rows = _rows(3000)
    rows[2999]["in_role"] = "true"
    rows[2999]["title"] = "Financial Analyst"
    title, body = render_issue("2026-11-02", rows, STATUS)
    assert len(body) < MAX_BODY + 5000
    assert body.index("Financial Analyst") < body.index("Job (0)")
    assert "…and" in body
