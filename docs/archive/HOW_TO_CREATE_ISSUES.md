# How to Create GitHub Issues for Cleanup Tasks

## Quick Summary

I've created **10 granular GitHub issues** for the cleanup and refactoring work, organized into 4 phases:

### Phase 1: Quick Wins (Issues #1-4)
1. Move test/validation scripts from root
2. Consolidate test YAML files
3. Remove duplicate connection manager
4. Add cleanup documentation

### Phase 2: Major Refactoring (Issue #5)
5. Split sql_generator.py into modules

### Phase 3: Secondary Refactoring (Issues #6-8)
6. Refactor cache manager
7. Refactor intent analyzers
8. Consolidate documentation

### Phase 4: Polish (Issues #9-10)
9. Add log rotation
10. Code quality audit

---

## How to Create These Issues

### Option 1: Automated Script (Recommended) ⚡

I've created `create_github_issues.py` that will automatically create all 10 issues.

**Prerequisites**:
- PyGithub installed ✓ (already done in venv)
- GitHub authentication configured

**Run it:**

```bash
# Dry run first (see what will be created)
source venv/bin/activate
python create_github_issues.py --dry-run

# Create the issues (you'll need a GitHub token)
python create_github_issues.py --token YOUR_GITHUB_TOKEN
```

**To get a GitHub token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (full control)
4. Copy the token and use it above

---

### Option 2: Manual Creation via Web UI 🌐

1. Go to: https://github.com/sundar-blr76/report-smith/issues/new
2. Open `GITHUB_ISSUES_TEMPLATE.md` 
3. Copy/paste each issue
4. Assign to: **@agent**
5. Add labels as indicated

---

### Option 3: GitHub CLI (if installed)

```bash
# First, authenticate
gh auth login

# Then create issues from template
gh issue create \
  --repo sundar-blr76/report-smith \
  --title "Move test/validation scripts from root to tests/validation/" \
  --body-file <(sed -n '/^## Issue 1:/,/^---$/p' GITHUB_ISSUES_TEMPLATE.md) \
  --assignee agent \
  --label "cleanup,quick-win,phase-1"

# Repeat for other issues...
```

---

## Files Created

1. **CLEANUP_ANALYSIS.md** - Detailed technical analysis
2. **GITHUB_ISSUES_TEMPLATE.md** - Full issue descriptions (manual reference)
3. **create_github_issues.py** - Automated issue creation script
4. **HOW_TO_CREATE_ISSUES.md** - This file

---

## Recommended Next Steps

1. **Review** the issues in `GITHUB_ISSUES_TEMPLATE.md`
2. **Run** the automated script:
   ```bash
   source venv/bin/activate
   python create_github_issues.py --dry-run  # Preview first
   python create_github_issues.py --token YOUR_TOKEN  # Then create
   ```
3. **Assign** to @agent (script does this automatically)
4. **Start** with Phase 1 issues (quick wins)

---

## Issue Labels Created

The script will create these labels automatically:
- `cleanup` - Organization and cleanup tasks
- `quick-win` - Fast, high-value tasks
- `refactoring` - Code restructuring
- `technical-debt` - Addressing tech debt
- `breaking-down-large-files` - File splitting tasks
- `documentation` - Doc updates
- `tooling` - Developer tools
- `maintenance` - Ongoing maintenance
- `code-quality` - Quality improvements
- `phase-1`, `phase-2`, `phase-3`, `phase-4` - Work phases

---

## Troubleshooting

**"Error: PyGithub not installed"**
```bash
source venv/bin/activate
pip install PyGithub
```

**"Error: No token provided"**
- Get token from https://github.com/settings/tokens
- Or configure gh CLI: `gh auth login`

**"Error accessing repository"**
- Verify token has `repo` scope
- Check repository name is correct

---

## What Gets Assigned to @agent

All 10 issues will be assigned to `@agent` with appropriate:
- Priority levels
- Time estimates  
- Task checklists
- Success criteria
- Phase labels

Each issue is self-contained and can be worked on independently (within phase dependencies).

---

**Ready to proceed?** Run the script or manually create the issues!
