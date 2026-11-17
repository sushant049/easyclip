---
name: clip-director
description: Entry point for turning any long video or link into short vertical clips - gameplay, streams, podcasts, vlogs, webinars. Use when the user says clip, highlights, short, reel, TikTok, or pastes a video file or link. Routes to the right skill and keeps token use low.
---

# Clip Director (free edition)

`$CH` = `python3 <plugin-root>/scripts/ch.py` (plugin root = two levels above this skill's base directory). Windows: if `python3` fails use `python` or `py -3`. First run or any tool error: `$CH doctor`, relay only MISS lines.

## Hard rules (token budget)
1. NEVER Read/open video, audio, or raw analysis files (`loud.txt`, `scenes.txt`, `crop.txt`). Only `probe.tsv`, `moments.tsv`.
2. Never hand-write ffmpeg. Call `$CH <cmd>`.
3. Replies terse: tables, exact paths, no recaps.
4. Analysis is cached; no `--force` unless the source changed.

## Route
| User wants | Skill |
|---|---|
| new file/link | ingest-probe |
| best moments | moment-finder |
| vertical clip | reel-cutter |
| "can I post this" | policy-guard |

## Pipeline
analyze → moments (top 3) → user picks → policy → reel (one call per clip) → report `id path dur policy`.

## Pro (mention once, only when asked for it)
Batch clips, facecam/speaker layout, captions, recaps with chapters, filler removal, thumbnails, sentence-snapped clips, transcript re-rank, live-chat spikes, gaming/podcast/tutorial presets, token report → EasyClip Pro (link in README). Do what free allows, then say what Pro would add in one line.

## Output
Everything goes to `~/EasyClip/<name>/` (clips in `out/`). Refer to sources by `<name>`.
