# README-SkiAnalysisOpenSourcePrep.md

**Goal:** Prepare Ski Technique Analysis application for open source release and resolve repository structure  
**Date:** February 13, 2026 (session completed ~2:30 PM)

---

## Architecture Table

| Component | Location | Role |
|-----------|----------|------|
| **Cool-projects** | `https://github.com/fireonthemountain/Cool-projects` | Parent repository containing ski-analysis as subdirectory. Authorized for git push in Claude Code session. |
| **ski-analysis subdirectory** | `Cool-projects/ski-analysis/` | Full ski analysis application code. Working branch: `claude/review-changes-mjowcx6cubkx701x-Y1VMk` |
| **ski-analysis standalone repo** | `https://github.com/fireonthemountain/ski-analysis` | Target standalone repository (pre-existing, discovered mid-session) |
| **Movement_Analysis repo** | `https://github.com/fireonthemountain/Movement_Analysis` | Initially created as standalone repo, abandoned in favor of existing ski-analysis repo |
| **Local Movement_Analysis copy** | `/home/user/Movement_Analysis` | Temporary local copy with 2 commits, not pushed (session not authorized) |
| **Documentation** | README.md, CONTRIBUTING.md, MAC_SETUP.md, etc. | Open source release documentation with proper repo references |

---

## How It Works

### Repository Structure Evolution

1. **Original state:** Ski analysis code lived in `Cool-projects/ski-analysis/` subdirectory
2. **Attempt 1:** Created new `Movement_Analysis` repo to extract code into standalone repository
3. **Authentication issue:** Claude Code session only authorized to push to Cool-projects, not Movement_Analysis
4. **Discovery:** User had pre-existing `https://github.com/fireonthemountain/ski-analysis` repository
5. **Resolution:** Updated all documentation to reference `ski-analysis` instead of `Movement_Analysis`

### Git Authentication in Claude Code

Claude Code sessions use a local proxy for git operations:
- Format: `http://local_proxy@127.0.0.1:PORT/git/OWNER/REPO`
- Port is dynamic (changes each session)
- Session is authorized for specific repositories only
- Example from this session: `http://local_proxy@127.0.0.1:25652/git/fireonthemountain/Cool-projects`

**Critical quirk:** Cannot push to repositories not authorized in the session, even if they belong to the same user.

### Open Source Release Checklist Items Completed

1. ✅ **MIT License** - Updated copyright year to 2026
2. ✅ **README.md** - Added badges, "Why this project", better structure, repo URL updates
3. ✅ **CONTRIBUTING.md** - Comprehensive contribution guidelines, updated repo URLs
4. ✅ **MAC_SETUP.md** - Complete guide for running on Mac mini (Docker + manual setup)
5. ⏳ **CODE_OF_CONDUCT.md** - Pending (not completed this session)
6. ⏳ **Issue templates** - Pending
7. ⏳ **GitHub Actions CI/CD** - Pending
8. ⏳ **v1.0.0 release tag** - Pending

### Documentation Reference Changes

All GitHub URLs updated from `Movement_Analysis` to `ski-analysis`:
- Clone URLs in Quick Start
- Issue tracker links
- Discussions links
- Contributing instructions
- Project links

---

## Incident History / Root Cause

### Issue 1: Cannot Push to New Repositories

**What was broken:**  
Attempts to push to `Movement_Analysis` and `ski-analysis` repos failed with "repository not authorized" error.

**Why:**  
Claude Code sessions are authorized for specific repositories. This session was authorized only for `Cool-projects`, not for newly created or other existing repositories.

**Fix:**  
1. Keep working in Cool-projects (authorized)
2. Update documentation to reference target repo (`ski-analysis`)
3. User manually transfers code from Cool-projects to ski-analysis on their Mac

**Error messages seen:**
```
remote: Proxy error: repository not authorized
fatal: unable to access 'http://127.0.0.1:PORT/git/fireonthemountain/REPO/': The requested URL returned error: 502
```

