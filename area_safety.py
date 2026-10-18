#!/usr/bin/env python3
"""Area safety, young-professional share and commute table for London areas, from public data only.

Sources (all public, no API key):
  - TfL StopPoint search: station name, coordinates and id
  - data.police.uk crimes-street/all-crime: street-level crime per month (1-mile query), kept within RADIUS_M
  - postcodes.io reverse geocode: the station's MSOA (2021)
  - Nomis NM_2020_1 (Census 2021 TS007A, age by five-year bands): share of residents aged 25 to 34
  - TfL Journey Planner: station to each anchor, arriving 08:30 on the next weekday

Usage:
  python3 area_safety.py "Clapham Common" "Angel" "Canary Wharf"
  python3 area_safety.py --anchor "Trafalgar Square=51.5080,-0.1281" --anchor "Kings Cross=51.5308,-0.1238" "Mile End"
  python3 area_safety.py --file areas.txt          (one station search term per line)

Always include positive controls (a known busy hotspot and a known quiet area) so you can see the data
separates them. Leicester Square and Richmond are included by default; pass --no-controls to drop them.

Writes a TSV (one row per area, flushed as it goes) to ./area-data/areas-<date>.tsv and prints each
row plus the median-scaled serious-crime index. Python 3 standard library only.
"""
import argparse, csv, datetime, json, math, os, statistics, subprocess, time, urllib.parse

RADIUS_M = 800
SERIOUS = {"violent-crime", "robbery", "theft-from-the-person", "possession-of-weapons"}
CONTROLS = ["Leicester Square", "Richmond"]
DEFAULT_ANCHORS = {"Trafalgar Square": (51.5080, -0.1281)}  # a central landmark; pass --anchor for your own


