"""The daily GitHub Issue: titled with the date, listing new and removed postings."""
import json
import re
import subprocess

TITLE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_BODY = 60000  # GitHub allows 65,536 characters


def _line(row):
    title = row["title"].replace("[", "(").replace("]", ")") or "(untitled)"
    where = f" · {row['location']}" if row["location"] else ""
    mark = " ⭐" if row["in_role"] == "true" else ""
    return f"- [{title}]({row['url']}) — {row['employer']}{where}{mark}"


def _section(heading, rows, budget):
    rows = sorted(rows, key=lambda r: (r["in_role"] != "true", r["employer"], r["title"]))
    lines = [f"## {heading} ({len(rows)})", ""]
    if not rows:
        return "\n".join(lines + ["None.", ""]), budget
    used = 0
    for i, row in enumerate(rows):
        line = _line(row)
        if used + len(line) > budget:
            lines.append(f"- …and {len(rows) - i} more (see `data/history.csv`)")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines + [""]), budget - used


def render_issue(run_date, rows, status):
    """Return (title, body). The title is the date, so every day has its own issue."""
    new = [r for r in rows if r["first_seen"] == run_date and r["first_run"] == "false"]
    removed = [r for r in rows if r["removed_date"] == run_date]
    failed = [s["name"] for s in status["sources"] if not s["ok"]]
    head = [
        f"Run at {status['run_time']}",
        "",
        f"- Open postings: **{status['open']}**",
        f"- New today: **{len(new)}**",
        f"- Removed today: **{len(removed)}**",
        f"- Days with a successful run: **{status['days_with_success']}**",
        f"- Sources that failed: {', '.join(failed) if failed else 'none'}",
        "",
        "⭐ marks a posting in the watched role (entry-level FP&A / wealth management).",
        "",
    ]
    budget = MAX_BODY // 2
    new_text, _ = _section("New postings", new, budget)
    removed_text, _ = _section("Removed postings", removed, budget)
    return run_date, "\n".join(head) + "\n" + new_text + "\n" + removed_text


def _gh(args, body=None):
    return subprocess.run(["gh", *args], input=body, text=True, encoding="utf-8",
                          capture_output=True, check=True).stdout


def publish_issue(title, body):
    """Create today's issue (or update it on a re-run) and close every earlier one."""
    issues = json.loads(_gh(["issue", "list", "--state", "all", "--limit", "200",
                             "--json", "number,title,state"]))
    today = next((i for i in issues if i["title"] == title), None)
    if today is None:
        out = _gh(["issue", "create", "--title", title, "--body-file", "-"], body)
        print("opened issue:", out.strip())
    else:
        _gh(["issue", "edit", str(today["number"]), "--body-file", "-"], body)
        if today["state"] != "OPEN":
            _gh(["issue", "reopen", str(today["number"])])
        print("updated issue", today["number"])
    for issue in issues:
        if issue["state"] == "OPEN" and TITLE.match(issue["title"]) and issue["title"] != title:
            _gh(["issue", "close", str(issue["number"]), "--comment", f"Superseded by {title}."])
            print("closed issue", issue["number"])
