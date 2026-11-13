"""Reading and writing the compressed raw files: data/raw/<date>/<source>.json.gz"""
import gzip
import io
import json
import re
from pathlib import Path

DATE_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def raw_path(raw_dir, day, source):
    return Path(raw_dir) / day / f"{source}.json.gz"


def write_raw(raw_dir, day, source_cfg, postings, fetched_at=""):
    """Save what a source returned. An existing file for the same day is replaced."""
    path = raw_path(raw_dir, day, source_cfg["name"])
    path.parent.mkdir(parents=True, exist_ok=True)
    envelope = {
        "source": source_cfg["name"],
        "employer": source_cfg["employer"],
        "ats": source_cfg["ats"],
        "params": source_cfg["params"],
        "fetched_at": fetched_at,
        "postings": postings,
    }
    payload = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:  # mtime=0: stable bytes
        gz.write(payload)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(buf.getvalue())
    tmp.replace(path)
    return path


def read_raw(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def list_raw(raw_dir):
    """{'2026-11-13': {'blackrock': Path, ...}, ...} for every raw file on disk."""
    days = {}
    root = Path(raw_dir)
    if not root.is_dir():
        return days
    for day_dir in sorted(root.iterdir()):
        if not (day_dir.is_dir() and DATE_DIR.match(day_dir.name)):
            continue
        files = {p.name[: -len(".json.gz")]: p for p in sorted(day_dir.glob("*.json.gz"))}
        if files:
            days[day_dir.name] = files
    return days