def get(url, tries=4):
    """Fetch with system curl (some Python builds fail TLS with these hosts). Retries with backoff."""
    for i in range(tries):
        try:
            return subprocess.run(["curl", "-sf", "-m", "90", "-A", "area-safety-screen/1.0", url],
                                  capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError:
            if i == tries - 1:
                raise
            time.sleep(2 + 3 * i)


def hav(a, b):
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def latest_months(n=12):
    """The n most recent months data.police.uk has published."""
    d = json.loads(get("https://data.police.uk/api/crimes-street-dates"))
    return sorted(x["date"] for x in d)[-n:]


def station(term):
    q = urllib.parse.quote(term)
    d = json.loads(get(f"https://api.tfl.gov.uk/StopPoint/Search/{q}"
                       "?modes=tube,overground,dlr,elizabeth-line,national-rail"))
    if not d.get("matches"):
        raise LookupError(f"no TfL station matched {term!r}")
    m = d["matches"][0]
    return m["name"], m["lat"], m["lon"], m["id"]


def crimes(lat, lng, months):
    total = serious = 0
    for mo in months:
        d = json.loads(get(f"https://data.police.uk/api/crimes-street/all-crime?lat={lat}&lng={lng}&date={mo}"))
        for c in d:
            p = (float(c["location"]["latitude"]), float(c["location"]["longitude"]))
            if hav((lat, lng), p) <= RADIUS_M:
                total += 1
                serious += c["category"] in SERIOUS
        time.sleep(0.15)
    return total, serious


def age_share(lat, lng):
    d = json.loads(get(f"https://api.postcodes.io/postcodes?lon={lng}&lat={lat}&limit=1&radius=1000"))
    if not d.get("result"):
        raise LookupError("postcodes.io found no postcode within 1 km")
    r = d["result"][0]
    msoa = r.get("codes", {}).get("msoa21")
    if not msoa:
        raise LookupError("postcodes.io returned no 2021 MSOA code")
    rows = list(csv.DictReader(get(
        f"https://www.nomisweb.co.uk/api/v01/dataset/NM_2020_1.data.csv?geography={msoa}&measures=20100"
        "&select=geography_name,c2021_age_19_name,obs_value").splitlines()))
    v = {x["C2021_AGE_19_NAME"]: int(x["OBS_VALUE"]) for x in rows}
    share = (v["Aged 25 to 29 years"] + v["Aged 30 to 34 years"]) / v["Total"]
    return rows[0]["GEOGRAPHY_NAME"], r["admin_district"], share


def next_weekday():
    d = datetime.date.today() + datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d.strftime("%Y%m%d")


def commute(station_id, dest, date):
    """Minutes from the station (by TfL id; coordinates proved fragile) to dest, arriving 08:30. 'NA' on failure."""
    try:
        d = json.loads(get(f"https://api.tfl.gov.uk/Journey/JourneyResults/{station_id}/to/{dest[0]},{dest[1]}"
                           f"?date={date}&time=0830&timeIs=Arriving", tries=2))
        return min(j["duration"] for j in d["journeys"])
    except Exception:
        return "NA"


def parse_anchor(s):
    name, coords = s.split("=", 1)
    lat, lng = (float(x) for x in coords.split(","))
    return name.strip(), (lat, lng)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("areas", nargs="*", help="station search terms")
    ap.add_argument("--file", help="file with one station search term per line")
    ap.add_argument("--anchor", action="append", default=[], help='commute anchor, "Name=lat,lng" (repeatable)')
    ap.add_argument("--no-controls", action="store_true", help="skip the default positive controls")
    ap.add_argument("--out", default="area-data", help="output folder")
    a = ap.parse_args()

    terms = list(a.areas)
    if a.file:
        terms += [l.strip() for l in open(a.file) if l.strip() and not l.startswith("#")]
    if not a.no_controls:
        have = {t.lower() for t in terms}
        terms += [c for c in CONTROLS if c.lower() not in have]
    if not terms:
        ap.error("give at least one area")
    anchors = dict(parse_anchor(s) for s in a.anchor) or DEFAULT_ANCHORS

    months = latest_months()
    date = next_weekday()
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"areas-{datetime.date.today().isoformat()}.tsv")
    print(f"crime months {months[0]} to {months[-1]}; commute arriving 08:30 on {date}; writing {path}", flush=True)

    head = ["search_term", "station", "lat", "lng", "msoa", "borough", "share_25_34",
            f"crimes_{len(months)}m_{RADIUS_M}m", f"serious_{len(months)}m_{RADIUS_M}m"] + \
           [f"min_to_{n}" for n in anchors]
    rows = []
    with open(path, "w") as f:
        f.write("\t".join(head) + "\n")
        for term in terms:
            try:
                name, lat, lng, sid = station(term)
                msoa, boro, share = age_share(lat, lng)
                tot, ser = crimes(lat, lng, months)
                mins = [commute(sid, dest, date) for dest in anchors.values()]
                row = [term, name, f"{lat:.5f}", f"{lng:.5f}", msoa, boro, f"{share:.3f}", tot, ser] + mins
                rows.append(row)
            except Exception as e:  # one bad area (no station match, API error) must not kill the run
                row = [term, f"FAILED: {type(e).__name__}: {e}"] + ["NA"] * (len(head) - 2)
            f.write("\t".join(map(str, row)) + "\n")
            f.flush()
            print("\t".join(map(str, row)), flush=True)

    if not rows:
        print("\nNo area succeeded; nothing to compare.")
        return
    ctrl = {c.lower() for c in CONTROLS}
    candidates = [r for r in rows if r[0].lower() not in ctrl] or rows
    med = statistics.median(r[8] for r in candidates)
    print(f"\nserious-crime index (1.00 = median of the {len(candidates)} candidate areas; controls excluded from the median):")
    for r in sorted(rows, key=lambda r: r[8], reverse=True):
        tag = "  [control]" if r[0].lower() in ctrl else ""
        print(f"  {r[8] / med if med else float('nan'):5.2f}x  {r[0]} ({r[1]}){tag}")
    print("Check the controls: the hotspot should be well above 1.00x and the quiet area well below.")
    print("The index is relative to this run's areas: compare at least 5 candidates for a stable median.")


if __name__ == "__main__":
    main()
