"""Score a candidate against jobs, explain the score, and turn the gaps into a plan.

Score = (sum over the job's skills of  weight x evidence credit) / (sum of weights)
  weight  how much the job cares (1.0 required, 0.7 mentioned, 0.5 nice to have)
  credit  how well the candidate can prove it (demonstrated 1.0, mentioned 0.7, claimed 0.4, none 0)
So a skill you have actually built with counts more than one you only listed, and every number can be traced back to a word in the job post.
"""
from __future__ import annotations
from collections import defaultdict
import re
from dataclasses import dataclass

from .candidate import Candidate
from .extract import job_skills, years_required
from .skills import CATEGORY

PROOF_IDEAS = {
    "language": "build and publish a small project that uses it, with tests",
    "web": "ship a small deployed app with a public link",
    "data": "do an analysis on a real dataset and write up the conclusion",
    "ml": "train, evaluate and honestly report a model on a public benchmark",
    "bi": "build a dashboard on a real dataset and publish a screenshot or link",
    "data eng": "build a pipeline that loads, checks and transforms real data on a schedule",
    "database": "model a real dataset and write the queries you would run in production",
    "cloud": "deploy one of your projects there and document the setup",
    "devops": "containerise or automate the build of a project you already have",
    "practice": "add it to a project you already have and show the result in the README",
}


@dataclass
class Match:
    job: dict
    score: float
    matched: list        # (skill, weight, level)
    gaps: list           # (skill, weight)
    years: int | None


PRIOR = 2.0     # a job that lists only 2 skills tells us little: pretend it also asked for two things we cannot verify


def score_job(candidate: Candidate, job: dict) -> Match:
    weights = job["skills"]
    total = sum(weights.values())
    if total == 0:
        return Match(job, 0.0, [], [], job.get("years"))
    got = sum(w * candidate.credit(s) for s, w in weights.items())
    total += PRIOR
    matched = sorted(((s, w, candidate.level(s)) for s, w in weights.items() if candidate.credit(s) > 0), key=lambda t: -t[1])
    gaps = sorted(((s, w) for s, w in weights.items() if candidate.credit(s) < 1.0), key=lambda t: -t[1])
    return Match(job, got / total, matched, gaps, job.get("years"))


def prepare_jobs(raw_jobs: list[dict]) -> list[dict]:
    out = []
    for j in raw_jobs:
        text = j["text"]
        out.append(dict(j, skills=job_skills(text), years=years_required(text)))
    return [j for j in out if len(j["skills"]) >= 2]          # a job post with no recognisable skills cannot be matched


SENIOR_TITLE = re.compile(r"(senior|\bsr\b|lead|principal|staff|head of|director|manager|architect|\bvp\b|chief)", re.I)
SENIOR_LABELS = ("Senior", "Lead", "Manager", "Director", "Executive")


def too_senior(job: dict, max_years: int) -> bool:
    """Judged from the stated years, the job title, and the job site's own seniority label when it has one."""
    if job.get("years") is not None and job["years"] > max_years:
        return True
    if SENIOR_TITLE.search(job.get("title", "")):
        return True
    return any(w in job.get("seniority", "") for w in SENIOR_LABELS)


def rank(candidate: Candidate, jobs: list[dict], max_years: int | None = None) -> list[Match]:
    ms = [score_job(candidate, j) for j in jobs]
    if max_years is not None:
        ms = [m for m in ms if not too_senior(m.job, max_years)]
    return sorted(ms, key=lambda m: -m.score)


def learning_plan(candidate: Candidate, matches: list[Match], top_jobs: int = 30, n: int = 6) -> list[dict]:
    """Which missing or weakly proven skills, if demonstrated, would help the most across the jobs you are aiming at?"""
    top = matches[:top_jobs]
    need = defaultdict(lambda: dict(weight=0.0, jobs=0, current=0.0))
    for m in top:
        for s, w in m.gaps:
            d = need[s]
            d["weight"] += w * (1.0 - candidate.credit(s))
            d["jobs"] += 1
            d["current"] = candidate.credit(s)
    plan = []
    for s, d in sorted(need.items(), key=lambda kv: -kv[1]["weight"])[:n]:
        cat = CATEGORY.get(s, "practice")
        adj = sorted(k for k, v in candidate.evidence.items() if v.level == "demonstrated" and CATEGORY.get(k) == cat and k != s)[:3]
        lift = sum(score_job(candidate.with_demonstrated([s]), m.job).score - m.score for m in top) / len(top)
        plan.append(dict(skill=s, wanted_by=d["jobs"], of=len(top), current_level=candidate.level(s), category=cat,
                         you_already_have_nearby=adj, how_to_prove_it=PROOF_IDEAS.get(cat, PROOF_IDEAS["practice"]),
                         average_score_gain=round(lift, 4)))
    return plan


def resume_suggestions(candidate: Candidate) -> dict:
    """Skills your code proves but your resume does not list, and skills the resume lists that nothing proves."""
    listed = candidate.resume_skill_list
    proven = {s for s, e in candidate.evidence.items() if e.level == "demonstrated"}
    return dict(add_to_resume=sorted(proven - listed - {"python"} if "python" in listed else proven - listed),
                listed_but_unproven=sorted(s for s in listed if candidate.level(s) == "claimed"))
