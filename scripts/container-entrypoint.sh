#!/usr/bin/env bash
set -euo pipefail

run_once() {
  bash /workspace/scripts/local_pipeline.sh || true
}

if [ "${1:-daemon}" = "once" ]; then
  exec bash /workspace/scripts/local_pipeline.sh
fi

run_once
while true; do
  now=$(date -u +%s)
  next=$(date -u -d 'tomorrow 06:00' +%s)
  today=$(date -u -d 'today 06:00' +%s)
  if [ "$now" -lt "$today" ]; then next=$today; fi
  sleep $((next - now))
  run_once
done
