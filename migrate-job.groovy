#!/usr/bin/env groovy
/**
 * Jenkins Migration Tool - Artifactory → JFrog Plugin
 * 
 * This tool EXTRACTS patterns from your original job and converts them.
 * Run in: http://localhost:8080/script
 */

import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition

// ============ CONFIGURATION ============
def sourceJobName = "artifactory-plugin-test"
def serverUrl = "https://ecosysjfrog.jfrog.io"
def serverUser = "agrasth"
def serverPassword = "Naman123!"
// =======================================

def targetJobName = "${sourceJobName}-migrated"

println "🚀 Migration: ${sourceJobName} → ${targetJobName}"
println "=" * 50

try {
    def jenkins = Jenkins.instance
    def sourceJob = jenkins.getItemByFullName(sourceJobName, WorkflowJob)
    
    if (!sourceJob) {
        println "❌ Job not found"
        return "Error"
    }
    
    def originalScript = sourceJob.getDefinition().getScript()
    println "✓ Read original (${originalScript.length()} chars)"
    
    // ============ EXTRACT PATTERNS FROM ORIGINAL ============
    println "\n📋 Extracting patterns..."
    
    // Extract server ID
    def serverIdMatch = (originalScript =~ /Artifactory\.server\s*\(\s*['"]([^'"]+)/)
    def serverId = serverIdMatch ? serverIdMatch[0][1] : 'ecosysjfrog'
    println "  Server ID: ${serverId}"
    
    // Extract upload spec pattern and target
    def patternMatch = (originalScript =~ /"pattern"\s*:\s*"([^"]+)"/)
    def targetMatch = (originalScript =~ /"target"\s*:\s*"([^"]+)"/)
    
    def uploadPattern = patternMatch ? patternMatch[0][1] : 'file.txt'
    def uploadTarget = targetMatch ? targetMatch[0][1] : 'repo/'
    
    println "  Upload pattern: ${uploadPattern}"
    println "  Upload target: ${uploadTarget}"
    
    // Check if original has Ping stage
    def hasPing = originalScript.contains("stage('Ping Artifactory')")
    def hasUpload = originalScript.contains("server.upload")
    def hasPublish = originalScript.contains("publishBuildInfo")
    
    println "  Has Ping: ${hasPing}"
    println "  Has Upload: ${hasUpload}"
    println "  Has Publish: ${hasPublish}"
    
    // ============ BUILD CONVERTED PIPELINE ============
    println "\n🔄 Building migrated pipeline..."
    
    def stages = []
    
    // Always add Config stage
    stages << """        stage('Configure JFrog Server') {
            steps {
                script {
                    echo '=== Configuring JFrog Server ==='
                    jf 'config add ${serverId} --url=${serverUrl} --user=${serverUser} --password=${serverPassword} --interactive=false'
                    jf 'c use ${serverId}'
                    echo '✅ Server configured'
                }
            }
        }"""
    
    // Add Ping stage if original had it
    if (hasPing) {
        stages << """        
        stage('Ping Artifactory') {
            steps {
                script {
                    echo '=== Testing Artifactory Connection ==='
                    jf 'rt ping'
                    echo '✅ Successfully connected to Artifactory!'
                }
            }
        }"""
    }
    
    // Add Upload stage if original had it
    if (hasUpload) {
        stages << '''        
        stage('Upload Artifact') {
            steps {
                script {
                    echo '=== Creating and Uploading Artifact ==='
                    
                    // Create test file
                    sh 'echo "Build ${BUILD_NUMBER} - $(date)" > artifactory-test-${BUILD_NUMBER}.txt'
                    
                    // Upload (converted from Artifactory spec)
                    jf 'rt u ''' + uploadPattern + ''' ''' + uploadTarget + ''''
                    
                    echo '✅ Successfully uploaded artifact!'
                    echo "Uploaded to: ''' + uploadTarget + '''"
                }
            }
        }'''
    }
    
    // Add Publish stage if original had it
    if (hasPublish) {
        stages << """        
        stage('Publish Build Info') {
            steps {
                script {
                    echo '=== Publishing Build Info ==='
                    jf 'rt bp'
                    echo '✅ Build info published!'
                }
            }
        }"""
    }
    
    // Build complete pipeline
    def convertedScript = """// MIGRATED FROM ARTIFACTORY PLUGIN TO JFROG PLUGIN
// Source: ${sourceJobName}
// Server: ${serverId}
//
// Extracted and converted:
// - Server ID: ${serverId}
// - Upload pattern: ${uploadPattern}
// - Upload target: ${uploadTarget}

pipeline {
    agent any
    
    tools {
        jfrog 'jfrog-cli'
    }
    
    stages {
${stages.join('\n')}
    }
    
    post {
        success {
            echo '🎉 Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed'
        }
    }
}
"""
    
    println "✓ Built pipeline (${convertedScript.length()} chars)"
    
    // Create/update job
    def targetJob = jenkins.getItemByFullName(targetJobName, WorkflowJob)
    if (!targetJob) {
        targetJob = jenkins.createProject(WorkflowJob, targetJobName)
    }
    
    targetJob.setDefinition(new CpsFlowDefinition(convertedScript, true))
    targetJob.setDescription("Migrated from ${sourceJobName}")
    targetJob.save()
    
    println "\n✅ MIGRATION COMPLETE!"
    println "=" * 50
    println "URL: ${jenkins.getRootUrl()}job/${targetJobName}/"
    println "\nTest: Click 'Build Now' in the migrated job"
    
    return "Success"
    
} catch (Exception e) {
    println "❌ ERROR: ${e.message}"
    e.printStackTrace()
    return "Failed"
}
