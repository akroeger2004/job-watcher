"""Build data/history.csv from the raw files alone.

    python -m jobwatcher.build

Nothing but the raw files is read, so running this again gives the same file, and a
change to the title rule or the US location rule applies to every day of the history.

Only postings located in the United States (jobwatcher/location.py) are kept in the
history. The raw files still hold everything each board returned.

For each day with raw files, in date order, and for each source with a file that day:
  * a posting seen for the first time gets that day as first_seen;
  * every posting the source lists gets that day as last_seen, and is open again if it
    had been removed (removed_date cleared, first_seen unchanged);
  * an open posting the source no longer lists is marked removed with that day's date.
A source with no raw file on a day (it failed) changes nothing that day.
"""
import csv
import sys
from datetime import date
from pathlib import Path

from .location import is_us
from .rawio import list_raw, read_raw
from .role import in_role
from .sources import convert

COLUMNS = [
    "posting_id", "source", "source_id", "employer", "title", "location", "department",
    "posted_date", "url", "in_role", "first_run", "first_seen", "last_seen", "status",
    "removed_date",
]


def build_history(raw_dir):
    days = list_raw(raw_dir)
    first_day = {}  # source -> date of its earliest raw file
    for day in sorted(days):
        for source in days[day]:
            first_day.setdefault(source, day)

    rows = {}
    for day in sorted(days):
        run_date = date.fromisoformat(day)
        for source in sorted(days[day]):
            env = read_raw(days[day][source])
            listed = set()
            for posting in env["postings"]:
                try:
                    c = convert(env["ats"], posting, env["params"], run_date)
                except (KeyError, TypeError):
                    continue  # no id to track it by
                if not is_us(c["location"]):
                    continue  # the history keeps US-based postings only; the raw file keeps all
                pid = f"{source}:{c['source_id']}"
                if pid in listed:
                    continue
                listed.add(pid)
                row = rows.get(pid)
                if row is None:
                    row = rows[pid] = {
                        "posting_id": pid, "source": source,
                        "first_run": "true" if day == first_day[source] else "false",
                        "first_seen": day,
                    }
                row.update(
                    source_id=c["source_id"], employer=env["employer"], title=c["title"],
                    location=c["location"], department=c["department"],
                    posted_date=c["posted_date"], url=c["url"],
                    last_seen=day, status="open", removed_date="",
                )
            for pid, row in rows.items():
                if row["source"] == source and row["status"] == "open" and pid not in listed:
                    row["status"] = "removed"
                    row["removed_date"] = day

    for row in rows.values():
        row["in_role"] = "true" if in_role(row["title"]) else "false"
    return [rows[pid] for pid in sorted(rows)]


def write_history(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_history(path):
    with Path(path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main(argv=None):
    root = Path(__file__).resolve().parent.parent / "data"
    rows = build_history(root / "raw")
    write_history(rows, root / "history.csv")
    print(f"wrote {len(rows)} postings to {root / 'history.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
