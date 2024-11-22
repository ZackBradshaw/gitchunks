import zipfile
import tempfile
import shutil
import subprocess
import shlex
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Initialize variables
current_chunk = []
current_chunk_size = 0
# chunk_size_limit = 1 * 1024 * 1024 * 1024  # 1 GB in bytes
chunk_size_limit = 500 * 1024 * 1024 # 500 MB in bytes
chunk_counter = 1
file_size_limit = 100 * 1024 * 1024  # 100 MB in bytes for GitHub
remote_name = "origin"
branch_name = "main"
huggingface_token = os.getenv("HF_TOKEN")

# Get the project path from the environment variable
directory_path = os.getenv('PROJECT_PATH')
if not directory_path:
    print("Error: PROJECT_PATH not set in .env file")
    sys.exit(1)

# Ensure the path exists
if not os.path.exists(directory_path):
    print(f"Error: The specified PROJECT_PATH does not exist: {directory_path}")
    sys.exit(1)

# Change to the project directory
os.chdir(directory_path)
print(f"Changed working directory to: {os.getcwd()}")

# Set Hugging Face credentials for Git
subprocess.check_call(["git", "config", "--global", "credential.helper", "store"])

def clean_repository_history():
    try:
        subprocess.check_call(["git", "filter-branch", "--force", "--index-filter",
                               "git rm --cached --ignore-unmatch PATH_TO_LARGE_FILE", "--prune-empty", "--tag-name-filter", "cat", "--", "--all"])
        print("Repository history cleaned.")
    except subprocess.CalledProcessError as e:
        print(f"Error cleaning repository history: {e}")

    clean_repository_history()

def add_ssh_key():
    try:
        subprocess.check_call(["ssh-add", "~/.ssh/id_vied25519.pub"])
        print("SSH key added to the agent.")
    except subprocess.CalledProcessError as e:
        print(f"Error adding SSH key to the agent: {e}")
        sys.exit(1)
# add_ssh_key()

def get_ignored_paths(paths, batch_size=1000):
    ignored_paths = []
    for i in range(0, len(paths), batch_size):
        batch = paths[i:i + batch_size]
        try:
            ignored_paths += subprocess.check_output(["git", "check-ignore"] + batch).decode().splitlines()
        except subprocess.CalledProcessError:
            pass
    return ignored_paths

def setup_git_lfs():
    try:
        subprocess.check_call(["git", "lfs", "install"])
        print("Git LFS installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing Git LFS: {e}")

def track_large_files():
    try:
        subprocess.check_call(["git", "lfs", "track", "*.large_extension"])
        subprocess.check_call(["git", "add", ".gitattributes"])
        print("Large files are being tracked with Git LFS.")
    except subprocess.CalledProcessError as e:
        print(f"Error tracking large files with Git LFS: {e}")

def authenticate_with_huggingface():
    print("Authenticating with Hugging Face CLI.")
    try:
        subprocess.check_call(["huggingface-cli", "login", "--token", huggingface_token])
        print("Authentication successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error authenticating with Hugging Face: {e}")
        sys.exit(1)

def branch_exists_on_remote(branch_name):
    try:
        subprocess.check_output(["git", "ls-remote", "--heads", remote_name, branch_name])
        return True
    except subprocess.CalledProcessError:
        return False

first_push = not branch_exists_on_remote(branch_name)

def test_push():
    test_filename = "test_push_file.txt"
    with open(os.path.join(directory_path, test_filename), "w") as f:
        f.write("This is a test file to verify push.")

    try:
        subprocess.check_call(["git", "add", os.path.join(directory_path, test_filename)])
        subprocess.check_call(["git", "commit", "-m", "Test commit for verifying push"])
        if first_push:
            subprocess.check_call(["git", "push", "--set-upstream", remote_name, branch_name, "-f"])
        # else:
            # subprocess.check_call(["git", "push"])
        print("Test file pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during test push: {e}")
        sys.exit(1)
    finally:
        # Clean up the test file from the repo
        subprocess.check_call(["git", "rm", os.path.join(directory_path, test_filename)])
        subprocess.check_call(["git", "commit", "-m", "Remove test push file"])
        subprocess.check_call(["git", "push", "--set-upstream", remote_name, branch_name, "-f"])
        # subprocess.check_call(["git", "push"])

