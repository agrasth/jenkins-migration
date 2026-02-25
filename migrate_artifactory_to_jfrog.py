#!/usr/bin/env python3
"""
Jenkins Artifactory Plugin to JFrog Plugin Migration Tool

Converts Jenkinsfiles from Artifactory Plugin to JFrog Plugin.

Usage:
    python3 migrate_artifactory_to_jfrog.py <input-jenkinsfile> <output-jenkinsfile>
    
Example:
    python3 migrate_artifactory_to_jfrog.py Jenkinsfile.old Jenkinsfile.migrated
"""

import sys
import re
import html
from pathlib import Path


def decode_html_entities(content):
    """Decode HTML entities from Jenkins XML export"""
    content = content.replace('&apos;', "'")
    content = content.replace('&quot;', '"')
    content = content.replace('&gt;', '>')
    content = content.replace('&lt;', '<')
    content = content.replace('&amp;', '&')
    return content


def extract_server_id(content):
    """Extract server ID from Artifactory.server() calls"""
    match = re.search(r"Artifactory\.server\s*\(\s*['\"]([^'\"]+)['\"]", content)
    return match.group(1) if match else 'ecosysjfrog'


def extract_upload_spec(content):
    """Extract pattern and target from JSON upload spec"""
    pattern_match = re.search(r'"pattern"\s*:\s*"([^"]+)"', content)
    target_match = re.search(r'"target"\s*:\s*"([^"]+)"', content)
    
    pattern = pattern_match.group(1) if pattern_match else '*.txt'
    target = target_match.group(1) if target_match else 'repo/'
    
    return pattern, target


def convert_pipeline(content, server_url="https://ecosysjfrog.jfrog.io", server_user="agrasth"):
    """Convert Artifactory plugin pipeline to JFrog plugin"""
    
    # Extract patterns
    server_id = extract_server_id(content)
    upload_pattern, upload_target = extract_upload_spec(content)
    
    print(f"  Server ID: {server_id}")
    print(f"  Upload pattern: {upload_pattern}")
    print(f"  Upload target: {upload_target}")
    
    # Detect what stages exist
    has_setup = "stage('Setup Artifactory')" in content
    has_ping = "stage('Ping Artifactory')" in content
    has_upload = "server.upload" in content
    has_publish = "publishBuildInfo" in content
    
    print(f"  Stages detected: Setup={has_setup}, Ping={has_ping}, Upload={has_upload}, Publish={has_publish}")
    
    # Build stages list
    stages = []
    
    # Always add Config stage
    stages.append("""        stage('Configure JFrog Server') {
            steps {
                script {
                    echo '=== Configuring JFrog Server ==='
                    jf 'config add """ + server_id + """ --url=""" + server_url + """ --user=""" + server_user + """ --password=YOUR_PASSWORD --interactive=false'
                    jf 'c use """ + server_id + """'
                    echo '✅ Server configured'
                }
            }
        }""")
    
    # Add Ping stage
    if has_ping:
        stages.append("""        
        stage('Ping Artifactory') {
            steps {
                script {
                    echo '=== Testing Artifactory Connection ==='
                    jf 'rt ping'
                    echo '✅ Successfully connected to Artifactory!'
                }
            }
        }""")
    
    # Add Upload stage
    if has_upload:
        stages.append("""        
        stage('Upload Artifact') {
            steps {
                script {
                    echo '=== Creating and Uploading Artifact ==='
                    
                    // Create test file
                    sh 'echo "Build ${BUILD_NUMBER} - $(date)" > artifactory-test-${BUILD_NUMBER}.txt'
                    
                    // Upload (converted from Artifactory plugin spec)
                    jf 'rt u """ + upload_pattern + """ """ + upload_target + """'
                    
                    echo '✅ Successfully uploaded artifact!'
                    echo "Uploaded to: """ + upload_target + """"
                }
            }
        }""")
    
    # Add Publish stage
    if has_publish:
        stages.append("""        
        stage('Publish Build Info') {
            steps {
                script {
                    echo '=== Publishing Build Info ==='
                    jf 'rt bp'
                    echo '✅ Build info published!'
                }
            }
        }""")
    
    # Build complete pipeline
    converted = """// MIGRATED FROM ARTIFACTORY PLUGIN TO JFROG PLUGIN
// Original server ID: """ + server_id + """
// 
// Conversion applied:
// - Removed stage: Setup Artifactory
// - Artifactory.server() → jf 'config add' + 'c use'
// - server.upload(spec) → jf 'rt u pattern target'
// - server.publishBuildInfo() → jf 'rt bp'
// - BuildInfo objects → Removed (auto-managed)
//
// TODO: Replace YOUR_PASSWORD on line 24 with actual password

pipeline {
    agent any
    
    tools {
        jfrog 'jfrog-cli'
    }
    
    stages {
""" + '\n'.join(stages) + """
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
    
    return converted


def main():
    """Main entry point"""
    
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nError: Please provide both input and output filenames")
        print("\nExample:")
        print("  python3 migrate_artifactory_to_jfrog.py Jenkinsfile.old Jenkinsfile.migrated")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)
    
    print(f"Reading: {input_file}")
    content = input_file.read_text()
    
    # Decode HTML entities if present (from Jenkins XML export)
    content = decode_html_entities(content)
    print("✓ Decoded HTML entities")
    
    print("\nConverting pipeline...")
    converted = convert_pipeline(content)
    
    # Write output
    output_file.write_text(converted)
    print(f"✓ Converted pipeline written to: {output_file}")
    
    print("\n" + "=" * 50)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 50)
    print(f"\nNext steps:")
    print(f"1. Review {output_file}")
    print(f"2. Replace YOUR_PASSWORD on line 24")
    print(f"3. Create Jenkins job with this script")
    print(f"4. Test it!")


if __name__ == '__main__':
    main()
