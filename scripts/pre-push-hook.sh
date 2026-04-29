#!/usr/bin/env bash
# Pre-push hook: verify CHANGELOG.md has an entry for the current version.
# Install: cp scripts/pre-push-hook.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push

set -euo pipefail

# Detect project type and extract version
if [ -f package.json ]; then
  VERSION=$(node -e "console.log(require('./package.json').version)" 2>/dev/null) || exit 0
elif [ -f pyproject.toml ]; then
  VERSION=$(grep -m1 '^version' pyproject.toml | sed 's/.*"\(.*\)".*/\1/') || exit 0
else
  exit 0
fi

if [ -z "$VERSION" ]; then
  exit 0
fi

# Check CHANGELOG.md has an entry for this version
if [ ! -f CHANGELOG.md ]; then
  echo "Warning: CHANGELOG.md not found."
  exit 0
fi

if ! grep -q "^## $VERSION" CHANGELOG.md; then
  echo "Error: CHANGELOG.md has no entry for version $VERSION."
  echo "Add a '## $VERSION' section before pushing."
  exit 1
fi
