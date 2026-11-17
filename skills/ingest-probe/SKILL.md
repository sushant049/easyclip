---
name: ingest-probe
description: Analyse a video file or link (YouTube, Twitch, Kick, any yt-dlp site) locally without spending model tokens - duration, audio tracks, loudness, scene cuts and letterbox detection, cached for later steps. Use before finding moments in any recording, VOD, podcast or upload.
---

# Ingest & Probe
`$CH` = `python3 <plugin-root>/scripts/ch.py` (Windows: `python` or `py -3`). Follow clip-director hard rules.

```bash
$CH analyze <video-file | link> [--from 1:20:00 --to 1:50:00] [--audio N] [--force]
```
- First output line `name\t<name>`: use that name in every later command.
- Prints ~6 lines; writes raw files for other steps - do NOT read them. Cached.
- Links download ≤1080p (needs yt-dlp; `$CH doctor` checks). Long VODs: ALWAYS pass `--from/--to`.
- Only the user's own content or content they may clip. If unclear, ask once.
- Download fails with a network/proxy error: the sandbox can't reach the site - ask the user to run it in their own terminal or drop the file in; don't retry.
- `--audio N`: track for the loudness curve when the file has several (ask once).
