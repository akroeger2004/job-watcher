"""The Market page groups spellings of the same place; assets/calc.js is run under Node."""
import json
import subprocess
from pathlib import Path

import pytest

from test_market_calc import NODE

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")


def run(expr):
    script = ("const C=require(process.argv[1]);"
              f"console.log(JSON.stringify({expr}));")
    out = subprocess.run(NODE + ["-e", script, str(ROOT / "assets" / "calc.js")],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def rows(locations):
    return "[" + ",".join(f"{{status:'open',in_role:false,location:{json.dumps(s)}}}" for s in locations) + "]"


def test_top_locations_group_spellings_of_the_same_place():
    top = run(f"C.topLocations({rows(['McLean VA (+3 more)', 'McLean, VA', 'McLean VA', 'Dallas, TX'])},{{n:5}})")
    assert top[0]["count"] == 3 and top[0]["name"].startswith("McLean")
    assert [t["count"] for t in top] == [3, 1]


def test_closed_postings_are_not_counted():
    removed = "{status:'removed',in_role:false,location:'Dallas, TX'}"
    top = run(f"C.topLocations([{{status:'open',in_role:false,location:'Dallas, TX'}},{removed}],{{n:5}})")
    assert top == [{"name": "Dallas, TX", "count": 1}]


def test_top_locations_merge_state_names_and_a_trailing_country():
    spellings = ["New York, NY", "New York, NY, United States", "New York, New York", "New York NY (+2 more)",
                 "Boston, Massachusetts", "Boston, MA"]
    top = run(f"C.topLocations({rows(spellings)},{{n:5}})")
    assert [(t["name"], t["count"]) for t in top] == [("New York, NY", 4), ("Boston, MA", 2)]


def test_top_locations_do_not_merge_different_cities_or_states():
    spellings = ["Arlington, TX", "Arlington, VA", "Washington, DC", "Washington, Washington"]
    assert len(run(f"C.topLocations({rows(spellings)},{{n:9}})")) == 4


def test_regions_filter_top_locations():
    spellings = ["Plano, TX", "Bentonville, AR", "Boston, MA"]
    assert [t["name"] for t in run(f"C.topLocations({rows(spellings)},{{region:'dfw',n:5}})")] == ["Plano, TX"]
    assert [t["name"] for t in run(f"C.topLocations({rows(spellings)},{{region:'nwa',n:5}})")] == ["Bentonville, AR"]
