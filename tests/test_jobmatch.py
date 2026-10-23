import os, sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jobmatch import candidate as cand
from jobmatch import match
from jobmatch.extract import job_skills, years_required
from jobmatch.skills import find_skills


# ---------------- skill extraction ----------------
def test_finds_aliases_and_ignores_case():
    got = find_skills("We use PostgreSQL, Docker and k8s on AWS (EC2). Python3 and JS.")
    assert {"postgresql", "docker", "kubernetes", "aws", "python", "javascript"} <= set(got)


def test_javascript_does_not_count_as_java():
    assert "java" not in find_skills("Strong JavaScript skills") and "java" in find_skills("Java and Kotlin")


@pytest.mark.parametrize("text,skill", [
    ("Take the rest of the week off", "rest api"), ("We react to change quickly", "react"),
    ("Agile Robots builds machines", "agile"), ("our lab automation team", "automation"),
    ("an accurate forecast of sales", "time series"), ("experimentation culture", "a/b testing"),
])
def test_known_false_friends_are_not_skills(text, skill):
    assert skill not in find_skills(text)


@pytest.mark.parametrize("text,skill", [("Build REST APIs", "rest api"), ("We use React and Next.js", "react"), ("Run A/B tests", "a/b testing"),
                                        ("C++ and C# experience", "c++"), ("Knowledge of Power BI and Tableau", "power bi")])
def test_real_mentions_are_found(text, skill):
    assert skill in find_skills(text)


def test_weights_follow_the_section_headings():
    text = "Requirements:\n- Python\n- SQL\nNice to have:\n- Docker\n"
    w = job_skills(text)
    assert w["python"] == 1.0 and w["sql"] == 1.0 and w["docker"] == 0.5


def test_years_of_experience():
    assert years_required("You have 3+ years of experience with Python") == 3
    assert years_required("5-7 years experience required") == 5
    assert years_required("Company founded 12 years ago") is None


# ---------------- candidate evidence ----------------
def make_repo(tmp_path, files):
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return str(tmp_path)


def test_levels_claimed_mentioned_demonstrated(tmp_path):
    repo = make_repo(tmp_path, {"app.py": "import pandas as pd\nimport fastapi\n", "q.sql": "select 1", "README.md": "Built with Tableau dashboards."})
    resume = "Technical Skills\nLanguages: Java, Python\nExperience\nWorked with Tableau at an internship.\nEducation"
    c = cand.build("x", resume, [repo])
    assert c.level("pandas") == "demonstrated" and c.level("fastapi") == "demonstrated" and c.level("sql") == "demonstrated"
    assert c.level("tableau") == "mentioned"          # described but never used in code
    assert c.level("java") == "claimed"               # only listed
    assert c.level("rust") == "none"


def test_credit_ordering():
    assert cand.CREDIT["demonstrated"] > cand.CREDIT["mentioned"] > cand.CREDIT["claimed"] > cand.CREDIT["none"]


# ---------------- scoring ----------------
def job(skills, title="Data Analyst", years=None):
    return dict(title=title, company="c", url="u", source="s", skills=skills, years=years)


def test_demonstrated_skill_scores_higher_than_listed_skill(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "import pandas\n"})
    c = cand.build("x", "Technical Skills\nTools: Tableau\nExperience\nEducation", [repo])
    a = match.score_job(c, job({"pandas": 1.0, "sql": 1.0})).score
    b = match.score_job(c, job({"tableau": 1.0, "sql": 1.0})).score
    assert a > b


def test_score_is_between_zero_and_one_and_explained(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "import pandas\n"})
    c = cand.build("x", "Technical Skills\nPython\nExperience\nEducation", [repo])
    m = match.score_job(c, job({"pandas": 1.0, "docker": 0.5, "kafka": 1.0}))
    assert 0 <= m.score <= 1
    assert [s for s, _, _ in m.matched] == ["pandas"] and {s for s, _ in m.gaps} == {"docker", "kafka"}


def test_a_job_with_few_listed_skills_cannot_win_just_by_being_short():
    c = cand.Candidate("x", "", {"python": cand.Evidence("demonstrated"), "sql": cand.Evidence("demonstrated")}, set())
    short = match.score_job(c, job({"python": 1.0, "sql": 1.0})).score
    long_ = match.score_job(c, job({"python": 1.0, "sql": 1.0, "pandas": 1.0, "numpy": 1.0})).score
    assert short < 1.0 and short > 0.4
    assert match.score_job(cand.Candidate("y", "", {s: cand.Evidence("demonstrated") for s in ["python", "sql", "pandas", "numpy"]}, set()),
                           job({"python": 1.0, "sql": 1.0, "pandas": 1.0, "numpy": 1.0})).score > short


def test_experience_filter():
    assert match.too_senior({"title": "Principal Engineer", "years": None}, 2) and not match.too_senior({"title": "Data Analyst", "years": 1}, 2)
    c = cand.Candidate("x", "", {"python": cand.Evidence("demonstrated")}, set())
    ranked = match.rank(c, [job({"python": 1.0, "sql": 1.0}, years=1), job({"python": 1.0, "sql": 1.0}, years=5)], max_years=2)
    assert len(ranked) == 1 and ranked[0].years == 1


def test_learning_plan_recommends_the_skill_most_jobs_need(tmp_path):
    c = cand.Candidate("x", "", {"python": cand.Evidence("demonstrated")}, set())
    jobs = [job({"python": 1.0, "airflow": 1.0}), job({"python": 1.0, "airflow": 1.0, "kafka": 0.5}), job({"python": 1.0, "airflow": 1.0, "dbt": 0.5})]
    plan = match.learning_plan(c, match.rank(c, jobs), top_jobs=3, n=3)
    assert plan[0]["skill"] == "airflow" and plan[0]["wanted_by"] == 3 and plan[0]["average_score_gain"] > 0


def test_resume_suggestions(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "import fastapi\n", "Dockerfile": "FROM python"})
    c = cand.build("x", "Technical Skills\nJava\nExperience\nEducation", [repo])
    s = match.resume_suggestions(c)
    assert "fastapi" in s["add_to_resume"] and "docker" in s["add_to_resume"] and "java" in s["listed_but_unproven"]
