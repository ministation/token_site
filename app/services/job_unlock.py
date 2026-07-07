"""Требования к разблокировке ролей из билда mini-station-goob."""
from __future__ import annotations

import json
from pathlib import Path

from app.services.job_icons import role_id_from_tracker, tracker_from_role_id

_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "mini_station_job_unlock.json"
_DEPT_YAML_PATH = Path(__file__).resolve().parents[2] / "data" / "departments.yml"

DEPARTMENT_LABELS = {
    "Cargo": "Карго",
    "Civilian": "Гражданские",
    "CentralCommand": "ЦентКом",
    "Command": "Командование",
    "Engineering": "Инженерия",
    "Medical": "Медицина",
    "Security": "Служба безопасности",
    "Science": "Наука",
    "Silicon": "Силикон",
    "Specific": "Особые",
    "_other": "Прочие",
}

TIME_REQ_TYPES = {
    "DepartmentTimeRequirement",
    "OverallTimeRequirement",
    "OverallPlaytimeRequirement",
    "RoleTimeRequirement",
}

_cache: dict | None = None
_dept_config_cache: tuple[list[str], dict[str, str], dict[str, list[str]]] | None = None


def _parse_departments_yaml(text: str) -> tuple[list[str], dict[str, str], dict[str, list[str]]]:
    import re

    dept_order: list[str] = []
    role_to_dept: dict[str, str] = {}
    dept_roles: dict[str, list[str]] = {}
    current_dept: str | None = None
    in_roles = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- type: department"):
            current_dept = None
            in_roles = False
            continue
        if current_dept is None and stripped.startswith("id:"):
            current_dept = stripped.split(":", 1)[1].strip()
            dept_order.append(current_dept)
            dept_roles.setdefault(current_dept, [])
            in_roles = False
            continue
        if stripped == "roles:":
            in_roles = True
            continue
        if in_roles and stripped.startswith("- "):
            role_id = stripped[2:].strip()
            dept_roles[current_dept or ""].append(role_id)
            if role_id not in role_to_dept and current_dept:
                role_to_dept[role_id] = current_dept
            continue
        if in_roles and stripped and not stripped.startswith("-"):
            in_roles = False

    return dept_order, role_to_dept, dept_roles


def get_department_config() -> tuple[list[str], dict[str, str], dict[str, list[str]]]:
    global _dept_config_cache
    if _dept_config_cache is not None:
        return _dept_config_cache

    if _DEPT_YAML_PATH.is_file():
        dept_order, role_to_dept, dept_roles = _parse_departments_yaml(
            _DEPT_YAML_PATH.read_text(encoding="utf-8")
        )
    else:
        dept_order, role_to_dept, dept_roles = [], {}, {}

    data = _load_data()
    for role_id, dept in data.get("role_to_department", {}).items():
        role_to_dept.setdefault(role_id, dept)
        dept_roles.setdefault(dept, [])
        if dept not in dept_order:
            dept_order.append(dept)

    _dept_config_cache = (dept_order, role_to_dept, dept_roles)
    return _dept_config_cache


def department_label(dept_id: str) -> str:
    return DEPARTMENT_LABELS.get(dept_id, dept_id.replace("_", " "))


def enrich_and_sort_roles(roles: list[dict]) -> list[dict]:
    dept_order, role_to_dept, dept_roles = get_department_config()
    dept_index = {dept: idx for idx, dept in enumerate(dept_order)}

    enriched: list[dict] = []
    for role in roles:
        role_id = role.get("role_id", "")
        dept = role.get("department") or role_to_dept.get(role_id, "_other")
        enriched.append({
            **role,
            "department": dept,
            "department_label": department_label(dept),
        })

    def sort_key(role: dict) -> tuple:
        dept = role["department"]
        role_id = role.get("role_id", "")
        dept_idx = dept_index.get(dept, len(dept_order) + (0 if dept == "_other" else 1))
        order_list = dept_roles.get(dept, [])
        role_idx = order_list.index(role_id) if role_id in order_list else 10_000
        return (dept_idx, role_idx, role.get("label", role_id))

    enriched.sort(key=sort_key)
    return enriched


