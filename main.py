import subprocess
import os
import sys
from dotenv import load_dotenv, find_dotenv

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
huggingface_token = os.getenv("HF_TOKEN")

if not find_dotenv():
    print("Warning: .env file does not exist or is ignored.")
load_dotenv()

# Ensure HF_TOKEN is set
if not huggingface_token:
    print("Error: HF_TOKEN environment variable is not set.")
    sys.exit(1)

# Set Hugging Face credentials for Git
def set_git_credentials():
    try:
        subprocess.check_call(["git", "config", "--global", "user.email", "your_email@example.com"])
        subprocess.check_call(["git", "config", "--global", "user.name", "Your Name"])
        subprocess.check_call(["git", "config", "credential.username", "ZackBradshaw"])
    except subprocess.CalledProcessError:
        print("Error setting Git credentials.")
        sys.exit(1)

# Function to check if branch exists on remote
def branch_exists_on_remote(branch_name):
    try:
        subprocess.check_output(["git", "ls-remote", "--exit-code", "origin", branch_name])
        return True
    except subprocess.CalledProcessError:
        return False

# Function to print a progress bar
def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', print_end='\r'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if iteration == total:
        print()

# Function to check if a path is in a Git submodule
def is_in_submodule(path):
    try:
        relative_path = os.path.relpath(path, script_directory)
        output = subprocess.check_output(["git", "submodule", "status", relative_path])
        return len(output) > 0
    except subprocess.CalledProcessError:
        return False

# Function to commit and push a chunk of files
def commit_and_push_chunk(chunk, message, first_push):
    global chunk_counter
    if not chunk:
        print("No files to commit. Skipping chunk.")
        return first_push

    print(f"\nCommitting chunk {chunk_counter}...")
    for i, f in enumerate(chunk):
        relative_path = os.path.relpath(f, script_directory)
        if is_in_submodule(f):
            print(f"Skipping file {relative_path} in submodule.")
            continue
        try:
            subprocess.check_call(["git", "add", relative_path])
        except subprocess.CalledProcessError:
            print(f"Error adding file {relative_path}.")
            continue
        print_progress_bar(i + 1, len(chunk), prefix=f'Progress:', suffix=f'Complete ({i+1}/{len(chunk)})', length=50)
    
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

# Function to get ignored paths
def get_ignored_paths(paths, batch_size=10):
    ignored_paths = []
    for i in range(0, len(paths), batch_size):
        batch = paths[i:i + batch_size]
        try:
            ignored_paths += subprocess.check_output(["git", "check-ignore"] + batch, text=True).splitlines()
        except subprocess.CalledProcessError:
            pass
    return ignored_paths

# Function to setup Git LFS
def setup_git_lfs():
    try:
        subprocess.check_call(["git", "lfs", "install"])
        print("Git LFS installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing Git LFS: {e}")

# Function to authenticate with Hugging Face CLI
def authenticate_with_huggingface():
    print("Authenticating with Hugging Face...")
    try:
        subprocess.check_call(["huggingface-cli", "login", "--token", huggingface_token])
        print("Authentication successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error authenticating with Hugging Face: {e}")
        sys.exit(1)

# Function to test push with a small file
def test_push():
    test_filename = "test_push_file.txt"
    with open(os.path.join(script_directory, test_filename), "w") as f:
        f.write("This is a test file to verify push.")

    try:
        subprocess.check_call(["git", "add", test_filename])
        subprocess.check_call(["git", "commit", "-m", "Test commit for verifying push"])
        if first_push:
            subprocess.check_call(["git", "push", "--set-upstream", remote_name, branch_name])
        else:
            subprocess.check_call(["git", "push"])
        print("Test file pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during test push: {e}")
        sys.exit(1)
    finally:
        # Clean up the test file from the repository
        subprocess.check_call(["git", "rm", test_filename])
        subprocess.check_call(["git", "commit", "-m", "Remove test push file"])
        subprocess.check_call(["git", "push"])

# Function to push small commits one by one if too many small commits
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

# Authenticate with Hugging Face CLI
# authenticate_with_huggingface()

# Setup Git LFS
# setup_git_lfs()

# Set Git user credentials (optional but recommended)
set_git_credentials()

# Check if the branch exists on remote
first_push = not branch_exists_on_remote(branch_name)

# Test push with a small file
test_push()

print("Test push completed successfully.")

# Continue with staging and committing the remaining files in chunks
all_paths = []
for root, dirs, files_in_dir in os.walk(script_directory):
    if '.git' in root.split(os.path.sep):
        continue
    for name in dirs + files_in_dir:
        all_paths.append(os.path.join(root, name))

ignored_paths = get_ignored_paths(all_paths)

files = []
for path in all_paths:
    if path in ignored_paths or not os.path.exists(path):
        print(f"Warning: File {path} does not exist or is ignored.")
        continue
    if is_in_submodule(path):
        print(f"Skipping file {path} in submodule.")
        continue
    file_size = os.path.getsize(path)
    if file_size <= chunk_size_limit:
        files.append((path, file_size))
    else:
        print(f"File {path} is too large to handle in chunks. Skipping.")

for filepath, filesize in files:
    if filesize > file_size_limit:
        try:
            subprocess.check_call(["git", "lfs", "track", filepath])
            subprocess.check_call(["git", "add", ".gitattributes"])
        except subprocess.CalledProcessError as e:
            print(f"Error tracking large file {filepath} with Git LFS: {e}")

    if current_chunk_size + filesize <= chunk_size_limit:
        current_chunk.append(filepath)
        current_chunk_size += filesize
    else:
        commit_message = f"Chunk {chunk_counter}"
        first_push = commit_and_push_chunk(current_chunk, commit_message, first_push)
        current_chunk = [filepath]
        current_chunk_size = filesize

if current_chunk:
    commit_message = f"Chunk {chunk_counter}"
    commit_and_push_chunk(current_chunk, commit_message, first_push)

print("All chunks committed and pushed.")