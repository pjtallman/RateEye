import yaml
import subprocess
import sys
import os

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

def main():
    yaml_path = "milestone_tasks.yaml"
    if not os.path.exists(yaml_path):
        print(f"[ERROR] {yaml_path} not found. Please create it first.")
        sys.exit(1)

    try:
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse {yaml_path}: {e}")
        sys.exit(1)

    milestone_name = config.get("milestone_name")
    milestone_desc = config.get("description", "")
    branch_name = config.get("branch_name")
    issues = config.get("issues", [])

    if not milestone_name or not branch_name:
        print("[ERROR] 'milestone_name' and 'branch_name' are required in YAML.")
        sys.exit(1)

    print("\n" + "="*40)
    print("   RATEEYE MILESTONE START PLAN")
    print("="*40)
    print(f"New Milestone: {milestone_name}")
    print(f"New Branch:    {branch_name}")
    print(f"Issue Count:   {len(issues)}")
    print("-"*40)
    print("Plan of Action:")
    print(f"1. Create GitHub Milestone '{milestone_name}'")
    print(f"2. Create branch '{branch_name}' from main")
    print(f"3. Push branch to origin")
    print(f"4. Create {len(issues)} issues linked to milestone")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue.get('title')}")
    print("="*40 + "\n")

    confirm = input("Begin initiating this milestone? (y/n): ")
    if confirm.lower() != 'y':
        print("[INFO] Initialization aborted.")
        sys.exit(0)

    # 1. Milestone
    print(f"[1/4] Creating GitHub Milestone '{milestone_name}'...")
    run(f"gh issue milestone create --title '{milestone_name}' --description '{milestone_desc}'", check=False)

    # 2. Branch
    print(f"[2/4] Creating local branch '{branch_name}'...")
    run("git checkout main")
    run("git pull origin main")
    run(f"git checkout -b {branch_name}")

    # 3. Push
    print(f"[3/4] Pushing branch to origin...")
    run(f"git push -u origin {branch_name}")

    # 4. Issues
    print(f"[4/4] Creating GitHub issues...")
    for issue in issues:
        title = issue.get("title")
        body = issue.get("body", "").strip()
        labels = ",".join(issue.get("labels", []))
        
        label_arg = f"--label '{labels}'" if labels else ""
        print(f"   - Creating: {title}")
        
        # Use temporary file for multiline body to avoid shell escaping issues
        with open(".issue_body.md", "w") as bf:
            bf.write(body)
        
        run(f"gh issue create --title '{title}' --body-file .issue_body.md --milestone '{milestone_name}' {label_arg}")
        
    if os.path.exists(".issue_body.md"):
        os.remove(".issue_body.md")

    print(f"\n[SUCCESS] {milestone_name} is now active on GitHub and branch '{branch_name}' is ready.")

if __name__ == "__main__":
    main()
