"""Build a candidate's skill EVIDENCE from their resume and their real code.

Three levels, from weakest to strongest:
  claimed        the skill is listed on the resume, nothing else backs it up
  mentioned      it appears in project descriptions or READMEs ("built with FastAPI")
  demonstrated   it is actually used in code: imported libraries, SQL files, a Dockerfile, CI workflows, tests
A recruiter or interviewer can check a repository. Skills with evidence are worth more in a match than skills that are only listed.
"""
from __future__ import annotations
import ast
import os
import re
from dataclasses import dataclass, field

from .skills import CATEGORY, find_skills

CREDIT = {"demonstrated": 1.0, "mentioned": 0.7, "claimed": 0.4, "none": 0.0}
IMPORT_TO_SKILL = {
    "pandas": "pandas", "numpy": "numpy", "sklearn": "scikit-learn", "torch": "pytorch", "tensorflow": "tensorflow", "keras": "keras",
    "fastapi": "fastapi", "flask": "flask", "django": "django", "streamlit": "streamlit", "plotly": "data visualization",
    "matplotlib": "data visualization", "seaborn": "data visualization", "duckdb": "duckdb", "sqlite3": "sqlite", "psycopg2": "postgresql",
    "sqlglot": "sql", "pytest": "testing", "playwright": "testing", "selenium": "testing", "langchain": "langchain", "openai": "llm",
    "cv2": "computer vision", "mediapipe": "computer vision", "scipy": "statistics", "statsmodels": "statistics", "arch": "time series",
    "fastembed": "rag", "sentence_transformers": "rag", "chromadb": "rag", "rank_bm25": "rag", "pymongo": "mongodb", "redis": "redis",
    "boto3": "aws", "uvicorn": "api design", "requests": "api design", "httpx": "api design", "yfinance": "time series", "joblib": "machine learning",
    "airflow": "airflow", "pyspark": "spark",
}


@dataclass
class Evidence:
    level: str = "none"
    repos: set = field(default_factory=set)
    kinds: set = field(default_factory=set)
    files: int = 0


def _read(path: str, limit: int = 400_000) -> str:
    try:
        return open(path, encoding="utf-8", errors="ignore").read(limit)
    except OSError:
        return ""


def resume_parts(text: str) -> tuple[str, str]:
    """Split resume text into (skills section, everything else)."""
    m = re.search(r"technical skills(.*?)(experience|projects|education)", text, re.I | re.S)
    skills = m.group(1) if m else ""
    return skills, text.replace(skills, " ") if skills else text


def scan_repo(path: str) -> dict[str, dict]:
    """skill -> {'kinds': set, 'files': int} from the files in one repository folder."""
    found: dict[str, dict] = {}

    def add(skill, kind, n=1):
        d = found.setdefault(skill, dict(kinds=set(), files=0))
        d["kinds"].add(kind)
        d["files"] += n

    test_files = 0
    for dp, dn, fn in os.walk(path):
        dn[:] = [d for d in dn if d not in {".git", "venv", ".venv", "node_modules", "__pycache__", "data", "outputs", "raw", "models", "landing"}]
        for f in fn:
            p = os.path.join(dp, f)
            low = f.lower()
            if low.endswith(".py"):
                add("python", "import")
                src = _read(p)
                try:
                    tree = ast.parse(src)
                except SyntaxError:
                    continue
                mods = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        mods |= {a.name.split(".")[0] for a in node.names}
                    elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                        mods.add(node.module.split(".")[0])
                for m in mods & set(IMPORT_TO_SKILL):
                    add(IMPORT_TO_SKILL[m], "import")
                if re.search(r"(?i)\b(select|insert|create table|group by)\b.{0,80}\b(from|into|table|order by)\b", src, re.S):
                    add("sql", "sql in code")
                if low.startswith("test_") or low.endswith("_test.py"):
                    test_files += 1
            elif low.endswith(".sql"):
                add("sql", "sql file")
            elif low == "dockerfile":
                add("docker", "Dockerfile")
            elif low.endswith((".yml", ".yaml")) and ".github" in dp.replace("\\", "/"):
                add("ci/cd", "CI workflow")
            elif low in ("requirements.txt",):
                for line in _read(p).splitlines():
                    pkg = re.split(r"[<>=\[ ]", line.strip(), maxsplit=1)[0].lower().replace("-", "_")
                    if pkg in IMPORT_TO_SKILL:
                        add(IMPORT_TO_SKILL[pkg], "dependency")
            elif low in ("readme.md",):
                for s, n in find_skills(_read(p)).items():
                    add(s, "readme", 0)
    if test_files:
        add("testing", "tests", test_files)
    return found


@dataclass
class Candidate:
    name: str
    resume_text: str
    evidence: dict[str, Evidence]
    resume_skill_list: set

    def level(self, skill: str) -> str:
        return self.evidence.get(skill, Evidence()).level

    def credit(self, skill: str) -> float:
        return CREDIT[self.level(skill)]

    def full_text(self) -> str:
        return self.resume_text

    def with_demonstrated(self, skills) -> "Candidate":
        ev = {k: Evidence(v.level, set(v.repos), set(v.kinds), v.files) for k, v in self.evidence.items()}
        for s in skills:
            ev[s] = Evidence("demonstrated", {"(hypothetical)"}, {"added"}, 1)
        return Candidate(self.name, self.resume_text, ev, self.resume_skill_list)


CODE_KINDS = {"import", "sql in code", "sql file", "Dockerfile", "CI workflow", "tests", "dependency"}


def build(name: str, resume_text: str, repo_paths: list[str]) -> Candidate:
    skills_sec, prose = resume_parts(resume_text)
    claimed = set(find_skills(skills_sec))
    prose_hits = set(find_skills(prose))
    ev: dict[str, Evidence] = {}
    for s in claimed:
        ev[s] = Evidence("claimed")
    for s in prose_hits:
        e = ev.setdefault(s, Evidence())
        e.level = "mentioned"
    for rp in repo_paths:
        rname = os.path.basename(rp.rstrip("\\/"))
        for s, d in scan_repo(rp).items():
            e = ev.setdefault(s, Evidence())
            e.repos.add(rname)
            e.kinds |= d["kinds"]
            e.files += d["files"]
            if d["kinds"] & CODE_KINDS:
                e.level = "demonstrated"
            elif e.level in ("none", "claimed"):
                e.level = "mentioned"
    return Candidate(name, resume_text, ev, claimed)
