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

# Publish only the APKs patched in this run; apks/patched keeps older builds.
mapfile -t apks < <(python - <<'PY'
import json, os
try:
    built = json.load(open("build-results.json"))["built"]
except (OSError, ValueError, KeyError):
    built = []
for path in built:
    if path.endswith(".apk") and os.path.isfile(path):
        print(path)
PY
)
if [ "${#apks[@]}" -gt 0 ]; then
  # GitHub strips a leading dot from asset names (".patch-state.json" becomes
  # "default.patch-state.json"), which breaks --clobber, so use a plain name.
  release_state=patch-state.json
  cp "$candidate_state" "$release_state"
  {
    printf 'Curated build generated on %s UTC.\n\n' "$(date -u +'%Y-%m-%d %H:%M')"
    for apk in "${apks[@]}"; do printf -- '- `%s`\n' "${apk##*/}"; done
  } > release-notes.md
  release_title="Latest build"

  if gh release view latest >/dev/null 2>&1; then
    gh release upload latest "${apks[@]}" "$release_state" --clobber
    # "gh release edit" needs gh >= 2.5 and the container's gh is older, so use the API.
    release_id=$(gh api "repos/{owner}/{repo}/releases/tags/latest" --jq .id)
    gh api -X PATCH "repos/{owner}/{repo}/releases/$release_id" \
      -f name="$release_title" -F body=@release-notes.md > /dev/null
  else
    gh release create latest "${apks[@]}" "$release_state" --title "$release_title" --notes-file release-notes.md
  fi
  # Keep only the newest build of each app on the release.
  python scripts/prune_release_assets.py --tag latest --built "${apks[@]##*/}" \
    || echo "WARNING: could not remove older builds from the release"
  cp "$candidate_state" "$previous_state"
fi

exit "$build_status"
