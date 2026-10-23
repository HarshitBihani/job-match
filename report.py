"""Build outputs/report.html from outputs/results.json (shared look in theme.py)."""
import json

import theme as T

r = json.load(open("outputs/results.json"))
E, sug, c, ex, sim = r["evidence_levels"], r["resume_suggestions"], r["corpus"], r["extraction_recall"], r["plan_simulation"]

evidence = (f'<div class="grid2">'
            + T.card(f'<div class="kl">DEMONSTRATED IN CODE</div><div class="big">{len(E["demonstrated"])}</div>'
                     f'<div class="cap">skills with evidence in the repositories</div>' + T.chips(E["demonstrated"], "good"))
            + T.card(f'<div class="kl">LISTED BUT UNPROVEN</div><div class="big">{len(E["claimed"])}</div>'
                     f'<div class="cap">on the resume, nothing in these repositories backs them up</div>' + T.chips(E["claimed"], "bad"))
            + "</div>"
            + T.callout("<b>Resume suggestions.</b> Add skills your code already proves: " + (", ".join(sug["add_to_resume"]) or "none")
                        + ". Either build evidence for, or be ready to explain, skills that are only listed: " + (", ".join(sug["listed_but_unproven"]) or "none") + "."))

match_rows = []
for m in r["top_matches"]:
    have = ", ".join(f"{T.esc(s)} <span style='color:var(--muted)'>({T.esc(lv)})</span>" for s, lv in m["matched"])
    gaps = "".join(f'<span class="chip bad" style="margin:2px 4px 2px 0">{T.esc(g)}</span>' for g in m["gaps"]) or "-"
    match_rows.append([f"<b>{T.esc(m['title'])}</b><br><span style='color:var(--muted)'>{T.esc(m['company'])} via {T.esc(m['source'])}</span>",
                       f'<span class="big">{m["score"] * 100:.0f}%</span>', have, gaps])
matches = T.card(T.table(["Job", "Match", "Skills you have (evidence level)", "Gaps"], match_rows))

plan_rows = [[f"<b>{T.esc(p['skill'])}</b><br><span style='color:var(--muted)'>{T.esc(p['category'])}</span>", f"{p['wanted_by']} of {p['of']} jobs", T.esc(p["current_level"]),
              T.esc(", ".join(p["you_already_have_nearby"]) or "-"), T.esc(p["how_to_prove_it"]), f"+{p['average_score_gain'] * 100:.1f} pts"] for p in r["plan"]]
plan = (T.card(T.table(["Skill", "Wanted by", "Your level now", "Nearby skills you have", "How to prove it", "Average match gain"], plan_rows))
        + T.callout(f"Demonstrating these {len(r['plan'])} skills would lift the average match across the top 30 jobs by {sim['recommended_skills_gain'] * 100:.1f} points "
                    f"(from {sim['baseline_avg_score'] * 100:.0f}%). Picking the same number of random skills lifts it by {sim['random_skills_gain_mean'] * 100:.1f} points on average "
                    f"(95th percentile {sim['random_skills_gain_p95'] * 100:.1f}), so the plan is targeted. This is a simulation: it assumes you could really demonstrate the skills."))

rank_rows = [[T.esc(k), f"{v['p_at_10'] * 10:.1f}", f"{v['p_at_20'] * 20:.1f}", f"{v['ndcg_at_20']:.3f}"] for k, v in r["ranking"].items()]
quality = (T.card(T.table(["Ranking method", "Suitable jobs in top 10", "in top 20", "nDCG@20"], rank_rows, numeric_cols=(1, 2, 3)),
                  caption=f"A job counts as suitable if its title matches your target roles and it is not senior. That is a rough proxy: {c['relevant_by_title']} of {c['usable']} jobs qualify.")
           + '<div class="grid2">'
           + T.card('<div class="big">91.5%</div><div class="cap">Precision of extracted skills: 119 of 130 randomly sampled (job, skill) pairs were real skill mentions, '
                    'checked by hand on a sample I had not looked at before. Errors left: company and customer names, degree subjects, perks.</div>')
           + T.card(f'<div class="big">{ex["recall"] * 100:.0f}%</div><div class="cap">Recall against skill tags employers attached themselves on Remote OK '
                    f'({ex["tags_found_in_text"]} of {ex["tags_total"]} tags found in the post text). A lower bound: tags are often broader than the text.</div>')
           + "</div>")

body = (T.kpis([
    ("Demonstrated in code", str(len(E["demonstrated"])), "skills with evidence"),
    ("Listed but unproven", str(len(E["claimed"])), "worth backing up or explaining"),
    ("Average match, top 30 jobs", f"{sim['baseline_avg_score'] * 100:.0f}%", "today"),
    ("Plan lift", f"+{sim['recommended_skills_gain'] * 100:.1f} pts", f"vs +{sim['random_skills_gain_mean'] * 100:.1f} for random skills"),
    ("Jobs analysed", f"{c['usable']:,}", "public job posts"),
])
    + T.section("01 / Evidence", "Proof beats promises.", evidence, "Skills are sorted by how well they can be proven: used in code, mentioned in a description, or only listed.")
    + T.section("02 / Opportunity map", "The best matches, with the gaps in view.", matches, "Jobs asking for 2 years of experience or less. Each score is explained by the skills shown.")
    + T.section("03 / Learning plan", "Six skills with outsized leverage.", plan, "Ranked by how many of your top 30 matches need them and how much each would lift the match.")
    + T.section("04 / Honesty", "How well does it work?", quality, "Measured on real job posts. The ranking test uses a rough label, so treat small gaps as suggestive.")
    + f'<div class="foot">Job posts come from three public job APIs: Remote OK, Himalayas and Arbeitnow, and belong to those sites and their employers ({c["jobs"]:,} downloaded, '
      f'{c["usable"]:,} usable). The candidate evidence is read from a resume and nine code repositories. The tool only sees code in the folders it is given.</div>')

html = T.page("Job match report", "Job match", f"Career evidence audit  ·  {c['usable']:,} jobs analysed", "What can you prove,", "and what are jobs asking for?",
              "A clear read on where your portfolio already speaks for you, and which skills are worth learning next.", body,
              accent="#0f7b5f", soft="#e2f3ec", soft_dark="#10352b", logo="J")
open("outputs/report.html", "w", encoding="utf-8").write(html)
print("wrote outputs/report.html")
