
import re
from typing import Tuple

# ============================================================================
# PATTERNS (Copied from HiringCafe Reference)
# ============================================================================

CITIZENSHIP_PATTERNS = [
    r"\bu\.?s\.?\s*citizen\b", r"\bus citizens?\s*only\b",
    r"\bcitizenship required\b", r"\bno sponsorship\b",
    r"\bno visa sponsorship\b",
    r"\bwithout\s+(?:company\s+)?sponsorship\b",
    r"\bwill not sponsor\b",
    r"\bnot eligible for(?:.*\b)?sponsorship\b",
    r"not able to offer.*sponsorship",
]

# ============================================================================
# Helper Functions
# ============================================================================

def safe_text(s: str) -> str:
    """Normalize whitespace"""
    return re.sub(r"\s+", " ", s).strip()

def normalize_tech_terms(text: str) -> str:
    """Fix common recruiter typos and normalize casing"""
    replacements = {
        r"\bjava script\b": "JavaScript",
        r"\breact[\s\.]?js\b": "React",
        r"\bnode[\s\.]?js\b": "Node.js",
        r"\bgit\b": "Git",
        r"\baws\b": "AWS",
        r"\bazur\b": "Azure", # Typos like 'Azur'
        r"\bkuber.*?s\b": "Kubernetes", # ubernetes
        r"\bdocker\b": "Docker",
        r"\bci\s*/\s*cd\b": "CI/CD",
        r"\bpostgres\b": "PostgreSQL",
    }
    for pat, rep in replacements.items():
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    return text

def clean_description(raw: str) -> str:
    """Remove UI noise from scraped text"""
    if not raw:
        return ""
    
    lines = [safe_text(x) for x in raw.splitlines() if safe_text(x)]
    
    blacklist = [
        "hiringcafe", "switch to ai", "log in", "sign in", "save search",
        "clear filters", "show all jobs", "talent network", "cookie",
    ]
    
    lines = [x for x in lines if not any(b in x.lower() for b in blacklist) and len(x) > 2]
    
    # Remove consecutive duplicates
    deduped = []
    prev = None
    for x in lines:
        if x != prev:
            deduped.append(x)
        prev = x
    
    text = "\n".join(deduped)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

# ============================================================================
# Main Cleaning Functions
# ============================================================================

def check_sponsorship_viability(text: str) -> Tuple[bool, str]:
    """
    Check if the job requires US Citizenship or strictly denies sponsorship.
    Returns (True, "") if safe, (False, reason) if blocked.
    """
    for pat in CITIZENSHIP_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return False, "Citizenship/sponsorship restriction found in JD."
    return True, ""

