#!/usr/bin/env python3
"""Phase 0 self-check — probes your environment and writes a submission report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from autograder import env_checks  # noqa: E402

REPORT_PATH = REPO_ROOT / "submission" / "phase0_report.json"


# --------------------------------------------------------------------------- #
# Functions YOU implement
# --------------------------------------------------------------------------- #
def parse_gcloud_config(raw: str) -> dict:
    """Parse the JSON emitted by gcloud config list --format=json."""
    if not raw or not raw.strip():
        return {"account": "", "project": ""}
    try:
        data = json.loads(raw)
        core = data.get("core", {}) if isinstance(data, dict) else {}
        account = str(core.get("account") or "")
        project = str(core.get("project") or "")
        return {"account": account, "project": project}
    except Exception:
        return {"account": "", "project": ""}


def parse_repo_slug(remote_url: str) -> str:
    """Turn a GitHub remote URL into an owner/repo slug (no .git suffix)."""
    if not remote_url or "github.com" not in remote_url:
        return ""

    cleaned = remote_url.strip()
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    if "github.com/" in cleaned:
        slug = cleaned.split("github.com/")[-1]
    elif "github.com:" in cleaned:
        slug = cleaned.split("github.com:")[-1]
    else:
        return ""

    return slug.strip("/")


# --------------------------------------------------------------------------- #
# Provided probes (do not modify)
# --------------------------------------------------------------------------- #
def check_python() -> dict:
    major, minor, micro = env_checks.python_version()
    return {
        "version": f"{major}.{minor}.{micro}",
        "ok": env_checks.python_is_supported(),
    }


def check_environment() -> dict:
    return {"cloud_shell": env_checks.in_cloud_shell()}


def check_gcloud() -> dict:
    code, out, err = env_checks.run(["gcloud", "config", "list", "--format=json"])
    if code != 0:
        return {"account": "", "project": "", "error": err or "gcloud not found"}
    try:
        parsed = parse_gcloud_config(out)
    except NotImplementedError as exc:
        return {"account": "", "project": "", "error": str(exc)}
    return {"account": parsed["account"], "project": parsed["project"], "error": None}


def check_docker() -> dict:
    code, out, err = env_checks.run(["docker", "--version"])
    return {"version": out if code == 0 else "", "present": code == 0}


def check_git() -> dict:
    url = env_checks.git_remote_url()
    try:
        slug = parse_repo_slug(url)
    except NotImplementedError:
        slug = ""
    return {
        "remote": url,
        "is_github": "github.com" in url,
        "slug": slug,
    }


def build_report() -> dict:
    return {
        "phase": "0",
        "environment": check_environment(),
        "python": check_python(),
        "gcloud": check_gcloud(),
        "docker": check_docker(),
        "git": check_git(),
    }


def _print_summary(report: dict) -> None:
    def mark(ok: bool) -> str:
        return "OK  " if ok else "MISS"

    py = report["python"]
    gc = report["gcloud"]
    dk = report["docker"]
    gt = report["git"]
    env = report["environment"]
    print("Phase 0 environment check")
    print("-" * 40)
    where = "Cloud Shell" if env["cloud_shell"] else "local machine"
    print(f"[OK  ] Running on: {where}")
    print(f"[{mark(py['ok'])}] Python {py['version']} (need 3.11 or 3.12)")
    print(f"[{mark(bool(gc['account']))}] gcloud account: {gc['account'] or '(unset)'}")
    print(f"[{mark(bool(gc['project']))}] gcloud project: {gc['project'] or '(unset)'}")
    print(f"[{mark(dk['present'])}] {dk['version'] or 'docker not found'}")
    print(f"[{mark(gt['is_github'])}] git remote: {gt['remote'] or '(unset)'}")
    print("-" * 40)


def main() -> int:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _print_summary(report)
    print(f"\nWrote {REPORT_PATH.relative_to(REPO_ROOT)} — commit it and push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
