#!/bin/bash

# Define the maximum file size limit in MB for GitHub
max_file_size_limit=100

# Function to find files larger than the specified size limit
find_large_files() {
    local max_size_mb=$1
    find .git/objects -type f -size +${max_size_mb}M
}

# Install git filter-repo if not already installed
if ! command -v git filter-repo &> /dev/null; then
    echo "git filter-repo is not installed. Installing..."
    pip install git-filter-repo
fi

# Find files larger than the GitHub limit
large_files=$(find_large_files $max_file_size_limit)

# Remove files from Git history using git filter-repo
for file in $large_files; do
    echo "Removing file $file from Git history..."
    git filter-repo --path "$file" --invert-paths
done

# Optionally, force push changes to remote repository
git push --force origin main

