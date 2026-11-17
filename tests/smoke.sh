#!/usr/bin/env bash
# Smoke test: builds a 3-min synthetic test video and runs the whole pipeline. ~1 min.
set -euo pipefail
command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH. Windows: winget install Gyan.FFmpeg, then open a NEW terminal."; exit 1; }
PY=""; for c in "python3" "python" "py -3"; do $c -c "import sys; assert sys.version_info >= (3, 9)" 2>/dev/null && { PY="$c"; break; }; done
[ -n "$PY" ] || { echo "No working Python 3.9+. Windows: winget install Python.Python.3.12, turn OFF python App execution aliases, open a NEW terminal."; exit 1; }
echo "using: $PY"
CH="$PY $(cd "$(dirname "$0")/.." && pwd)/scripts/ch.py"
T=$(mktemp -d); cd "$T"; export EASYCLIP_DIR="$T/out"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "testsrc2=s=1280x720:r=30:d=180" -f lavfi -i "smptehdbars=s=1280x720:r=30:d=180" \
 -f lavfi -i "sine=f=220:d=180" -filter_complex "[0:v][1:v]overlay=enable='between(t,40,48)*lt(mod(t,1),0.5)',drawbox=y=0:w=iw:h=ih*0.13:color=black:t=fill:enable='between(t,100,130)',drawbox=y=ih*0.87:w=iw:h=ih*0.13:color=black:t=fill:enable='between(t,100,130)'[v];[2:a]volume='if(between(t,40,48),1,0.03)':eval=frame[a]" \
 -map "[v]" -map "[a]" -c:v libx264 -preset ultrafast -crf 30 -c:a aac s.mp4
$CH doctor | tail -1
$CH analyze s.mp4
$CH moments s | tee /dev/stderr | grep -q "loud" && echo "PASS moments"
$CH policy --work s --start 100 --end 128 | grep -q BLOCK && echo "PASS cutscene flag"
$CH reel s.mp4 35 48 out.mp4 --layout blur --hook "smoke test" && echo "PASS reel"
{ $CH reel s.mp4 35 48 out2.mp4 --layout facecam --cam 0,0,.2,.2 2>&1 || true; } | grep -q "Pro feature" && echo "PASS pro gate"
echo "all good: $T"
