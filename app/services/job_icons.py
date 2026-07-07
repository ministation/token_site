"""Иконки должностей из static/job_icons/."""
import os

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
JOB_ICONS_DIR = os.path.join(_PROJECT_ROOT, "static", "job_icons")
DEFAULT_ICON = "/static/job_icons/Unknown.png"

ROLE_ICON_ALIASES = {
    "SalvageSpecialist": "ShaftMiner",
    "Quartermaster": "QuarterMaster",
    "TypanCommander": "commander",
    "TypanTechnicalOperationsSupervisor": "technicalsupervisor",
    "TypanAtmosTech": "atmospheric_technician",
    "TypanBotanist": "botanist",
    "TypanCargotech": "cargo_technician",
    "TypanChef": "chef",
    "TypanMedic": "medical_doctor",
    "TypanResearchDirector": "research_director",
    "TypanScience": "scientist",
    "TypanPatrol": "security_officer",
    "TypanBorg": "borg",
}

TRACKER_OVERRIDES = {
    "TypanBorg": "JobBorgTypan",
}

TRACKER_TO_ROLE_OVERRIDES = {
    "JobBorgTypan": "TypanBorg",
}


def role_id_from_tracker(tracker: str) -> str:
    t = (tracker or "").strip()
    if t in TRACKER_TO_ROLE_OVERRIDES:
        return TRACKER_TO_ROLE_OVERRIDES[t]
    if t.startswith("Job:"):
        return t[4:]
    if t.startswith("Job") and len(t) > 3:
        return t[3:]
    return t


def tracker_from_role_id(role_id: str) -> str:
    r = (role_id or "").strip()
    if not r:
        return ""
    if r in TRACKER_OVERRIDES:
        return TRACKER_OVERRIDES[r]
    if r.startswith("Job") and not r.startswith("Job:"):
        return r
    if r.startswith("Job:"):
        return "Job" + r[4:]
    return f"Job{r}"


def job_icon_url(role_id: str) -> str:
    name = role_id_from_tracker(role_id)
    candidates = [name]
    alias = ROLE_ICON_ALIASES.get(name)
    if alias:
        candidates.append(alias)
    candidates.append("Unknown")
    for candidate in candidates:
        if os.path.isfile(os.path.join(JOB_ICONS_DIR, f"{candidate}.png")):
            return f"/static/job_icons/{candidate}.png"
    return DEFAULT_ICON