def _load_data() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return _cache


def _role_tracker_from_req(value: str) -> str:
    raw = (value or "").strip()
    if raw.startswith("Job"):
        return raw if not raw.startswith("Job:") else tracker_from_role_id(raw[4:])
    return tracker_from_role_id(raw)


class _PlaytimeState:
    def __init__(self, minutes_map: dict[str, float], role_to_dept: dict[str, str]):
        self.minutes_by_tracker = {k: float(v) for k, v in minutes_map.items()}
        self.role_to_dept = role_to_dept
        self._recompute()

    def _recompute(self) -> None:
        self.dept_seconds: dict[str, float] = {}
        for tracker, minutes in self.minutes_by_tracker.items():
            if tracker == "Overall":
                continue
            role_id = role_id_from_tracker(tracker)
            dept = self.role_to_dept.get(role_id)
            if dept:
                self.dept_seconds[dept] = self.dept_seconds.get(dept, 0.0) + minutes * 60.0
        self.overall_seconds = self.minutes_by_tracker.get("Overall", 0.0) * 60.0

    def add_minutes(self, tracker: str, minutes: float) -> None:
        self.minutes_by_tracker[tracker] = self.minutes_by_tracker.get(tracker, 0.0) + minutes
        self._recompute()

    def clone(self) -> "_PlaytimeState":
        return _PlaytimeState(self.minutes_by_tracker, self.role_to_dept)


def _check_time_requirement(req: dict, state: _PlaytimeState, job_tracker: str) -> bool:
    inverted = bool(req.get("inverted"))
    rtype = req.get("type")
    time_sec = float(req.get("time_seconds") or 0)

    if rtype == "DepartmentTimeRequirement":
        dept = req.get("department")
        total = state.dept_seconds.get(dept, 0.0)
        ok = total >= time_sec
    elif rtype == "OverallPlaytimeRequirement":
        ok = state.overall_seconds >= time_sec
    elif rtype == "OverallTimeRequirement":
        tracker = req.get("tracker") or job_tracker
        ok = state.minutes_by_tracker.get(tracker, 0.0) * 60.0 >= time_sec
    elif rtype == "RoleTimeRequirement":
        tracker = _role_tracker_from_req(req.get("role", "")) or job_tracker
        ok = state.minutes_by_tracker.get(tracker, 0.0) * 60.0 >= time_sec
    else:
        return True

    return (not ok) if inverted else ok


def is_job_unlocked(job: dict | None, state: _PlaytimeState) -> bool:
    if not job:
        return True
    for req in job.get("requirements", []):
        if req.get("type") not in TIME_REQ_TYPES:
            continue
        if not _check_time_requirement(req, state, job["tracker"]):
            return False
    return True


def _requirement_label(req: dict) -> str:
    minutes = round(float(req.get("time_seconds") or 0) / 60.0, 1)
    rtype = req.get("type")
    if rtype == "DepartmentTimeRequirement":
        return f"{minutes} м в {req.get('department', 'отделе')}"
    if rtype == "OverallPlaytimeRequirement":
        return f"{minutes} м общего времени"
    if rtype == "OverallTimeRequirement":
        tracker = req.get("tracker", "")
        return f"{minutes} м на {translate_tracker_label(tracker)}"
    if rtype == "RoleTimeRequirement":
        return f"{minutes} м на {translate_tracker_label(_role_tracker_from_req(req.get('role', '')))}"
    return ""


def translate_tracker_label(tracker: str) -> str:
    from app.services.bans import translate_role
    return translate_role(tracker or "")


def get_job_config(role_id: str) -> dict | None:
    return _load_data()["jobs"].get(role_id)


