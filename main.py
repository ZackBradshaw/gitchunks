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

# Function to commit and push the current chunk
def commit_and_push_chunk(chunk, message):
    for f in chunk:
        if not is_ignored(f):
            subprocess.check_call(f"git add {shlex.quote(f)}", shell=True)
    
    # Check if there are changes staged for commit
    staged_changes = subprocess.check_output(["git", "diff", "--cached"])
    if staged_changes:
        # Commit if there are staged changes
        subprocess.check_call(["git", "commit", "-m", message])
        # Push the commit
        subprocess.check_call(["git", "push"])
    else:
        print("No changes to commit for this chunk.")

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
        commit_and_push_chunk(current_chunk, commit_message)

        # Reset the chunk
        current_chunk = [filepath]
        current_chunk_size = filesize
        chunk_counter += 1

# Commit and push the last chunk if there are any files left
if current_chunk:
    commit_message = f"Chunk {chunk_counter}"
    commit_and_push_chunk(current_chunk, commit_message)
