# JOB APPLICATION AUTOMATION - MASTER CONTEXT
## CANDIDATE PROFILE
**Name:** Nuthan Reddy Vaddi Reddy
**Email:** nuthanreddy001@gmail.com
**Phone:** +1 682-406-5646
**LinkedIn:** linkedin.com/in/nuthan-reddy-vaddi-reddy
**GitHub:** github.com/Nuthanreddy05
**Current Status:**
- International student on STEM OPT (expires May 2025)
- Seeking H1B sponsorship
- Currently employed at Albertsons (Dallas, TX)
- 4 years of software engineering experience
**Target Roles:**
- Software Engineer (Backend, Frontend, Full-stack)
- Data Engineer
- Cloud Engineer
- AI/ML Engineer
- Data Analyst
**Location Preferences:**
1. Dallas, TX (primary)
2. Remote (USA)
3. Open to relocation
**Compensation Range:** $90,000 - $130,000
---
## SCREENING QUESTION DEFAULTS
### Generic Questions (Always Same Answer):
| Question Pattern | Answer |
|-----------------|--------|
| Work authorization? | Yes (STEM OPT, authorized until May 2025) |
| Require sponsorship? | Yes (H1B sponsorship needed) |
| Years of experience? | 4 |
| Desired salary? | $90,000-$130,000 |
| Available start date? | 2 weeks notice OR Immediately |
| Willing to relocate? | Yes |
| US Citizen? | No |
| Security clearance? | No |
### Role-Specific Questions (Context-Aware):
**Logic:**
1. Parse question to extract skill/technology
2. Check if mentioned in BOTH JD.txt AND resume.txt
3. If both → Answer with years from resume
4. If only JD → "Familiar, willing to learn"
5. If neither → "No" (be honest)
**Examples:**
**Q:** "Do you have React experience?"
**Logic:** Check resume.txt for "React" → Found "React 4+ years"
**Answer:** "Yes, 4+ years"
**Q:** "Years of AWS experience?"
**Logic:** Check resume.txt → Found "AWS services including EC2, S3, Lambda"
**Answer:** "3 years"
**Q:** "Describe your CI/CD experience"
**Logic:** Search resume.txt for "CI/CD" → Found relevant project
**Answer:** "Built CI/CD pipelines using Jenkins and GitLab, reduced deployment time by 40%"
---
## EMAIL PATTERNS
### Rejection Email Indicators:
**Subject lines that mean rejection:**
- "Thank you for your application"
- "Update on your application"
- "We've decided to move forward with other candidates"
- "Application status update"
- "Your application for [Job Title]"
**Body text patterns:**
- "not moving forward"
- "other candidates more closely match"
- "position has been filled"
- "decided to pursue other applicants"
- "will keep your resume on file"
- "encourage you to apply for future openings"
**Companies that send automated rejections:**
- Workday-based ATS → Rejection within 24 hours (usually auto-filter)
- Greenhouse → Rejection within 48-72 hours
- Lever → Manual review, 1-2 weeks
### Positive Response Indicators:
**Subject lines:**
- "Next steps in our hiring process"
- "Interview invitation"
- "Scheduling your interview"
**Body text:**
- "would like to schedule"
- "move you to the next round"
- "interested in speaking with you"
---
## APPLICATION WORKFLOW (STEP-BY-STEP)
### Phase 1: Job Scraped (job_auto_apply.py already does this)
```
Input: Hiring Cafe search results
Output: Folder with apply_url.txt, JD.txt, resume.txt, NuthanReddy.pdf
Status: "ready_to_apply"
```
### Phase 2: Application Submission (NEW)
```
1. Read files from folder
2. Launch browser (Playwright-Stealth, headless=False for debugging)
3. Navigate to apply_url
4. Screenshot: initial page load
5. Analyze form structure (Gemini vision)
6. Fill basic info:
- Name: Nuthan Reddy Vaddi Reddy
- Email: nuthanreddy001@gmail.com
- Phone: +1 682-406-5646
- LinkedIn: linkedin.com/in/nuthan-reddy-vaddi-reddy
7. Upload resume: NuthanReddy.pdf from SAME folder
8. Screenshot: after upload
9. Answer screening questions (use logic from MASTER_CONTEXT.md)
10. Screenshot: after each question
11. Click Submit
12. Screenshot: confirmation page
13. Save all to: audit/audit_log.csv + screenshots/
14. Update status: "submitted"
```
### Phase 3: QA Audit (IMMEDIATE)
```
1. Read audit_log.csv
2. Compare with resume.txt + JD.txt
3. Check for discrepancies:
- Years claimed vs resume
- Skills claimed vs resume
- Answers aligned with JD requirements
4. Generate qa_report.json:
- quality_score: 0-100
- issues: list of problems
- recommendation: APPROVE or REVIEW_MANUALLY
5. If score < 80 → Flag for manual review
```
### Phase 4: Rejection Monitoring (WEEKLY)
```
1. Scan Gmail for rejection emails (past 7 days)
2. For each rejection:
- Extract company name
- Extract job title
- Extract reason (if provided)
- Link to original application folder
3. Analyze patterns:
- Which industries reject most?
- Which ATS platforms auto-reject?
- Common rejection reasons?
4. Generate improvement report
```
---
## SUCCESS PATTERNS (WHAT WORKS)
### High Success Rate Jobs:
- Companies explicitly stating "visa sponsorship available"
- Startups (more flexible on sponsorship)
- Companies with existing H1B sponsorship history
- Roles emphasizing skills over credentials
### Application Quality Indicators:
- QA score ≥ 85 → 70% response rate
- Resume tailored to JD → 60% higher callback
- Answering "4 years experience" vs "2-3 years" → Better match
### Timing Matters:
- Apply within 48 hours of job posting → 3x higher response
- Avoid applying on weekends (lower visibility)
---
## FAILURE PATTERNS (WHAT TO AVOID)
### Auto-Rejection Triggers:
- "US Citizen required" in JD → 100% rejection
- "Security clearance required" → 100% rejection
- Asking $130K at early-stage startups → High rejection
- Graduation date after August 2025 → New grad filter
### Industries with Low Success:
- Defense contractors (clearance required)
- Government agencies (citizenship required)
- Oil & Gas (industry exclusion)
- Biotech/Pharma (unless software role)
### ATS-Specific Issues:
- Workday → Aggressive keyword filters (need exact matches)
- Taleo → Often requires citizenship declaration upfront
- Greenhouse → Manual review (better for H1B candidates)
---
## AGENT COORDINATION
### Agent 1 (Application Bot)
Must:
- Read this MASTER_CONTEXT.md before each application
- Use screening question defaults from above
- Apply role-specific logic for technical questions
- Take screenshots at EVERY step (for QA verification)
### Agent 2 (QA Auditor)
Must:
- Read this MASTER_CONTEXT.md to understand expected behavior
- Cross-check claimed experience against resume.txt
- Flag discrepancies using severity: HIGH/MEDIUM/LOW
- Use DeepSeek reasoning to explain issues
### Agent 3 (Rejection Analyzer)
Must:
- Read this MASTER_CONTEXT.md to understand email patterns
- Parse rejection emails using patterns above
- Link rejections to original applications
- Analyze patterns weekly (not daily - need enough data)
---
## QUALITY THRESHOLDS
### QA Score Interpretation:
- **90-100:** Excellent - Strong match, high callback probability
- **80-89:** Good - Acceptable, proceed
- **70-79:** Fair - Review manually, may have issues
- **<70:** Poor - Likely has errors, manual review required
### Rejection Rate Benchmarks:
- **<15%:** Excellent (you're competitive)
- **15-30%:** Normal (standard rejection rate)
- **30-50%:** High (need to adjust strategy)
- **>50%:** Very High (serious issues, stop and analyze)
---
## TELEGRAM NOTIFICATIONS
### Real-Time Alerts:
- ✅ Application submitted successfully
- ⚠️ QA score < 80 (needs review)
- 🚨 Application failed (CAPTCHA, error, etc.)
### Daily Summary (8 PM):
- Total applications today: X
- Average QA score: Y/100
- Flagged for review: Z
- Common issues: [list]
### Weekly Report (Sunday 6 PM):
- Applications this week: X
- Rejections: Y (Z% rate)
- Top rejection reasons: [list]
- Recommended adjustments: [list]
---
## FILE STRUCTURE REFERENCE
```
~/Desktop/Google Auto/
├── company_jobid_001/
│ ├── apply_url.txt
│ ├── JD.txt
│ ├── resume.txt
│ ├── NuthanReddy.pdf
│ ├── meta.json (status: ready_to_apply → submitted → rejected/no_response)
│ ├── audit/
│ │ ├── audit_log.csv
│ │ ├── screenshots/
│ │ │ ├── 01_loaded.png
│ │ │ ├── 02_filled.png
│ │ │ └── 03_submitted.png
│ ├── qa_report.json
│ └── workflow_trace.txt
```
---
## CRITICAL RULES
1. **Never lie on applications** - If don't have a skill, say "No" or "Learning"
2. **Never apply to clearance jobs** - 100% rejection, waste of time
3. **Always upload resume from SAME folder** - Each resume is tailored
4. **Screenshot everything** - Proof of what was filled
5. **Context-aware answers** - Don't just keyword match, understand the question
---
END OF MASTER CONTEXT
