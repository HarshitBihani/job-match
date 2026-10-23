"""Run the whole analysis for one candidate and measure how well each part works.   python evaluate.py

Measured:
  1. skill extraction recall, against skill tags that employers attached themselves on Remote OK (independent labels)
  2. ranking quality: does the evidence-based score put suitable jobs near the top better than plain text similarity?
  3. is the learning plan targeted? average score gain from the recommended skills vs the same number of random skills
(Extraction precision was measured by hand-checking samples of extracted skills, see README.)
"""
import json
import os
import random
import re

import numpy as np
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobmatch import candidate as cand
from jobmatch import match
from jobmatch.skills import TAXONOMY, find_skills

HERE = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO = os.environ.get("REPOS_DIR", os.path.dirname(HERE))      # a folder that holds the repositories to read
RESUME_PDF = os.environ.get("RESUME_PDF", os.path.join(HERE, "resume.pdf"))
REPOS = ["retail-analytics", "ask-your-data", "ml-monitor", "doc-qa", "pipeline-lab", "finance-lab", "code-reviewer", "net-anomaly", "web-tester"]

TARGET = re.compile(r"(data analyst|analytics|business intelligence|\bbi\b|data scien|machine learning|\bml\b|\bai\b|data engineer|python|automation|research|quant|backend)", re.I)
SENIOR = re.compile(r"(senior|lead|principal|staff|head|director|manager|architect|vp\b|chief)", re.I)


def read_resume(path: str) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)


def ndcg(rels, k):
    rels = rels[:k]
    dcg = sum(r / np.log2(i + 2) for i, r in enumerate(rels))
    ideal = sum(r / np.log2(i + 2) for i, r in enumerate(sorted(rels, reverse=True)))
    return dcg / ideal if ideal else 0.0


def main():
    os.makedirs("outputs", exist_ok=True)
    raw = json.load(open("data/jobs.json", encoding="utf-8"))
    jobs = match.prepare_jobs(raw)
    resume = read_resume(RESUME_PDF)
    repos = [os.path.join(PORTFOLIO, r) for r in REPOS if os.path.isdir(os.path.join(PORTFOLIO, r))]
    me = cand.build("Harshit Bihani", resume, repos)
    levels = {lv: sorted(s for s, e in me.evidence.items() if e.level == lv) for lv in ("demonstrated", "mentioned", "claimed")}

    # ---- 1. extraction recall vs employer-chosen tags (Remote OK only) ----
    rec, n_jobs, hit, tot = [], 0, 0, 0
    for j in raw:
        if j["source"] != "Remote OK" or not j.get("tags"):
            continue
        expected = set()
        for t in j["tags"]:
            expected |= set(find_skills(t))
        if not expected:
            continue
        found = set(find_skills(j["text"]))
        n_jobs += 1
        hit += len(expected & found)
        tot += len(expected)
    recall = dict(jobs_with_mappable_tags=n_jobs, tags_total=tot, tags_found_in_text=hit, recall=round(hit / max(tot, 1), 3))

    # ---- 2. ranking ----
    for j in jobs:
        too_senior = SENIOR.search(j["title"]) or any(w in j.get("seniority", "") for w in ("Senior", "Lead", "Manager", "Director", "Executive"))
        j["relevant"] = 1 if (TARGET.search(j["title"]) and not too_senior) else 0
    rel_total = sum(j["relevant"] for j in jobs)
    evidence_rank = match.rank(me, jobs)
    corpus = [me.resume_text + "\n" + "\n".join(open(os.path.join(r, "README.md"), encoding="utf-8").read() for r in repos if os.path.exists(os.path.join(r, "README.md")))]
    vec = TfidfVectorizer(stop_words="english", max_features=20000, ngram_range=(1, 2), sublinear_tf=True)
    X = vec.fit_transform([j["text"] for j in jobs] + corpus)
    sims = cosine_similarity(X[-1], X[:-1]).ravel()
    tfidf_order = np.argsort(-sims)
    naive_claims = cand.Candidate("naive", resume, {s: cand.Evidence("demonstrated") for s in find_skills(resume)}, set())
    naive_rank = match.rank(naive_claims, jobs)
    idx = {id(j): i for i, j in enumerate(jobs)}
    methods = {
        "evidence-based skill match (this project)": [m.job["relevant"] for m in evidence_rank],
        "every listed skill counts equally (no evidence)": [m.job["relevant"] for m in naive_rank],
        "plain text similarity (TF-IDF)": [jobs[i]["relevant"] for i in tfidf_order],
    }
    rng = random.Random(0)
    shuffled = [j["relevant"] for j in jobs]
    rand = []
    for _ in range(200):
        rng.shuffle(shuffled)
        rand.append((np.mean(shuffled[:10]), np.mean(shuffled[:20]), ndcg(shuffled, 20)))
    ranking = {k: dict(p_at_10=round(float(np.mean(v[:10])), 3), p_at_20=round(float(np.mean(v[:20])), 3), ndcg_at_20=round(ndcg(v, 20), 3)) for k, v in methods.items()}
    ranking["random order (average of 200 shuffles)"] = dict(p_at_10=round(float(np.mean([r[0] for r in rand])), 3), p_at_20=round(float(np.mean([r[1] for r in rand])), 3),
                                                              ndcg_at_20=round(float(np.mean([r[2] for r in rand])), 3))

    # ---- 3. learning plan ----
    plan = match.learning_plan(me, evidence_rank, top_jobs=30, n=6)
    top = evidence_rank[:30]
    base = np.mean([m.score for m in top])
    plan_skills = [p["skill"] for p in plan]
    plan_gain = np.mean([match.score_job(me.with_demonstrated(plan_skills), m.job).score for m in top]) - base
    pool = [s for s in TAXONOMY if me.level(s) != "demonstrated" and s not in plan_skills]
    random_gains = []
    for _ in range(200):
        pick = rng.sample(pool, len(plan_skills))
        random_gains.append(np.mean([match.score_job(me.with_demonstrated(pick), m.job).score for m in top]) - base)

    # ---- job families the candidate fits best ----
    entry = match.rank(me, jobs, max_years=2)
    out = dict(
        corpus=dict(jobs=len(raw), usable=len(jobs), sources=sorted({j["source"] for j in raw}), relevant_by_title=rel_total),
        evidence_levels={k: v for k, v in levels.items()}, resume_suggestions=match.resume_suggestions(me),
        extraction_recall=recall, ranking=ranking,
        plan=plan, plan_simulation=dict(top_jobs=30, baseline_avg_score=round(float(base), 3), recommended_skills_gain=round(float(plan_gain), 3),
                                        random_skills_gain_mean=round(float(np.mean(random_gains)), 3), random_skills_gain_p95=round(float(np.percentile(random_gains, 95)), 3)),
        top_matches=[dict(title=m.job["title"], company=m.job["company"], url=m.job["url"], source=m.job["source"], score=round(m.score, 3), years=m.years,
                          matched=[(s, lv) for s, _, lv in m.matched][:8], gaps=[s for s, _ in m.gaps][:5]) for m in entry[:12]],
    )
    json.dump(out, open("outputs/results.json", "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("corpus", "extraction_recall", "ranking", "plan_simulation")}, indent=1))
    print("demonstrated:", levels["demonstrated"])
    print("claimed only:", levels["claimed"])
    print("resume suggestions:", out["resume_suggestions"])
    print("plan:", [(p["skill"], p["wanted_by"], p["average_score_gain"]) for p in plan])


if __name__ == "__main__":
    main()
