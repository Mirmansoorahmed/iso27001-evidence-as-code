#!/bin/sh
# Verify this evidence pack. External commands: sha256sum and jq only.
# Run it from the pack directory: ./verify.sh
set -eu

if [ ! -f MANIFEST.json ] || [ ! -f MANIFEST.sha256 ]; then
  echo "run ./verify.sh from the pack directory" >&2
  exit 2
fi

jq -r '.files[] | "\(.sha256)  \(.path)"' MANIFEST.json | sha256sum -c -
sha256sum -c MANIFEST.sha256

prev=$(jq -r '.prev_manifest_sha256' MANIFEST.json)
if [ -n "$prev" ] && [ "$prev" != "null" ]; then
  if [ ! -f previous/MANIFEST.json ]; then
    echo "prev_manifest_sha256 is set but previous/MANIFEST.json is missing" >&2
    exit 1
  fi
  echo "$prev  previous/MANIFEST.json" | sha256sum -c -
fi

echo "manifest ok"
echo "prev_manifest_sha256=${prev}"
