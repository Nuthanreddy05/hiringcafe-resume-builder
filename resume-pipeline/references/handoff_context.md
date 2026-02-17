# RESUME PIPELINE — COMPLETE SESSION HANDOFF
# Upload this file to a new chat for full context continuity.
# Created: Feb 13, 2026 | Model: Opus 4.6

---

## WHAT THIS PROJECT IS

An automated job application system for Nuthan Reddy:
1. **Scraper** (Scrapy + Playwright) scrapes JDs from HiringCafe
2. **Pre-filter** classifies JDs as SKIP or APPLY (not yet implemented)
3. **DeepSeek** (writer) generates a tailored resume in JSON
4. **Jinja2 template** converts JSON → LaTeX → PDF
5. **Gemini** (evaluator) scores the resume on 10 dimensions (0-100)
6. If FAIL → **DeepSeek** (iteration prompt) revises → loop back to Gemini
7. If PASS → submit application

The candidate works at **Albertsons** (Fortune 50 grocery retailer, 2,300 stores, $70B revenue, 8M weekly customers). All resumes translate JD requirements into Albertsons work context.

---

## FILES WE CREATED (all in the user's Google Drive folder)

| File | What It Contains |
|------|-----------------|
| `Resume_Pipeline_Master_Analysis.docx` | 7-page master document: mappability framework, 7 departments, skip/apply thresholds, pipeline defects, all 13 fixes, future problems, verification |
| `Pipeline_Breakdown_Analysis.docx` | Detailed analysis of 3 pipeline failure points with evidence tables |
| `jd_classifier_prompt.txt` | The pre-filter prompt for Gemini Flash — classifies JDs as SKIP/APPLY before DeepSeek runs |
| `Resume_Defect_Analysis.xlsx` | 4-sheet Excel: per-resume analysis, systemic defects, prompt fixes, skip decisions (NOTE: some "prompt fixes" in this file are WRONG — user corrected us that the prompts already have those rules) |
| `Score_Change_Research_Memo.docx` | Research on C/C++ at retail, DX teams, why mappability scores changed |
| `Job_Application_Analysis.xlsx` | 8-sheet Excel: Gmail analysis of 27 applications, rejection patterns, ATS timing |
| `CORRECTED_Analysis.md` | Corrections to initial analysis based on user feedback |

---

## THE 3 PROMPTS (v3, updated Jan 29, 2026)

### 1. Writer Prompt (`resume_json_prompt_v3.txt`) — 337 lines
- Tells DeepSeek how to generate resume JSON
- Has 7 Albertsons departments, translation framework, bullet patterns
- Has 12-step validation checklist
- **KEY RULES THAT WORK:** Department mapping, toddler test, collaborative language, technology era, project timelines
- **KEY RULES DEEPSEEK IGNORES:** Metric uniqueness (4 separate rules, all violated in 15/17 packages), LaTeX escaping (100% violation rate)

### 2. Evaluator Prompt (`resume_evaluator_prompt_v3.txt`) — 386 lines
- Tells Gemini how to score resumes on 10 dimensions (0-10 each, max 100)
- 5 auto-fail conditions
- Verdict logic: PASS = score ≥80 AND zero CRITICAL issues. FAIL = score <80 OR any CRITICAL issue.

### 3. Iteration Prompt (`resume_iteration_prompt_v3.txt`) — 217 lines
- Tells DeepSeek how to surgically fix issues Gemini flagged
- "Fix only what's broken. Preserve what works."

---

## THE 5 DEFECTS FOUND

### DEFECT 1 (CRITICAL): Evaluator Tenure Mismatch
- Evaluator prompt header says "20 months" but scoring rubrics say "8 months" in 4 places (lines 167, 204, 222, 377)
- Copy-paste leftover from older prompt version
- Causes Gemini to judge 20 months of work against 8-month standard
- metric_realism scores 2-4/10 on almost every package as a result
- Also: Gemini says "approximately 2 months" because it doesn't know current date
- **FIX:** Change "8 months" → "20 months" at 4 locations. Add current date context after line 14.

### DEFECT 2 (CRITICAL): Code Checks Score Instead of Verdict
- Pipeline code uses `score >= 85` to stop iterating
- Ignores the `verdict` field entirely
- JPMorgan (score 90, verdict FAIL), DailyPay (88, FAIL), Ziphire (85, FAIL) — all submitted with CRITICAL defects
- Mathematical impossibility: one bad dimension out of 10 can never drop score below 85
- **FIX:** Change to `verdict == "PASS"`. One line of code.

