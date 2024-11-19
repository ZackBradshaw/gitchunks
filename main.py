import subprocess
import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv()

# Initialize variables
current_chunk = []
current_chunk_size = 0
chunk_size_limit = 2 * 1024 * 1024 * 1024  # 2GB
chunk_counter = 1
file_size_limit = 100 * 1024 * 1024  # 100MB
script_directory = os.path.dirname(os.path.abspath(__file__))
remote_name = "origin"
branch_name = "main"

# Get Hugging Face token
huggingface_token = os.getenv("HF_TOKEN")
if not huggingface_token:
    print("Error: HF_TOKEN environment variable is not set.")
    sys.exit(1)

# Get project path
project_path = os.getenv('PROJECT_PATH')
if not project_path:
    print("Error: PROJECT_PATH not set in .env file")
    sys.exit(1)

# Ensure the path exists
if not os.path.exists(project_path):
    print(f"Error: The specified PROJECT_PATH does not exist: {project_path}")
    sys.exit(1)

# Change to the project directory
os.chdir(project_path)

def print_git_status():
    try:
        status = subprocess.check_output(["git", "status"], text=True)
        print("Git Status:")
        print(status)
    except subprocess.CalledProcessError as e:
        print(f"Error getting Git status: {e}")
    print("Current Directory:")
    print(os.getcwd())

print_git_status()

def set_git_credentials():
    try:
        subprocess.check_call(["git", "config", "--global", "user.email", "your_email@example.com"])
        subprocess.check_call(["git", "config", "credential.username", "ZackBradshaw"])
        print("Git credentials set successfully.")
    except subprocess.CalledProcessError:
        print("Error setting Git credentials.")
        sys.exit(1)

def branch_exists_on_remote(branch_name):
    try:
        subprocess.check_output(["git", "ls-remote", "--exit-code", remote_name, branch_name])
        return True
    except subprocess.CalledProcessError:
        return False

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if iteration == total:
        print()

def is_in_submodule(path):
    try:
        relative_path = os.path.relpath(path, project_path)
        output = subprocess.check_output(["git", "submodule", "status", relative_path])
        return len(output) > 0
    except subprocess.CalledProcessError:
        return False

def commit_and_push_chunk(chunk, message, first_push):
    global chunk_counter
    if not chunk:
        print("No files to commit. Skipping chunk.")
        return first_push

    print(f"\nCommitting chunk {chunk_counter}...")
    for i, f in enumerate(chunk):
        relative_path = os.path.relpath(f, project_path)
        if is_in_submodule(f):
            print(f"Skipping file {relative_path} in submodule.")
            continue
        try:
            subprocess.check_call(["git", "add", relative_path])
        except subprocess.CalledProcessError:
            print(f"Error adding file {relative_path}.")
            continue
        print_progress_bar(i + 1, len(chunk), prefix=f'Progress:', suffix=f'Complete ({i+1}/{len(chunk)})')

    try:
        subprocess.check_output(["git", "diff", "--quiet", "--exit-code"])
        print("No changes to commit. Skipping commit and push.")
        return first_push
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.check_call(["git", "commit", "-m", message])
        print(f"Chunk {chunk_counter} committed.")
        if first_push:
            print("First push, setting upstream branch.")
            subprocess.check_call(["git", "push", "--set-upstream", remote_name, branch_name])
            first_push = False
        else:
            print("Pushing with --force.")
            subprocess.check_call(["git", "push", "--force", remote_name, branch_name])
        print(f"Chunk {chunk_counter} pushed successfully.")
        chunk_counter += 1
    except subprocess.CalledProcessError as e:
        print(f"Error during commit or push: {e}")
    return first_push

def get_ignored_paths(paths, batch_size=10):
    ignored_paths = []
    for i in range(0, len(paths), batch_size):
        batch = paths[i:i + batch_size]
        try:
            ignored_paths += subprocess.check_output(["git", "check-ignore"] + batch, text=True).splitlines()
        except subprocess.CalledProcessError:
            pass
    return ignored_paths

def setup_git_lfs():
    try:
        subprocess.check_call(["git", "lfs", "install"])
        print("Git LFS installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing Git LFS: {e}")

def authenticate_with_huggingface():
    print("Authenticating with Hugging Face...")
    try:
        subprocess.check_call(["huggingface-cli", "login", "--token", huggingface_token])
        print("Authentication successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error authenticating with Hugging Face: {e}")
        sys.exit(1)

def push_small_commits():
    try:
        small_commits = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], text=True).strip()
        if int(small_commits) > 1000:  # Arbitrary threshold for small commits
            print(f"Too many small commits ({small_commits}). Pushing one by one.")
            commits = subprocess.check_output(["git", "rev-list", "--reverse", "--no-merges", "HEAD"], text=True).splitlines()
            for commit in commits:
                subprocess.check_call(["git", "push", remote_name, f"{commit}:refs/heads/{branch_name}"])
            return True
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error checking or pushing small commits: {e}")
        sys.exit(1)

# Main script execution starts here
authenticate_with_huggingface()
setup_git_lfs()
set_git_credentials()

# Check if the branch exists on remote
first_push = not branch_exists_on_remote(branch_name)

print("Starting file processing...")

all_paths = []
for root, dirs, files_in_dir in os.walk(project_path):
    if '.git' in root.split(os.path.sep):
        continue
    for name in dirs + files_in_dir:
        all_paths.append(os.path.join(root, name))

# Filter only valid, tracked paths
tracked_paths = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
tracked_files = set(tracked_paths)
files = [path for path in all_paths if os.path.relpath(path, project_path) in tracked_files]

# Remove ignored paths
ignored_paths = get_ignored_paths(files)
filtered_files = [file for file in files if file not in ignored_paths]

# Commit and push in chunks
if filtered_files:
    chunk_size = 0
    chunk = []
    for i, file in enumerate(filtered_files):
        file_size = os.path.getsize(file)
        if chunk_size + file_size > file_size_limit:
            first_push = commit_and_push_chunk(chunk, f"Chunk {chunk_counter} commit", first_push)
            chunk = []
            chunk_size = 0
        chunk.append(file)
        chunk_size += file_size
        print_progress_bar(i + 1, len(filtered_files), prefix='Overall Progress:', suffix='Complete')

    if chunk:
        commit_and_push_chunk(chunk, f"Final chunk commit", first_push)
else:
    print("No files to process.")

print("File processing completed.")

# Push small commits if necessary
if push_small_commits():
    print("Small commits pushed successfully.")

print("All operations completed successfully.")



