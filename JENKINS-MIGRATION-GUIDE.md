# Jenkins Plugin Migration Guide
## Artifactory Plugin → JFrog Plugin

### Quick Facts

**Why Migrate?**
- JFrog Plugin uses JFrog CLI (modern, maintained)
- Artifactory Plugin uses legacy Java integration (maintenance mode)
- Same functionality, different syntax

**What Changes?**
- Pipeline syntax: `Artifactory.server()` → `jf 'rt ...'`
- Freestyle: Build wrappers → "Run JFrog CLI" step
- Configuration: Same servers, simplified credentials

**Migration Time:** 15 min to 2 hours per job (depending on complexity)

---

## Migration Steps

### Step 1: Install JFrog Plugin (5 min)

```
Jenkins → Manage Jenkins → Manage Plugins → Available
Search: "JFrog"
Install without restart
```

### Step 2: Configure Server (10 min)

```
Manage Jenkins → Configure System → JFrog Platform Instances
Click "Add JFrog Platform Instance"
```

**Copy from Artifactory Plugin config:**
- Server ID: `<same as before>`
- Platform URL: `<same as before>`
- Credentials: `<select same credentials>`

**Note**: If you use separate deployer/resolver credentials:
- Create 2 server configs (e.g., `my-server-deploy` and `my-server-resolve`)
- OR grant deployer credentials read access

### Step 3: Setup JFrog CLI (5 min)

```
Manage Jenkins → Global Tool Configuration → JFrog CLI
Add JFrog CLI → Name: jfrog-cli
Install automatically from releases.jfrog.io
```

### Step 4: Migrate Jobs

Choose your job type:

---

## Pipeline Jobs Migration

### Basic Upload/Download (15-30 min)

**Before:**
```groovy
def server = Artifactory.server('my-server')
def buildInfo = Artifactory.newBuildInfo()

def uploadSpec = """{
  "files": [{"pattern": "*.jar", "target": "repo/"}]
}"""
server.upload(uploadSpec, buildInfo)
server.publishBuildInfo(buildInfo)
```

**After:**
```groovy
pipeline {
    agent any
    tools { jfrog 'jfrog-cli' }
    stages {
        stage('Deploy') {
            steps {
                jf 'rt u "*.jar" repo/'
                jf 'rt bp'
            }
        }
    }
}
```

**Changes:**
1. Add `tools { jfrog 'jfrog-cli' }` at pipeline level
2. Replace `server.upload()` with `jf 'rt u ...'`
3. Replace `server.publishBuildInfo()` with `jf 'rt bp'`
4. Remove buildInfo object (auto-managed)

---

### Maven Build (30-60 min)

**Before:**
```groovy
def rtMaven = Artifactory.newMavenBuild()
rtMaven.deployer server: server, 
                 releaseRepo: 'libs-release-local',
                 snapshotRepo: 'libs-snapshot-local'
rtMaven.resolver server: server,
                 releaseRepo: 'libs-release',
                 snapshotRepo: 'libs-snapshot'
rtMaven.run pom: 'pom.xml', goals: 'clean install', buildInfo: buildInfo
server.publishBuildInfo(buildInfo)
```

**After:**
```groovy
pipeline {
    agent any
    tools { jfrog 'jfrog-cli' }
    stages {
        stage('Build') {
            steps {
                jf 'mvn-config --repo-deploy-releases=libs-release-local --repo-deploy-snapshots=libs-snapshot-local --repo-resolve-releases=libs-release --repo-resolve-snapshots=libs-snapshot'
                jf 'mvn clean install'
                jf 'rt bp'
            }
        }
    }
}
```

**Changes:**
1. Replace `rtMaven` object with `jf 'mvn-config ...'`
2. Replace `rtMaven.run()` with `jf 'mvn ...'`
3. Build-info auto-collected (no buildInfo object needed)

---

### Gradle Build (30-60 min)

**Before:**
```groovy
def rtGradle = Artifactory.newGradleBuild()
rtGradle.deployer server: server, repo: 'libs-release-local'
rtGradle.resolver server: server, repo: 'libs-release'
rtGradle.run buildFile: 'build.gradle', tasks: 'clean build', buildInfo: buildInfo
```

**After:**
```groovy
jf 'gradle-config --repo-deploy=libs-release-local --repo-resolve=libs-release'
jf 'gradle clean build'
jf 'rt bp'
```

---

### Docker (30-60 min)

**Before:**
```groovy
def docker = Artifactory.docker(server)
docker.push("registry/image:tag", 'docker-local', buildInfo)
```

**After:**
```groovy
jf 'docker push registry/image:tag'
jf 'rt bp'
```

---

### Build Promotion (15 min)

**Before:**
```groovy
server.promote([
    targetRepo: 'prod-local',
    buildName: buildInfo.name,
    buildNumber: buildInfo.number,
    status: 'Released',
    copy: true
])
```

