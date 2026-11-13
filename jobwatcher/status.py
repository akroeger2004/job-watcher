"""data/status.json: a description of the latest run."""
import json
from pathlib import Path

from .rawio import list_raw


def make_status(rows, raw_dir, run_time, results):
    """run_time is a UTC timestamp like 2026-11-13T14:05:00Z; results is one dict per
    source with name, ok and count (failed sources have ok false and count 0)."""
    days = sorted(list_raw(raw_dir))
    run_date = run_time[:10]
    return {
        "run_time": run_time,
        "first_run_date": days[0] if days else run_date,
        "days_with_success": len(days),
        "open": sum(1 for r in rows if r["status"] == "open"),
        "new_today": sum(1 for r in rows
                         if r["first_seen"] == run_date and r["first_run"] == "false"),
        "removed_today": sum(1 for r in rows if r["removed_date"] == run_date),
        "sources": [{"name": r["name"], "ok": bool(r["ok"]), "count": int(r["count"])}
                    for r in sorted(results, key=lambda r: r["name"])],
    }


def write_status(status, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
