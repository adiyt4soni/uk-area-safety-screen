---
name: uk-area-safety-screen
description: Compare London areas for where to live using public data only - police street-level crime within 800 m of each station (scaled to the median of the areas compared), the Census 2021 share of 25-34 year olds, and TfL commute times to the user's anchors - with positive controls that prove the data separates a known hotspot from a known quiet area. Use when the user asks which London areas are safe, where to live, or to check an area before renting.
---

# UK area safety screen (London)

It ships with `area_safety.py`, which does the data work (Python 3 standard library, public APIs, no key).

## 0. Rules
- **Data, not reputation.** Every row is source-stamped and dated. Forum opinions and friends' advice are leads to
  check, never the result.
- **Ethnicity and demographics other than age are never used.** The age share ranks areas; it never excludes one.
- **Busy places inflate counts.** Nightlife, shopping streets and transport hubs show high totals because of
  footfall, not residents' risk. Say so instead of auto-excluding them; judge them street by street.
- **The user approves the avoid list** before any listing search uses it.
- **Controls first.** Run a known hotspot and a known quiet area (default: Leicester Square and Richmond). If they
  don't separate clearly, or a control matched the wrong station, say so and don't trust the run.

## 1. Inputs
- The candidate areas (station names), the user's commute anchors (for example their office) with coordinates, and
  any areas they already ruled in or out.

## 2. Run
```bash
python3 area_safety.py --anchor "Trafalgar Square=51.5080,-0.1281" "Clapham Common" "Angel" "Canary Wharf" "Mile End"
```
It fetches the last 12 published months of street-level crime (data.police.uk), keeps incidents within 800 m of
each station, counts "serious" ones (violent crime, robbery, theft from the person, weapons possession), looks up
the Census 2021 age share for the station's MSOA (Nomis), and asks the TfL Journey Planner for the minutes to each
anchor arriving 08:30 on the next weekday. It writes a TSV and prints a serious-crime index scaled to the median of
the candidate areas (controls excluded). One failed area is written as FAILED and the run carries on. Compare at
least 5 candidates for a stable median.

## 3. Read the output
- Check the controls first (hotspot well above 1.00x, quiet area well below).
- Check each station name matched what you meant (a search for "Hampstead" once returned West Hampstead).
- Station commute times are not door to door: add a 5-10 minute walk.
- The London-wide 25-34 share is about 18% (Census 2021) for comparison.

## 4. Write the table (`area-safety-YYYY-MM-DD.md`)
Area | serious-crime index vs median | 25-34 share | commute to each anchor | recommendation (search / search with
caution / avoid) | note. Then "How this was measured", the controls and their results, and the limits: crime data
is by location of the report, not residents; small areas swing month to month; the police data lags by about two
months; commutes are from the station, not the door.

## 5. Hand off
Give the user the avoid list to approve. Once approved, it feeds `room-listing-triage` as a hard filter.
