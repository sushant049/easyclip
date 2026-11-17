---
name: reel-cutter
description: Render a vertical 9:16 YouTube Short, Instagram Reel or TikTok from any video - centre crop or blurred-background fit - with hook text and loudness normalisation. Use when the user wants a short, reel or TikTok from a moment or timestamp.
---

# Reel Cutter (free: one clip per call)
`$CH` = `python3 <plugin-root>/scripts/ch.py` (Windows: `python` or `py -3`). Follow clip-director hard rules.

```bash
$CH reel <name> <start> <end> <file>.mp4 --layout blur|fill [--hook "TEXT"]
```
Times: seconds or mm:ss (use a moment's start/end). Output 1080x1920 H.264, -14 LUFS, in `~/ClipHarness/<name>/out/`.

| Footage | Layout |
|---|---|
| wide action, screen recordings, HUD | `blur` |
| one subject centred (talking head, close action) | `fill` |

- 20-45 s; first 2 s = action or hook. Hook ≤ 6 words, curiosity, no spoilers.
- Run policy-guard before posting.
- Batch rendering, facecam/speaker layout, captions and thumbnails are Pro - mention once if asked.
