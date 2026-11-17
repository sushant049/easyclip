#!/usr/bin/env bash
# Build dist/easyclip-<ver>.mcpb : copies the CLI + presets in, then packs with the official mcpb CLI.
set -euo pipefail
cd "$(dirname "$0")"
cp ../scripts/ch.py src/ch.py
rm -rf presets && cp -r ../presets presets
mkdir -p ../dist
VER=$(python3 -c "import json;print(json.load(open('manifest.json'))['version'])")
npx -y @anthropic-ai/mcpb validate manifest.json
NAME=$(python3 -c "import json;print(json.load(open('manifest.json'))['name'])")
npx -y @anthropic-ai/mcpb pack . "../dist/$NAME-$VER.mcpb"
