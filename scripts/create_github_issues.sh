#!/usr/bin/env bash
set -euo pipefail

# Create GitHub issues from docs/issues/*.md using the GitHub CLI.
#
# Requirements:
# - gh installed
# - gh auth login already done
# - run from the repository root
#
# Usage:
#   chmod +x scripts/create_github_issues.sh
#   ./scripts/create_github_issues.sh
#
# Optional:
#   LABELS="codex-ready,backend" ./scripts/create_github_issues.sh

LABELS="${LABELS:-codex-ready}"

for file in docs/issues/*.md; do
  title="$(head -n 1 "$file" | sed 's/^# //')"
  echo "Creating issue: $title"
  gh issue create \
    --title "$title" \
    --body-file "$file" \
    --label "$LABELS"
done
