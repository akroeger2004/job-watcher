"""The Market page computes its numbers in the browser with assets/calc.js. This test runs
that same file under Node and checks every number against an independent Python
implementation of the six definitions, on a randomized multi-day history."""
import json
import random
import shutil
import statistics
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

from jobwatcher.build import build_history, read_history, write_history
from jobwatcher.rawio import write_raw

ROOT = Path(__file__).resolve().parent.parent


def find_node():
    exe = shutil.which("node")
    if exe:
        return [exe]
    try:
        import nodejs_wheel.executable as nw
        return [str(Path(nw.__file__).with_name("node.exe" if (Path(nw.__file__).with_name("node.exe")).exists() else "node"))]
    except Exception:
        return None


NODE = find_node()
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")

SCRIPT = r"""
const Calc = require(process.argv[2]);
const fs = require('fs');
const rows = Calc.parseHistory(fs.readFileSync(process.argv[3], 'utf8'));
const last = Calc.lastRunDate(rows);
const days = Calc.daysOpen(rows);
console.log(JSON.stringify({
  rows: rows.length, last: last, first: Calc.firstDate(rows),
  newAll: Calc.newPerDay(rows, last, false), newRole: Calc.newPerDay(rows, last, true),
  removed: Calc.removedPerDay(rows, last),
  openAll: Calc.openByEmployer(rows, false), openRole: Calc.openByEmployer(rows, true),
  daysOpen: days.slice().sort(function (a, b) { return a - b; }), median: Calc.median(days),
  within7: Calc.removedWithinSeven(rows, last),
  topAll: Calc.topLocations(rows, { n: 5 }), topDfw: Calc.topLocations(rows, { region: 'dfw', n: 5 }),
  topRoleNwa: Calc.topLocations(rows, { region: 'nwa', roleOnly: true, n: 5 })
}));
"""

PLACES = ["Dallas, Texas", "Fort Worth, Texas", "Plano, Texas", "Bentonville, Arkansas",
          "Springdale, Arkansas", "Boston, Massachusetts", "New York, New York",
          "Arlington, Virginia", "Little Rock, Arkansas"]
TITLES = ["Financial Analyst", "Wealth Associate", "Senior Financial Analyst", "Software Engineer",
          "FP&A Analyst", "Teller", "Director of Finance", "Associate Wealth Advisor"]
EMPLOYERS = {"acme": "Acme Bank", "beta": "Beta Wealth", "gamma": "Gamma Capital"}


def make_history(tmp_path):
    rng = random.Random(7)
    start = date(2026, 11, 1)
    catalog = {s: [(f"{s}{i}", rng.choice(TITLES), rng.choice(PLACES)) for i in range(60)]
               for s in EMPLOYERS}
    live = {s: set(rng.sample(range(60), 25)) for s in EMPLOYERS}
    raw = tmp_path / "raw"
    for offset in range(25):
        day = (start + timedelta(days=offset)).isoformat()
        for s in EMPLOYERS:
            if s == "gamma" and offset < 6:
                continue  # a source that starts being watched later
            if rng.random() < 0.1:
                continue  # a failed source day
            for i in list(live[s]):
                if rng.random() < 0.12:
                    live[s].discard(i)
            for i in rng.sample(range(60), 4):
                live[s].add(i)  # new or returning postings
            postings = [{"data": {"slug": catalog[s][i][0], "req_id": catalog[s][i][0],
                                  "title": catalog[s][i][1], "full_location": catalog[s][i][2],
                                  "posted_date": day}} for i in sorted(live[s])]
            write_raw(raw, day, {"name": s, "employer": EMPLOYERS[s], "ats": "jibe",
                                 "params": {"host": f"jobs.{s}.test"}}, postings)
    path = tmp_path / "history.csv"
    write_history(build_history(raw), path)
    return path


# ---------------------------------------------------------- Python reference


def dnum(s):
    return date.fromisoformat(s).toordinal()


