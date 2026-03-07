#!/usr/bin/env python3
"""
Deploy FX Dashboard

Complete deployment pipeline:
1. Re-export all pipeline data (clears and regenerates exports)
2. Copy fresh exports to dashboard site folder
3. Deploy to GitHub Pages

Usage:
    python3 scripts/deploy-dashboard.py

Environment variables required:
    GITHUB_REPO - Repository URL (e.g., https://github.com/user/repo)
    GITHUB_TOKEN - GitHub personal access token with repo write access
"""

import os
import sys
import subprocess
import shutil
import glob
from datetime import datetime

sys.path.append('/workspace/group/fx-portfolio/scripts')
from pipeline_logger import PipelineLogger

# Constants
SITE_NAME = "fx-dashboard"
DASHBOARD_PATH = f"/workspace/group/sites/{SITE_NAME}"
DASHBOARD_DATA_PATH = f"{DASHBOARD_PATH}/data"
EXPORTS_PATH = "/workspace/group/fx-portfolio/data/exports"
CONFIG_PATH = "/workspace/group/fx-portfolio/config/system_config.json"
DEPLOY_DIR = "/tmp/nanopages-deploy"

def run_command(cmd, description, capture_output=False):
    """Run shell command with error handling"""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result.stdout
        else:
            subprocess.run(cmd, shell=True, check=True)
            return None
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed: {description}\nCommand: {cmd}\nError: {e}")

def clear_dashboard_data():
    """Clear old export files from dashboard data folder"""
    print("\n" + "="*60)
    print("Clearing Old Dashboard Data")
    print("="*60)

    patterns = [
        "step*.csv",
        "step*.json",
        "tracking_*.json",
        "pipeline_steps.json"
    ]

    files_deleted = 0
    for pattern in patterns:
        files = glob.glob(f"{DASHBOARD_DATA_PATH}/{pattern}")
        for file in files:
            try:
                os.remove(file)
                files_deleted += 1
                print(f"  ✓ Deleted: {os.path.basename(file)}")
            except Exception as e:
                print(f"  ⚠️  Could not delete {os.path.basename(file)}: {e}")

    print(f"\n✓ Cleared {files_deleted} old files")

def export_pipeline_data():
    """Run all export scripts to regenerate data"""
    print("\n" + "="*60)
    print("Exporting Pipeline Data")
    print("="*60)

    export_scripts = [
        ("scripts/export-step-counts.py", "Step counts"),
        ("scripts/export-pipeline-data.py", "Pipeline data (steps 2-6)"),
        ("scripts/export-logs.py", "Pipeline logs"),
        ("scripts/export-exchange-rates.py", "Exchange rates matrix")
    ]

    for script, description in export_scripts:
        print(f"\n• {description}...")
        run_command(f"cd /workspace/group/fx-portfolio && python3 {script}", description)
        print(f"  ✓ Completed")

def copy_to_dashboard():
    """Copy fresh exports to dashboard folder"""
    print("\n" + "="*60)
    print("Copying Exports to Dashboard")
    print("="*60)

    # Ensure dashboard data directory exists
    os.makedirs(DASHBOARD_DATA_PATH, exist_ok=True)

    # Copy all CSV and JSON files from exports
    files_copied = 0

    for ext in ['*.csv', '*.json']:
        files = glob.glob(f"{EXPORTS_PATH}/{ext}")
        for file in files:
            basename = os.path.basename(file)
            dest = f"{DASHBOARD_DATA_PATH}/{basename}"
            shutil.copy2(file, dest)
            files_copied += 1
            print(f"  ✓ Copied: {basename}")

    # Copy system config (source of truth)
    if os.path.exists(CONFIG_PATH):
        shutil.copy2(CONFIG_PATH, f"{DASHBOARD_DATA_PATH}/system_config.json")
        files_copied += 1
        print(f"  ✓ Copied: system_config.json")

    print(f"\n✓ Copied {files_copied} files to dashboard")

