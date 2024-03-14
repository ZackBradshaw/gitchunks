import subprocess
import shlex
import os
import sys
import dotenv
from dotenv import load_dotenv

load_dotenv()

# Initialize variables
current_chunk = []
current_chunk_size = 0
chunk_size_limit = 2 * 1024 * 1024 * 1024  # 2 GB in bytes
chunk_counter = 1
directory_path = os.path.expanduser(os.getenv("PROJECT_PATH"))
# TODO remove before commit
directory_path = r"C:\Users\zack-\OneDrive - zackbradshaw\UnrealProjects\RiseOfAgora\"
# directory_path = os.path.expanduser(os.getenv("PROJECT_PATH"))
remote_name = "origin"
branch_name = "main"

# Change to the Git repository directory
os.chdir(directory_path)

# Function to check if the branch exists on the remote
def branch_exists_on_remote(branch_name):
    try:
        subprocess.check_output(["git", "ls-remote", "--heads", remote_name, branch_name])
        return True
    except subprocess.CalledProcessError:
        return False

# Determine if this is the first push by checking if the branch exists on the remote
first_push = not branch_exists_on_remote(branch_name)

# Function to print an ASCII progress bar
def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')

# Function to commit and push the current chunk
def commit_and_push_chunk(chunk, message, first_push):
    global chunk_counter
    if not chunk:  # If the chunk is empty, skip
        print("No files to commit. Skipping...")
        return

    print(f"\nCommitting chunk {chunk_counter} with {len(chunk)} files...")
    for i, f in enumerate(chunk):
        # Get the relative path of the file from the Git repository root
        relative_path = os.path.relpath(f, start=directory_path)

        # Check if the file is ignored
        try:
            subprocess.check_output(["git", "check-ignore", relative_path])
            print(f"Skipping ignored file: {f}")
            continue  # Skip this file
        except subprocess.CalledProcessError:
            # File is not ignored, proceed to add
            pass

        subprocess.check_call(f"git add {shlex.quote(relative_path)}", shell=True)
        print_progress_bar(i + 1, len(chunk), prefix='Staging Progress:', suffix='Complete', length=50)

    # Check if there are any changes to commit
    try:
        subprocess.check_output(["git", "diff", "--cached", "--exit-code"])
        print("No changes to commit. Skipping...")
        return  # Exit the function if there are no changes
    except subprocess.CalledProcessError:
        # There are changes to commit
        pass

    # Commit the changes
    subprocess.check_call(["git", "commit", "-m", message])
    print(f"Chunk {chunk_counter} committed.")
    
    # Push the commit
    if first_push:
        subprocess.check_call(["git", "push", "--set-upstream", remote_name, branch_name])
        first_push = False  # Ensure subsequent pushes don't try to set the upstream again
    else:
        subprocess.check_call(["git", "push"])
    print(f"Chunk {chunk_counter} pushed to remote.")
    chunk_counter += 1
    
all_paths = []
for root, dirs, files_in_dir in os.walk(directory_path):
    for name in dirs + files_in_dir:
        all_paths.append(os.path.join(root, name))

# Use git check-ignore to filter out ignored paths
try:
    ignored_paths = subprocess.check_output(["git", "check-ignore"] + all_paths).decode().splitlines()
except subprocess.CalledProcessError:
    ignored_paths = []

# Filter out ignored paths
files = [(path, os.path.getsize(path)) for path in all_paths if path not in ignored_paths and os.path.isfile(path)]

# Loop through each file in our list
for filepath, filesize in files:
    if filesize > chunk_size_limit:
        print(f"File {filepath} is too large to handle in a single chunk.")
        continue

    # If adding file doesn't cause the chunk to exceed the size limit
    if current_chunk_size + filesize <= chunk_size_limit:
        current_chunk.append(filepath)
        current_chunk_size += filesize
    else:
        # Commit and push the current chunk
        commit_message = f"Chunk {chunk_counter}"
        commit_and_push_chunk(current_chunk, commit_message, first_push)
        if first_push:  # Update the first_push flag after the first push
            first_push = False

        # Reset the chunk
        current_chunk = [filepath]
        current_chunk_size = filesize

# Commit and push the last chunk if there are any files left
if current_chunk:
    commit_message = f"Chunk {chunk_counter}"
    commit_and_push_chunk(current_chunk, commit_message, first_push)

