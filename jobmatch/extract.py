"""Read a job description and say which skills it needs, and how much each one matters.

Weight of a skill in a job:
  1.0  it appears under a "requirements / must have / you have / qualifications" style heading, or is mentioned 2+ times
  0.5  it appears only under a "nice to have / bonus / preferred / plus" heading
  0.7  anything else (mentioned once, in the body)
Also pulls out the experience asked for ("3+ years") so seniority can be checked.
"""
from __future__ import annotations
import re

from .skills import find_skills

NICE = re.compile(r"(nice[- ]to[- ]have|bonus|preferred|a plus|is a plus|plus points|good to have|desirable|optional)", re.I)
MUST = re.compile(r"(requirements?|must[- ]have|you have|you bring|what we.re looking for|qualifications?|skills required|required skills|what you.ll need|who you are)", re.I)
YEARS = re.compile(r"(\d{1,2})\s*(?:\+|-|–|to)?\s*(\d{1,2})?\s*\+?\s*(?:years?|yrs?)", re.I)


def split_sections(text: str) -> list[tuple[str, str]]:
    """Cut the text at heading-like lines (short lines ending in ':' or short lines containing a section word)."""
    lines = [l.strip() for l in text.splitlines()]
    sections, kind, buf = [], "body", []
    for l in lines:
        is_heading = 0 < len(l) <= 60 and (l.endswith(":") or (not l.endswith(".") and (NICE.search(l) or MUST.search(l))))
        if is_heading and NICE.search(l):
            sections.append((kind, "\n".join(buf))); kind, buf = "nice", []
        elif is_heading and MUST.search(l):
            sections.append((kind, "\n".join(buf))); kind, buf = "must", []
        elif is_heading:
            sections.append((kind, "\n".join(buf))); kind, buf = "body", []
        else:
            buf.append(l)
    sections.append((kind, "\n".join(buf)))
    return sections


def job_skills(text: str) -> dict[str, float]:
    weights: dict[str, float] = {}
    counts = find_skills(text)
    by_kind: dict[str, set] = {"must": set(), "nice": set(), "body": set()}
    for kind, chunk in split_sections(text):
        by_kind[kind] |= set(find_skills(chunk))
    for skill, n in counts.items():
        if skill in by_kind["must"] or n >= 2:
            weights[skill] = 1.0
        elif skill in by_kind["nice"] and skill not in by_kind["body"]:
            weights[skill] = 0.5
        else:
            weights[skill] = 0.7
    return weights


def years_required(text: str) -> int | None:
    """The smallest 'N years' figure that sits near the word experience, or None."""
    vals = []
    for m in YEARS.finditer(text):
        window = text[max(0, m.start() - 60): m.end() + 60].lower()
        if "experience" in window or "exp" in window:
            vals.append(int(m.group(1)))
    return min(vals) if vals else None
