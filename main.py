import os
import subprocess

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output.decode('utf-8'), error.decode('utf-8')

def commit_and_push(message):
    # Stage all changes
    run_command("git add .")
    
    # Commit changes
    output, error = run_command(f'git commit -m "{message}"')
    if "nothing to commit" in output:
        print("No changes to commit.")
        return False
    
    # Push changes
    output, error = run_command("git push")
    if error:
        print(f"Error pushing changes: {error}")
        return False
    
    print("Changes committed and pushed successfully.")
    return True

# Get the current directory
current_dir = os.getcwd()

# Get list of files in the current directory
files = os.listdir(current_dir)

# Filter out hidden files and directories
files = [f for f in files if not f.startswith('.') and not f == 'main.py']

# Sort files alphabetically
files.sort()

# Calculate the number of chunks
chunk_size = 7
num_chunks = (len(files) + chunk_size - 1) // chunk_size

print(f"Current directory: {current_dir}")
print(f"Total files: {len(files)}")
print(f"Number of chunks: {num_chunks}")

# Commit and push each chunk
for i in range(num_chunks):
    start = i * chunk_size
    end = min((i + 1) * chunk_size, len(files))
    chunk = files[start:end]
    
    print(f"\nCommitting chunk {i+1}...")
    
    # Create commit message
    commit_message = f"Add files: {', '.join(chunk)}"
    
    # Commit and push the chunk
    if commit_and_push(commit_message):
        print(f"Chunk {i+1} committed and pushed successfully.")
    else:
        print(f"No changes in chunk {i+1} or error occurred.")

print("\nAll chunks committed and pushed.")