def ref(rows):
    for r in rows:
        r["in_role"] = r["in_role"] == "true"
        r["first_run"] = r["first_run"] == "true"
    last = max(max(r["last_seen"], r["first_seen"], r["removed_date"]) for r in rows)
    first = min(r["first_seen"] for r in rows)
    span = [(date.fromisoformat(first) + timedelta(days=i)).isoformat()
            for i in range(dnum(last) - dnum(first) + 1)]

    def per_day(sel, key):
        c = {}
        for r in rows:
            if sel(r) and r[key]:
                c[r[key]] = c.get(r[key], 0) + 1
        return {"days": span, "counts": [c.get(d, 0) for d in span]}

    def ranked(counter):
        return sorted(({"name": k, "count": v} for k, v in counter.items()),
                      key=lambda x: (-x["count"], x["name"]))

    def tally(sel, key):
        c = {}
        for r in rows:
            if sel(r):
                c[r[key]] = c.get(r[key], 0) + 1
        return c

    removed_rows = [r for r in rows if r["status"] == "removed" and r["removed_date"] and not r["first_run"]]
    days = sorted(dnum(r["removed_date"]) - dnum(r["first_seen"]) for r in removed_rows)
    eligible = [r for r in rows if not r["first_run"] and dnum(last) - dnum(r["first_seen"]) >= 7]
    quick = [r for r in eligible if r["status"] == "removed" and r["removed_date"]
             and dnum(r["removed_date"]) - dnum(r["first_seen"]) <= 7]
    dfw = ("dallas", "fort worth", "plano")
    nwa = ("bentonville", "springdale")
    return {
        "rows": len(rows), "last": last, "first": first,
        "newAll": per_day(lambda r: not r["first_run"], "first_seen"),
        "newRole": per_day(lambda r: not r["first_run"] and r["in_role"], "first_seen"),
        "removed": per_day(lambda r: True, "removed_date"),
        "openAll": ranked(tally(lambda r: r["status"] == "open", "employer")),
        "openRole": ranked(tally(lambda r: r["status"] == "open" and r["in_role"], "employer")),
        "daysOpen": days, "median": statistics.median(days) if days else None,
        "within7": {"eligible": len(eligible), "removed": len(quick),
                    "share": len(quick) / len(eligible) if eligible else None},
        "topAll": ranked(tally(lambda r: r["status"] == "open", "location"))[:5],
        "topDfw": ranked(tally(lambda r: r["status"] == "open" and any(k in r["location"].lower() for k in dfw), "location"))[:5],
        "topRoleNwa": ranked(tally(lambda r: r["status"] == "open" and r["in_role"] and any(k in r["location"].lower() for k in nwa), "location"))[:5],
    }


def test_browser_calculations_match_python_reference(tmp_path):
    history = make_history(tmp_path)
    script = tmp_path / "run.js"
    script.write_text(SCRIPT)
    out = subprocess.run(NODE + [str(script), str(ROOT / "assets" / "calc.js"), str(history)],
                         capture_output=True, text=True, check=True).stdout
    got = json.loads(out)
    want = ref(read_history(history))
    assert got["rows"] > 100  # the scenario is non-trivial
    assert want["daysOpen"] and want["within7"]["eligible"] > 0 and want["within7"]["removed"] > 0
    for key in want:
        if key == "within7":
            assert got[key]["eligible"] == want[key]["eligible"], key
            assert got[key]["removed"] == want[key]["removed"], key
            assert got[key]["share"] == pytest.approx(want[key]["share"]), key
        elif key == "median":
            assert got[key] == pytest.approx(want[key])
        else:
            assert got[key] == want[key], key
    # the headline "share" really is removed / eligible
    assert got["within7"]["share"] == got["within7"]["removed"] / got["within7"]["eligible"]


def test_csv_parser_handles_quotes_commas_and_blank_fields(tmp_path):
    script = tmp_path / "csv.js"
    script.write_text("const C=require(process.argv[2]);"
                      "console.log(JSON.stringify(C.parseCSV('a,b,c\\r\\n\"x, \"\"y\"\"\",,z\\n')));")
    out = subprocess.run(NODE + [str(script), str(ROOT / "assets" / "calc.js")],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [["a", "b", "c"], ['x, "y"', "", "z"]]
