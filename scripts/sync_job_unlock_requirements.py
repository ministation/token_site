"""Скачивает требования к ролям из mini-station-goob и сохраняет JSON."""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.request
from pathlib import Path

REPO = "ministation/mini-station-goob"
BRANCH = "master"
BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
API_TREE = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
OUT = Path(__file__).resolve().parents[1] / "data" / "mini_station_job_unlock.json"
TREE_CACHE = Path(__file__).resolve().parents[1] / "data" / "goob-tree.json"
DEPT_CACHE = Path(__file__).resolve().parents[1] / "data" / "departments.yml"
JOBS_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "goob_jobs"

TIME_REQ_TYPES = {
    "DepartmentTimeRequirement",
    "OverallTimeRequirement",
    "OverallPlaytimeRequirement",
    "RoleTimeRequirement",
}


def download_job_file(path: str) -> str:
    JOBS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = JOBS_CACHE_DIR / path.replace("/", "__")
    if cache.is_file() and cache.stat().st_size > 0:
        return cache.read_text(encoding="utf-8")
    url = BASE + path
    for attempt in range(5):
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Invoke-WebRequest -Uri '{url}' -OutFile '{cache}' -UseBasicParsing",
            ],
            capture_output=True,
            timeout=120,
        )
        if cache.is_file() and cache.stat().st_size > 0:
            return cache.read_text(encoding="utf-8")
        time.sleep(1 + attempt)
    raise RuntimeError(
        f"Failed to download {url}: {result.stderr.decode(errors='ignore')}"
    )


def parse_departments(yaml_text: str) -> dict[str, str]:
    role_to_dept: dict[str, str] = {}
    current_dept: str | None = None
    in_roles = False
    for line in yaml_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("- type: department"):
            current_dept = None
            in_roles = False
            continue
        if stripped.startswith("id:") and not in_roles:
            current_dept = stripped.split(":", 1)[1].strip()
            continue
        if stripped == "roles:":
            in_roles = True
            continue
        if in_roles and stripped.startswith("- "):
            role = stripped[2:].strip()
            if current_dept and role:
                role_to_dept[role] = current_dept
            continue
        if in_roles and stripped and not stripped.startswith("-"):
            in_roles = False
    return role_to_dept


def parse_requirement_block(block: str) -> dict | None:
    type_match = re.search(r"!type:(\w+)", block)
    if not type_match:
        return None
    rtype = type_match.group(1)
    if rtype not in TIME_REQ_TYPES:
        return None
    entry: dict = {"type": rtype}
    for key in ("department", "tracker", "role", "group"):
        m = re.search(rf"^\s*{key}:\s*(\S+)", block, re.M)
        if m:
            entry[key] = m.group(1)
    time_match = re.search(r"^\s*time:\s*(\d+)", block, re.M)
    if time_match:
        entry["time_seconds"] = int(time_match.group(1))
    if re.search(r"^\s*inverted:\s*true", block, re.M):
        entry["inverted"] = True
    return entry


def parse_job_requirements(text: str) -> list[dict]:
    req_match = re.search(r"^  requirements:\n((?:    .+\n)*)", text, re.M)
    if not req_match:
        return []
    section = req_match.group(1)
    blocks = re.findall(r"- !type:\w+.*?(?=\n    - !type:|\Z)", section, re.S)
    requirements: list[dict] = []
    for block in blocks:
        req = parse_requirement_block(block)
        if req:
            requirements.append(req)
    return requirements


def parse_job_file(text: str) -> dict | None:
    if "- type: job" not in text:
        return None
    job_match = re.search(r"- type: job[^\n]*\n\s*id:\s*(\w+)", text)
    tracker_match = re.search(r"playTimeTracker:\s*(\w+)", text)
    if not job_match or not tracker_match:
        return None
    job_id = job_match.group(1)
    tracker = tracker_match.group(1)
    requirements = parse_job_requirements(text)
    return {
        "role_id": job_id,
        "tracker": tracker,
        "requirements": requirements,
    }


def main() -> None:
    if not TREE_CACHE.is_file():
        raise SystemExit(f"Missing {TREE_CACHE}")
    tree = json.loads(TREE_CACHE.read_text(encoding="utf-8"))
    job_prefixes = (
        "Resources/Prototypes/Roles/Jobs/",
        "Resources/Prototypes/_Mini/Roles/Jobs/",
    )
    skip_paths = {
        "Resources/Prototypes/Roles/Jobs/departments.yml",
        "Resources/Prototypes/_Mini/Roles/Jobs/departments.yml",
    }
    job_files = [
        node["path"]
        for node in tree["tree"]
        if any(node["path"].startswith(prefix) for prefix in job_prefixes)
        and node["path"].endswith(".yml")
        and node["path"] not in skip_paths
        and "/CentComm/" not in node["path"]
    ]
    role_to_dept = parse_departments(DEPT_CACHE.read_text(encoding="utf-8"))

    jobs: dict[str, dict] = {}
    for index, path in enumerate(sorted(job_files)):
        try:
            text = download_job_file(path)
        except Exception as exc:
            print("skip", path, exc)
            continue
        parsed = parse_job_file(text)
        if not parsed:
            continue
        parsed["department"] = role_to_dept.get(parsed["role_id"])
        jobs[parsed["role_id"]] = parsed
        if (index + 1) % 10 == 0:
            print(f"parsed {index + 1}/{len(job_files)}")

    payload = {
        "source": f"https://github.com/{REPO}",
        "branch": BRANCH,
        "role_to_department": role_to_dept,
        "jobs": jobs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(jobs)} jobs to {OUT}")


if __name__ == "__main__":
    main()
