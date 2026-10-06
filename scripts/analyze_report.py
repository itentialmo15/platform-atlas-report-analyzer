#!/usr/bin/env python3
"""
analyze_report.py — Platform Atlas ER Triage Analyzer

Reads a Platform Atlas session export (ZIP, tar.gz, or extracted directory),
loads the validation parquet, and produces a customer-ready markdown draft
with failures grouped into three severity buckets.

Usage:
    python analyze_report.py <path-to-zip-or-dir> [--ticket KEY] [--output PATH]

Exit 0 on success, 1 with error message on failure.
"""

import argparse
import json
import os
import re
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


def find_pandas():
    """Import pandas/pyarrow, pointing to atlas-venv if system Python lacks them."""
    try:
        import pandas as pd
        import pyarrow  # noqa: F401
        return pd
    except ImportError:
        pass

    atlas_venv_python = Path.home() / "Documents/IAPbuilds/platform-atlas/atlas-venv/lib"
    if atlas_venv_python.exists():
        import glob
        for site in glob.glob(str(atlas_venv_python / "python3*/site-packages")):
            if site not in sys.path:
                sys.path.insert(0, site)
        try:
            import pandas as pd
            import pyarrow  # noqa: F401
            return pd
        except ImportError:
            pass

    print(
        "ERROR: pandas/pyarrow not found. Install them or activate the atlas-venv:\n"
        "  source ~/Documents/IAPbuilds/platform-atlas/atlas-venv/bin/activate",
        file=sys.stderr,
    )
    sys.exit(1)


def extract_archive(path: Path) -> Path:
    """Extract ZIP or tar to a temp dir and return the path. Caller must clean up."""
    tmp = Path(tempfile.mkdtemp(prefix="atlas-triage-"))
    suffix = "".join(path.suffixes).lower()
    if ".zip" in suffix:
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp)
    elif ".tar" in suffix or ".tgz" in suffix:
        with tarfile.open(path) as tf:
            tf.extractall(tmp)
    else:
        raise ValueError(f"Unsupported archive format: {path}")
    return tmp


def find_parquet(root: Path) -> Path | None:
    for p in root.rglob("02_validation.parquet"):
        return p
    return None


def find_session_json(root: Path) -> dict:
    for p in root.rglob("session.json"):
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def load_metadata(df, session_json: dict) -> dict:
    """Extract org/env/version metadata from df.attrs → session.json → defaults."""
    attrs = getattr(df, "attrs", {}) or {}

    def get(*keys):
        for k in keys:
            v = attrs.get(k) or session_json.get(k)
            if v:
                return str(v)
        return None

    org = get("organization_name", "organization") or "Unknown Organization"
    env = get("environment_name", "environment") or "Unknown Environment"
    atlas_ver = get("atlas_version", "version") or "Unknown"
    platform_ver = get("platform_version") or "Unknown"
    capture_date = get("capture_date", "created_at") or "Unknown"

    # Normalise ISO timestamps to just the date part
    if "T" in capture_date:
        capture_date = capture_date.split("T")[0]

    return {
        "org": org,
        "env": env,
        "atlas_version": atlas_ver,
        "platform_version": platform_ver,
        "capture_date": capture_date,
    }


SEVERITY_BUCKETS = [
    ("critical", "⛔ Mandatory — Must Fix",
     "These issues carry direct production risk. Address them before go-live."),
    ("warning", "⚠️ Recommended — Should Fix",
     "Best-practice gaps that increase risk over time. Prioritise for the next maintenance window."),
    ("info", "ℹ️ Optional — Best Practice",
     "Non-blocking improvements worth scheduling at your convenience."),
]

HEALTH_THRESHOLDS = [
    (90, "Excellent"),
    (75, "Good"),
    (60, "Fair"),
    (40, "Poor"),
    (0, "Critical"),
]


def health_label(pass_rate: float) -> str:
    for threshold, label in HEALTH_THRESHOLDS:
        if pass_rate >= threshold:
            return label
    return "Critical"


def build_summary(df) -> dict:
    total = len(df)
    skipped = int((df["status"] == "SKIP").sum())
    errors = int((df["status"] == "ERROR").sum())
    evaluated = total - skipped - errors
    compliant = int((df["status"] == "PASS").sum())
    non_compliant = int((df["status"] == "FAIL").sum())
    pass_rate = round(compliant / evaluated * 100, 1) if evaluated > 0 else 0.0
    return {
        "total_rules": total,
        "evaluated": evaluated,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "skipped": skipped,
        "errors": errors,
        "pass_rate": pass_rate,
        "health_rating": health_label(pass_rate),
    }


def truncate(val, max_len=80) -> str:
    s = str(val) if val is not None else "—"
    return (s[:max_len] + "…") if len(s) > max_len else s


