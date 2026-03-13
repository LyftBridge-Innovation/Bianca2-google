#!/usr/bin/env bash
# Batch-enable all Google Workspace APIs needed by Bianca.
# Idempotent: safe to run multiple times.
#
# Usage:
#   ./scripts/enable_gws_apis.sh [PROJECT_ID]

set -euo pipefail

PROJECT="${1:-$(gcloud config get-value project 2>/dev/null)}"

if [ -z "$PROJECT" ]; then
  echo "ERROR: No project ID supplied and no active gcloud project found."
  echo "Usage: $0 <PROJECT_ID>"
  exit 1
fi

echo "Enabling Google Workspace APIs for project: $PROJECT"
echo ""

APIS=(
  # Core (already used by Gmail + Calendar skills)
  gmail.googleapis.com
  calendar-json.googleapis.com
  drive.googleapis.com
  # Expansion skills
  tasks.googleapis.com
  people.googleapis.com
  sheets.googleapis.com
  docs.googleapis.com
  slides.googleapis.com
  # Future skills
  chat.googleapis.com
  keep.googleapis.com
  forms.googleapis.com
  admin.googleapis.com
)

echo "APIs to enable:"
for api in "${APIS[@]}"; do
  echo "  - $api"
done
echo ""

gcloud services enable "${APIS[@]}" --project="$PROJECT"

echo ""
echo "All APIs enabled for project: $PROJECT"
