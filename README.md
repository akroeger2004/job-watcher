# Job Watcher

[![tests](https://github.com/akroeger2004/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/akroeger2004/job-watcher/actions/workflows/tests.yml)
[![daily](https://github.com/akroeger2004/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/akroeger2004/job-watcher/actions/workflows/daily.yml)

A tool that watches the job market for **entry-level FP&A and wealth management roles** (the
kind a new graduate applies to), with extra attention to **Dallas-Fort Worth** and
**Northwest Arkansas** as well as national employers. Every day, on its own, it pulls the open
postings at 19 employers, compares them with the day before, records what is new and what is
gone, and publishes the result to a website.

Live site: <https://akroeger2004.github.io/job-watcher/>

Financial Data Analytics course project. Built with Claude Code.

## How it works

1. A GitHub Actions workflow (`daily.yml`) runs once a day.
2. `jobwatcher/pipeline.py` calls every source and saves what it returns, compressed, to
   `data/raw/<date>/<source>.json.gz`. A source that fails writes no file that day; the failure
   is recorded in `data/status.json` and the run carries on.
3. `jobwatcher/build.py` builds `data/history.csv` from the raw files alone.
4. The pipeline writes `data/status.json` and opens a GitHub Issue titled with the date that
   lists the new and removed postings (each with a link), then closes the previous day's issue.
   The issue is opened every day, even when nothing changed.
5. The workflow commits the raw files, the history and the status to the repository, and
   GitHub Pages serves the site from the repository root.

A successful run is one that finishes and commits, even when some sources failed. A second run
on the same day replaces that day's raw files, rebuilds the history and updates that day's issue,
so each day counts once.

## Build the history from the raw files

```
python -m jobwatcher.build
```

This reads only `data/raw/` and rewrites `data/history.csv`. Running it again produces the same
file, and a change to the title rule applies to every day of the history.

Rules used for each day with raw files, in date order, for each source that has a file that day:

- A posting seen for the first time gets that day as `first_seen`.
- Every posting the source lists gets that day as `last_seen`. If it had been removed it becomes
  open again, `removed_date` is cleared and `first_seen` is unchanged.
- An open posting the source no longer lists is marked `removed` with that day's date.
- A source with no raw file that day (it failed) changes nothing that day.
- Rows are sorted by `posting_id`. `first_run` is true for postings listed in the first raw file
  of their source.

## Sources (19 employers, 4 applicant tracking systems)

All of them return JSON to a request made with no login. No HTML is read.

| Employer | Applicant tracking system | Area |
|---|---|---|
| BlackRock | Workday | National |
| State Street | Workday | National |
| Invesco | Workday | National |
| T. Rowe Price | Workday | National |
| LPL Financial | Workday | National |
| Broadridge | Workday | National |
| Carlyle | Workday | National |
| Capital One | Workday | National |
| PNC | Workday | National |
| Cambridge Associates | Workday | National |
| Marcus & Millichap | Workday | National |
| Fortress Investment Group | Workday | National |
| Texas Capital Bank | Workday | Dallas |
| Tyson Foods | Workday | Northwest Arkansas |
| GM Financial | Oracle HCM | Fort Worth |
| JPMorgan Chase | Oracle HCM | National |
| Stephens Inc. | UKG UltiPro | Little Rock |
| Welltower | UKG UltiPro | National |
| First Citizens Bank | Jibe | National |

**Search terms.** JPMorgan Chase's board returns more than 5,000 postings (7,010 when this was
checked), so it is requested with search terms instead of in full: **`analyst`** and
**`associate`** (the two are requested separately and the results combined). Every other board
is read in full. Large text fields (job descriptions) are dropped from the raw files to keep the
repository small.

Employers that were tried and left out because their board has no login-free JSON feed: Walmart
(its Workday endpoint rejects requests), Lockheed Martin (HTML only) and Hilltop (empty feed).

## The title rule

`in_role` marks a posting as in my role. The rule lives in `jobwatcher/role.py` and is tested in
`tests/test_role.py`. A title is in the role when **all** of these hold:

1. It names a role keyword: FP&A, financial planning and analysis, financial/finance analyst or
   associate, business finance, corporate or strategic finance, financial reporting, treasury
   analyst, investment analyst or associate, portfolio analyst, wealth, financial advisor or
   planner, private client, private bank, client associate, STARs analyst, and similar.
2. It carries a junior signal: analyst, associate, trainee, rotational, graduate, early career,
   entry level, junior, a development or leadership program, or level I / II.
3. It carries **no** senior signal (senior, Sr., principal, director, VP/AVP/SVP, managing, head,
   lead, chief, staff, executive, manager, partner, level III or higher) and is not an engineering
   or internship title (software, engineer, developer, intern, co-op, recruiter, compliance, ...).

Every posting the employer's board returns is kept in the history; the rule only sets `in_role`.

## Files

| File | What it does |
|---|---|
| `jobwatcher/sources.py` | The 19 sources, how to call each applicant tracking system, and the conversion of each to the common columns |
| `jobwatcher/role.py` | The title rule |
| `jobwatcher/rawio.py` | Writes and reads the compressed raw files |
| `jobwatcher/build.py` | Builds `data/history.csv` from the raw files (`python -m jobwatcher.build`) |
| `jobwatcher/status.py` | Builds `data/status.json` |
| `jobwatcher/issue.py` | Writes and publishes the daily GitHub Issue |
| `jobwatcher/pipeline.py` | The daily run (`python -m jobwatcher.pipeline --issue`) |
| `jobwatcher/__init__.py` | Marks `jobwatcher` as a Python package |
| `tests/conftest.py` | Shared test helpers for building raw files |
| `tests/test_role.py` | Tests of the title rule |
| `tests/test_sources.py` | Tests of the conversion of each source to the common columns and of the fetchers |
| `tests/test_history.py` | Tests of the first-seen, last-seen, removed and first-run logic and of the deterministic build |
| `tests/test_pipeline.py` | Tests of the daily run: failed sources, status counts, same-day re-runs and issue text |
| `tests/test_issue.py` | Tests of how the daily GitHub Issue is created, updated, reopened and the previous one closed |
| `tests/test_market_calc.py` | Runs `assets/calc.js` under Node and checks every Market number against Python |
| `pyproject.toml` | Project metadata and pytest settings |
| `.gitignore`, `.gitattributes` | Ignore rules and line-ending rules (raw `.gz` files are binary) |
| `data/raw/.gitkeep` | Keeps the raw data folder in the repository |
| `README.md` | This file |
| `.github/workflows/daily.yml` | Runs the pipeline every day and commits the data |
| `.github/workflows/tests.yml` | Runs the tests on every push |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day |
| `data/history.csv` | One row per posting (see columns below) |
| `data/status.json` | Describes the latest run |
| `index.html` | Today page: last run, source status, counts, new and removed postings |
| `browse.html` | Browse page: open postings, role switch, region, filters, search, sort, shortlist |
| `market.html` | Market page: six sections computed in the browser from the history file |
| `assets/calc.js` | The Market calculations (pure functions, also run under Node by the tests) |
| `assets/common.js`, `assets/charts.js`, `assets/style.css` | Shared navigation, data loading, charts and styles |
| `assets/today.js`, `assets/browse.js`, `assets/market.js` | Page scripts |
| `sw.js`, `manifest.webmanifest`, `icons/` | Make the site installable and usable offline |
| `tools/make_icons.py` | Draws the app icons |

## Data files

`data/history.csv` columns: `posting_id` (source and the source's own ID), `source`, `source_id`,
`employer`, `title`, `location`, `department`, `posted_date`, `url`, `in_role`, `first_run`,
`first_seen`, `last_seen`, `status` (`open` or `removed`), `removed_date`. Dates are UTC dates
(`YYYY-MM-DD`). A column a source does not provide is left empty for that source's rows (for
example Workday has no department, and its "30+ days ago" has no posted date).

`data/status.json` keys: `run_time`, `first_run_date`, `days_with_success`, `open`, `new_today`
(first seen in the latest run, leaving out first-run postings), `removed_today`, and `sources`
(one entry per source with `name`, `ok` and `count`).

## Run it yourself

```
python -m pip install pytest
python -m pytest -q                     # tests
python -m jobwatcher.pipeline           # fetch everything and rebuild (about 10 minutes)
python -m jobwatcher.build              # rebuild the history from data/raw only
python -m http.server 8000              # then open http://localhost:8000
```

Python 3.11 or later. The pipeline uses only the standard library.