def render_markdown(meta: dict, summary: dict, buckets: dict, ticket: str | None) -> str:
    now = datetime.now().strftime("%Y-%m-%d")
    ticket_str = f"ER-{ticket}" if ticket and not ticket.upper().startswith("ER-") else (ticket or "—")

    lines = []

    # Header
    lines.append("# Platform Atlas — Assessment Findings")
    lines.append("")
    lines.append(f"**Customer:** {meta['org']}  ")
    if ticket_str != "—":
        lines.append(f"**Ticket:** {ticket_str}  ")
    lines.append(f"**Environment:** {meta['env']}  ")
    lines.append(f"**Captured:** {meta['capture_date']}  ")
    lines.append(f"**Atlas Version:** {meta['atlas_version']}  ")
    if meta["platform_version"] != "Unknown":
        lines.append(f"**Platform Version:** {meta['platform_version']}  ")
    lines.append(f"**Report Prepared:** {now}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Overall health
    health = summary["health_rating"]
    rate = summary["pass_rate"]
    lines.append(f"## Overall Health: {health} ({rate}%)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Health Rating | **{health}** |")
    lines.append(f"| Pass Rate | {rate}% |")
    lines.append(f"| Rules Evaluated | {summary['evaluated']} |")
    lines.append(f"| ⛔ Mandatory Issues | {len(buckets.get('critical', []))} |")
    lines.append(f"| ⚠️ Recommended Issues | {len(buckets.get('warning', []))} |")
    lines.append(f"| ℹ️ Optional Issues | {len(buckets.get('info', []))} |")
    if summary["skipped"]:
        lines.append(f"| Skipped (no data) | {summary['skipped']} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-bucket sections
    for sev_key, heading, subtitle in SEVERITY_BUCKETS:
        rows = buckets.get(sev_key, [])
        lines.append(f"## {heading} ({len(rows)})")
        lines.append("")
        if not rows:
            lines.append("_No issues in this category. ✓_")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        lines.append(subtitle)
        lines.append("")
        lines.append("| Rule | Area | Issue | Expected | Actual |")
        lines.append("|------|------|-------|----------|--------|")
        for r in rows:
            rule_num = r.get("rule_number", "—")
            category = r.get("category", "—")
            name = truncate(r.get("name", "—"), 60)
            expected = truncate(r.get("expected"), 50)
            actual = truncate(r.get("actual"), 50)
            lines.append(f"| {rule_num} | {category} | {name} | `{expected}` | `{actual}` |")

        # Failure messages / recommendations (if present)
        lines.append("")
        if sev_key == "critical":
            lines.append("### Details")
            lines.append("")
            for r in rows:
                rule_num = r.get("rule_number", "—")
                name = r.get("name", "—")
                rec = r.get("recommendations") or ""
                # pandas NaN shows up as float; coerce to empty string
                if not isinstance(rec, str):
                    rec = ""
                lines.append(f"**{rule_num} — {name}**  ")
                if rec:
                    lines.append(f"{rec}  ")
                lines.append("")

        lines.append("---")
        lines.append("")

    # Next steps
    lines.append("## Suggested Next Steps")
    lines.append("")

    mandatory_count = len(buckets.get("critical", []))
    if mandatory_count:
        lines.append(
            f"1. **Address all {mandatory_count} Mandatory item(s) above** before promoting this "
            "environment to production. These carry direct platform risk."
        )
    else:
        lines.append("1. ✓ No Mandatory issues — the environment is in a production-ready state for critical checks.")

    lines.append(
        "2. **Re-run Platform Atlas after remediation** to confirm compliance and generate an updated report."
    )

    if meta["atlas_version"] not in ("Unknown", "2.2.0"):
        lines.append(
            f"3. **Upgrade Platform Atlas** from {meta['atlas_version']} to v2.2.0 "
            "to benefit from the latest rules and improvements."
        )

    lines.append(
        "4. **Schedule a follow-up review** for the Recommended items at your next maintenance window."
    )
    lines.append(
        "5. Please let us know if you'd like to schedule a review call to walk through these findings."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "_Prepared by: Itential Customer SRE Team | "
        f"Platform Atlas v{meta['atlas_version']} | "
        f"Report date: {now}_"
    )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze a Platform Atlas session export.")
    parser.add_argument("path", help="ZIP, tar.gz, or extracted directory of the session export")
    parser.add_argument("--ticket", help="Jira ticket key (e.g. ER-508)", default=None)
    parser.add_argument("--output", help="Output path for the markdown draft (default: stdout)", default=None)
    args = parser.parse_args()

    pd = find_pandas()

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: path does not exist: {path}", file=sys.stderr)
        sys.exit(1)

    tmp_dir = None
    try:
        if path.is_dir():
            root = path
        else:
            tmp_dir = extract_archive(path)
            root = tmp_dir

        parquet_path = find_parquet(root)
        if parquet_path is None:
            print(
                "ERROR: could not find 02_validation.parquet in the export. "
                "Make sure you're passing a valid Platform Atlas session export.",
                file=sys.stderr,
            )
            sys.exit(1)

        df = pd.read_parquet(parquet_path)
        session_json = find_session_json(root)

        meta = load_metadata(df, session_json)
        summary = build_summary(df)

        fail_df = df[df["status"] == "FAIL"].copy()

        buckets = {}
        for sev_key, _, _ in SEVERITY_BUCKETS:
            subset = fail_df[fail_df["severity"] == sev_key]
            buckets[sev_key] = subset.to_dict(orient="records")

        markdown = render_markdown(meta, summary, buckets, args.ticket)

        if args.output:
            Path(args.output).write_text(markdown, encoding="utf-8")
            print(f"Draft written to: {args.output}", file=sys.stderr)
        else:
            print(markdown)

    finally:
        if tmp_dir is not None:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
