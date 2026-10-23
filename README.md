# Evidence-Based Job Match: what can you prove, and what are jobs asking for?

Most "resume matchers" count keywords. This one asks a different question: for each skill a job wants, **can the candidate prove it?** It reads the resume and the candidate's real code repositories, and sorts every skill into three levels of evidence. Then it matches that against real job posts, explains every score, and turns the gaps into a plan.

| Level | Meaning | Credit in a match |
|---|---|---|
| Demonstrated | the skill is used in code: imported libraries, SQL files, a Dockerfile, CI workflows, tests | 1.0 |
| Mentioned | it appears in a project description or README but not in code | 0.7 |
| Claimed | it is only listed on the resume | 0.4 |

I ran it on my own resume and nine of my own projects. It was a little uncomfortable, which is what makes it useful:

- **Skills my code proves but my resume did not list:** FastAPI, DuckDB, Docker, CI/CD, machine learning, RAG, time series, testing, SQLite. Easy wins: put them on the resume.
- **Skills my resume lists but nothing in my code backs up:** Java, MySQL, Excel, system design and automation (my n8n work is in older repositories I did not include). I should either build evidence or be ready to explain these in an interview.

Open `outputs/report.html` for the full report (evidence, best matches, learning plan).

## How well does it work?

I measured each part, and some of the results are not flattering.

**Does it extract the right skills from a job post?**
- *Precision:* I read random samples of (job, extracted skill) pairs and judged whether each was a real skill mention. First sample: 114 of 130 correct (87.7%). I fixed the patterns I found (for example the word "rest" in "the rest of the week" being read as REST APIs, "react to" as React, and the company name "Agile Robots" as agile). On a fresh sample I had not looked at: **119 of 130 correct (91.5%)**. What still goes wrong: company or customer names ("Oracle NetSuite", "Elasticsearch develops..."), degree subjects ("degree in Statistics"), and perks ("certification budget for AWS").
- *Recall:* employers on Remote OK attach skill tags to their posts. 42 of 63 of those tags (67%) were found in the post text. That is a lower bound, because tags are often broader than the text (a tag "aws" when the post says "cloud").

**Does the ranking put suitable jobs near the top?** Out of 928 usable posts, 230 are "suitable" by a rough proxy (title matches data, analytics, ML, AI, Python, automation or backend, and is not senior).

| Ranking method | Suitable jobs in top 10 | in top 20 | nDCG@20 |
|---|---|---|---|
| Evidence-based match (this project) | 6 | 9 | 0.878 |
| Every listed skill counts equally (no evidence) | 4 | 8 | 0.831 |
| Plain text similarity (TF-IDF) | 2 | 4 | 0.509 |
| Random order (average of 200 shuffles) | 2.4 | 4.8 | 0.573 |

The two skill-based methods clearly beat text similarity, which did no better than random here: comparing a whole resume plus READMEs with a whole job post mostly measures style and length. The gap between the evidence-based and no-evidence versions (6 vs 4 in the top 10) is small, one candidate and 10 jobs, so I would call it suggestive, not proven. The "suitable job" label is a crude proxy based on titles.

I also had to fix a mistake while building this: my first score gave 100% to any job that listed only two skills I knew. Adding a small prior (as if every job also asked for two things I cannot verify) fixed that.

**Is the learning plan targeted?** The top 6 recommended skills would lift the average match across my top 30 jobs by 4.9 points. The same number of random skills lifts it by 0.7 points on average (95th percentile 1.6). So the plan is about 7 times better than guessing. This is a simulation that assumes I could really demonstrate those skills.

## How it works

- `jobmatch/skills.py`: a transparent dictionary of 94 skills and the words people use for each. You can see exactly which words triggered a skill.
- `jobmatch/extract.py`: weights each skill in a job (required 1.0, mentioned 0.7, nice to have 0.5) from the headings it appears under, and reads the years of experience asked for.
- `jobmatch/candidate.py`: builds the evidence from a resume and repository folders (it reads imports, SQL, Dockerfiles, CI files, tests and READMEs).
- `jobmatch/match.py`: scores each job, lists matched skills and gaps, filters by experience, and builds the learning plan and resume suggestions.
- `fetch_jobs.py` downloads public job posts. `evaluate.py` runs the measurements. `report.py` writes the report.

## Run it

```bash
pip install -r requirements.txt
mkdir data
python fetch_jobs.py          # downloads about 1,200 public job posts into data/jobs.json
RESUME_PDF=my_resume.pdf REPOS_DIR=path/to/my/repos python evaluate.py
python report.py
python -m pytest tests -q     # 23 tests
```

## Data and credits

Job posts come from three public job APIs: [Remote OK](https://remoteok.com), [Himalayas](https://himalayas.app) and [Arbeitnow](https://www.arbeitnow.com). The posts belong to those sites and their employers, so the downloaded file is not in this repository and each result links back to the original post.

## Limits

- The skill dictionary is hand-written, so a skill that is not in it is invisible. It covers 94 mainstream tech skills.
- The tool only sees code in the folders you point it at. My n8n automation projects live in older repositories I did not include, so "automation" shows up as only claimed.
- "Demonstrated" means used in code, not used well. It cannot judge quality.
- The job posts are mostly remote roles from Europe and the US. They are real, but not a sample of the Indian entry-level market.
- Seniority is read from "N years" phrases and, where available, the site's own label.

Harshit Bihani
