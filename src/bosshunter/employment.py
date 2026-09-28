"""Conservative employment-type checks, independent of campus/social recruitment."""

import re
from collections.abc import Mapping
from typing import Any, Literal

EmploymentType = Literal["internship", "full_time", "part_time", "unknown"]
_EXPLICIT_TYPE = re.compile(r"(?:职位|岗位|工作|招聘|用工)(?:类型|性质)\s*[:：]\s*(实习|全职|兼职)")
_TYPE_NAMES: dict[str, EmploymentType] = {"实习": "internship", "全职": "full_time", "兼职": "part_time"}


def classify_employment(job: Mapping[str, Any]) -> EmploymentType:
    """Require positive evidence; contradictory title/JD signals remain unknown."""
    title = str(job.get("title") or "")
    jd = str(job.get("jd") or "")
    # A negative internship statement must not become positive internship evidence.
    non_intern = bool(re.search(r"非实习|不招实习|不接受实习", title))
    signals: set[EmploymentType] = set()
    if non_intern or re.search(r"全职|正式岗", title):
        signals.add("full_time")
    if not non_intern and re.search(r"实习|\bintern(?:ship)?\b", title, re.I):
        signals.add("internship")
    if re.search(r"兼职", title):
        signals.add("part_time")
    signals.update(_TYPE_NAMES[match] for match in _EXPLICIT_TYPE.findall(jd))
    # Daily pay, campus recruitment and past internship experience are not proof.
    return next(iter(signals)) if len(signals) == 1 else "unknown"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def internship_only(config: Mapping[str, Any]) -> bool:
    """Only the explicit BOSS internship-only filter enables this guard.

    Platform filters override legacy search filters, including an empty mapping.
    Mixed selections must not accidentally turn into an internship-only search.
    """
    boss = _mapping(_mapping(_mapping(config.get("platforms")).get("boss")).get("search"))
    filters = boss.get("filters") if "filters" in boss else _mapping(config.get("search")).get("filters")
    value = _mapping(filters).get("job_type", [])
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        return False
    return {item.strip() for item in value} == {"实习"}


def internship_rejection(job: Mapping[str, Any], config: Mapping[str, Any]) -> str:
    if str(job.get("source_platform") or "boss") != "boss" or not internship_only(config):
        return ""
    kind = classify_employment(job)
    if kind == "internship":
        return ""
    if kind in {"full_time", "part_time"}:
        return "仅实习：非实习岗位"
    return "仅实习：职位类型待核实，禁止自动投递"
