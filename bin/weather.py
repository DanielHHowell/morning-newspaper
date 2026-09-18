#!/usr/bin/env python3
"""Today's weather for a US zip (or 'lat,lon') via zippopotam.us + Open-Meteo. No API key. Plain text output."""
import json, os, sys, urllib.request

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
