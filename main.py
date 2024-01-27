import subprocess
import shlex
import os

# Initialize variables
current_chunk = []
current_chunk_size = 0
chunk_size_limit = 2 * 1024 * 1024 * 1024  # 2 GB in bytes
chunk_counter = 1

# Assuming 'files' is a list of file paths, you need to get their sizes
# Replace 'your_directory_path' with the path to the directory you want to process
files = [(f, os.path.getsize(f)) for f in os.listdir('your_directory_path') if os.path.isfile(f)]

# Check whether the file is ignored
def is_ignored(filepath):
    try:
        subprocess.check_output(f"git check-ignore {shlex.quote(filepath)}", shell=True)
        return True
    except subprocess.CalledProcessError:
        return False

# Loop through each file in our list
for filepath, filesize in files:
    # If adding file doesn't cause the chunk to exceed the size limit
    if current_chunk_size + filesize <= chunk_size_limit:
        current_chunk.append(filepath)
        current_chunk_size += filesize
    else:
        # If chunk size exceeds, commit the current chunk
        print(f"Chunk {chunk_counter} size {current_chunk_size / (1024 * 1024 * 1024)} GB")

        for f in current_chunk:
            if not is_ignored(f):
                subprocess.check_call(f"git add {shlex.quote(f)}", shell=True)

        # Commit the chunk
        commit_message = f"Chunk {chunk_counter}"
        subprocess.check_call(["git", "commit", "-m", commit_message])

        # Reset the chunk
        current_chunk = [filepath]
        current_chunk_size = filesize
        chunk_counter += 1

# Commit the last chunk if there are any files left
if current_chunk:
    print(f"Chunk {chunk_counter} size {current_chunk_size / (1024 * 1024 * 1024)} GB")
    for f in current_chunk:
        if not is_ignored(f):
            subprocess.check_call(f"git add {shlex.quote(f)}", shell=True)

    commit_message = f"Chunk {chunk_counter}"
    subprocess.check_call(["git", "commit", "-m", commit_message])
