# Artifactory → JFrog Plugin Migration Tool

**Two ways to migrate your Jenkins jobs:**

## Files in This Folder

1. **`migrate-job.groovy`** - Groovy tool (runs in Jenkins Script Console)
2. **`migrate_artifactory_to_jfrog.py`** - Python tool (runs from command line)
3. **`Jenkinsfile.artifactory-migrated`** - Example output
4. **`JENKINS-MIGRATION-GUIDE.md`** - Detailed patterns reference
5. **`README.md`** - This file

---

## Method 1: Groovy Tool (For Live Jenkins Jobs)

**When to use**: Your jobs are already in Jenkins, you want to migrate them directly

### Steps:

**1. Open Script Console**
```
http://localhost:8080/script
```

**2. Edit Configuration**

Open `migrate-job.groovy` and change lines 14-17:
```groovy
def sourceJobName = "your-job-name"        // ← Change this
def serverUrl = "https://your-url.jfrog.io" // ← Change this
def serverUser = "your-username"           // ← Change this
def serverPassword = "your-password"       // ← Change this
```

**3. Run Migration**
- Copy entire `migrate-job.groovy` content
- Paste into Script Console
- Click "Run"

**4. Result**
```
🚀 Migration: your-job-name → your-job-name-migrated
📋 Extracting patterns...
  Server ID: ecosysjfrog
  Upload pattern: your-file.txt
  Upload target: your-repo/path/
✅ MIGRATION COMPLETE!
URL: http://localhost:8080/job/your-job-name-migrated/
```

**5. Test**
- Open the migrated job
- Click "Build Now"
- Check console output

---

## Method 2: Python Tool (For Jenkinsfiles in Git)

**When to use**: You have Jenkinsfiles in your Git repo, want to convert them before committing

### Steps:

**1. Get Your Jenkinsfile**

If your Jenkinsfile is in Git:
```bash
cd /path/to/your/repo
# Your Jenkinsfile is already there
```

If your job is in Jenkins, export it:
```bash
# Export the pipeline script from Jenkins
docker exec jenkins cat /var/jenkins_home/jobs/YOUR-JOB/config.xml > job.xml

# Extract the <script> section to a file
grep -A 200 "<script>" job.xml | grep -B 200 "</script>" | sed 's/<script>//;s/<\/script>//' > Jenkinsfile.old
```

**2. Run the Python Tool**
```bash
cd /Users/agrasthn/workspace/plugins

python3 jenkins-migration/migrate_artifactory_to_jfrog.py \
    Jenkinsfile.old \
    Jenkinsfile.migrated
```

**3. Check the Output**
```bash
cat Jenkinsfile.migrated
```

You'll see:
- Comments at the top explaining changes
- Conversion report
- Migrated pipeline script

**4. Review and Commit**
```bash
# Review the changes
diff Jenkinsfile.old Jenkinsfile.migrated

# If good, replace original
mv Jenkinsfile.migrated Jenkinsfile

# Commit to Git
git add Jenkinsfile
git commit -m "Migrate from Artifactory plugin to JFrog plugin"
git push
```

**5. Create Jenkins Job**
- Go to Jenkins
- New Item → Pipeline
- Choose "Pipeline script from SCM"
- Point to your Git repo
- Build it

---

## What Gets Converted

Both tools do the same conversions:

| Before (Artifactory Plugin) | After (JFrog Plugin) |
|-----------------------------|----------------------|
| `Artifactory.server('id')` | `jf 'config add id ...'` + `jf 'c use id'` |
| `Artifactory.newBuildInfo()` | Removed (auto-managed) |
| `buildInfo.name/number` | Removed (auto-set) |
| `server.upload(uploadSpec)` | `jf 'rt u "pattern" target/'` |
| `server.publishBuildInfo()` | `jf 'rt bp'` |
| JSON upload spec | Parsed and converted to CLI |

---

## Example: Python Tool in Action