def deploy_to_github():
    """Deploy dashboard to GitHub Pages"""
    print("\n" + "="*60)
    print("Deploying to GitHub Pages")
    print("="*60)

    # Get environment variables
    github_repo = os.environ.get('GITHUB_REPO')
    github_token = os.environ.get('GITHUB_TOKEN')

    if not github_repo or not github_token:
        raise Exception("Missing GITHUB_REPO or GITHUB_TOKEN environment variable")

    # Parse repo info
    repo_url = github_repo.replace('https://', f'https://x-access-token:{github_token}@')
    parts = github_repo.split('/')
    github_user = parts[3]
    github_repo_name = parts[4]
    pages_url = f"https://{github_user}.github.io/{github_repo_name}/{SITE_NAME}/"

    # Clone repo
    print(f"\n• Cloning repository...")
    if os.path.exists(DEPLOY_DIR):
        shutil.rmtree(DEPLOY_DIR)

    run_command(
        f"git clone {repo_url} {DEPLOY_DIR}",
        "Clone repository",
        capture_output=True
    )
    print(f"  ✓ Cloned to {DEPLOY_DIR}")

    # Configure git
    print(f"\n• Configuring git...")
    run_command(f"cd {DEPLOY_DIR} && git config user.name 'nano'", "Set git user.name")
    run_command(f"cd {DEPLOY_DIR} && git config user.email 'nano@nanoclaw'", "Set git user.email")
    print(f"  ✓ Git configured")

    # Copy dashboard files
    print(f"\n• Copying dashboard files...")
    site_path = f"{DEPLOY_DIR}/{SITE_NAME}"
    if os.path.exists(site_path):
        shutil.rmtree(site_path)
    shutil.copytree(DASHBOARD_PATH, site_path)
    print(f"  ✓ Copied dashboard to {site_path}")

    # Check for changes
    print(f"\n• Checking for changes...")
    run_command(f"cd {DEPLOY_DIR} && git add -A", "Stage changes")

    result = subprocess.run(
        f"cd {DEPLOY_DIR} && git diff --cached --quiet",
        shell=True,
        capture_output=True
    )

    if result.returncode == 0:
        print("\n" + "="*60)
        print("✓ No changes - dashboard already up to date")
        print("="*60)
        print(f"\nDashboard URL: {pages_url}")
        return False

    # Commit and push
    print(f"  ✓ Changes detected")

    commit_msg = f"Update {SITE_NAME}: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    print(f"\n• Committing: {commit_msg}")
    run_command(f"cd {DEPLOY_DIR} && git commit -m '{commit_msg}'", "Commit changes")
    print(f"  ✓ Committed")

    print(f"\n• Pushing to GitHub...")
    run_command(f"cd {DEPLOY_DIR} && git push origin main", "Push to GitHub")
    print(f"  ✓ Pushed")

    print("\n" + "="*60)
    print("✓ Deployment Complete")
    print("="*60)
    print(f"\nDashboard URL: {pages_url}")
    print("\nNote: GitHub Pages may take 30-60 seconds to rebuild.")
    print("      Hard refresh your browser (Ctrl+Shift+R) to see changes.")

    return True

def main():
    """Main deployment pipeline"""
    logger = PipelineLogger('deploy', 'Deploy Dashboard')
    logger.start()

    try:
        print("="*60)
        print("FX Dashboard Deployment Pipeline")
        print("="*60)
        print(f"\nSite: {SITE_NAME}")
        print(f"Dashboard path: {DASHBOARD_PATH}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Step 1: Clear old data
        clear_dashboard_data()
        logger.add_info('cleared_data', True)

        # Step 2: Export fresh data
        export_pipeline_data()
        logger.add_info('exported_data', True)

        # Step 3: Copy to dashboard
        copy_to_dashboard()
        logger.add_info('copied_to_dashboard', True)

        # Step 4: Deploy to GitHub
        deployed = deploy_to_github()
        logger.add_info('deployed_to_github', deployed)

        if deployed:
            logger.success()
        else:
            logger.success()  # Still success, just no changes

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()

if __name__ == '__main__':
    main()