**After:**
```groovy
jf 'rt bpr --status=Released --copy=true --target-repo=prod-local ${env.JOB_NAME} ${env.BUILD_NUMBER}'
```

---

## Freestyle Jobs Migration

### Maven Job (30-60 min)

**Before:**
```
Build Environment:
  ☑ Artifactory Maven 3 Configurator
    Server: my-server
    Deploy Repository: libs-release-local
    Resolve Repository: libs-release
    ☑ Deploy artifacts
    ☑ Deploy build info
```

**After:**
```
Build Steps:
  Add build step → Run JFrog CLI
    JFrog CLI Installation: jfrog-cli
    JFrog CLI Command:
      jf mvn-config --repo-deploy-releases=libs-release-local --repo-resolve-releases=libs-release
      jf mvn clean install
      jf rt bp
```

**Steps:**
1. Remove "Artifactory Maven 3 Configurator" from Build Environment
2. Add "Run JFrog CLI" build step
3. Copy repository names to CLI command
4. Test the job

---

### Generic Upload Job (15-30 min)

**Before:**
```
Post-build Actions:
  ☑ Deploy artifacts to Artifactory
    Server: my-server
    Target Repository: my-repo
    File pattern: target/*.jar
```

**After:**
```
Build Steps:
  Add build step → Run JFrog CLI
    JFrog CLI Installation: jfrog-cli
    JFrog CLI Command:
      jf rt u "target/*.jar" my-repo/
      jf rt bp
```

---

## Common Issues & Solutions

### Issue 1: "Server ID not found"

**Error:**
```
[Error] server ID 'my-server' does not exist
```

**Solution:**
Check server ID matches exactly:
```
Manage Jenkins → Configure System → JFrog Platform Instances
Copy the exact "Server ID" value
```

---

### Issue 2: "jf: command not found"

**Error:**
```
/bin/sh: jf: command not found
```

**Solution:**
Add tools block:
```groovy
tools {
    jfrog 'jfrog-cli'  // Use exact name from Global Tool Configuration
}
```

---

### Issue 3: Different credentials for deploy/resolve

**Problem:** Artifactory plugin had separate credentials

**Solution A** (Recommended): Use same credentials
```
Grant deployer credentials read access to resolve repos
Use single server config
```

**Solution B**: Create 2 server configs
```
Server 1: my-server-resolve (resolver credentials)
Server 2: my-server-deploy (deployer credentials)

In job:
jf 'mvn-config --server-id=my-server-resolve --repo-resolve-releases=libs-release'
jf 'mvn-config --server-id=my-server-deploy --repo-deploy-releases=libs-release-local'
jf 'mvn clean install'
```

---

### Issue 4: Build name with spaces/special characters

**Problem:** Build fails with "invalid build name"

**Solution:**
```groovy
environment {
    JFROG_CLI_BUILD_NAME = env.JOB_NAME.replaceAll('[^a-zA-Z0-9-_]', '-')
}
```

---

### Issue 5: Maven 2 projects

**Problem:** No Maven 2 support in JFrog plugin

**Solution:**
Option 1: Upgrade to Maven 3 (recommended)
Option 2: Use generic upload after build:
```groovy
sh 'mvn clean install'  // Regular Maven 2 build
jf 'rt u "target/*.jar" libs-release-local/'  // Upload with CLI
jf 'rt bp'
```

---

## Validate Migration

After migrating, verify:
- Job runs without errors
- Artifacts uploaded to correct repository  
- Build-info visible in Artifactory UI with correct artifacts and dependencies

---

## Quick Reference

| Action | Artifactory Plugin | JFrog Plugin |
|--------|-------------------|--------------|
| Upload | `server.upload(spec, buildInfo)` | `jf 'rt u "pattern" repo/'` |
| Download | `server.download(spec, buildInfo)` | `jf 'rt dl "pattern" target/'` |
| Publish build-info | `server.publishBuildInfo(buildInfo)` | `jf 'rt bp'` |
| Promote | `server.promote([...])` | `jf 'rt bpr --status=... --target-repo=... BUILD BUILD_NUM'` |
| Xray scan | `server.xrayScan(buildInfo: buildInfo)` | `jf 'rt bs BUILD BUILD_NUM'` |
| Maven | `rtMaven.run(...)` | `jf 'mvn-config ...'` + `jf 'mvn ...'` |
| Gradle | `rtGradle.run(...)` | `jf 'gradle-config ...'` + `jf 'gradle ...'` |
| Docker push | `docker.push(...)` | `jf 'docker push ...'` |

---

## Support

- **JFrog Support:** https://jfrog.com/support/
- **Plugin Docs:** https://github.com/jfrog/jenkins-jfrog-plugin
- **CLI Reference:** https://docs.jfrog-applications.jfrog.io/jfrog-applications/jfrog-cli

---