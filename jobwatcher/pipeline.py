"""The daily run:  python -m jobwatcher.pipeline [--issue]

1. call every source and save what it returns to data/raw/<date>/<source>.json.gz
   (a source that fails writes no file; its failure is recorded in the status file)
2. build data/history.csv from the raw files
3. write data/status.json
4. with --issue, open today's GitHub Issue and close the previous one
The workflow then commits the raw files, the history and the status.
"""
import argparse
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .build import build_history, write_history
from .issue import publish_issue, render_issue
from .rawio import write_raw
from .sources import SOURCES, fetch
from .status import make_status, write_status

DATA = Path(__file__).resolve().parent.parent / "data"


def run(sources=None, fetcher=fetch, data_dir=DATA, now=None, issue=False, workers=6):
    sources = SOURCES if sources is None else sources
    now = now or datetime.now(timezone.utc)
    run_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    run_date = run_time[:10]
    raw_dir = Path(data_dir) / "raw"

    def one(src):
        try:
            postings = fetcher(src)
        except Exception as exc:  # one source failing must not stop the run
            print(f"FAILED {src['name']}: {exc!r}", file=sys.stderr)
            if not isinstance(exc, OSError):
                traceback.print_exc()
            return {"name": src["name"], "ok": False, "count": 0}
        write_raw(raw_dir, run_date, src, postings, fetched_at=run_time)
        print(f"ok {src['name']}: {len(postings)} postings")
        return {"name": src["name"], "ok": True, "count": len(postings)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, sources))

    rows = build_history(raw_dir)
    write_history(rows, Path(data_dir) / "history.csv")
    status = make_status(rows, raw_dir, run_time, results)
    write_status(status, Path(data_dir) / "status.json")
    title, body = render_issue(run_date, rows, status)
    if issue:
        publish_issue(title, body)
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", action="store_true", help="open/update today's GitHub Issue")
    parser.add_argument("--only", help="comma-separated source names (for testing)")
    args = parser.parse_args(argv)
    chosen = None
    if args.only:
        names = set(args.only.split(","))
        chosen = [s for s in SOURCES if s["name"] in names]
    status = run(sources=chosen, issue=args.issue)
    ok = sum(1 for s in status["sources"] if s["ok"])
    print(f"{ok}/{len(status['sources'])} sources ok; {status['open']} open postings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