```bash
# Start with original Artifactory plugin job
$ cat Jenkinsfile.old
pipeline {
    agent any
    stages {
        stage('Upload') {
            steps {
                script {
                    def server = Artifactory.server('ecosysjfrog')
                    def uploadSpec = """{"files": [{"pattern": "*.jar", "target": "libs/"}]}"""
                    server.upload(uploadSpec)
                }
            }
        }
    }
}

# Run migration
$ python3 jenkins-migration/migrate_artifactory_to_jfrog.py Jenkinsfile.old Jenkinsfile.new

Reading: Jenkinsfile.old
Converting pipeline...
✓ Converted pipeline written to: Jenkinsfile.new

MIGRATION REPORT
================
Server ID: ecosysjfrog
Conversions Applied:
- Server initialization → --server-id flag
- Upload with spec → jf 'rt u ...'

# Check output
$ cat Jenkinsfile.new
// MIGRATED FROM ARTIFACTORY PLUGIN TO JFROG PLUGIN
// Original server ID: ecosysjfrog
// 
// IMPORTANT: Before running this job:
// 1. Ensure JFrog CLI is configured
// 2. Tool name should be: 'jfrog-cli'
// 3. Verify server 'ecosysjfrog' is configured
// 4. Ensure credentials are set
//
// REVIEW REQUIRED: Please verify repository names and paths are correct

pipeline {
    agent any
    
    tools {
        jfrog 'jfrog-cli'
    }
    
    stages {
        stage('Upload') {
            steps {
                script {
                    jf 'config add ecosysjfrog --url=... --user=... --password=... --interactive=false'
                    jf 'c use ecosysjfrog'
                    jf 'rt u "*.jar" libs/'
                }
            }
        }
    }
}
```

---

## Which Method Should You Use?

| Scenario | Best Tool | Why |
|----------|-----------|-----|
| Jobs already in Jenkins | **Groovy** | Migrates directly, auto-creates new job |
| Jenkinsfiles in Git | **Python** | Edit before committing |
| Batch migration (many jobs) | **Python** | Can script it easily |
| One-off migration | **Groovy** | Faster, no file handling |
| Want to review before applying | **Python** | Generates file you can edit |
| Running Jenkins in Docker | **Groovy** | No need to export/import |

---

## Troubleshooting

### Python Tool Issues

**Problem**: `python3: command not found`
```bash
# Check Python installation
which python3
python3 --version

# Or use python instead
python migrate_artifactory_to_jfrog.py ...
```

**Problem**: `Error: Input file not found`
```bash
# Use absolute path
python3 /Users/agrasthn/workspace/plugins/jenkins-migration/migrate_artifactory_to_jfrog.py \
    /full/path/to/Jenkinsfile.old \
    /full/path/to/Jenkinsfile.new
```

### Groovy Tool Issues

**Problem**: "Script Console not accessible"
```bash
# Jenkins must be running
docker ps | grep jenkins

# Access via
open http://localhost:8080/script
```

**Problem**: "Job not found"
```groovy
// Check available jobs - add this to Script Console:
import jenkins.model.Jenkins
Jenkins.instance.allItems(org.jenkinsci.plugins.workflow.job.WorkflowJob).each {
    println it.name
}
```

---

## Test Your Migration

After migration, both original and migrated jobs should:
1. ✅ Upload to same repository path
2. ✅ Publish same build info
3. ✅ Show same artifacts in Artifactory UI

**Compare them**:
```bash
# Run both jobs
# Check artifacts
docker exec jenkins ls /var/jenkins_home/workspace/original-job/
docker exec jenkins ls /var/jenkins_home/workspace/original-job-migrated/

# Both should have same files
```

---

## Quick Reference

**Groovy Tool**:
```
1. http://localhost:8080/script
2. Edit config (lines 14-17)
3. Paste & Run
4. Test migrated job
```

**Python Tool**:
```bash
1. python3 migrate_artifactory_to_jfrog.py INPUT OUTPUT
2. Review OUTPUT file
3. Replace/commit to Git
4. Create Jenkins job
```

---

## Need Help?

- **Complex patterns**: Check `JENKINS-MIGRATION-GUIDE.md`
- **Example output**: See `Jenkinsfile.artifactory-migrated`
- **Working example**: Test with `artifactory-plugin-test` → `artifactory-plugin-test-migrated`

Both tools are tested and working! ✅