### Issue 2: Repository Naming Confusion

**What was broken:**  
Documentation referenced `Movement_Analysis` but user had existing `ski-analysis` repo.

**Why:**  
Initial plan was to create Movement_Analysis as standalone repo. Mid-session discovered pre-existing ski-analysis repo.

**Fix:**  
Bulk find/replace in README.md and CONTRIBUTING.md to change all `Movement_Analysis` references to `ski-analysis`.

**Files updated:**
- `ski-analysis/README.md` (3 URL changes)
- `ski-analysis/CONTRIBUTING.md` (4 URL and title changes)

---

## Operations

### Check Current Repository Status

```bash
# Check which repository you're in
pwd
git remote -v

# Check branch
git branch

# Check for uncommitted changes
git status
```

### View Git Proxy Configuration (Claude Code)

```bash
# See current proxy URL
git remote -v

# Example output:
# origin  http://local_proxy@127.0.0.1:25652/git/fireonthemountain/Cool-projects (fetch)
```

### Push Changes to Cool-projects

```bash
cd /home/user/Cool-projects

# Add files
git add ski-analysis/

# Commit
git commit -m "Your commit message"

# Push to authorized branch
git push -u origin claude/review-changes-mjowcx6cubkx701x-Y1VMk
```

### Transfer Code to Standalone ski-analysis Repo (On Mac)

**Method 1: Direct Copy (Recommended)**

```bash
# Clone Cool-projects
git clone https://github.com/fireonthemountain/Cool-projects.git
cd Cool-projects

# Clone ski-analysis (standalone)
cd ~
git clone https://github.com/fireonthemountain/ski-analysis.git

# Copy all files
cp -r ~/Cool-projects/ski-analysis/* ~/ski-analysis/
cp ~/Cool-projects/ski-analysis/.env.example ~/ski-analysis/
cp ~/Cool-projects/ski-analysis/.gitignore ~/ski-analysis/

# Commit and push
cd ~/ski-analysis
git add .
git commit -m "Initial commit: Complete ski analysis application v1.0"
git push origin main
```

**Method 2: Git Subtree**

```bash
cd Cool-projects
git subtree split --prefix=ski-analysis -b ski-analysis-only

cd ~/ski-analysis
git pull ~/Cool-projects ski-analysis-only
git push origin main
```

### Run Application Locally (Mac Mini)

**With Docker (Easiest):**

```bash
cd ~/ski-analysis
docker-compose up

# Open http://localhost:5173
```

**Manual Setup:**

```bash
# Backend
cd ~/ski-analysis/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
cd ~/ski-analysis/frontend
npm install
npm run dev
```

---

## Open Items

### Critical (Blocks Open Source Launch)

1. **Transfer code to ski-analysis repo** - Currently only in Cool-projects
2. **Create CODE_OF_CONDUCT.md** - Standard Contributor Covenant
3. **Create issue templates** - Bug report, feature request, question
4. **Create PR template** - In `.github/pull_request_template.md`
5. **Set up GitHub Actions** - Run tests on push/PR
6. **Tag v1.0.0 release** - With release notes

### Nice to Have

1. Demo GIF showing upload → analysis workflow
2. Live demo deployment (Vercel/Netlify for frontend)
3. Add sample skiing photos to examples/ directory
4. Create announcement post for r/skiing, r/MachineLearning
5. Submit to awesome-machine-learning list

### Manual Steps Required (On Mac)

1. Push code from Cool-projects to ski-analysis repo (see Operations section)
2. Verify application runs locally with `docker-compose up`
3. Test with real skiing photos
4. Create GitHub release v1.0.0
5. Announce on social media / Reddit

---

## Scripts and Configuration Files

### File: `/home/user/Cool-projects/ski-analysis/README.md` (excerpt)

Key sections updated for open source release:

