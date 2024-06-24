import subprocess
import sys
import os
from datetime import datetime, timedelta
from git import Repo
import difflib

rate = ''
def clone_repository(repo_url, clone_dir):
    Repo.clone_from(repo_url, clone_dir)
    print(f"\nRepository cloned to {clone_dir}")
    return True
        
def find_python_files(directory):
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

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

def calculate_code_similarity(old_code, new_code):
    old_tokens = list(old_code.split())
    new_tokens = list(new_code.split())
    
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)
    similarity_ratio = matcher.ratio()
    
    return similarity_ratio

def check_refactoring_frequency(repo_path, file_path, num_commits):
    try:
        # Initialize repository object
        repo = Repo(repo_path)
        
        # Convert backslashes to forward slashes for Git compatibility
        git_file_path = file_path.replace('\\', '/')
        
        # Fetch commits with a max count of 'num_commits' or all available commits if fewer
        commits = list(repo.iter_commits(paths=git_file_path, max_count=num_commits))
        
        print(f"\nNumber of commits affecting {git_file_path}: {len(commits)}")
        
        # Check if there are enough commits to analyze
        if len(commits) < 2:
            print("Not enough commits to analyze refactoring frequency.")
            return None
        
        refactoring_time_ratios = []
        
        # Calculate refactoring time ratios between consecutive commits
        for i in range(1, len(commits)):
            commit_time = commits[i-1].committed_datetime
            previous_commit_time = commits[i].committed_datetime
            time_diff = abs((commit_time - previous_commit_time).total_seconds()) / 3600  # in hours
            
            old_code = (commits[i].tree / git_file_path).data_stream.read().decode()
            new_code = (commits[i-1].tree / git_file_path).data_stream.read().decode()
            
            similarity = calculate_code_similarity(old_code, new_code)
            refactoring_time_ratio = (1 - similarity) * time_diff
            refactoring_time_ratios.append(refactoring_time_ratio)
        
        if not refactoring_time_ratios:
            print("No refactoring detected in the specified commits.")
            return 0.0  # Return 0.0 or another default value if no refactoring is detected
        
        # Calculate average refactoring time ratio
        avg_refactoring_time_ratio = sum(refactoring_time_ratios) / len(refactoring_time_ratios)
        print(f"Average refactoring time ratio: {avg_refactoring_time_ratio:.2f}")
        
        return avg_refactoring_time_ratio
    
    except Exception as e:
        print(f"An error occurred while analyzing the repository: {e}")
        return None

def check_python_code_smells(file_path):
    global rate
    try:
        # Run pylint on the provided file and capture the output
        result = subprocess.run(
            ['pylint', file_path],
            capture_output=True,
            text=True
        )

        # Parse pylint output
        issues = []
        for line in result.stdout.splitlines():
            if line.startswith('cloned_repo'):
                parts = line.split(': ', 1)
                if len(parts) == 2:
                    path = parts[0].split(' ', 1)[0]  # Extract path and issue type
                    message = parts[1]
                    issues.append(f"{path}: {message}")
            elif "Your code has been rated" in line:
                rate = line

        return issues
    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
        return -1
    except Exception as e:
        print(f"An error occurred: {e}")
        return -1

