import subprocess
import sys
import os
import shutil
from datetime import datetime, timedelta
from git import Repo
import difflib

def clone_repository(repo_url, clone_dir):
    try:
        if os.path.exists(clone_dir):
            shutil.rmtree(clone_dir)
        Repo.clone_from(repo_url, clone_dir)
        print(f"Repository cloned to {clone_dir}")
        return True
    except Exception as e:
        print(f"An error occurred while cloning the repository: {e}")
        return False

def find_python_files(directory):
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def find_java_files(directory):
    java_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.java'):
                java_files.append(os.path.join(root, file))
    return java_files

def select_main_python_file(python_files):
    # Heuristic to prioritize certain files
    priority_files = ['main.py', 'app.py']
    for priority_file in priority_files:
        for file in python_files:
            if file.endswith(priority_file):
                return file
    # If no priority file is found, return the first Python file found
    if python_files:
        return python_files[0]
    return None

def select_main_java_file(java_files):
    priority_files = ['Main.java', 'App.java']
    for priority_file in priority_files:
        for file in java_files:
            if file.endswith(priority_file):
                return file
    if java_files:
        return java_files[0]
    return None

def calculate_code_similarity(old_code, new_code):
    diff = difflib.ndiff(old_code.splitlines(), new_code.splitlines())
    changes = [line for line in diff if line.startswith(('+', '-'))]
    return 1 - (len(changes) / max(len(old_code.splitlines()), len(new_code.splitlines())))

def check_refactoring_frequency(repo_path, file_path, days):
    try:
        repo = Repo(repo_path)
        # Convert backslashes to forward slashes for Git compatibility
        git_file_path = file_path.replace('\\', '/')
        commits = list(repo.iter_commits(paths=git_file_path, since=(datetime.now() - timedelta(days=days)).isoformat()))

        print(f"\nNumber of commits affecting {git_file_path} in the last {days} days: {len(commits)}")

        if len(commits) < 2:
            print("Not enough commits to analyze refactoring frequency.")
            return

        refactoring_time_ratios = []
        for i in range(1, len(commits)):
            commit_time = commits[i-1].committed_datetime
            previous_commit_time = commits[i].committed_datetime
            time_diff = (commit_time - previous_commit_time).total_seconds() / 3600  # in hours

            old_code = (commits[i].tree / git_file_path).data_stream.read().decode()
            new_code = (commits[i-1].tree / git_file_path).data_stream.read().decode()

            similarity = calculate_code_similarity(old_code, new_code)
            refactoring_time_ratio = (1 - similarity) * time_diff
            refactoring_time_ratios.append(refactoring_time_ratio)

        avg_refactoring_time_ratio = sum(refactoring_time_ratios) / len(refactoring_time_ratios)
        print(f"Average refactoring time ratio: {avg_refactoring_time_ratio:.2f}")

        return avg_refactoring_time_ratio
    except Exception as e:
        print(f"An error occurred while analyzing the repository: {e}")
        return -1

def main(repo_url, days):
    clone_dir = 'cloned_repo'

    # Check if clone directory already exists
    if not os.path.exists(clone_dir):
        # Clone the repository if it doesn't exist
        if not clone_repository(repo_url, clone_dir):
            return
    else:
        print(f"Using existing clone directory: {clone_dir}")

    # Find Python and Java files in the cloned repository
    python_files = find_python_files(clone_dir)
    java_files = find_java_files(clone_dir)

    # Combine Python and Java files for flexibility in analysis
    all_files = python_files + java_files

    if not all_files:
        print("No Python or Java files found in the repository.")
        return

    # Analyze refactoring frequency for each file
    for file_path in all_files:
        print(f"\nSelected file for analysis: {file_path}")

        # Check refactoring frequency
        file_path_in_repo = os.path.relpath(file_path, clone_dir)
        refactor_ratio = check_refactoring_frequency(clone_dir, file_path_in_repo, days)

        if refactor_ratio is None:
            print("Error occurred during refactoring frequency analysis.")
            continue
        elif refactor_ratio == -1:
            print("Not enough commits to analyze refactoring frequency.")
            continue

        # Provide insights based on refactoring frequency for the current file
        if refactor_ratio < 0.1:
            print("\nRefactoring is recommended based on the observed refactoring time ratios.")
        elif refactor_ratio > 0.5:
            print("\nIt seems like there has been frequent refactoring recently. Consider stabilizing the code.")
        else:
            print("\nThe code seems stable with minimal recent changes.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python check_refactoring.py <repository_url> <Number_Of_Days>")
    else:
        repo_url = sys.argv[1]
        try:
            days = int(sys.argv[2])
        except ValueError:
            print("NumberOfDays must be an integer.")
            sys.exit(1)
        main(repo_url, days)
