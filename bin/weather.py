#!/usr/bin/env python3
"""Today's weather for a US zip (or 'lat,lon') via zippopotam.us + Open-Meteo. No API key. Plain text output."""
import json, os, sys, math, datetime, pathlib, urllib.request

loc = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LOCATION", "")).strip()
if not loc:
    sys.exit(0)
def get(url):
    with urllib.request.urlopen(url, timeout=15) as r: return json.load(r)

if "," in loc and loc.replace(",", "").replace(".", "").replace("-", "").isdigit():
    lat, lon = loc.split(","); place = loc
else:
    z = get(f"https://api.zippopotam.us/us/{loc}")["places"][0]
    lat, lon, place = z["latitude"], z["longitude"], f"{z['place name']}, {z['state abbreviation']}"

CODES = {0:"Clear",1:"Mostly clear",2:"Partly cloudy",3:"Overcast",45:"Fog",48:"Rime fog",51:"Light drizzle",53:"Drizzle",55:"Heavy drizzle",
         61:"Light rain",63:"Rain",65:"Heavy rain",66:"Freezing rain",67:"Freezing rain",71:"Light snow",73:"Snow",75:"Heavy snow",77:"Snow grains",
         80:"Showers",81:"Showers",82:"Heavy showers",85:"Snow showers",86:"Snow showers",95:"Thunderstorms",96:"Thunderstorms w/ hail",99:"Thunderstorms w/ hail"}
d = get("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&daily=temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,weather_code,sunrise,sunset,wind_speed_10m_max,uv_index_max&hourly=temperature_2m,precipitation_probability"
        "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=2" % (lat, lon))["daily"]
for i, label in enumerate(("TODAY", "TOMORROW")):
    print(f"{label} ({place}): {CODES.get(d['weather_code'][i], 'Mixed')}, high {round(d['temperature_2m_max'][i])}°F / low {round(d['temperature_2m_min'][i])}°F, "
          f"rain chance {d['precipitation_probability_max'][i]}%, wind up to {round(d['wind_speed_10m_max'][i])} mph, UV {d['uv_index_max'][i]}, "
          f"sunrise {d['sunrise'][i][-5:]}, sunset {d['sunset'][i][-5:]}")


# ---- Moon phase (no API): days since a reference new moon, mod the synodic month ----
def moon(today=None):
    today = today or datetime.datetime.now(datetime.timezone.utc)
    ref = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc)
    p = ((today - ref).total_seconds() / 86400 % 29.530588853) / 29.530588853  # 0 new, .5 full
    lit = (1 - math.cos(2 * math.pi * p)) / 2
    d = min(abs(p - k) for k in (0, 1)) ; q = 0.035  # within ~1 day of an exact phase gets its proper name
    if d < q: name = "New moon"
    elif abs(p - 0.5) < q: name = "Full moon"
    elif abs(p - 0.25) < q: name = "First quarter"
    elif abs(p - 0.75) < q: name = "Last quarter"
    else: name = ("Waxing " if p < 0.5 else "Waning ") + ("crescent" if lit < 0.5 else "gibbous")
    r, rx = 10, abs(math.cos(2 * math.pi * p)) * 10
    waxing = p < 0.5
    # lit region: half-disc on the lit side + terminator ellipse; sweep flags pick which way it bulges
    if waxing:
        path = f"M0,-{r} A{r},{r} 0 0 1 0,{r} A{rx:.2f},{r} 0 0 {0 if lit < 0.5 else 1} 0,-{r} Z"
    else:
        path = f"M0,-{r} A{r},{r} 0 0 0 0,{r} A{rx:.2f},{r} 0 0 {1 if lit < 0.5 else 0} 0,-{r} Z"
    svg = (f'<svg class="moon" viewBox="-11 -11 22 22" width="14" height="14" aria-label="{name}">'
           f'<circle r="{r}" fill="#111"/><path d="{path}" fill="#fff"/><circle r="{r}" fill="none" stroke="#111" stroke-width="1"/></svg>')
    return name, lit, svg

name, lit, svg = moon()
try:
    (pathlib.Path(__file__).resolve().parent.parent / "editions").mkdir(exist_ok=True)
    (pathlib.Path(__file__).resolve().parent.parent / "editions" / "moon.svg").write_text(svg)
except Exception:
    pass
print(f"MOON: {name}, {round(lit * 100)}% illuminated. In the weather strip write the literal token {{{{MOON}}}} followed by the phase name; the build step swaps in the icon.")
