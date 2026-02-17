---
name: resume-pipeline
description: |
  Automated resume generation pipeline for Nuthan Reddy (Albertsons, Fortune 50 grocery retailer).
  System: Scrape JDs → pre-filter (Gemini Flash) → generate resume (DeepSeek) → evaluate (Gemini) → iterate until PASS → submit.
  All resumes translate JD requirements into Albertsons work context across 7 internal departments.
  MANDATORY TRIGGERS: resume pipeline, job application, Albertsons resume, mappability, JD classifier, resume generation, DeepSeek writer, Gemini evaluator, resume iteration, job scraper, HiringCafe, bulk apply, automated applications, resume scoring, skip/apply decision, resume prompt, writer prompt, evaluator prompt, iteration prompt, resume defects, pipeline fixes
---

# Resume Pipeline Skill

## Immediate Context Load

On activation, ALWAYS read these references first:

1. **`references/handoff_context.md`** — Complete project state: 5 defects, 13 fixes, 17 packages analyzed, mappability framework, 7 departments, user corrections, next steps
2. **`references/jd_classifier_prompt.txt`** — Pre-filter prompt for Gemini Flash (SKIP/APPLY decisions)

Read prompts ONLY when modifying or analyzing them:

3. `references/writer_prompt_v3.txt` — DeepSeek writer prompt (337 lines)
4. `references/evaluator_prompt_v3.txt` — Gemini evaluator prompt (386 lines)
5. `references/iteration_prompt_v3.txt` — DeepSeek iteration prompt (217 lines)

## Pipeline Architecture

```
JD scrape (Scrapy+Playwright)
    ↓
Pre-filter (Gemini Flash, ~$0.001/JD) → SKIP or APPLY
    ↓ (APPLY only)
DeepSeek writer → resume JSON
    ↓
Jinja2 template → LaTeX → PDF
    ↓
Gemini evaluator → score (0-100) + verdict (PASS/FAIL)
    ↓ (FAIL)
DeepSeek iteration → revised JSON → back to Gemini (up to 5x)
    ↓ (PASS)
Submit application
```

## Core Principle

**Domain determines mappability, NOT tech stack.**

Python at a bank → APPLY (maps to Payments dept). Python at a game studio → SKIP (no department). Same skills, different domain. Domain is what matters.

Common roles (SWE, Data Engineer, Cloud Engineer, Full-Stack, DevOps, ML Engineer) → always Tier 1-2 APPLY unless the domain is a kill-domain.

## 7 Albertsons Departments (Translation Targets)

| # | Department | Maps FROM |
|---|-----------|-----------|
| 1 | Pharmacy & Health | Healthcare IT, HIPAA, clinical data, insurance claims |
| 2 | E-Commerce & Digital | Marketplace, mobile apps, delivery logistics |
| 3 | Payments & Financial Ops | Fintech, banking, fraud, POS (C++17 Verifone SDK) |
| 4 | Supply Chain & Distribution | Logistics, warehouse, fleet routing, demand planning |
| 5 | Customer 360 Data & Analytics | Data science (ANY domain), ML, recommendations, A/B testing |
| 6 | IT Infrastructure & Security | Cloud, DevOps, SRE, DX tooling, networking, SaaS backend |
| 7 | Marketing & Store Ops | Adtech (Media Collective, 100M+ profiles), growth marketing |

**Kill domains** (always SKIP): game dev, nuclear/defense, aerospace/satellite, biotech research, hardware design (VHDL/FPGA), pure academic research.

**Thresholds**: >=65% mappable → APPLY. 50-64% → APPLY_WITH_CAUTION. <50% → SKIP.

## 5 Known Defects (Documented, Not Yet Fixed)

1. **CRITICAL — Evaluator tenure**: "8 months" in 4 places (lines 167, 204, 222, 377) should be "20 months"
2. **CRITICAL — Code checks score not verdict**: `score >= 85` ignores verdict. JPMorgan (90, FAIL) submitted with CRITICAL defects
3. **HIGH — Fixed number pool**: 8 numbers listed 3x. 9+ metrics needed = guaranteed duplication
4. **HIGH — Skills contradiction**: Writer allows education-based skills; evaluator requires 100% in bullets
5. **HIGH — Metric range**: Cap says 15-40% but examples list 58-73%

All 13 specific line-by-line changes documented in `references/handoff_context.md` under "COMPLETE CHANGE LIST".

## User Corrections (CRITICAL — Never Repeat)

1. C/C++ CAN be done at Albertsons — POS terminals use Verifone SDK (C++17)
2. DX teams CAN be done — Walmart has DX Platform, Target has TAP, Albertsons has 1,000+ engineers
3. Advertising CAN be done — Albertsons Media Collective (retail media network, TransUnion partnership)
4. Seniority titles don't cause ATS auto-reject — stripping "Senior" is correct but not a rejection cause
5. v3 prompts ALREADY have rules for: duplicate metrics (4 rules), cloud matching (lines 44-67), metric caps (line 190), collaborative language (lines 126-151), education skills (lines 242-265). DeepSeek just ignores them.
6. Education-based orphaned skills are intentionally allowed by the writer prompt

## Candidate Profile

- **Name**: Nuthan Reddy
- **Current employer**: Albertsons (Fortune 50, 2,300 stores, $70B revenue, 8M weekly customers)
- **Tenure**: May 2024 – Present (~20 months as of Feb 2026)
- **Prior**: ValueLabs (May 2020 – July 2023)
- **Education**: MS Computer Science
- **Resume packages**: `Google Auto Internet/` folder — 17 packages, each with JD.txt, resume.tex, NuthanReddy.pdf, workflow_trace.txt, iterations.json, meta.json

## What To Do Next

1. Apply the 13 changes to the 3 prompt files (writer, evaluator, iteration)
2. Fix pipeline code: change `score >= 85` to `verdict == "PASS"`, add LaTeX post-processing regex
3. Implement pre-filter (`jd_classifier_prompt.txt`) as Layer 1 before DeepSeek
4. Re-run on 17 existing JDs to verify improvements
5. Scale to new JDs

## Documents Created (In User's Google Drive)

| File | Contents |
|------|----------|
| `Resume_Pipeline_Master_Analysis.docx` | 7-page master: framework, departments, defects, all 13 fixes, future problems |
| `Pipeline_Breakdown_Analysis.docx` | 3 failure points with evidence tables |
| `jd_classifier_prompt.txt` | Pre-filter prompt for Gemini Flash |
| `Resume_Defect_Analysis.xlsx` | 4-sheet: per-resume analysis, defects, fixes, skip decisions |
| `Score_Change_Research_Memo.docx` | C/C++ at retail, DX teams research |
| `Job_Application_Analysis.xlsx` | 8-sheet: Gmail analysis of 27 applications |
| `CORRECTED_Analysis.md` | Corrections based on user feedback |
| `HANDOFF_CONTEXT.md` | Complete session handoff file |