def provide_python_recommendations(issues):
    issues_by_code = {}
    recommendations = {
        'C0103': 'Invalid name . Use a consistent naming style, such as snake_case for variables and functions, and CamelCase for classes.',
        'C0111': 'Missing module/class/function docstring. Consider adding a docstring to improve code documentation.',
        'C0114': 'To improve code readability and maintainability, include a docstring at the beginning of your module. A good module docstring should provide a brief overview of the module\'s purpose, its functionality, and any important information that might help other developers understand and use the module. Follow the PEP 257 conventions for module docstrings.',
        'C0116': 'To improve code readability and maintainability, always include a docstring at the beginning of your functions and methods. A good docstring should describe the purpose of the function, its parameters, return values, and any exceptions it might raise. Follow the PEP 257 conventions for docstrings.',
        'C0200': 'Consider using enumerate() instead of iterating with range() and len().',
        'C0301': 'Line too long . Consider breaking the line into smaller parts.',
        'C0302': 'Too many lines in module . Consider refactoring into smaller modules.',
        'C0303': 'Consider removing unnecessary empty spaces.',
        'C0305': 'Consider removing unnecessary empty lines.',
        'C0321': 'Multiple statements on one line.',
        'C0325': 'Unnecessary parens after.',
        'C0330': 'Consider fixing indentation.',
        'C0411': 'Wrong import order. Imports should be grouped in the following order: standard library imports, related third-party imports, local application/library-specific imports.',
        'C0412': 'Imports not grouped. Separate imports by blank line.',
        'C1801': 'Do not use `len()` to check if a sequence is empty. Instead, use `if`.',
        'E0401': 'Consider installing the mentioned libraries.',
        'E1101': 'Module has no  member. Ensure the module or class has the expected attributes or methods.',
        'E1121': 'Too many positional arguments for function call .',
        'E1133': 'Unused variable . Remove the variable or use it in the code.',
        'E1134': 'Unnecessary statement.',
        'E1200': 'Unsupported token.',
        'E9999': 'SyntaxError: invalid syntax.',
        'F0001': 'Internal error.',
        'F0010': 'Syntax error.',
        'F0202': 'Unable to find module. Check if the module is installed and available in the correct path.',
        'F0401': 'Unable to import module. Check if the module is installed and available in the correct path.',
        'R0201': 'Method has no argument.',
        'R0801': 'Similar lines in files.',
        'R0901': 'Too many ancestors .',
        'R0902': 'Too many instance attributes .',
        'R0903': 'Too few public methods . Consider combining similar methods or ensuring the class has enough functionality.',
        'R0904': 'Too many public methods . Consider refactoring to reduce the number of methods.',
        'R0911': 'Too many return statements . Consider refactoring to reduce the complexity of the method.',
        'R0912': 'Too many branches . Consider refactoring to reduce the complexity of the method.',
        'R0913': 'Too many arguments . Consider refactoring to reduce the number of arguments.',
        'R0914': 'Too many local variables . Try to reduce the number of variables or break the function into smaller ones.',
        'R0915': 'Too many statements . Consider breaking the function into smaller, more manageable pieces.',
        'R1702': 'Too many nested blocks . Consider refactoring to reduce the nesting.',
        'R1705': 'No exception type(s) specified.',
        'R1716': 'Consider separating comparisons with prantesis.',
        'R1722': 'Consider using sys.exit().',
        'W0102': 'Dangerous default value. Avoid using mutable default values in function/method definitions.',
        'W0201': 'Attribute defined outside __init__ method.',
        'W0212': 'Access to a protected member of a client class.',
        'W0221': 'Arguments number differs from method.',
        'W0231': 'Instance attribute defined outside __init__ method.',
        'W0611': 'Unused import. Remove the import statement.',
        'W0612': 'Unused variable. Remove the variable or use it in the code.',
        'W0613': 'Unused argument. Remove the argument or use it in the code.',
        'W0621': 'Redefining built-in .',
        'W0702': 'No exception type(s) specified in except clause. Specify the exception type(s) to catch.',
        'W0703': 'Catching "Exception" is too broad. Instead, catch specific exceptions to handle expected errors and avoid masking other issues. For example, use "except ValueError:" instead of "except Exception:".',
        'W1514': 'Using `open()` without explicitly specifying an encoding can lead to compatibility issues across different systems and locales. Always specify an encoding (e.g., `open(filename, mode, encoding="utf-8")`) to ensure consistent behavior and to avoid potential encoding-related bugs.',
    }

    print("\nDetected code smells and recommendations:")
    for issue in issues:
        # Split issue string to extract path_and_issue and message
        issue_parts = issue.split(': ', 1)
        if len(issue_parts) >= 2:
            path = issue_parts[0]
            parts = path.split(':')
            file_path = parts[0]
            try:
                line = parts[1]
            except:
                line = 'No code smells detected!'
            message = issue_parts[1]
            code = message.split(': ', 1)[0].strip()
            message = message.split(': ', 1)[1].strip()
            
            # Add issue to the dictionary
            if code not in issues_by_code:
                issues_by_code[code] = {'message': message, 'recommendation': recommendations.get(code, None), 'locations': []}
            try:
                issues_by_code[code]['locations'].append((file_path, int(line)))
            except:
                pass

    # Print issues grouped by code
    for code, issue_info in issues_by_code.items():
        print('######################################################################################')
        print(f"Code: {code}\n")
        print(f"Code Smell: {issue_info['message']}\n")
        
        print("Locations:")
        for file_path, line_number in issue_info['locations']:
            try:
                print(f"- Line: {line_number}")
            except:
                continue
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                if line_number <= len(lines):
                    print(f"  {lines[line_number - 1].strip()}")  # Print the line of code
                else:
                    print(f"  Line number {line_number} exceeds total lines in file.")
        print() 

        if code in recommendations:
            print(f"Recommendation: {recommendations[code]}\n")

        else:
            print(f"Recommendation: General code improvement suggested.\n")
    print('#####################################################################################################')
    print(rate)
    print('######################################################################################')

