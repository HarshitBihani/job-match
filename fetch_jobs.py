"""Download a snapshot of public job posts into data/jobs.json.

Sources (both free public APIs): Remote OK (https://remoteok.com, jobs must be credited to Remote OK and linked back, which the
`url` field allows) and Arbeitnow (https://www.arbeitnow.com). The snapshot is for local analysis only and is not committed to the
repository, because the posts belong to those sites and their employers.
"""
import html
import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (portfolio research project)"}


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))


COMMON = set("the and with to of for you our will your are is in on as we that this be a an or by from have has team work experience".split())


def is_english(t: str) -> bool:
    words = re.findall(r"[a-zA-Z']+", t.lower())[:400]
    return len(words) > 40 and sum(w in COMMON for w in words) / len(words) > 0.25


def clean(h: str) -> str:
    h = html.unescape(h or "")          # some feeds escape their HTML twice
    h = re.sub(r"(?i)<\s*(br|/p|/li|/h\d|/div|/ul)\s*/?>", "\n", h or "")
    h = re.sub(r"(?i)<li[^>]*>", "- ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def main():
    jobs = []
    for j in get("https://remoteok.com/api")[1:]:
        jobs.append(dict(source="Remote OK", title=j.get("position", ""), company=j.get("company", ""), url=j.get("url", ""), text=clean(j.get("description", "")),
                         tags=j.get("tags", [])))
    for page in (1, 2, 3):
        try:
            for j in get(f"https://www.arbeitnow.com/api/job-board-api?page={page}")["data"]:
                jobs.append(dict(source="Arbeitnow", title=j["title"], company=j["company_name"], url=j["url"], text=clean(j["description"]), tags=j.get("tags", [])))
        except Exception as e:
            print("page", page, "failed:", e)
    queries = ["data analyst", "data scientist", "machine learning engineer", "data engineer", "python developer", "backend engineer",
               "automation engineer", "software engineer", "business analyst", "ai engineer", "junior developer", "analytics engineer"]
    for q in queries:
        for page in range(1, 6):
            try:
                res = get("https://himalayas.app/jobs/api/search?q=" + q.replace(" ", "%20") + f"&page={page}")["jobs"]
            except Exception as e:
                print("himalayas", q, page, "failed:", e)
                break
            for j in res:
                jobs.append(dict(source="Himalayas", title=j["title"], company=j["companyName"], url=j["applicationLink"] or j["guid"], text=clean(j["description"]),
                                 tags=j.get("categories", []), seniority=", ".join(j.get("seniority") or [])))
    seen, uniq = set(), []
    for j in jobs:
        key = (j["title"].lower(), j["company"].lower())
        if key not in seen and len(j["text"]) > 300 and is_english(j["text"]):
            seen.add(key)
            uniq.append(j)
    json.dump(uniq, open("data/jobs.json", "w", encoding="utf-8"), indent=1)
    print(len(uniq), "jobs saved")


if __name__ == "__main__":
    main()
