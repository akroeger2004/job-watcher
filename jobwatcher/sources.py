"""Source definitions: how to call each employer's job board and how to convert
what it returns into the common columns.

Every source is described by plain data (ats + params). The params are stored in
the raw file next to the postings, so the history build can convert a raw file
without importing this list: the raw files alone are enough.

Supported applicant tracking systems (all return JSON with no login):
  workday  - POST {tenant}.wd{n}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
  oracle   - GET  {host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions
  ultipro  - POST recruiting.ultipro.com/{company}/JobBoard/{guid}/JobBoardView/LoadSearchResults
  jibe     - GET  {host}/api/jobs
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Fields every converter returns. The build adds employer, source, ids and dates.
CONVERTED = ("source_id", "title", "location", "department", "posted_date", "url")

SOURCES = [
    # --- Workday ---
    {"name": "blackrock", "employer": "BlackRock", "ats": "workday",
     "params": {"tenant": "blackrock", "wd": 1, "site": "BlackRock_Professional"}},
    {"name": "statestreet", "employer": "State Street", "ats": "workday",
     "params": {"tenant": "statestreet", "wd": 1, "site": "Global"}},
    {"name": "invesco", "employer": "Invesco", "ats": "workday",
     "params": {"tenant": "invesco", "wd": 1, "site": "IVZ"}},
    {"name": "troweprice", "employer": "T. Rowe Price", "ats": "workday",
     "params": {"tenant": "troweprice", "wd": 5, "site": "TRowePrice"}},
    {"name": "lpl", "employer": "LPL Financial", "ats": "workday",
     "params": {"tenant": "lplfinancial", "wd": 1, "site": "External"}},
    {"name": "broadridge", "employer": "Broadridge", "ats": "workday",
     "params": {"tenant": "broadridge", "wd": 5, "site": "Careers"}},
    {"name": "carlyle", "employer": "Carlyle", "ats": "workday",
     "params": {"tenant": "carlyle", "wd": 1, "site": "carlyle"}},
    {"name": "capitalone", "employer": "Capital One", "ats": "workday",
     "params": {"tenant": "capitalone", "wd": 12, "site": "Capital_One"}},
    {"name": "pnc", "employer": "PNC", "ats": "workday",
     "params": {"tenant": "pnc", "wd": 5, "site": "External"}},
    {"name": "texascapital", "employer": "Texas Capital Bank", "ats": "workday",
     "params": {"tenant": "texascapitalbank", "wd": 12, "site": "Careers"}},
    {"name": "tyson", "employer": "Tyson Foods", "ats": "workday",
     "params": {"tenant": "tysonfoods", "wd": 5, "site": "TSN"}},
    {"name": "cambridgeassociates", "employer": "Cambridge Associates", "ats": "workday",
     "params": {"tenant": "cambridgeassociates", "wd": 5, "site": "Cambridge_Associates"}},
    {"name": "marcusmillichap", "employer": "Marcus & Millichap", "ats": "workday",
     "params": {"tenant": "marcusmillichap", "wd": 108, "site": "MarcusMillichap"}},
    {"name": "fortress", "employer": "Fortress Investment Group", "ats": "workday",
     "params": {"tenant": "fortress", "wd": 503, "site": "Careers"}},
    # --- Oracle HCM (JPMorgan has more than 5,000 postings, so it is searched by term) ---
    {"name": "gmfinancial", "employer": "GM Financial", "ats": "oracle",
     "params": {"host": "fa-exvu-saasfaprod1.fa.ocs.oraclecloud.com", "site": "CX_1"}},
    {"name": "jpmorgan", "employer": "JPMorgan Chase", "ats": "oracle",
     "params": {"host": "jpmc.fa.oraclecloud.com", "site": "CX_1001",
                "terms": ["analyst", "associate"]}},
    # --- UKG UltiPro ---
    {"name": "stephens", "employer": "Stephens Inc.", "ats": "ultipro",
     "params": {"base": "https://recruiting2.ultipro.com/STE1004/JobBoard/"
                        "fbeef081-b55b-0ae3-a2ac-7b4fb3db6826"}},
    {"name": "welltower", "employer": "Welltower", "ats": "ultipro",
     "params": {"base": "https://recruiting.ultipro.com/WEL1008WLLT/JobBoard/"
                        "30969ce4-3b7e-40a6-b86c-34d3616fe0ed"}},
    # --- Jibe ---
    {"name": "firstcitizens", "employer": "First Citizens Bank", "ats": "jibe",
     "params": {"host": "jobs.firstcitizens.com"}},
]


# --------------------------------------------------------------------------- http


def http_json(url, body=None, headers=None, retries=5, timeout=60):
    """GET (or POST when body is given) and decode JSON, retrying transient errors."""
    hdrs = {"User-Agent": UA, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json; charset=utf-8"
    hdrs.update(headers or {})
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code < 500 and exc.code != 429:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
        time.sleep(3 * (attempt + 1))
    raise last


# ------------------------------------------------------------------------- fetch


def fetch_workday(params):
    t, n, site = params["tenant"], params["wd"], params["site"]
    url = f"https://{t}.wd{n}.myworkdayjobs.com/wday/cxs/{t}/{site}/jobs"
    out, seen = [], set()
    for term in params.get("terms") or [""]:
        offset, total = 0, None
        while total is None or offset < total:
            page = http_json(url, {"appliedFacets": {}, "limit": 20, "offset": offset,
                                   "searchText": term})
            if total is None:  # Workday only reports the total on the first page
                total = page.get("total", 0)
            rows = page.get("jobPostings") or []
            if not rows:
                break
            for row in rows:
                key = row.get("externalPath")
                if key and key not in seen:
                    seen.add(key)
                    out.append(row)
            offset += 20
    return out


def fetch_oracle(params):
    host, site = params["host"], params["site"]
    base = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    out, seen = [], set()
    for term in params.get("terms") or [""]:
        offset, total, limit = 0, None, 200
        while total is None or offset < total:
            finder = f"findReqs;siteNumber={site},limit={limit},offset={offset}," \
                     f"sortBy=POSTING_DATES_DESC"
            if term:
                finder += f",keyword={term}"
            query = urllib.parse.urlencode(
                {"onlyData": "true", "expand": "requisitionList.secondaryLocations",
                 "finder": finder}, safe=";,=")
            item = http_json(f"{base}?{query}")["items"][0]
            if total is None:
                total = item.get("TotalJobsCount", 0)
            rows = item.get("requisitionList") or []
            if not rows:
                break
            for row in rows:
                row.pop("ShortDescriptionStr", None)  # large text, not used
                if row.get("Id") not in seen:
                    seen.add(row.get("Id"))
                    out.append(row)
            offset += limit
    return out


def fetch_ultipro(params):
    url = params["base"] + "/JobBoardView/LoadSearchResults"
    out, seen, skip, top, total = [], set(), 0, 50, None
    while total is None or skip < total:
        body = {
            "opportunitySearch": {
                "Top": top, "Skip": skip, "QueryString": "",
                "OrderBy": [{"Value": "postedDateDesc", "PropertyName": "PostedDate",
                             "Ascending": False}],
                "Filters": [],
            },
            "matchCriteria": {"PreferredJobs": [], "Educations": [],
                              "LicenseAndCertifications": [], "Skills": [],
                              "hasNoLicenses": False, "SkippedSkills": []},
        }
        page = http_json(url, body)
        if total is None:
            total = page.get("totalCount", 0)
        rows = page.get("opportunities") or []
        if not rows:
            break
        for row in rows:
            if row.get("Id") not in seen:
                seen.add(row.get("Id"))
                out.append(row)
        skip += top
    return out


def fetch_jibe(params):
    host = params["host"]
    out, seen, page_no, total = [], set(), 1, None
    while total is None or len(seen) < total:
        page = http_json(f"https://{host}/api/jobs?page={page_no}&limit=100")
        if total is None:
            total = page.get("totalCount", 0)
        rows = page.get("jobs") or []
        if not rows:
            break
        for row in rows:
            data = row.get("data") or {}
            for big in ("description", "qualifications", "responsibilities"):
                data.pop(big, None)  # large HTML, not used
            key = data.get("req_id") or data.get("slug")
            if key not in seen:
                seen.add(key)
                out.append(row)
        page_no += 1
    return out


FETCHERS = {"workday": fetch_workday, "oracle": fetch_oracle,
            "ultipro": fetch_ultipro, "jibe": fetch_jibe}


def fetch(source):
    """Return the postings a source's board lists right now."""
    return FETCHERS[source["ats"]](source["params"])


