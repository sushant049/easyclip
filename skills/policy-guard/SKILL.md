---
name: policy-guard
description: Pre-upload risk check for any clip - flags cinematic or letterboxed footage (game cutscenes, film or TV), spoiler or leak words in titles, licensed music and permission to clip someone else's content. Use before posting a clip or when asked if a clip is safe to post.
---

# Policy Guard
`$CH` = `python3 <plugin-root>/scripts/ch.py` (Windows: `python` or `py -3`). Follow clip-director hard rules.

```bash
$CH policy --work <name> --start S --end E --title "..." [--no-voice]
```
Output `RESULT PASS|WARN|BLOCK` + lines. Relay as-is; on BLOCK propose the fix (re-cut, add commentary, rename).

Encodes (not legal advice): game publishers take down standalone cutscenes/endings/leaks; film/TV footage isn't yours; spoiler words; licensed music (mute or talk over); others' content needs permission; reused, unedited uploads get demoted. Heuristics can miss things - final call is the user's.
