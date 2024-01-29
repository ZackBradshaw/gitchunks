import subprocess
import shlex
import os
import dotenv
from dotenv import load_dotenv

load_dotenv()

# Initialize variables
current_chunk = []
current_chunk_size = 0
chunk_size_limit = 2 * 1024 * 1024 * 1024  # 2 GB in bytes
chunk_counter = 1
directory_path = os.path.expanduser(os.getenv("PROJECT_PATH"))
remote_name = "origin"
branch_name = "chunked-upload"

# Change to the Git repository directory
os.chdir(directory_path)

# Get a list of all files in the directory and subdirectories, with their sizes
files = []
for root, dirs, files_in_dir in os.walk(directory_path):
    for f in files_in_dir:
        full_path = os.path.join(root, f)
        if os.path.isfile(full_path):
            files.append((full_path, os.path.getsize(full_path)))

# Check whether the file is ignored
def is_ignored(filepath):
    try:
        subprocess.check_output(f"git check-ignore {shlex.quote(filepath)}", shell=True)
        return True
    except subprocess.CalledProcessError:
        return False

# Function to print an ASCII progress bar
def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if iteration == total:
        print()

# Function to commit and push the current chunk
def commit_and_push_chunk(chunk, message, first_push=False):
    print(f"Committing chunk {chunk_counter} with {len(chunk)} files...")
    for i, f in enumerate(chunk):
        if not is_ignored(f):
            print(f"Staging {f}")
            subprocess.check_call(f"git add {shlex.quote(f)}", shell=True)
            print_progress_bar(i + 1, len(chunk), prefix='Progress:', suffix='Complete', length=50)
    
    # Check if there are changes staged for commit
    staged_changes = subprocess.check_output(["git", "diff", "--cached"])
    if staged_changes:
        # Commit if there are staged changes
        subprocess.check_call(["git", "commit", "-m", message])
        print(f"Chunk {chunk_counter} committed.")
        # Push the commit
        if first_push:
            subprocess.check_call(["git", "push", "--set-upstream", remote_name, branch_name])
        else:
            subprocess.check_call(["git", "push"])
        print(f"Chunk {chunk_counter} pushed to remote.")
    else:
        print("No changes to commit for this chunk.")

# Loop through each file in our list
for filepath, filesize in files:
    print(f"Processing {filepath} ({filesize / (1024**3):.2f} GB)")
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
        commit_and_push_chunk(current_chunk, commit_message, chunk_counter == 1)

        # Reset the chunk
        current_chunk = [filepath]
        current_chunk_size = filesize
        chunk_counter += 1

# Commit and push the last chunk if there are any files left
if current_chunk:
    commit_message = f"Chunk {chunk_counter}"
    commit_and_push_chunk(current_chunk, commit_message, chunk_counter == 1)
