"""The site shows US-based jobs by default. assets/calc.js decides what is in the United
States from the location text; these cases run that code under Node."""
import json
import subprocess
from pathlib import Path

import pytest

from test_market_calc import NODE

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is not installed")

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
    "Tbilisi, Georgia", "Multiple locations", "", "Bengaluru-EPIP Industrial Area",
    "Charlottetown, Prince Edward Island", "ON; BC", "Markham, ON", "Edmonton, Alberta, Canada",
    "Home Location - Ontario (CNH12)", "Toronto, ON, Canada", "Istanbul, Türkiye",
]


def run(expr):
    script = ("const C=require(process.argv[1]);"
              f"console.log(JSON.stringify({expr}));")
    out = subprocess.run(NODE + ["-e", script, str(ROOT / "assets" / "calc.js")],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_us_locations_are_recognised():
    got = run(f"{json.dumps(US)}.map(l=>C.isUS(l))")
    wrong = [l for l, g in zip(US, got) if not g]
    assert not wrong, f"treated as non-US: {wrong}"


def test_non_us_and_unknown_locations_are_excluded():
    got = run(f"{json.dumps(NOT_US)}.map(l=>C.isUS(l))")
    wrong = [l for l, g in zip(NOT_US, got) if g]
    assert not wrong, f"treated as US: {wrong}"


def test_us_is_a_region_and_composes_with_other_regions():
    assert run("[C.inRegion('Dallas, TX','us'),C.inRegion('London, United Kingdom','us'),"
               "C.inRegion('London, United Kingdom','all'),C.inRegion('Plano, TX','dfw')]") == [True, False, True, True]


def test_top_locations_group_spellings_of_the_same_place():
    rows = ("[{status:'open',in_role:false,location:'McLean VA (+3 more)'},"
            "{status:'open',in_role:false,location:'McLean, VA'},"
            "{status:'open',in_role:false,location:'McLean VA'},"
            "{status:'open',in_role:false,location:'Dallas, TX'},"
            "{status:'removed',in_role:false,location:'Dallas, TX'}]")
    top = run(f"C.topLocations({rows},{{n:5}})")
    assert top[0]["count"] == 3 and top[0]["name"].startswith("McLean")
    assert [t["count"] for t in top] == [3, 1]


def test_top_locations_merge_state_names_and_a_trailing_country():
    spellings = ["New York, NY", "New York, NY, United States", "New York, New York", "New York NY (+2 more)",
                 "Boston, Massachusetts", "Boston, MA"]
    rows = "[" + ",".join(f"{{status:'open',in_role:false,location:{json.dumps(s)}}}" for s in spellings) + "]"
    top = run(f"C.topLocations({rows},{{n:5}})")
    assert [(t["name"], t["count"]) for t in top] == [("New York, NY", 4), ("Boston, MA", 2)]


def test_top_locations_do_not_merge_different_cities_or_states():
    rows = ("[{status:'open',in_role:false,location:'Arlington, TX'},"
            "{status:'open',in_role:false,location:'Arlington, VA'},"
            "{status:'open',in_role:false,location:'Washington, DC'},"
            "{status:'open',in_role:false,location:'Washington, Washington'}]")
    assert len(run(f"C.topLocations({rows},{{n:9}})")) == 4