def main(repo_url, num_commits):
    clone_dir = 'cloned_repo'
    checkstyle_jar = "checkstyle-10.17.0-all.jar"
    checkstyle_config = "checkstyle.xml"

    # Check if clone directory already exists
    if os.path.exists(clone_dir):
        os.system(f'rd /s /q "{clone_dir}"')

    if not clone_repository(repo_url, clone_dir):
        return

    # Find Python files in the cloned repository
    all_files = find_python_files(clone_dir)


    if not all_files:
        print("No Python files found in the repository.")
        return

    # Analyze refactoring frequency for each file
    for file_path in all_files:
        print("*****************************************************************************************************")
        print(f"Selected file for analysis: {file_path}")
        print("*****************************************************************************************************")
        
        if '.py' in file_path:
            # Check for python code smells
            issues = check_python_code_smells(file_path)
            if issues == -1:
                return

            # Provide Python refactoring recommendations
            provide_python_recommendations(issues)

        # Check refactoring frequency
        file_path_in_repo = os.path.relpath(file_path, clone_dir)
        refactor_ratio = check_refactoring_frequency(clone_dir, file_path_in_repo, num_commits)

        if refactor_ratio is None:
            print("Not enough data for refactoring frequency analysis.\n")
            continue
        elif refactor_ratio == -1:
            print("Not enough commits to analyze refactoring frequency.\n")
            continue

        # Provide insights based on refactoring frequency for the current file
        if refactor_ratio is None:
            print("\nNot enough data for refactoring frequency analysis.\n")
        elif refactor_ratio == 0:
            print("\nNo significant refactoring activity detected in the specified commits.\n")
        elif refactor_ratio < 0.1:
            print("\nThe observed refactoring time ratios suggest low refactoring activity.\n")
            print("Recommendation: Consider periodically reviewing and refactoring the codebase to maintain code quality and flexibility.\n")
        elif 0.1 <= refactor_ratio <= 0.5:
            print("\nThere has been moderate refactoring activity observed recently.\n")
            print("Recommendation: Ensure that refactoring efforts are targeted and aligned with improving maintainability and reducing technical debt.\n")
        elif refactor_ratio > 0.5:
            print("\nThere has been significant refactoring activity recently.\n")
            print("Recommendation: Evaluate the impact of frequent changes and consider strategies to stabilize the codebase to avoid introducing unintended issues.\n")
        else:
            print("\nUnexpected value for refactor_ratio. Please review the analysis.\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python check_refactoring.py <repository_url> <number_of_commits>")
    else:
        repo_url = sys.argv[1]
        num_commits = int(sys.argv[2])
        main(repo_url, num_commits)
