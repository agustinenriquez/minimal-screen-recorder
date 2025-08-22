#!/bin/bash

# Setup pre-commit hooks for minimal-screen-recorder
# This script installs and configures pre-commit hooks

set -e

echo "Setting up pre-commit hooks..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository. Please run this script from the project root."
    exit 1
fi

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
else
    echo "pre-commit is already installed"
fi

# Install the git hook scripts
echo "Installing pre-commit hooks..."
pre-commit install

# Optionally run pre-commit on all files to check setup
echo "Running pre-commit on all files to verify setup..."
pre-commit run --all-files || {
    echo ""
    echo "Some pre-commit checks failed. This is normal for the first run."
    echo "The hooks will automatically fix many issues on the next commit."
    echo "You may need to manually fix some issues and commit again."
}

echo ""
echo "Pre-commit setup complete!"
echo ""
echo "The following hooks are now active:"
echo "- black (code formatting)"
echo "- isort (import sorting)"
echo "- flake8 (linting)"
echo "- bandit (security checks)"
echo "- mypy (type checking)"
echo "- General file checks (trailing whitespace, file endings, etc.)"
echo ""
echo "These will run automatically on every commit."
echo "To run manually: pre-commit run --all-files"