def evaluate_role_unlock(role_id: str, minutes_map: dict[str, float]) -> dict:
    data = _load_data()
    job = data["jobs"].get(role_id)
    state = _PlaytimeState(minutes_map, data["role_to_department"])
    unlocked = is_job_unlocked(job, state)
    deficit_minutes = 0.0
    unlock_labels: list[str] = []

    if job:
        for req in job.get("requirements", []):
            if req.get("type") not in TIME_REQ_TYPES or req.get("inverted"):
                continue
            label = _requirement_label(req)
            if label:
                unlock_labels.append(label)
            if _check_time_requirement(req, state, job["tracker"]):
                continue
            if req["type"] == "DepartmentTimeRequirement":
                dept = req.get("department")
                need = float(req.get("time_seconds") or 0) - state.dept_seconds.get(dept, 0.0)
                deficit_minutes = max(deficit_minutes, need / 60.0)
            elif req["type"] == "OverallPlaytimeRequirement":
                need = float(req.get("time_seconds") or 0) - state.overall_seconds
                deficit_minutes = max(deficit_minutes, need / 60.0)
            elif req["type"] in ("OverallTimeRequirement", "RoleTimeRequirement"):
                tracker = (
                    req.get("tracker")
                    or _role_tracker_from_req(req.get("role", ""))
                    or job["tracker"]
                )
                need = float(req.get("time_seconds") or 0) - state.minutes_by_tracker.get(tracker, 0.0) * 60.0
                deficit_minutes = max(deficit_minutes, need / 60.0)

    return {
        "unlocked": unlocked,
        "deficit_minutes": round(max(0.0, deficit_minutes), 1),
        "unlock_labels": unlock_labels,
        "unlock_hint": "; ".join(unlock_labels) if unlock_labels else "без ограничений",
    }


def plan_unlock_all_transfers(minutes_map: dict[str, float], from_tracker: str) -> dict:
    data = _load_data()
    state = _PlaytimeState(minutes_map, data["role_to_department"])
    transfers: dict[str, float] = {}

    for _ in range(300):
        progress = False
        for job in data["jobs"].values():
            if job["tracker"] == from_tracker:
                continue
            if is_job_unlocked(job, state):
                continue
            for req in job.get("requirements", []):
                if req.get("inverted") or req.get("type") not in TIME_REQ_TYPES:
                    continue
                if _check_time_requirement(req, state, job["tracker"]):
                    continue

                target_tracker = job["tracker"]
                add_seconds = 0.0
                if req["type"] == "DepartmentTimeRequirement":
                    dept = req.get("department")
                    add_seconds = float(req.get("time_seconds") or 0) - state.dept_seconds.get(dept, 0.0)
                elif req["type"] == "OverallPlaytimeRequirement":
                    target_tracker = "Overall"
                    add_seconds = float(req.get("time_seconds") or 0) - state.overall_seconds
                elif req["type"] == "OverallTimeRequirement":
                    target_tracker = req.get("tracker") or job["tracker"]
                    add_seconds = (
                        float(req.get("time_seconds") or 0)
                        - state.minutes_by_tracker.get(target_tracker, 0.0) * 60.0
                    )
                elif req["type"] == "RoleTimeRequirement":
                    target_tracker = _role_tracker_from_req(req.get("role", "")) or job["tracker"]
                    add_seconds = (
                        float(req.get("time_seconds") or 0)
                        - state.minutes_by_tracker.get(target_tracker, 0.0) * 60.0
                    )

                if add_seconds <= 0 or target_tracker == from_tracker:
                    continue

                add_minutes = round(add_seconds / 60.0, 1)
                transfers[target_tracker] = round(transfers.get(target_tracker, 0.0) + add_minutes, 1)
                state.add_minutes(target_tracker, add_minutes)
                progress = True
                break
        if not progress:
            break

    items = [
        {
            "to_tracker": tracker,
            "to_label": translate_tracker_label(tracker),
            "minutes": minutes,
        }
        for tracker, minutes in sorted(transfers.items(), key=lambda item: item[0])
        if minutes > 0
    ]
    total = round(sum(item["minutes"] for item in items), 1)
    available = round(float(minutes_map.get(from_tracker, 0.0)), 1)
    return {
        "from_tracker": from_tracker,
        "from_label": translate_tracker_label(from_tracker),
        "transfers": items,
        "total_minutes": total,
        "available_minutes": available,
    }


def get_unlock_metadata() -> dict:
    data = _load_data()
    return {
        "source": data.get("source"),
        "branch": data.get("branch"),
        "jobs_count": len(data.get("jobs", {})),
    }
