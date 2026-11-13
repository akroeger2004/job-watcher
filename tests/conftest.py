import pytest

from jobwatcher.rawio import write_raw


def cfg(name="acme", employer="Acme"):
    return {"name": name, "employer": employer, "ats": "jibe",
            "params": {"host": f"jobs.{name}.test"}}


def posting(pid, title="Financial Analyst", city="Fort Worth", state="Texas"):
    return {"data": {"slug": str(pid), "req_id": str(pid), "title": title,
                     "full_location": f"{city}, {state}", "posted_date": "2026-01-01T00:00:00Z"}}


@pytest.fixture
def raw(tmp_path):
    """raw(day, ids, source='acme', **kw) writes one raw file and returns the raw dir."""
    def make(day, ids, source="acme", titles=None, employer=None):
        titles = titles or {}
        write_raw(tmp_path, day, cfg(source, employer or source.title()),
                  [posting(i, titles.get(i, "Financial Analyst")) for i in ids])
        return tmp_path
    make.dir = tmp_path
    return make
