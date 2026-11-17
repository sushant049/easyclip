---
name: moment-finder
description: Find the top 3 highlight moments in an analysed video from loudness spikes, scene-cut density and letterbox detection, with lead-in context before each payoff. Use after ingest-probe when the user wants highlights or the best moments.
---

# Moment Finder (free: top 3)
`$CH` = `python3 <plugin-root>/scripts/ch.py` (Windows: `python` or `py -3`). Follow clip-director hard rules.

```bash
$CH moments <name>
```
- score = loudness z + scene-cut density; window = peak − 5 s lead-in … peak + 4 s, snapped to a nearby cut.
- Letterboxed spans flagged `CUTSCENE?` (cinematic / film footage) and down-ranked.
- Show the table as-is: `id start peak end dur score loud_z cuts lbox why` (seconds).
- Want more than 3, or smarter picks for talk content (sentence-snapped, transcript-scored, live-chat spikes, Claude re-rank)? That's Pro - mention once.