### DEFECT 3 (HIGH): Fixed Number Pool Guarantees Duplicates
- Writer prompt lists same 8 numbers (23%, 27%, 34%, 41%, 47%, 58%, 67%, 73%) three times
- DeepSeek treats as whitelist. 9+ metrics needed, 8 numbers available = guaranteed duplication
- Gemini catches duplicates only 29% of the time
- **FIX:** Remove fixed list. "Generate unique irregular numbers, never reuse."

### DEFECT 4 (HIGH): Writer/Evaluator Skills Contradiction
- Writer: "Education-based skills without bullet evidence are valid" (lines 242-260)
- Evaluator: "100% of skills must appear in bullets. Zero orphaned skills." (line 264)
- These directly fight each other
- **FIX:** Align one way or the other.

### DEFECT 5 (HIGH): Metric Range Contradiction
- Writer line 190: "Performance improvements 15-40%"
- Writer lines 88/163/192: Lists 58%, 67%, 73% as valid irregular numbers
- DeepSeek uses the larger numbers, Gemini penalizes them
- **FIX:** Make consistent.

---

## COMPLETE CHANGE LIST (13 Changes)

| # | File | Priority | Line | Current | Change To |
|---|------|----------|------|---------|-----------|
| 1 | evaluator_prompt | CRITICAL | 167 | "realistic for 8 months" | "realistic for 20 months" |
| 2 | evaluator_prompt | CRITICAL | 204 | "for an 8-month tenure" | "for a 20-month tenure" |
| 3 | evaluator_prompt | CRITICAL | 222 | "unrealistic for 8 months" | "unrealistic for 20 months" |
| 4 | evaluator_prompt | CRITICAL | 377 | "An 8-month tenure" | "A 20-month tenure" |
| 5 | evaluator_prompt | CRITICAL | +14 | [missing] | Add: "Current Date: Feb 2026. May 2024 to Present = 20 months." |
| 6 | pipeline code | CRITICAL | loop | if score >= 85 | if verdict == "PASS" |
| 7 | evaluator_prompt | HIGH | +366 | [missing] | Add auto-fail #6: Metric Duplication |
| 8 | writer_prompt | HIGH | 88 | (23%, 27%, 34%...73%) | "Generate unique irregular numbers, never reuse" |
| 9 | writer_prompt | HIGH | 163 | 23%, 27%, 34%...73% | "any non-round % (e.g. 19%, 31%, 42%, 53%...)" |
| 10 | writer_prompt | HIGH | 192 | (23%, 27%, 34%...73%) | "Generate UNIQUE number for each metric" |
| 11 | writer_prompt | HIGH | 190 | "improvements 15-40%" | "improvements 15-45%, up to 60-75% for automation" |
| 12 | evaluator_prompt | MEDIUM | 264 | "100% of skills in bullets" | "90%+. Education-based skills are valid." |
| 13 | iteration_prompt | MEDIUM | 35 | (23%, 27%...73%) | "Pick any non-round number not already used" |

---

## THE MAPPABILITY FRAMEWORK (Core Concept)

### Rule: Domain determines mappability, NOT tech stack.
- Python at a gaming company → SKIP (domain = gaming, no Albertsons department)
- Python at a bank → APPLY (domain = fintech, maps to Payments department)
- Same language. Different domain. Domain is what matters.

### Common roles (Software Engineer, Data Engineer, Full-Stack, DevOps, Cloud Engineer, ML Engineer) are ALWAYS Tier 1-2 unless the domain is a kill-domain.

### 7 Albertsons Departments (Translation Targets):
1. **Pharmacy & Health** ← Healthcare IT, HIPAA, clinical data, insurance claims
2. **E-Commerce & Digital** ← Marketplace, mobile apps, delivery logistics
3. **Payments & Financial Ops** ← Fintech, banking, fraud detection, POS (C++17 Verifone)
4. **Supply Chain & Distribution** ← Logistics, warehouse, fleet routing
5. **Customer 360 Data & Analytics** ← Data science (ANY domain), ML, recommendations, A/B testing
6. **IT Infrastructure & Security** ← Cloud, DevOps, SRE, DX tooling, networking
7. **Marketing & Store Ops** ← Adtech (Media Collective), growth marketing, content

