#!/usr/bin/env bash
set -euo pipefail

cd /workspace

# One run at a time: a second start (cron plus a manual run) exits instead of racing on state.
exec 9>/data/state/.pipeline.lock
if ! flock -n 9; then
  echo "Another pipeline run is in progress; exiting."
  exit 0
fi

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
  python scripts/notify_ntfy.py --previous "$previous_state" --candidate "$candidate_state" || true
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

# Summary for ntfy, taken before the candidate state replaces the previous one.
results_args=()
if [ -f build-results.json ]; then results_args=(--results build-results.json); fi
download_args=()
if [ -f download-results.json ]; then download_args=(--download-results download-results.json); fi
python scripts/notify_ntfy.py --previous "$previous_state" --candidate "$candidate_state" "${results_args[@]}" "${download_args[@]}" || true

# Publish only the APKs patched in this run (apks/patched keeps older builds): each app
# gets its own release, titled "<App> <version>" so Obtainium can read a real version.
# (Capture the dry run instead of piping it into "grep -q": with pipefail, grep closing the
# pipe early makes python fail with a broken pipe and the publish step was skipped silently.)
to_publish=""
if [ -f build-results.json ]; then
  to_publish=$(python scripts/publish_releases.py --results build-results.json --dry-run)
fi
if [ -n "$to_publish" ]; then
  cp "$candidate_state" patch-state.json
  python scripts/publish_releases.py --results build-results.json --state patch-state.json
  cp "$candidate_state" "$previous_state"
fi

exit "$build_status"
