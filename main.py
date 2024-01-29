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

# Assuming 'files' is a list of file paths, you need to get their sizes
files = [
    (os.path.join(directory_path, f), os.path.getsize(os.path.join(directory_path, f)))
    for f in os.listdir(directory_path)
    if os.path.isfile(os.path.join(directory_path, f))
]

# Check whether the file is ignored
def is_ignored(filepath):
    try:
        subprocess.check_output(f"git check-ignore {shlex.quote(filepath)}", shell=True)
        return True
    except subprocess.CalledProcessError:
        return False

def commit_chunk(chunk, message):
    # Stage files for commit, skipping ignored files
    for f in chunk:
        if not is_ignored(f):
            subprocess.check_call(f"git add {shlex.quote(f)}", shell=True)
    
    # Check if there are changes staged for commit
    staged_changes = subprocess.check_output(["git", "diff", "--cached"])
    if staged_changes:
        # Commit if there are staged changes
        subprocess.check_call(["git", "commit", "-m", message])
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
        # Commit the current chunk
        commit_message = f"Chunk {chunk_counter}"
        commit_chunk(current_chunk, commit_message)

        # Reset the chunk
        current_chunk = [filepath]
        current_chunk_size = filesize
        chunk_counter += 1

# Commit the last chunk if there are any files left
if current_chunk:
    commit_message = f"Chunk {chunk_counter}"
    commit_chunk(current_chunk, commit_message)
