# UK area safety screen (London)

Compares London areas to live in using public data only: police crime near each station, the Census 25-34 share, and TfL commute times, with built-in positive controls.

**Type:** Claude Code skill · **Area:** General skills

## What it does

- `area_safety.py` (included, Python standard library, no API key) pulls the last 12 published months of street-level crime from data.police.uk and keeps incidents within 800 m of each station.
- Counts serious crime (violent crime, robbery, theft from the person, weapons) and scales it to the median of the areas compared.
- Adds the Census 2021 share of 25-34 year olds for the station's neighbourhood (Nomis) and TfL commute minutes to your anchors, arriving 08:30 on a weekday.
- Runs a known hotspot and a known quiet area as controls, excluded from the median. Tested on live data: Leicester Square had 14,338 serious crimes within 800 m over 12 months, Richmond 475. A failed area is logged and the run carries on.

## Guardrails

- Ethnicity and other demographics are never used; the age share ranks, never excludes.
- Busy hubs and nightlife inflate counts; the skill says so rather than auto-excluding them.
- The avoid list goes to the user for approval before anything uses it.

## When it triggers

> Compare London areas for where to live using public data only - police street-level crime within 800 m of each station (scaled to the median of the areas compared), the Census 2021 share of 25-34 year olds, and TfL commute times to the user's anchors - with positive controls that prove the data separates a known hotspot from a known quiet area. Use when the user asks which London areas are safe, where to live, or to check an area before renting.

## What's in this repo

- `SKILL.md`: the skill itself, the file Claude or Codex reads.
- `area_safety.py`: the data script. Run `python3 area_safety.py --help`.
- Written to be generic: where the skill relies on the user's own files, it names them by role, not by content.

## Install

```bash
git clone https://github.com/adiyt4soni/uk-area-safety-screen.git ~/.claude/skills/uk-area-safety-screen
```