### Kill Domains (ALWAYS skip):
- Game development (Unity, Unreal, game physics)
- Nuclear / defense (clearance, SCADA, Modbus)
- Aerospace / satellite
- Biotech RESEARCH (≠ pharmacy operations)
- Hardware design (VHDL, FPGA, chip design)
- Pure academic research

### Decision Thresholds:
- ≥ 65% mappable → APPLY
- 50-64% → APPLY WITH CAUTION
- < 50% → SKIP

---

## USER CORRECTIONS (CRITICAL — Do Not Repeat These Mistakes)

1. **C/C++ CAN be done at Albertsons** — POS terminals use Verifone SDK (C++17), payment gateway firmware
2. **DX teams CAN be done** — Walmart has DX Platform, Target has TAP, Albertsons has 1,000+ engineers
3. **Advertising CAN be done** — Albertsons Media Collective is a real retail media network (adtech, 100M+ shopper profiles, TransUnion partnership)
4. **Seniority titles don't cause ATS auto-reject** — Stripping "Senior" is correct practice but not a rejection reason
5. **The v3 prompts ALREADY have rules for:** duplicate metrics (4 rules), cloud platform matching (lines 44-67), metric realism caps (line 190), collaborative language (lines 126-151), education-based skills (lines 242-265). Do NOT tell the user these rules are "missing" — they exist, DeepSeek just doesn't follow them.
6. **Orphaned skills partially wrong:** Education-based skills WITHOUT bullet evidence are intentionally allowed by the writer prompt. Not all "orphaned" skills are defects.

---

## 17 RESUME PACKAGES ANALYZED (all dated Feb 2, 2026)

Location: `Google Auto Internet/` folder. Each has: JD.txt, resume.tex, NuthanReddy.pdf, workflow_trace.txt, iterations.json, meta.json

| Company | Score | Verdict | Iters | Tier | Decision |
|---------|-------|---------|-------|------|----------|
| JPMorgan | 90 | FAIL | 1 (BUG) | 2 | APPLY |
| DailyPay | 88 | FAIL | 1 (BUG) | 2 | APPLY |
| Ziphire | 85 | FAIL | 1 (BUG) | 3 | APPLY |
| FundraiseUp | 89 | PASS | 1 | 2 | APPLY |
| Thumbtack | 99 | PASS | 1 | 2 | APPLY |
| Cognizant | 99 | PASS | 1 | 2 | APPLY |
| Google | 93 | PASS | 1 | 3 | CAUTION |
| Optum | 92 | PASS | 1 | 2 | APPLY |
| MongoDB | 95 | PASS | 1 | 2 | APPLY |
| MLabs | 95 | PASS | 1 | 3 | APPLY |
| DTC | 97 | PASS | 1 | 3 | APPLY |
| Atlas | 95 | PASS | 1 | 2 | APPLY |
| UPMC | 89 | PASS | 1 | 2 | APPLY |
| Westinghouse | 98 | PASS | 2 | 4 | SKIP |
| Knowtion | 91 | PASS | 2 | 2 | APPLY |
| Nex | 98 | PASS* | 2 | 4 | SKIP |
| F. Schumacher | 88 | FAIL | 2 | 1 | APPLY |

*Nex iter 2 had date fabrication issue

---

## FUTURE PROBLEMS AT SCALE (100+ jobs/week)

1. **Domain drift** — New domains appear (AR/VR, quantum, robotics). Update kill-list monthly.
2. **Metric exhaustion** — Pre-generate unique metric sets per resume, don't rely on LLM.
3. **Department saturation** — Track which department was used per company to avoid duplicates.
4. **Tenure staleness** — Compute tenure dynamically, never hardcode "20 months."
5. **ATS fingerprinting** — Vary bullet patterns, rotate department narratives.
6. **Gemini model updates** — Maintain 5-resume test set for regression testing.
7. **LaTeX escaping** — Add post-processing regex (% → \%, $ → \$) in code, not prompt.

---

## WHAT TO DO NEXT

1. Apply the 13 changes to the 3 prompt files
2. Fix the pipeline code (verdict check + LaTeX post-processing)
3. Implement the pre-filter (jd_classifier_prompt.txt) as Layer 1 before DeepSeek
4. Re-run on the 17 existing JDs to verify improvements
5. Scale to new JDs

---

## FILES THE USER HAS UPLOADED (in /mnt/uploads/)
- resume_json_prompt_v3.txt (writer prompt)
- resume_iteration_prompt_v3.txt (iteration prompt)
- resume_evaluator_prompt_v3.txt (evaluator prompt)