setup_git_lfs()
# update_remote_url_to_ssh()
first_push = not branch_exists_on_remote(branch_name)
# test_push()
# print("Test push completed successfully.")

# Continue with staging and committing the actual files
all_paths = []
for root, dirs, files_in_dir in os.walk(directory_path):
    if '.git' in root.split(os.path.sep):
        continue
    for name in dirs + files_in_dir:
        all_paths.append(os.path.join(root, name))

ignored_paths = get_ignored_paths(all_paths)

def update_remote_url_to_ssh():
    try:
        ssh_url = subprocess.check_output(["git", "-C", directory_path, "remote", "get-url", "--push", remote_name]).decode().strip()
        if not ssh_url.startswith("git@"):
            ssh_url = f"git@github.com:{ssh_url.split('github.com/')[-1]}"
            subprocess.check_call(["git", "-C", directory_path, "remote", "set-url", remote_name, ssh_url])
            print(f"Updated remote URL to use SSH: {ssh_url}")
    except subprocess.CalledProcessError as e:
        print(f"Error updating remote URL to SSH: {e}")
        sys.exit(1)

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {suffix}')
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')

def is_in_submodule(path):
    try:
        relative_path = os.path.relpath(path, start=directory_path)
        output = subprocess.check_output(["git", "submodule", "status", relative_path], stderr=subprocess.DEVNULL)
        return len(output) > 0
    except subprocess.CalledProcessError:
        return False

def compress_item(path):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            if os.path.isfile(path):
                zip_file.write(path, os.path.basename(path))
            else:
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(path))
                        zip_file.write(file_path, arcname)
    return temp_file.name

def commit_and_push_chunk(chunk, message, first_push):
    global chunk_counter
    if not chunk:
        print("No files to commit. Skipping...")
        return first_push

    print(f"\nCommitting chunk {chunk_counter} with {len(chunk)} files...")
    for i, f in enumerate(chunk):
        relative_path = os.path.relpath(f, start=directory_path)
        if is_in_submodule(f):
            print(f"Skipping file in submodule: {relative_path}")
            continue
        try:
            subprocess.check_call(["git", "-C",  directory_path, "add", relative_path])
        except subprocess.CalledProcessError as e:
            print(f"Error adding file {relative_path}: {e}")
            continue
        print_progress_bar(i + 1, len(chunk), prefix='Staging Progress:', suffix='Complete', length=50)

    try:
        subprocess.check_output(["git", "-C", directory_path, "diff", "--cached", "--exit-code"])
        print("No changes to commit. Skipping...")
        return first_push
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.check_call(["git", "-C", directory_path, "commit", "-m", message])
        print(f"Chunk {chunk_counter} committed.")
        
        if first_push:
            print("First push, setting upstream branch.")
            subprocess.check_call(["git", "-C", directory_path, "push", "--set-upstream", remote_name, branch_name])
            first_push = False
        else:
            print("Pushing with --force.")
            subprocess.check_call(["git", "-C", directory_path, "push", "--force"])
        print(f"Chunk {chunk_counter} pushed to remote.")
        chunk_counter += 1
    except subprocess.CalledProcessError as e:
        print(f"Error during commit or push: {e}")
    return first_push

files = []
for root, dirs, files_in_dir in os.walk(directory_path):
    if '.git' in root.split(os.path.sep):
        continue
    for name in files_in_dir:
        path = os.path.join(root, name)
        if path not in ignored_paths and not is_in_submodule(path):
            file_size = os.path.getsize(path)
            if file_size <= chunk_size_limit:
                files.append((path, file_size))
            else:
                print(f"File {path} is too large to handle in a single chunk and will be skipped.")