```markdown
# 🎿 Ski Technique Analysis

AI-powered skiing technique analysis using computer vision and biomechanics.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)](https://mediapipe.dev/)

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/fireonthemountain/ski-analysis.git
cd ski-analysis

# Start all services
docker-compose up

# Open http://localhost:5173 and upload a skiing photo!
```

## 📧 Contact & Support

- **Issues:** [GitHub Issues](https://github.com/fireonthemountain/ski-analysis/issues)
- **Discussions:** [GitHub Discussions](https://github.com/fireonthemountain/ski-analysis/discussions)
- **Project Link:** [https://github.com/fireonthemountain/ski-analysis](https://github.com/fireonthemountain/ski-analysis)
```

### File: `/home/user/Cool-projects/ski-analysis/CONTRIBUTING.md` (excerpt)

```markdown
# Contributing to Ski Technique Analysis

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ski-analysis.git
cd ski-analysis

# Add upstream remote
git remote add upstream https://github.com/fireonthemountain/ski-analysis.git
```

## ❓ Questions?

- Open a [Discussion](https://github.com/fireonthemountain/ski-analysis/discussions) for questions
- Join our community chat (if available)
- Check existing documentation first
```

### File: `/home/user/Cool-projects/ski-analysis/LICENSE`

```
MIT License

Copyright (c) 2026 Ski Analysis Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### File: `/home/user/Cool-projects/ski-analysis/MAC_SETUP.md`

Complete Mac mini setup guide created. Key commands:

```bash
# Install prerequisites
brew install python@3.11 node postgresql docker

# Quick start with Docker
cd ~/ski-analysis
docker-compose up

# Manual setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Git Commands Used This Session

```bash
# Update LICENSE year
cd /home/user/Cool-projects/ski-analysis
# (used Edit tool, not bash)

# Update README badges and structure
# (used Edit tool)

# Update CONTRIBUTING.md repo references
# (used Edit tool)

# Commit changes
git add ski-analysis/LICENSE ski-analysis/README.md
git commit -m "Prepare for open source release: Update LICENSE and polish README"
git push -u origin claude/review-changes-mjowcx6cubkx701x-Y1VMk

# Later: Update repo references from Movement_Analysis to ski-analysis
git add ski-analysis/README.md ski-analysis/CONTRIBUTING.md
git commit -m "Update repository references to ski-analysis"
git push -u origin claude/review-changes-mjowcx6cubkx701x-Y1VMk

# Add Mac setup guide
git add ski-analysis/MAC_SETUP.md
git commit -m "Add Mac mini setup guide for local development"
git push -u origin claude/review-changes-mjowcx6cubkx701x-Y1VMk
```

### Attempted Git Operations (Failed - Not Authorized)

```bash
# Attempted to push to Movement_Analysis
cd /home/user/Movement_Analysis
git remote add origin http://local_proxy@127.0.0.1:17164/git/fireonthemountain/Movement_Analysis
git push -u origin main
# Error: remote: Proxy error: repository not authorized

# Attempted to push to ski-analysis
git remote set-url origin http://local_proxy@127.0.0.1:25652/git/fireonthemountain/ski-analysis
git push -u origin main
# Error: remote: Proxy error: repository not authorized
```

---

## Verification

### Verified Files in Cool-projects - February 13, 2026 2:15 PM

```bash
$ cd /home/user/Cool-projects/ski-analysis
$ ls -la
total 120
drwx------ 7 root root  4096 Feb 13 18:26 .
drwxr-xr-x 4 root root  4096 Feb 13 18:26 ..
-rw-r--r-- 1 root root   873 Feb 13 18:26 .env.example
-rw-r--r-- 1 root root   817 Feb 13 18:26 .gitignore
-rw-r--r-- 1 root root  6411 Feb 13 18:26 CONTRIBUTING.md
-rw-r--r-- 1 root root  1082 Feb 13 18:26 LICENSE
-rw------- 1 root root  9344 Feb 13 18:26 MAC_SETUP.md
-rw------- 1 root root 12929 Feb 13 18:26 OPEN_SOURCE_CHECKLIST.md
-rw------- 1 root root 13071 Feb 13 18:26 PRODUCTION_ROADMAP.md
-rw------- 1 root root  7582 Feb 13 18:26 QUICKSTART_TESTING.md
-rw-r--r-- 1 root root 11141 Feb 13 18:26 README.md
-rw-r--r-- 1 root root 11706 Feb 13 18:26 RECREATION_PROMPT.md
-rw------- 1 root root  9749 Feb 13 18:26 TESTING.md
drwx------ 6 root root  4096 Feb 13 18:26 backend
-rw-r--r-- 1 root root  2494 Feb 13 18:26 docker-compose.yml
drwxr-xr-x 2 root root  4096 Feb 13 18:26 docs
drwx------ 2 root root  4096 Feb 13 18:26 examples
drwx------ 3 root root  4096 Feb 13 18:26 frontend
drwx------ 2 root root  4096 Feb 13 18:26 scripts
```

### Verified Git Status - February 13, 2026 2:20 PM

```bash
$ cd /home/user/Cool-projects
$ git status
On branch claude/review-changes-mjowcx6cubkx701x-Y1VMk
Your branch is up to date with 'origin/claude/review-changes-mjowcx6cubkx701x-Y1VMk'.

nothing to commit, working tree clean
```

### Verified Git Remote - February 13, 2026 2:20 PM

```bash
$ git remote -v
origin	http://local_proxy@127.0.0.1:25652/git/fireonthemountain/Cool-projects (fetch)
origin	http://local_proxy@127.0.0.1:25652/git/fireonthemountain/Cool-projects (push)
```

### Verified Recent Commits - February 13, 2026 2:25 PM

```bash
$ git log --oneline -5
2b4031e Update repository references to ski-analysis
efa2441 Add Mac mini setup guide for local development
faaa8c7 Prepare for open source release - update repo references
44f6b47 Prepare for open source release: Update LICENSE and polish README
34c7fe8 Add comprehensive open source release checklist
```

### Verified README References - February 13, 2026 2:28 PM

```bash
$ grep -n "github.com" ski-analysis/README.md | head -5
75:git clone https://github.com/fireonthemountain/ski-analysis.git
286:2. Check [open issues](https://github.com/fireonthemountain/ski-analysis/issues)
335:- **Issues:** [GitHub Issues](https://github.com/fireonthemountain/ski-analysis/issues)
336:- **Discussions:** [GitHub Discussions](https://github.com/fireonthemountain/ski-analysis/discussions)
337:- **Project Link:** [https://github.com/fireonthemountain/ski-analysis](https://github.com/fireonthemountain/ski-analysis)

# All references correctly point to ski-analysis, not Movement_Analysis
```

---

## Next Session Checklist

When continuing this work:

1. **Check git status first:**
   ```bash
   cd /home/user/Cool-projects
   git status
   git pull origin claude/review-changes-mjowcx6cubkx701x-Y1VMk
   ```

2. **Verify which repository the session is authorized for:**
   ```bash
   git remote -v
   # Should see Cool-projects with local_proxy URL
   ```

3. **To work on ski-analysis standalone repo:**
   - Work must be done on user's Mac, not in Claude Code session
   - OR start new Claude Code session authorized for ski-analysis repo

4. **Complete open source checklist items:**
   - CODE_OF_CONDUCT.md
   - Issue templates
   - GitHub Actions
   - Tag v1.0.0

5. **Test the application:**
   - Clone ski-analysis to Mac
   - Run with Docker
   - Upload test skiing photos
   - Verify analysis works

---

**Session Status:** ✅ Documentation updated and pushed to Cool-projects. User needs to manually transfer code to ski-analysis repo on their Mac.

**Repository URLs:**
- Source (authorized): https://github.com/fireonthemountain/Cool-projects
- Target (manual push needed): https://github.com/fireonthemountain/ski-analysis
- Abandoned: https://github.com/fireonthemountain/Movement_Analysis
