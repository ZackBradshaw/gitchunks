![Banner Image](banner.jpg)

 Git Chunked Upload Script
 This script is designed to add and commit files to a Git repository in chunks of 2GB to avoid issues with large commits.

 ## How to Use
 1. Ensure Python 3 and Git are installed on your system.
 2. Place the script in the root directory of your Git repository.
 3. Modify the `PROJECT_PATH` in your environment variables to point to your repository.
 4. Run the script using `python3 main.py` in your terminal.
 5. The script will automatically stage, commit, and push files in 2GB chunks.
 6. Monitor the terminal for progress updates and any error messages.

 ## Prerequisites
 - Python 3.x
 - Git

 ## Setup
 - Set the `PROJECT_PATH` environment variable to the root of your Git repository.
   ```
   export PROJECT_PATH='/path/to/your/repository'
   ```
 - Ensure the `.env` file in the same directory as the script has the `PROJECT_PATH` variable set.

 ## Script Breakdown
 - The script walks through the directory tree, including subdirectories, and lists all files.
 - It checks if each file is ignored by Git's `.gitignore`.
 - Files are added to a staging area until the size limit of 2GB is reached.
 - Once the limit is reached or no more files are left, it commits the staged files.
 - After committing, it pushes the commit to the remote repository.
 - Progress bars and messages are displayed in the terminal to show the script's progress.

 ## Notes
 - The script assumes that the remote repository is named 'origin' and the branch is 'chunked-upload'.
 - If a file is larger than 2GB, it will be skipped with a warning message.
 - The script will set the upstream branch on the first push. Ensure you have the correct permissions.

 ## Contribution
 - Contributions to improve the script are welcome. Please fork the repository and submit a pull request.

 ## License
 - This script is released under the MIT License.
