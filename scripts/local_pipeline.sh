#!/usr/bin/env bash
set -euo pipefail

cd /workspace
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

rm -rf dist build-results.json .patch-state.json release-notes.md
set +e
BUILD_DATE=$(date -u +%Y%m%d) \
SOURCES_TO_BUILD="$sources_to_build" \
BUILD_RESULTS_PATH=build-results.json \
python -m src
build_status=$?
set -e

if [ -f build-results.json ]; then
  python scripts/finalize_patch_state.py \
    --previous "$previous_state" \
    --candidate "$candidate_state" \
    --results build-results.json
fi

shopt -s nullglob
apks=(dist/*.apk)
if [ "${#apks[@]}" -gt 0 ]; then
  cp "$candidate_state" .patch-state.json
  {
    printf 'Curated build generated on %s UTC.\n\n' "$(date -u +'%Y-%m-%d %H:%M')"
    for apk in "${apks[@]}"; do printf -- '- `%s`\n' "${apk#dist/}"; done
  } > release-notes.md

  if gh release view latest >/dev/null 2>&1; then
    gh release upload latest "${apks[@]}" .patch-state.json --clobber
    gh release edit latest --title "Latest build" --notes-file release-notes.md
  else
    gh release create latest "${apks[@]}" .patch-state.json --title "Latest build" --notes-file release-notes.md --latest
  fi
  cp "$candidate_state" "$previous_state"
fi

exit "$build_status"