compressed_items = []
for filepath, filesize in files:
    if filesize > file_size_limit:
        print(f"\nCompressing {filepath}...")
        compressed_path = compress_item(filepath)
        compressed_size = os.path.getsize(compressed_path)
        
        if compressed_size <= file_size_limit:
            print(f"Compressed size: {compressed_size / (1024 * 1024):.2f} MB")
            compressed_items.append((compressed_path, filepath))
            os.remove(filepath)  # Remove the original file or folder
            filepath = compressed_path
            filesize = compressed_size
        else:
            print(f"Compressed size still exceeds limit: {compressed_size / (1024 * 1024):.2f} MB")
            os.unlink(compressed_path)
            subprocess.check_call(f"git lfs track {shlex.quote(filepath)}", shell=True)
            subprocess.check_call(f"git add .gitattributes", shell=True)
            continue

    if current_chunk_size + filesize <= chunk_size_limit:
        current_chunk.append(filepath)
        current_chunk_size += filesize
    else:
        print(f"\nCommitting chunk {chunk_counter} due to size limit reached. Current chunk size: {current_chunk_size}, adding file size: {filesize}")
        commit_message = f"Chunk {chunk_counter}"
        first_push = commit_and_push_chunk(current_chunk, commit_message, first_push)
        current_chunk = [filepath]
        current_chunk_size = filesize

def commit_and_push_chunk(chunk, message, first_push):
    global chunk_counter
    if not chunk:
        print("No files to commit. Skipping...")
        return first_push

    print(f"\nCommitting chunk {chunk_counter} with {len(chunk)} files...")
    for i, f in enumerate(chunk):
        relative_path = os.path.relpath(f, start=directory_path)
        if is_in_submodule(f):
            print(f"Skipping file in submodule: {relative_path}")
            continue
        try:
            subprocess.check_call(["git", "-C", directory_path, "add", relative_path])
        except subprocess.CalledProcessError as e:
            print(f"Error adding file {relative_path}: {e}")
            continue
        print_progress_bar(i + 1, len(chunk), prefix='Staging Progress:', suffix='Complete', length=50)

    try:
        subprocess.check_output(["git", "-C", directory_path, "diff", "--cached", "--exit-code"])
        print("No changes to commit. Skipping...")
        return first_push
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.check_call(["git", "-C", directory_path, "commit", "-m", message])
        print(f"Chunk {chunk_counter} committed.")
        
        if first_push:
            print("First push, setting upstream branch.")
            subprocess.check_call(["git", "-C", directory_path, "push", "--set-upstream", remote_name, branch_name])
            first_push = False
        else:
            print("Pushing with --force.")
            subprocess.check_call(["git", "-C", directory_path, "push"])
        print(f"Chunk {chunk_counter} pushed to remote.")
        chunk_counter += 1
    except subprocess.CalledProcessError as e:
        print(f"Error during commit or push: {e}")

    return first_push
files = []
for path in all_paths:
    if path in ignored_paths or os.path.isdir(path):
        continue
    if not os.path.exists(path):
        print(f"Warning: File {path} does not exist and will be skipped.")
        continue
    if is_in_submodule(path):
        print(f"Skipping file in submodule: {path}")
        continue
    file_size = os.path.getsize(path)
    if file_size <= chunk_size_limit:
        files.append((path, file_size))
    else:
        print(f"File {path} is too large to handle in a single chunk and will be skipped.")

for filepath, filesize in files:
    if filesize > file_size_limit:
        subprocess.check_call(f"git lfs track {shlex.quote(filepath)}", shell=True)
        subprocess.check_call(f"git add .gitattributes", shell=True)

    if current_chunk_size + filesize <= chunk_size_limit:
        current_chunk.append(filepath)
        current_chunk_size += filesize
    else:
        print(f"Committing chunk {chunk_counter} due to size limit reached. Current chunk size: {current_chunk_size}, adding file size: {filesize}")
        commit_message = f"Chunk {chunk_counter}"
        first_push = commit_and_push_chunk(current_chunk, commit_message, first_push)
        current_chunk = [filepath]
        current_chunk_size = filesize

if current_chunk:
    commit_message = f"Chunk {chunk_counter}"
    commit_and_push_chunk(current_chunk, commit_message, first_push)

print("All chunks committed and pushed.")

for compressed_path, _ in compressed_items:
    os.un