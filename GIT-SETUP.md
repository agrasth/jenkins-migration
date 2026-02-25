# Git Repository Setup Guide

## Repository Initialized ✅

The jenkins-migration folder is now a git repository with all files committed.

---

## Push to GitHub

### Option 1: Create New GitHub Repository (Recommended)

**Step 1**: Create repository on GitHub
```bash
# Go to: https://github.com/new
# Repository name: jenkins-artifactory-jfrog-migration
# Description: Tool to migrate Jenkins jobs from Artifactory plugin to JFrog plugin
# Public or Private: Your choice
# Do NOT initialize with README (we already have one)
```

**Step 2**: Add remote and push
```bash
cd /Users/agrasthn/workspace/plugins/jenkins-migration

# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/jenkins-artifactory-jfrog-migration.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Step 3**: Verify
```bash
# Open in browser:
# https://github.com/YOUR_USERNAME/jenkins-artifactory-jfrog-migration
```

---

### Option 2: Use GitHub CLI (if installed)

```bash
cd /Users/agrasthn/workspace/plugins/jenkins-migration

# Create repo and push in one command
gh repo create jenkins-artifactory-jfrog-migration --public --source=. --push

# Or for private:
gh repo create jenkins-artifactory-jfrog-migration --private --source=. --push
```

---

## Push to GitLab

```bash
cd /Users/agrasthn/workspace/plugins/jenkins-migration

# Create project on GitLab first: https://gitlab.com/projects/new
# Then add remote:
git remote add origin https://gitlab.com/YOUR_USERNAME/jenkins-artifactory-jfrog-migration.git

# Push
git branch -M main
git push -u origin main
```

---

## Push to Bitbucket

```bash
cd /Users/agrasthn/workspace/plugins/jenkins-migration

# Create repository on Bitbucket first
# Then add remote:
git remote add origin https://bitbucket.org/YOUR_USERNAME/jenkins-artifactory-jfrog-migration.git

# Push
git branch -M main
git push -u origin main
```

---

## Push to Your Own Git Server

```bash
cd /Users/agrasthn/workspace/plugins/jenkins-migration

# Add your git server URL
git remote add origin git@your-server.com:path/to/repo.git

# Or with HTTPS:
git remote add origin https://your-server.com/path/to/repo.git

# Push
git branch -M main
git push -u origin main
```

---

## Current Repository Status

```bash
# Check current status
cd /Users/agrasthn/workspace/plugins/jenkins-migration
git status

# View commit history
git log --oneline

# See what files are tracked
git ls-files
```

---

## Files Included in Repository

✅ **Tools:**
- `migrate_artifactory_to_jfrog.py` - Python CLI migration tool
- `migrate-job.groovy` - Groovy script for Jenkins Script Console

✅ **Examples:**
- `Jenkinsfile.old` - Example input (Artifactory plugin)
- `Jenkinsfile.migrated` - Example output (JFrog plugin)
- `Jenkinsfile.artifactory-migrated` - Alternative example

✅ **Documentation:**
- `README.md` - User guide with step-by-step instructions
- `DESIGN.md` - Architecture and design document
- `JENKINS-MIGRATION-GUIDE.md` - Detailed pattern reference
- `GIT-SETUP.md` - This file

✅ **Configuration:**
- `.gitignore` - Excludes temporary files, Python cache, etc.

❌ **Excluded:**
- `*.log` - Log files
- `__pycache__/` - Python cache
- `.DS_Store` - macOS files
- `*.tmp`, `*.bak` - Temporary files

---

## Quick Commands Reference

```bash
# Navigate to repo
cd /Users/agrasthn/workspace/plugins/jenkins-migration

# Check status
git status

# View recent commits
git log --oneline -5

# See remotes
git remote -v

# Pull latest changes (after push)
git pull

# Make changes and commit
git add .
git commit -m "Your commit message"
git push
```

---

## Next Steps

1. Choose your git hosting platform (GitHub, GitLab, Bitbucket, etc.)
2. Create a new repository there
3. Copy the repository URL
4. Run the commands from the appropriate section above
5. Verify the push was successful by visiting the repository URL

**Recommended**: Use GitHub for maximum visibility and community engagement.