# ----------------------------------------------------------------------- convert

_POSTED_ON = re.compile(r"posted\s+(today|yesterday|(\d+)\+?\s+days?\s+ago)", re.I)


def workday_posted_date(text, run_date):
    """Workday gives a relative age. '30+ Days Ago' has no usable date."""
    m = _POSTED_ON.search(text or "")
    if not m or "+" in m.group(1):
        return ""
    word = m.group(1).lower()
    days = 0 if word == "today" else 1 if word == "yesterday" else int(m.group(2))
    return (run_date - timedelta(days=days)).isoformat()


def convert_workday(posting, params, run_date):
    path = posting["externalPath"]
    bullets = posting.get("bulletFields") or []
    source_id = bullets[0] if bullets else path.rsplit("_", 1)[-1]
    location = posting.get("locationsText") or ""
    if re.fullmatch(r"\d+ Locations?", location.strip()):
        location = "Multiple locations"
    t, n, site = params["tenant"], params["wd"], params["site"]
    return {
        "source_id": source_id,
        "title": (posting.get("title") or "").strip(),
        "location": location.strip(),
        "department": "",
        "posted_date": workday_posted_date(posting.get("postedOn"), run_date),
        "url": f"https://{t}.wd{n}.myworkdayjobs.com/en-US/{site}{path}",
    }


