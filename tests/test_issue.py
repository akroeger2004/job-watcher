"""How the daily issue is created, updated and the previous one closed (gh is faked)."""
import json

import pytest

from jobwatcher import issue


@pytest.fixture
def gh(monkeypatch):
    """Fake the gh CLI: returns the given issue list and records every other call."""
    state = {"issues": [], "calls": []}

    def fake(args, body=None):
        if args[:2] == ["issue", "list"]:
            return json.dumps(state["issues"])
        state["calls"].append((args, body))
        return "https://github.com/x/y/issues/9\n" if args[:2] == ["issue", "create"] else ""

    monkeypatch.setattr(issue, "_gh", fake)
    return state


def verbs(state):
    return [(c[0][1], c[0][2] if len(c[0]) > 2 else None) for c in state["calls"]]


def test_new_day_opens_todays_issue_and_closes_the_previous_one(gh):
    gh["issues"] = [{"number": 4, "title": "2026-11-12", "state": "OPEN"},
                    {"number": 3, "title": "2026-11-11", "state": "CLOSED"},
                    {"number": 2, "title": "A bug someone filed", "state": "OPEN"}]
    issue.publish_issue("2026-11-13", "body text")
    create = [c for c in gh["calls"] if c[0][1] == "create"]
    assert len(create) == 1 and create[0][0][3] == "2026-11-13" and create[0][1] == "body text"
    assert ("close", "4") in verbs(gh)          # yesterday's issue is closed
    assert ("close", "2") not in verbs(gh)      # unrelated issues are left alone
    assert ("close", "3") not in verbs(gh)      # already closed


def test_second_run_on_the_same_day_updates_instead_of_creating(gh):
    gh["issues"] = [{"number": 7, "title": "2026-11-13", "state": "OPEN"}]
    issue.publish_issue("2026-11-13", "new body")
    assert [v[0] for v in verbs(gh)] == ["edit"]
    assert gh["calls"][0][1] == "new body"


def test_a_closed_issue_for_today_is_reopened_on_a_rerun(gh):
    gh["issues"] = [{"number": 7, "title": "2026-11-13", "state": "CLOSED"}]
    issue.publish_issue("2026-11-13", "again")
    assert ("edit", "7") in verbs(gh) and ("reopen", "7") in verbs(gh)
    assert not [c for c in gh["calls"] if c[0][1] == "create"]


def test_todays_issue_is_never_closed(gh):
    gh["issues"] = [{"number": 7, "title": "2026-11-13", "state": "OPEN"}]
    issue.publish_issue("2026-11-13", "x")
    assert ("close", "7") not in verbs(gh)
