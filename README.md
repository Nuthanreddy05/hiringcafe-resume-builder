# Job Application Automation Suite

This toolchain automates the process of finding jobs, tailoring your resume using AI (DeepSeek + Gemini), and filling out applications.

## 📂 Project Structure

- `job_auto_apply.py`: Scrapes jobs from HiringCafe and generates tailored resumes.
- `job_auto_submit.py`: Takes the generated resumes and attempts to apply on Greenhouse/Lever.
- `profile.json`: Your personal details for the application forms.
- `base_resume.tex`: YOUR base LaTex resume template (You must provide this).

## 🚀 Setup Instructions

### 1. Install Prerequisites
You need Python 3.10+ installed.

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

You also need `tectonic` for compiling PDFs:
```bash
# MacOS
brew install tectonic
```

### 2. Configure API Keys
You need keys for DeepSeek (Writer) and Gemini (Critic).

```bash
export DEEPSEEK_API_KEY="sk-..."
export GEMINI_API_KEY="AIzaSy..."
```

### 3. Customize Your Profile
1. Open `profile.json`.
2. Edit the fields with your real Name, Email, LinkedIn, etc.
3. Make sure you have a valid `base_resume.tex` in this folder.

## 🏃‍♂️ How to Run

### Step 1: Find Jobs & Generate Resumes
This script searches for jobs and creates unique PDF resumes for each one.

```bash
python job_auto_apply.py \
  --start_url "https://hiring.cafe/..." \
  --max_jobs 5
```
*Output: Creates an `application_packages` folder.*

### Step 2: Auto-Apply (Optional)
This script takes those packages and fills out the web forms for you.

```bash
python job_auto_submit.py \
  --jobs_dir ./application_packages \
  --profile profile.json
```

## ⚠️ Important Note
The "Auto-Submit" script runs in **Safe Mode** by default. It will fill the form but **STOP** before clicking submit, so you can review it.