def trim_jd_smart(jd_text: str) -> str:
    """Section-based extraction with hard blocklists (Copied from Reference)"""
    
    # HARD BLOCKLIST: Remove entire sections with these headings
    drop_sections = [
        # Company marketing
        r'about (us|the company|our company|freese|cognizant|google|wipro|bayer|starbucks|netjets|boston scientific|zynga|cassaday)',
        r'our (culture|mission|values|story)',
        r'why (work for|join)',
        r'we are (committed to|transforming|proud)',
        r'level up your career',
        r'founded in \d{4}',
        r'downloaded over.*billion',
        r'manages approximately.*billion',
        r'recognized for.*barron.*forbes',
        r'fastest growing compan',
        
        # Compensation & Benefits SECTIONS
        r'benefits:?\s*$', r'perks:?\s*$',
        r'what we offer( you)?:?',
        r'what.?s in it for you:?',
        r'compensation details?:?',
        r'salary description:?',
        r'how .* supports you',
        r'comprehensive benefits',
        r'world-class benefits',
        
        # Legal & Compliance
        r'equal employment opportunity', r'eeo policy', r'eeo statement',
        r'equal opportunity employer',
        r'e-verify', r'e verify',
        r'privacy policy', r'applicant privacy', r'do not sell',
        r'accommodations for applicants',
        r'drug/alcohol policy', r'recruitment fraud',
        r'without regard to race',
        r'arrest or conviction records',
        r'fair chance act',
        r'at-will position',
        r'right to modify.*compensation',
        r'position is for an existing vacancy',
        
        # Application UI
        r'apply (now|for this job|with indeed)',
        r'application form',
        r'save job', r'email job', r'create alert',
        r'first name\*', r'last name\*', r'resume/cv\*',
        r'indicates a required field',
        r'attach.*dropbox.*google drive',
        r'what is your expected salary',
        
        # Site chrome/navigation
        r'similar jobs', r'view all jobs', r'job alerts', r'follow us',
        r'powered by', r'recaptcha', r'©', r'all rights reserved',
        r'privacy policy.*terms of service',
        r'back to (all )?jobs', r'return to list',
        r'share this opening',
        
        # Screening/Other
        r'background screening.*clearinghouse',
        r'application deadline.*days',
        r'work arrangement:?.*hybrid',
        r'scam.*phishing'
    ]
    
    # KEEP SECTIONS: Priority extraction
    keep_sections = [
        r'responsibilities', r'what you.ll do', r'duties', r'how you.ll contribute',
        r'requirements', r'qualifications', r'minimum qualifications',
        r'preferred qualifications', r'preferred', r'nice to have',
        r'experience', r'education', r'skills', r'technical skills',
        r'what it takes', r'what you need', r'about you',
        r'tools', r'technologies', r'tech stack'
    ]
    
    # Split into lines
    lines = jd_text.split('\n')
    
    # Step 1: Remove sections with DROP headings
    filtered_lines = []
    skip_section = False
    skip_lines = 0
    
    for i, line in enumerate(lines):
        # Skip if in skip mode
        if skip_lines > 0:
            skip_lines -= 1
            continue
        
        line_lower = line.lower().strip()
        
        # Check if line is a DROP section heading
        is_drop_heading = any(re.search(pattern, line_lower) for pattern in drop_sections)
        
        if is_drop_heading:
            # Skip this line and next 3 (section content)
            skip_lines = 3
            skip_section = True
            continue
        
        # Reset skip if we hit a KEEP heading
        is_keep_heading = any(re.search(pattern, line_lower) for pattern in keep_sections)
        if is_keep_heading:
            skip_section = False
        
        # Keep line if not in skip mode
        if not skip_section:

            # Filter out inline junk (salary, benefits details, form fields)
            junk_patterns = [
                # Salary/Pay patterns (comprehensive)
                r'\$[0-9,]+\s*-\s*\$[0-9,]+',
                r'pay range.*\$[0-9,]+.*\$[0-9,]+.*per (year|hour)',
                r'salary.*\$[0-9,]+.*-.*\$[0-9,]+',
                r'minimum salary:.*\$',
                r'maximum salary:.*\$',
                r'anticipated compensation',
                r'compensation.*commensurate',
                r'expected to be between.*\$[0-9,]+',
                
                # Benefits details
                r'medical.*dental.*vision',
                r'401\(k\)',
                r'paid time off.*parental leave',
                r'employee benefits offered',
                r'annual bonus target',
                r'variable compensation',
                r'long-term incentives',
                r'subject to plan eligibility',
                r'total compensation.*may.*include',
                
                # Application form fields
                r'select\.\.\.',
                r'accepted file types:',
                r'autofill with',
            ]
            
            if any(re.search(pat, line_lower) for pat in junk_patterns):
                continue
            
            filtered_lines.append(line)

    
    # Step 2: Extract KEEP sections if they exist
    extracted = []
    in_keep_section = False
    
    for line in filtered_lines:
        line_lower = line.lower().strip()
        
        # Check if this is a KEEP section heading
        is_keep = any(re.search(pattern, line_lower) for pattern in keep_sections)
        
        if is_keep:
            in_keep_section = True
            extracted.append(line)
        elif in_keep_section:
            # Keep content under KEEP sections
            # Stop if we hit a DROP heading or empty section
            is_drop = any(re.search(pattern, line_lower) for pattern in drop_sections)
            if is_drop:
                in_keep_section = False
            elif len(line.strip()) > 20:  # Real content
                extracted.append(line)
    
    # If we extracted KEEP sections, use that; otherwise use filtered
    result_lines = extracted if extracted else filtered_lines
    
    # Step 3: Deduplicate repeated lines
    seen = set()
    deduped = []
    for line in result_lines:
        normalized = line.strip().lower()
        if normalized and normalized not in seen and len(line.strip()) > 15:
            seen.add(normalized)
            deduped.append(line)
    
    # Step 4: Final cleanup - remove obvious junk
    junk_keywords = ['copyright', '© 20', 'all rights reserved', 'powered by', 
                     'workday, inc', 'privacy policy', 'terms of service',
                     'follow us on', 'contact us', 'investor relations']
    
    final = []
    for line in deduped:
        line_lower = line.lower()
        if not any(kw in line_lower for kw in junk_keywords):
            final.append(line)
    
    trimmed = '\n'.join(final)
    return trimmed[:5000] if len(trimmed) > 5000 else trimmed

def clean_jd_smart(text: str) -> str:
    """
    Smart cleaning to fix typos and formatting.
    SOFT SKILLS ARE PRESERVED (User Request).
    """
    if not text: return ""

    # 1. Normalize Typos
    text = normalize_tech_terms(text)

    # 2. Parentheses Cleaning (Remove ONLY examples)
    # Target: (e.g. x, y), (i.e. x), (such as x)
    # We use a non-greedy match inside parens
    text = re.sub(r"\((?:e\.g\.|i\.e\.|such as|including)\b.*?\)", "", text, flags=re.IGNORECASE)

    # 3. Smart Line Filtering
    lines = text.splitlines()
    out_lines = []
    
    # Soft skill triggers
    soft_triggers = [
        "communication", "interpersonal", "organizational", "detail oriented",
        "team player", "self-starter", "motivated", "fast-paced", "written and verbal",
    ]
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            out_lines.append(line)
            continue
            
        # Check if line is "Soft Skill" heavy
        is_soft = any(trigger in line_clean.lower() for trigger in soft_triggers)
        
        if is_soft:
            # ALWAYS SAVE soft skills per user request
            saved = True 
            
            # 2. Capital Letter Check (Simple Heuristic: Capitalized word > 2 chars in middle of sentence)
            words = line_clean.split()
            if len(words) > 1:
                # check words starting from index 1 (skip first word "Strong", "Excellent")
                for w in words[1:]:
                    # Check if Title Case (and not just "I" or "A") and len > 2
                    if w[0].isupper() and len(w) > 2 and w.lower() not in ["excellent", "strong", "good", "proven", "ability"]:
                        saved = True
                        break
            
            if saved:
                out_lines.append(line) # Keep it, it has gems
            else:
                pass # Drop it, it's just fluff
        else:
            out_lines.append(line)
            
    return "\n".join(out_lines)