def convert_oracle(posting, params, run_date):
    return {
        "source_id": str(posting["Id"]),
        "title": (posting.get("Title") or "").strip(),
        "location": (posting.get("PrimaryLocation") or "").strip(),
        "department": (posting.get("JobFamily") or posting.get("Department") or "").strip(),
        "posted_date": (posting.get("PostedDate") or "")[:10],
        "url": f"https://{params['host']}/hcmUI/CandidateExperience/en/sites/"
               f"{params['site']}/job/{posting['Id']}",
    }


def convert_ultipro(posting, params, run_date):
    places = []
    for loc in posting.get("Locations") or []:
        addr = loc.get("Address") or {}
        city = addr.get("City") or ""
        state = (addr.get("State") or {}).get("Code") or ""
        text = ", ".join(x for x in (city, state) if x) or loc.get("LocalizedDescription") or ""
        if text and text not in places:
            places.append(text)
    return {
        "source_id": posting["Id"],
        "title": (posting.get("Title") or "").strip(),
        "location": "; ".join(places),
        "department": (posting.get("JobCategoryName") or "").strip(),
        "posted_date": (posting.get("PostedDate") or "")[:10],
        "url": f"{params['base']}/OpportunityDetail?opportunityId={posting['Id']}",
    }


def convert_jibe(posting, params, run_date):
    data = posting.get("data") or posting
    cats = data.get("categories") or []
    department = data.get("department") or (cats[0].get("name") if cats else "") or ""
    location = data.get("full_location") or ", ".join(
        x for x in (data.get("city"), data.get("state")) if x)
    return {
        "source_id": str(data.get("req_id") or data["slug"]),
        "title": (data.get("title") or "").strip(),
        "location": (location or "").strip(),
        "department": department.strip(),
        "posted_date": (data.get("posted_date") or "")[:10],
        "url": f"https://{params['host']}/jobs/{data['slug']}",
    }


CONVERTERS = {"workday": convert_workday, "oracle": convert_oracle,
              "ultipro": convert_ultipro, "jibe": convert_jibe}


def convert(ats, posting, params, run_date):
    """Convert one raw posting to the common columns (see CONVERTED)."""
    return CONVERTERS[ats](posting, params, run_date)
