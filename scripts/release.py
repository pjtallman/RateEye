import argparse
import subprocess
import sys
import os
import json

def run(cmd, check=True, capture=True):
    """Executes a shell command and returns output or handles errors."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, text=True, capture_output=capture)
        return result.stdout.strip() if capture else None
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed: {cmd}")
        print(f"[DETAILS] {e.stderr}")
        if check: sys.exit(1)
        return None

def get_current_branch():
    return run("git rev-parse --abbrev-ref HEAD")

def get_milestone_for_branch(branch):
    """Uses gh to find the milestone associated with the current branch/PR."""
    # First try to find via PR
    pr_json = run(f"gh pr view {branch} --json milestone", check=False)
    if pr_json:
        try:
            data = json.loads(pr_json)
            if data.get("milestone"):
                return data["milestone"]["title"]
        except json.JSONDecodeError:
            pass
    
    # Fallback: List open milestones and look for a fuzzy match in branch name
    milestones_json = run("gh milestone list --state open --json title")
    try:
        milestones = json.loads(milestones_json)
        for m in milestones:
            # e.g. if branch is 'feat/milestone-6-deployment' and milestone is 'Milestone 6'
            clean_m = m['title'].lower().replace(" ", "-")
            if clean_m in branch.lower():
                return m['title']
    except:
        pass
    return None

def main():
    parser = argparse.ArgumentParser(description="RateEye Milestone Release Automation")
    parser.add_argument("--version", required=True, help="Version to release (e.g., v1.0.4)")
    args = parser.parse_args()

    current_branch = get_current_branch()
    if current_branch == "main":
        print("[ERROR] You are already on the 'main' branch. Run this from your feature/milestone branch.")
        sys.exit(1)

    milestone = get_milestone_for_branch(current_branch)
    
    print("\n" + "="*40)
    print("   RATEEYE RELEASE PLAN OF ACTION")
    print("="*40)
    print(f"Current Branch:    {current_branch}")
    print(f"Target Version:    {args.version}")
    print(f"Detected Milestone: {milestone or 'None Found'}")
    print("-"*40)
    print("1. Create GitHub PR to 'main'")
    print("2. Merge PR and delete remote branch")
    print("3. Local Cleanup: checkout main, pull, delete local branch")
    print("4. Build: 'uv build' to generate .whl")
    print(f"5. Create GitHub Release {args.version} with auto-notes")
    if milestone:
        print(f"6. Close GitHub Milestone '{milestone}'")
    print("="*40 + "\n")

    confirm = input("Confirm execution of all steps? (y/n): ")
    if confirm.lower() != 'y':
        print("[INFO] Release aborted by user.")
        sys.exit(0)

    # 1. PR
    print(f"[1/6] Creating PR for {current_branch}...")
    run(f"gh pr create --title 'Release {args.version}' --body 'Automated release for {milestone or current_branch}' --base main --head {current_branch}", check=False)

    # 2. Merge
    print(f"[2/6] Merging PR into main...")
    run(f"gh pr merge {current_branch} --merge --delete-branch")

    # 3. Cleanup
    print(f"[3/6] Cleaning up local environment...")
    run("git checkout main")
    run("git pull origin main")
    run(f"git branch -d {current_branch}", check=False)

    # 4. Build
    print(f"[4/6] Building package with uv...")
    if os.path.exists("dist"):
        import shutil
        shutil.rmtree("dist")
    run("uv build")

    # 5. Release
    print(f"[5/6] Creating GitHub Release {args.version}...")
    wheel = next((f for f in os.listdir("dist") if f.endswith(".whl")), None)
    if not wheel:
        print("[ERROR] No .whl file found in dist/ after build.")
        sys.exit(1)
    
    run(f"gh release create {args.version} 'dist/{wheel}' --generate-notes --title 'Release {args.version}'")

    # 6. Milestone
    if milestone:
        print(f"[6/6] Closing milestone '{milestone}'...")
        run(f"gh milestone edit '{milestone}' --state closed")
    else:
        print("[6/6] No milestone detected to close. Skipping.")

    print(f"\n[SUCCESS] RateEye {args.version} has been released and environment is clean.")

if __name__ == "__main__":
    main()
