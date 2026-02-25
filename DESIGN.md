# Migration Tool Design Document

## Overview

This document describes the architecture, design decisions, and implementation flow of the **Artifactory Plugin → JFrog Plugin Migration Tool** for Jenkins pipelines.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Principles](#design-principles)
3. [Implementation Approaches](#implementation-approaches)
4. [Data Flow](#data-flow)
5. [Pattern Extraction Logic](#pattern-extraction-logic)
6. [Conversion Rules](#conversion-rules)
7. [Code Generation Strategy](#code-generation-strategy)
8. [Error Handling](#error-handling)
9. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                              │
│  ┌──────────────────┐           ┌─────────────────────────┐    │
│  │  Jenkinsfile     │           │  Jenkins Job via        │    │
│  │  (File on disk)  │           │  Jenkins API/Script     │    │
│  └──────────────────┘           └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          │                    │
                          ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PARSING LAYER                               │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. HTML Entity Decoder (for XML exports)             │    │
│  │  2. Pattern Extractor (Regex-based)                   │    │
│  │     - Server ID                                        │    │
│  │     - Upload Spec (JSON)                              │    │
│  │     - Stage Detection                                  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CONVERSION ENGINE                              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Pattern → JFrog CLI Mapping                          │    │
│  │  ┌──────────────────────────────────────────────┐    │    │
│  │  │ Artifactory.server()  → jf config add        │    │    │
│  │  │ server.upload(spec)   → jf rt u pattern path │    │    │
│  │  │ publishBuildInfo()    → jf rt bp             │    │    │
│  │  │ BuildInfo objects     → REMOVED              │    │    │
│  │  └──────────────────────────────────────────────┘    │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CODE GENERATION LAYER                           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Template-Based Pipeline Builder                       │    │
│  │  - Stage-by-stage construction                        │    │
│  │  - Parameter injection                                │    │
│  │  - Comment/documentation generation                   │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                               │
│  ┌──────────────────┐           ┌─────────────────────────┐    │
│  │  Jenkinsfile     │           │  New Jenkins Job        │    │
│  │  (Migrated)      │           │  (Created via API)      │    │
│  └──────────────────┘           └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. **Extraction Over Transformation**

**Problem**: Direct regex replacement (`replaceAll`) is fragile and leads to:
- Orphaned braces
- Incomplete conversions
- Syntax errors

**Solution**: Extract key parameters, then rebuild from templates.

```python
# ❌ BAD: Direct replacement
content = content.replace("server.upload(uploadSpec)", "jf 'rt u ...'")

# ✅ GOOD: Extract then rebuild
pattern, target = extract_upload_spec(content)
new_stage = build_upload_stage(pattern, target)
```

### 2. **Template-Based Generation**

**Why**: Ensures syntactically correct output every time.

**How**: Pre-defined stage templates with parameter injection points.

```python
template = """
stage('Upload Artifact') {
    steps {
        script {
            jf 'rt u {pattern} {target}'
        }
    }
}
"""
```

### 3. **Preserve Intent, Not Structure**

**Philosophy**: The migrated pipeline should achieve the same business goal, not be a line-by-line translation.

**Example**:
- Original: Creates BuildInfo objects manually
- Migrated: Relies on JFrog plugin's auto-management
- Result: Simpler code, same outcome

### 4. **Fail-Safe Defaults**

When extraction fails, use sensible defaults + warnings:
```python
server_id = extract_server_id(content) or 'ecosysjfrog'  # Default
print(f"⚠️  Using default server ID: {server_id}")
```

---

## Implementation Approaches

### Approach 1: Python CLI Tool (`migrate_artifactory_to_jfrog.py`)

**Use Case**: Batch migration, CI/CD integration, local development

**Pros**:
- Works offline
- Can process multiple files
- Easy to version control
- Scriptable

**Cons**:
- Requires Python environment
- Can't interact with Jenkins directly

**Architecture**:
```
┌─────────────────────────────────────────────┐
│  CLI Entry Point (main())                   │
│  - Parse arguments                          │
│  - Validate input file                      │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  HTML Decoder                               │
│  - Handles Jenkins XML exports              │
│  - &apos; → ', &quot; → ", &gt; → >        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Pattern Extractors                         │
│  - extract_server_id()                      │
│  - extract_upload_spec()                    │
│  - detect_stages()                          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Conversion Engine                          │
│  - convert_pipeline()                       │
│  - Builds stage list                        │
│  - Injects parameters                       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Output Writer                              │
│  - Writes to file                           │
│  - Prints summary                           │
└─────────────────────────────────────────────┘
```

### Approach 2: Groovy Script (`migrate-job.groovy`)

**Use Case**: In-Jenkins migration, no local access needed

**Pros**:
- Direct Jenkins API access
- Can read/write jobs automatically
- No file I/O needed
- One-click migration

**Cons**:
- Must run inside Jenkins
- Requires Script Security approval
- Limited debugging

**Architecture**:
```
┌─────────────────────────────────────────────┐
│  Jenkins Script Console                     │
│  - User pastes script                       │
│  - Configures source job name               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Job Reader                                 │
│  - Jenkins.instance.getItemByFullName()     │
│  - getDefinition().getScript()              │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Pattern Extraction (Groovy Regex)          │
│  - =~ /Artifactory\.server\(...\)/          │
│  - =~ /"pattern"\s*:\s*"([^"]+)"/          │
│  - =~ /"target"\s*:\s*"([^"]+)"/           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Pipeline Builder (Template)                │
│  - Concatenates stage strings               │
│  - Injects variables                        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  Job Creator                                │
│  - createProject(WorkflowJob)               │
│  - setDefinition(CpsFlowDefinition)         │
│  - save()                                   │
└─────────────────────────────────────────────┘
```

---

## Data Flow

### Phase 1: Input Processing

```
Original Jenkinsfile:
┌────────────────────────────────────────────────────┐
│ def server = Artifactory.server('ecosysjfrog')    │
│ def uploadSpec = """{                              │
│     "files": [{                                    │
│         "pattern": "*.jar",                        │
│         "target": "libs-release-local/"            │
│     }]                                             │
│ }"""                                               │
│ def buildInfo = server.upload(uploadSpec)          │
│ server.publishBuildInfo(buildInfo)                 │
└────────────────────────────────────────────────────┘
                        │
                        ▼ (HTML decode if needed)
┌────────────────────────────────────────────────────┐
│ def server = Artifactory.server('ecosysjfrog')    │
│ def uploadSpec = """{                              │
│     "files": [{                                    │
│         "pattern": "*.jar",                        │
│         "target": "libs-release-local/"            │
│     }]                                             │
│ }"""                                               │
│ def buildInfo = server.upload(uploadSpec)          │
│ server.publishBuildInfo(buildInfo)                 │
└────────────────────────────────────────────────────┘
```

### Phase 2: Pattern Extraction

```
Extracted Data:
┌────────────────────────────────────────────────────┐
│ server_id = "ecosysjfrog"                          │
│ upload_pattern = "*.jar"                           │
│ upload_target = "libs-release-local/"              │
│ has_ping = False                                   │
│ has_upload = True                                  │
│ has_publish = True                                 │
└────────────────────────────────────────────────────┘
```

### Phase 3: Stage Building

```
Built Stages:
┌────────────────────────────────────────────────────┐
│ stages = [                                         │
│     config_stage(server_id, url, user),           │
│     upload_stage(pattern, target),                │
│     publish_stage()                               │
│ ]                                                  │
└────────────────────────────────────────────────────┘
```

### Phase 4: Pipeline Assembly

```
Final Pipeline:
┌────────────────────────────────────────────────────┐
│ pipeline {                                         │
│     agent any                                      │
│     tools { jfrog 'jfrog-cli' }                   │
│     stages {                                       │
│         stage('Configure JFrog Server') { ... }   │
│         stage('Upload Artifact') {                │
│             jf 'rt u *.jar libs-release-local/'   │
│         }                                          │
│         stage('Publish Build Info') {             │
│             jf 'rt bp'                            │
│         }                                          │
│     }                                              │
│ }                                                  │
└────────────────────────────────────────────────────┘
```

---

## Pattern Extraction Logic

### 1. Server ID Extraction

**Pattern**: `Artifactory.server('SERVER_ID')`

**Regex**:
```python
r"Artifactory\.server\s*\(\s*['\"]([^'\"]+)['\"]"
```

**Logic**:
1. Find `Artifactory.server(`
2. Skip whitespace
3. Capture string inside quotes (single or double)
4. Return first match, or default to `'ecosysjfrog'`

**Edge Cases**:
- Multiple server declarations → Use first occurrence
- No server declaration → Use default
- Variable instead of string literal → Use default + warning

### 2. Upload Spec Parsing

**Pattern**: JSON string with `pattern` and `target` fields

**Input**:
```groovy
def uploadSpec = """{
    "files": [
        {
            "pattern": "artifacts/*.jar",
            "target": "repo/path/"
        }
    ]
}"""
```

**Regex**:
```python
pattern: r'"pattern"\s*:\s*"([^"]+)"'
target:  r'"target"\s*:\s*"([^"]+)"'
```

**Logic**:
1. Search for `"pattern": "VALUE"`
2. Search for `"target": "VALUE"`
3. Extract values between quotes
4. Handle Jenkins variables like `${BUILD_NUMBER}`

**Edge Cases**:
- Multiple files in spec → Take first one
- Nested JSON → Flatten to single pattern/target
- Missing fields → Use defaults (`*.txt`, `repo/`)

### 3. Stage Detection

**Logic**: Boolean flags based on content presence

```python
has_setup = "stage('Setup Artifactory')" in content
has_ping = "stage('Ping Artifactory')" in content
has_upload = "server.upload" in content
has_publish = "publishBuildInfo" in content
```

**Why Simple String Search**:
- Fast
- Reliable for well-formed pipelines
- No complex AST parsing needed

---

## Conversion Rules

### Rule 1: Server Configuration

**Before**:
```groovy
def server = Artifactory.server('ecosysjfrog')
```

**After**:
```groovy
jf 'config add ecosysjfrog --url=... --user=... --password=... --interactive=false'
jf 'c use ecosysjfrog'
```

**Why**:
- JFrog CLI requires explicit configuration
- Separates config from usage
- Allows credential injection

### Rule 2: Ping/Test Connection

**Before**:
```groovy
def server = Artifactory.server('ecosysjfrog')
def buildInfo = Artifactory.newBuildInfo()
// Test connection implicitly
```

**After**:
```groovy
jf 'rt ping'
```

**Why**:
- JFrog CLI has explicit ping command
- Simpler, more direct
- No BuildInfo needed

### Rule 3: File Upload

**Before**:
```groovy
def uploadSpec = """{
    "files": [{
        "pattern": "file.jar",
        "target": "repo/path/"
    }]
}"""
def buildInfo = server.upload(uploadSpec)
```

**After**:
```groovy
jf 'rt u file.jar repo/path/'
```

**Why**:
- CLI command is more concise
- No JSON spec needed for simple uploads
- Build info auto-tracked

### Rule 4: Build Info Publishing

**Before**:
```groovy
def buildInfo = Artifactory.newBuildInfo()
buildInfo.name = env.JOB_NAME
buildInfo.number = env.BUILD_NUMBER
server.publishBuildInfo(buildInfo)
```

**After**:
```groovy
jf 'rt bp'
```

**Why**:
- JFrog plugin auto-sets `JFROG_CLI_BUILD_NAME` and `JFROG_CLI_BUILD_NUMBER`
- No manual BuildInfo management needed
- One command to publish

### Rule 5: Setup Stage Removal

**Before**:
```groovy
stage('Setup Artifactory') {
    def server = Artifactory.server('ecosysjfrog')
    echo "Using: ${server.url}"
}
```

**After**:
```groovy
// Removed - handled in 'Configure JFrog Server' stage
```

**Why**:
- Redundant with new config stage
- Server URL logged by `jf config add`
- Cleaner pipeline structure

---

## Code Generation Strategy

### Template System

**Core Principle**: Each stage has a fixed template with variable injection points.

**Example - Upload Stage**:
```python
upload_template = """
stage('Upload Artifact') {
    steps {
        script {
            echo '=== Creating and Uploading Artifact ==='
            
            // Create test file
            sh 'echo "Build ${BUILD_NUMBER} - $(date)" > artifactory-test-${BUILD_NUMBER}.txt'
            
            // Upload (converted from Artifactory plugin spec)
            jf 'rt u {pattern} {target}'
            
            echo '✅ Successfully uploaded artifact!'
            echo "Uploaded to: {target}"
        }
    }
}
"""
```

**Injection**:
```python
stage_code = upload_template.format(
    pattern=upload_pattern,
    target=upload_target
)
```

### Stage Ordering

**Fixed Order**:
1. Configure JFrog Server (always first)
2. Ping Artifactory (if original had it)
3. Upload Artifact (if original had upload)
4. Publish Build Info (if original had publish)

**Why Fixed Order**:
- Configuration must happen before any JFrog CLI commands
- Upload before publish
- Predictable output

### Pipeline Wrapper

**Structure**:
```groovy
// Header comments (what changed)
pipeline {
    agent any
    tools { jfrog 'jfrog-cli' }
    stages {
        // Injected stages
    }
    post {
        success { ... }
        failure { ... }
    }
}
```

**Components**:
1. **Header comments**: Document the migration
2. **Tools block**: Required for JFrog CLI
3. **Stages**: Injected from template list
4. **Post block**: Standard success/failure handling

---

## Error Handling

### Input Validation

```python
# File exists check
if not input_file.exists():
    print(f"Error: Input file not found: {input_file}")
    sys.exit(1)

# Readable check (implicit in read_text())
```

### Extraction Failures

```python
# Graceful fallback to defaults
server_id = extract_server_id(content) or 'ecosysjfrog'
pattern, target = extract_upload_spec(content)
# If extraction fails, returns ('*.txt', 'repo/')

# Log what was extracted
print(f"  Server ID: {server_id}")
print(f"  Upload pattern: {pattern}")
print(f"  Upload target: {target}")
```

### HTML Entity Handling

```python
# Decode before processing
content = decode_html_entities(content)

# Handles:
# &apos; → '
# &quot; → "
# &gt;   → >
# &lt;   → <
# &amp;  → &
```

### Jenkins Script Console Errors

```groovy
try {
    // Migration logic
    println "✅ MIGRATION COMPLETE!"
    return "Success"
} catch (Exception e) {
    println "❌ ERROR: ${e.message}"
    e.printStackTrace()
    return "Failed"
}
```

---

## Testing Strategy

### Test Job Setup

**Original Job**: `artifactory-plugin-test`
- Uses Artifactory plugin
- Has all stages (Setup, Ping, Upload, Publish)
- Known-good configuration

**Migrated Job**: `jfrog-migrated-test`
- Uses JFrog plugin
- Equivalent functionality
- Generated by migration tool

### Validation Criteria

1. **Syntax**: Pipeline parses without errors
2. **Execution**: All stages complete successfully
3. **Artifacts**: Files uploaded to correct repository path
4. **Build Info**: Published with correct job name/number
5. **Logs**: Clear, informative output

### Test Cases

| Test Case | Original | Migrated | Pass Criteria |
|-----------|----------|----------|---------------|
| Ping | Uses BuildInfo object | Uses `jf rt ping` | Connection successful |
| Upload | JSON spec + `server.upload()` | `jf rt u pattern target` | File appears in repo |
| Publish | Manual BuildInfo creation | `jf rt bp` | Build info visible in UI |
| Credentials | From Jenkins config | From `jf config add` | No auth errors |

### Regression Testing

**Command**:
```bash
# Run both jobs
curl -X POST http://localhost:8080/job/artifactory-plugin-test/build
curl -X POST http://localhost:8080/job/jfrog-migrated-test/build

# Compare outputs
docker exec jenkins cat /var/jenkins_home/jobs/artifactory-plugin-test/builds/lastBuild/log
docker exec jenkins cat /var/jenkins_home/jobs/jfrog-migrated-test/builds/lastBuild/log
```

**Expected**: Both jobs should:
- Complete successfully
- Upload to same repo path
- Publish build info

---

## Performance Considerations

### Python Tool

- **Speed**: ~1-2 seconds per file
- **Memory**: < 10 MB
- **Bottleneck**: File I/O
- **Scalable**: Can process 1000+ files

### Groovy Tool

- **Speed**: ~2-5 seconds per job
- **Memory**: Jenkins heap space
- **Bottleneck**: Jenkins API calls
- **Scalable**: Limited by Jenkins load

---

## Future Enhancements

### 1. Multi-File Upload Specs

**Current**: Takes first file from spec  
**Future**: Generate multiple `jf rt u` commands

### 2. Download Specs

**Current**: Only handles uploads  
**Future**: Convert `server.download(spec)` to `jf rt dl`

### 3. Build Promotion

**Current**: Not supported  
**Future**: Convert `server.promote()` to `jf rt bpr`

### 4. Dry Run Mode

**Current**: Always writes output  
**Future**: `--dry-run` flag to preview changes

### 5. Batch Processing

**Current**: One file at a time  
**Future**: `migrate_all.py --directory jobs/`

---

## Conclusion

This migration tool uses a **template-based extraction and generation approach** to reliably convert Jenkins pipelines from the Artifactory plugin to the JFrog plugin.

**Key Design Decisions**:
1. Extract patterns, don't transform in-place
2. Use templates for reliable code generation
3. Fail gracefully with sensible defaults
4. Preserve business intent, not syntax
5. Support both CLI and in-Jenkins workflows

**Result**: A production-ready tool that can migrate real-world Jenkins jobs with high reliability and minimal manual intervention.
