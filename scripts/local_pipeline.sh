#!/usr/bin/env bash
set -euo pipefail

cd /workspace
git config --global --add safe.directory /workspace
git pull --ff-only origin main

state_dir=/data/state
previous_state="$state_dir/.patch-state.json"
candidate_state="$state_dir/.patch-state.candidate.json"
output_file=$(mktemp)
trap 'rm -f "$output_file"' EXIT

GITHUB_OUTPUT="$output_file" python scripts/check_patch_updates.py \
  --previous "$previous_state" \
  --state "$candidate_state" \
  ${FORCE_BUILD:+--force}

source "$output_file"
if [ "$should_build" != true ]; then
  echo "No patch-bundle updates found."
  exit 0
fi

# apks/original and apks/patched are permanent and never cleaned here.
rm -rf build-results.json download-results.json .patch-state.json patch-state.json release-notes.md
set +e
BUILD_DATE=$(date -u +%Y%m%d) \
SOURCES_TO_BUILD="$sources_to_build" \
BUILD_RESULTS_PATH=download-results.json \
python -m src download
download_status=$?
BUILD_DATE=$(date -u +%Y%m%d) \
SOURCES_TO_BUILD="$sources_to_build" \
BUILD_RESULTS_PATH=build-results.json \
python -m src patch
patch_status=$?
build_status=$((download_status || patch_status))
set -e

if [ -f build-results.json ]; then
  python scripts/finalize_patch_state.py \
    --previous "$previous_state" \
    --candidate "$candidate_state" \
    --results build-results.json
fi

# Publish only the APKs patched in this run (apks/patched keeps older builds): each app
# gets its own release, titled "<App> <version>" so Obtainium can read a real version.
if [ -f build-results.json ] && python scripts/publish_releases.py --results build-results.json --dry-run | grep -q .; then
  cp "$candidate_state" patch-state.json
  python scripts/publish_releases.py --results build-results.json --state patch-state.json
  cp "$candidate_state" "$previous_state"
fi

exit "$build_status"
