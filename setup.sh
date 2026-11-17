#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PY=python3; command -v python3 >/dev/null || PY=python
if ! command -v ffmpeg >/dev/null; then
  if command -v brew >/dev/null; then brew install ffmpeg
  elif command -v apt-get >/dev/null; then sudo apt-get update && sudo apt-get install -y ffmpeg
  else echo "Install ffmpeg with your package manager, then re-run."; exit 1; fi
fi
$PY -m pip install -q -U yt-dlp || $PY -m pip install -q -U --user yt-dlp
$PY scripts/ch.py doctor
