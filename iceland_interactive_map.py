#!/usr/bin/env python3
"""
Iceland South Coast Road Trip — Interactive Map v2
March 6-10, 2026

Requires: pip install folium polyline requests
Usage:    python3 iceland_interactive_map.py
Output:   iceland_interactive_map.html

Features:
  - Road-accurate route lines via Valhalla/OpenStreetMap
  - Hiking trail overlays (dashed orange) with trail info popups
  - Live weather forecast in every stop popup (Open-Meteo)
  - Color-coded day layers with toggleable checkboxes
  - Separate hiking trail toggle
  - Multiple basemaps: Street, Terrain, Satellite
"""

import folium
from folium import FeatureGroup, Marker, PolyLine, Popup, Icon, LayerControl
import polyline as pl_lib
import requests, json, time, os

MAP_CENTER = [63.95, -18.5]
ZOOM_START = 8
VALHALLA_URL = "https://valhalla1.openstreetmap.de/route"
ROUTE_CACHE = "route_cache.json"
WEATHER_CACHE = "weather_cache.json"
CACHE_MAX_AGE_HOURS = 1

DAY_COLORS = {1:"#E63946",2:"#457B9D",3:"#2A9D8F",4:"#D4A017",5:"#7B2D8E"}
DAY_LABELS = {
    1:"Day 1 — Fri 3/6: KEF → Vík",2:"Day 2 — Sat 3/7: Vík → Skaftafell",
    3:"Day 3 — Sun 3/8: Skaftafell → Höfn → East",4:"Day 4 — Mon 3/9: Höfn → Skaftafell → Selfoss",
    5:"Day 5 — Tue 3/10: Selfoss → Golden Circle → KEF",
}
DAY_DATES = {1:"2026-03-06",2:"2026-03-07",3:"2026-03-08",4:"2026-03-09",5:"2026-03-10"}
TRAIL_COLOR = "#FF6B35"

WMO = {
    0:("Clear sky","☀️"),1:("Mainly clear","🌤️"),2:("Partly cloudy","⛅"),3:("Overcast","☁️"),
    45:("Fog","🌫️"),48:("Rime fog","🌫️"),51:("Light drizzle","🌦️"),53:("Drizzle","🌦️"),
    55:("Dense drizzle","🌧️"),56:("Freezing drizzle","🌧️❄️"),57:("Heavy freezing drizzle","🌧️❄️"),
    61:("Slight rain","🌦️"),63:("Rain","🌧️"),65:("Heavy rain","🌧️"),
    66:("Freezing rain","🌧️❄️"),67:("Heavy freezing rain","🌧️❄️"),
    71:("Light snow","🌨️"),73:("Snow","🌨️"),75:("Heavy snow","❄️"),77:("Snow grains","❄️"),
    80:("Light showers","🌦️"),81:("Showers","🌧️"),82:("Heavy showers","⛈️"),
    85:("Snow showers","🌨️"),86:("Heavy snow showers","❄️"),
    95:("Thunderstorm","⛈️"),96:("T-storm + hail","⛈️"),99:("T-storm + heavy hail","⛈️"),
}

# ═══════════════════════ STOPS ═══════════════════════
# (name, lat, lon, day, type, notes, link, est_hour, weather_loc)
STOPS = [
    ("KEF Airport",63.985,-22.6056,1,"logistics","Pick up campervan, stock up at Bónus. Depart ~7:30–9am.",None,8,"KEF / Reykjanes"),
    ("Hveragerði",63.9966,-21.1876,1,"attraction","Iceland's 'Hot Spring Town'. Geothermal Park. ~45 min from KEF.",None,9,"Hveragerði"),
    ("Reykjadalur Hot River",64.0229,-21.2116,1,"hike","🥾 BONUS HIKE: 7.4 km round trip, ~2–3 hrs. Natural warm river (36–40°C). Bring swimsuit + towel. Microspikes for icy patches.","https://guidetoiceland.is/connect-with-locals/regina/reykjadalur-hot-spring-valley-in-south-iceland",10,"Hveragerði"),
    ("Seljalandsfoss",63.6156,-19.9885,1,"attraction","60m walk-behind waterfall. Full waterproofs. 45 min.","https://guidetoiceland.is/travel-iceland/drive/seljalandsfoss",13,"Seljalandsfoss"),
    ("Gljúfrabúi",63.6207,-19.9862,1,"attraction","Hidden waterfall in canyon slot. 500m from Seljalandsfoss. 30 min.","https://guidetoiceland.is/travel-iceland/drive/gljufrabui",14,"Seljalandsfoss"),
    ("Skógafoss",63.5321,-19.5113,1,"attraction","🐉 GoT: Wildling camp (S8). 370-step staircase. 45 min.","https://guidetoiceland.is/travel-iceland/drive/skogafoss",15,"Vík"),
    ("Dyrhólaey",63.4022,-19.1289,1,"attraction","120m basalt sea arch. 45 min. ⚠️ Skip upper viewpoint if gusts >20 m/s.","https://guidetoiceland.is/travel-iceland/drive/dyrholaey",16,"Vík"),
    ("Reynisfjara",63.4044,-19.0695,1,"attraction","🐉 GoT S7E5: Eastwatch-by-the-Sea. Basalt cave. ⚠️ SNEAKER WAVE WARNING.","https://guidetoiceland.is/travel-iceland/drive/reynisfjara",17,"Vík"),
    ("Súður-Vík (dinner)",63.419,-19.008,1,"food","🍽️ Lamb soup ~2,800 ISK, fish & chips ~3,200 ISK. Alt: Black Crust Pizzeria ~3,500 ISK.",None,18,"Vík"),
    ("Vík 🏕️",63.4186,-19.006,1,"overnight","🏕️ OVERNIGHT: Vík Campsite (Víkurbraut 5). Year-round, heated common room.",None,20,"Vík"),
    ("Eldhraun Lava Field",63.67,-18.32,2,"attraction","World's largest lava flow in luminous green moss. 30 min.","https://guidetoiceland.is/travel-iceland/drive/eldhraun",9,"Vík"),
    ("Fjaðrárgljúfur Canyon",63.7712,-18.172,2,"attraction","🐉 GoT filming location. 2km rim trail, 100m-deep gorge. 1.5 hrs. Microspikes.","https://guidetoiceland.is/travel-iceland/drive/fjadrargljufur",10,"Kirkjubæjarklaustur"),
    ("Kirkjugolf",63.7875,-17.9959,2,"attraction","'Church Floor' — hexagonal basalt columns. 5-min walk.","https://guidetoiceland.is/travel-iceland/drive/kirkjugolfid",12,"Kirkjubæjarklaustur"),
    ("Systrafoss",63.7835,-17.9745,2,"attraction","Twin cascades above Kirkjubæjarklaustur. 30-min walk.","https://guidetoiceland.is/travel-iceland/drive/systrafoss",12,"Kirkjubæjarklaustur"),
    ("Svartifoss + Sjónarnipa Loop",64.0274,-16.9753,2,"hike","🥾 HIKE #1: 7.4 km, ~3 hrs. Basalt-column waterfall → Sjónarnipa glacier viewpoint → Sel turf house. Microspikes.\n\n🏕️ OVERNIGHT: Skaftafell Campsite (Vatnajökull NP, year-round).","https://guidetoiceland.is/travel-iceland/drive/svartifoss",14,"Skaftafell"),
    ("Svínafellsjökull",64.008,-16.875,3,"attraction","🐉 GoT: North of the Wall (S2–S3). Walk to glacier snout. 45 min.","https://guidetoiceland.is/travel-iceland/drive/svinafellsjokull",9,"Skaftafell"),
    ("Fjallsárlón",64.0167,-16.3667,3,"attraction","Quieter glacier lagoon with icebergs. 45 min.","https://guidetoiceland.is/travel-iceland/drive/fjallsarlon",10,"Jökulsárlón"),
    ("Jökulsárlón",64.0784,-16.2297,3,"attraction","Floating icebergs, possible seals. Crown jewel lagoon. 1 hr.","https://guidetoiceland.is/travel-iceland/drive/jokulsarlon",11,"Jökulsárlón"),
    ("Diamond Beach",64.044,-16.178,3,"attraction","Translucent ice on jet-black sand. 30 min.","https://guidetoiceland.is/travel-iceland/drive/diamond-beach",12,"Jökulsárlón"),
    ("Hofskirkja",64.1978,-15.9418,3,"attraction","Last surviving turf-roofed church. 15-min detour.","https://guidetoiceland.is/travel-iceland/drive/hofskirkja",13,"Höfn"),
    ("Hafnarbuðin (lunch)",64.254,-15.21,3,"food","🍽️ Langoustine baguette ~1,800 ISK (~$13). Cheapest langoustine in town. Free coffee.",None,13,"Höfn"),
    ("Stokksnes / Vestrahorn",64.249,-14.965,3,"attraction","Iconic mountain + black sand + Viking set. 💰 1,100 ISK/pp.","https://guidetoiceland.is/travel-iceland/drive/stokksnes",15,"Stokksnes"),
    ("Eystrahorn",64.319,-14.694,3,"attraction","Turnaround point. Walk the black sand base. 1 hr.","https://adventures.is/iceland/attractions/eystrahorn/",16,"Stokksnes"),
    ("Höfn 🏕️",64.2539,-15.2081,3,"overnight","🏕️ OVERNIGHT: Höfn Campsite – Hamrar. Year-round.",None,19,"Höfn"),
    ("Kristínartindar Summit",64.0169,-16.9669,4,"hike","🥾 HIKE #2: 17.9 km loop, ~6–8 hrs, summit 1,126m. 360° Vatnajökull panorama. Full winter gear. Backup: Skaftafellsheiði plateau.","https://adventures.is/iceland/attractions/kristinartindar/",10,"Skaftafell"),
    ("Núpsstaurskógur",63.9372,-17.505,4,"attraction","Iceland's largest native birch forest. 30-min walk.","https://guidetoiceland.is/travel-iceland/drive/nupsstadaskogur",15,"Kirkjubæjarklaustur"),
    ("Lómagnúpur",63.8971,-17.645,4,"attraction","Sheer 767m wall. ⚠️ Notorious sudden gusts.","https://guidetoiceland.is/travel-iceland/drive/lomagnupur",15,"Kirkjubæjarklaustur"),
    ("Þingborg Wool Shop 🧶",63.9333,-20.8167,4,"shop","🧶 Since 1991. Handknit lopapeysa, Icelandic sheep's wool. Tax-free receipt (15% VAT at KEF). 📍 Route 1, 8 km east of Selfoss.","https://www.south.is/en/service/thingborg-wool-processing",18,"Selfoss"),
    ("Selfoss 🏕️",63.9332,-21.003,4,"overnight","🏕️ OVERNIGHT: Selfoss Campsite. Year-round. Bónus, N1, pool.",None,19,"Selfoss"),
    ("Þingvellir",64.2559,-21.1299,5,"attraction","🐉 GoT S4: Bloody Gate. Rift valley + Öxarárfoss. UNESCO. 💰 Parking 750 ISK.","https://guidetoiceland.is/travel-iceland/drive/thingvellir",8,"Þingvellir"),
    ("Þórufoss (optional)",64.2833,-21.0667,5,"attraction","🐉 GoT S4E6: Drogon torches a goatherd's flock. Quiet 18m waterfall. ⚠️ Route 48 is gravel, may be icy — check road.is.","https://guidetoiceland.is/travel-iceland/drive/thorufoss",8,"Þingvellir"),
    ("Geysir",64.3103,-20.3024,5,"attraction","Strokkur erupts every 6–10 min. 💰 Parking 1,000 ISK.","https://guidetoiceland.is/travel-iceland/drive/geysir",10,"Geysir"),
    ("Gullfoss",64.3271,-20.1199,5,"attraction","Iceland's most powerful waterfall. 💰 Free.","https://guidetoiceland.is/travel-iceland/drive/gullfoss",11,"Geysir"),
    ("Hallgrímskirkja",64.1417,-21.9267,5,"attraction","🗽 Leif Erikson statue + tower 1,500 ISK. 20–25 min.","https://www.hallgrimskirkja.is/en-gb",13,"Reykjavík"),
    ("Smékkleysa Records",64.1435,-21.928,5,"attraction","🎵 Björk's Sugarcubes label. Record shop + coffee. 25–30 min.","https://www.instagram.com/smekkleysa/",13,"Reykjavík"),
    ("Harpa Concert Hall",64.1505,-21.9327,5,"attraction","Geometric glass facade. Free lobby. Tours 2,750 ISK.","https://www.harpa.is/en",14,"Reykjavík"),
    ("Sun Voyager",64.1476,-21.9223,5,"attraction","Iconic steel ship sculpture. Quick photo.","https://guidetoiceland.is/travel-iceland/drive/sun-voyager",15,"Reykjavík"),
    ("Icelandic Street Food",64.147,-21.931,5,"food","🍽️ Lamb soup bread bowl, unlimited refills + free waffles. ~2,500–3,000 ISK.\n💡 Start with shellfish soup, then switch to lamb/tomato for free refills.","https://www.icelandicstreetfood.com/",15,"Reykjavík"),
    ("KEF Departure ✈️",63.985,-22.6056,5,"logistics","Drop off campervan ~4pm. Flight 5pm.",None,16,"KEF / Reykjanes"),
]

# ═══════════════════════ HIKING TRAILS ═══════════════════════
TRAILS = [
    {
        "name":"Reykjadalur Hot River Trail",
        "day":1,"distance":"7.4 km round trip","time":"2–3 hours",
        "difficulty":"Moderate","elevation":"250m gain",
        "url":"https://www.alltrails.com/trail/iceland/southern/reykjadalur-hot-spring-thermal-river",
        "notes":"Out-and-back from car park. Steep climb 20 min, then rolling valley past Djúpagilsfoss waterfall, steam vents, mud pots. Ends at warm river bathing area with wooden boardwalk. Microspikes essential in March.",
        "waypoints":[
            (64.0193,-21.2116),(64.0205,-21.2135),(64.0218,-21.2160),(64.0235,-21.2185),
            (64.0255,-21.2210),(64.0275,-21.2235),(64.0295,-21.2255),(64.0310,-21.2270),
            (64.0325,-21.2285),(64.0336,-21.2292),
        ],
    },
    {
        "name":"Svartifoss–Sjónarnipa Loop (S6)",
        "day":2,"distance":"7.4 km loop","time":"2.5–3 hours",
        "difficulty":"Moderate","elevation":"270m gain",
        "url":"https://www.alltrails.com/trail/iceland/southern/sjonarnipa-svartifoss-magnusafoss-hundafoss-via-austurbrekkur",
        "notes":"Loop from Skaftafell Visitor Centre. Through camp → Hundafoss → Magnúsarfoss → Svartifoss (basalt columns) → Sjónarsker viewpoint (310m) → Sjónarnipa glacier overlook → Sel turf house → Austurbrekkur descent. Well-marked blue/red trails (S5/S6).",
        "waypoints":[
            (64.0169,-16.9669),(64.0180,-16.9680),(64.0195,-16.9700),(64.0215,-16.9720),
            (64.0235,-16.9735),(64.0260,-16.9748),(64.0275,-16.9753),(64.0290,-16.9740),
            (64.0310,-16.9720),(64.0335,-16.9690),(64.0355,-16.9650),(64.0340,-16.9620),
            (64.0310,-16.9610),(64.0280,-16.9620),(64.0240,-16.9640),(64.0200,-16.9660),
            (64.0169,-16.9669),
        ],
    },
    {
        "name":"Kristínartindar Summit (S4)",
        "day":4,"distance":"17.9 km loop","time":"6–8 hours",
        "difficulty":"Difficult","elevation":"1,215m gain → 1,126m summit",
        "url":"https://www.alltrails.com/trail/iceland/southern/kristinartindar-via-svartifoss-skaftafellsheidi",
        "notes":"Full-day from Visitor Centre. Austurbrekkur → Sjónarnipa → Skaftafellsheiði heath → Gemludalur valley → ridge scramble (loose scree, steep) → summit. Views: Vatnajökull, Öræfajökull, Morsárjökull, black sand plains to sea.\n\n⚠️ Backup: Turn around at Skaftafellsheiði plateau for amazing views without summit scramble.",
        "waypoints":[
            (64.0169,-16.9669),(64.0195,-16.9700),(64.0275,-16.9753),(64.0355,-16.9650),
            (64.0380,-16.9600),(64.0400,-16.9550),(64.0420,-16.9500),(64.0440,-16.9450),
            (64.0460,-16.9420),(64.0470,-16.9390),(64.0460,-16.9360),(64.0445,-16.9340),
            (64.0430,-16.9320),(64.0415,-16.9310),(64.0430,-16.9320),(64.0445,-16.9340),
            (64.0460,-16.9380),(64.0470,-16.9420),(64.0450,-16.9480),(64.0420,-16.9540),
            (64.0380,-16.9590),(64.0340,-16.9620),(64.0280,-16.9640),(64.0200,-16.9660),
            (64.0169,-16.9669),
        ],
    },
]

# ═══════════════════════ ALTERNATIVE ROUTES ═══════════════════════
ALT_COLOR = "#4A90D9"
ALT_ROUTES = [
    {
        "name":"Skaftafellsheiði Plateau (Backup Hike)",
        "day":4,"distance":"~5 km","time":"2.5 hrs",
        "trigger":"⚠️ Use if sustained winds >15 m/s or poor visibility at altitude.",
        "notes":"Lower-elevation alternative to Kristínartindar summit. Glacier views without the exposed ridge scramble. Ask the ranger at Skaftafell visitor center for morning conditions.",
        "waypoints":[
            (64.0169,-16.9669),(64.0195,-16.9700),(64.0275,-16.9753),
            (64.0355,-16.9650),(64.0380,-16.9600),(64.0400,-16.9550),
        ],
    },
    {
        "name":"Þórufoss Detour (Route 48)",
        "day":5,"distance":"~30 min detour","time":"15 min stop",
        "trigger":"🐉 Optional GoT bonus — only if ahead of schedule by 8:30am.",
        "notes":"Detour off Route 36 onto gravel Route 48. Quiet 18m waterfall. GoT S4E6: Drogon torches a goatherd's flock. ⚠️ Route 48 is gravel, potentially icy in March — check road.is.",
        "waypoints":[
            (64.2559,-21.1299),(64.2650,-21.1100),(64.2750,-21.0900),
            (64.2833,-21.0667),
        ],
    },
    {
        "name":"Dyrhólaey Lower Viewpoint Only",
        "day":1,"distance":"Same stop","time":"30 min",
        "trigger":"⚠️ Use if gusts exceed 20 m/s — skip upper viewpoint.",
        "notes":"In high winds, stay at the lower parking area for views of the basalt sea arch. The upper viewpoint is extremely exposed and dangerous in strong gusts.",
        "waypoints":[
            (63.4022,-19.1289),(63.3990,-19.1250),(63.3970,-19.1220),
        ],
    },
]

# ═══════════════════════ WEATHER ═══════════════════════
def fetch_weather():
    if os.path.exists(WEATHER_CACHE):
        age_seconds = time.time() - os.path.getmtime(WEATHER_CACHE)
        if age_seconds < CACHE_MAX_AGE_HOURS * 3600:
            print(f"✓ Weather loaded from cache (expires in {int((CACHE_MAX_AGE_HOURS * 3600 - age_seconds) / 60)} min).")
            with open(WEATHER_CACHE) as f: return json.load(f)
        else:
            print("⟳ Weather cache expired — fetching fresh data...")
    locs = {}
    for s in STOPS:
        wl = s[8]
        if wl not in locs: locs[wl] = (s[1], s[2])
    print("Fetching weather from Open-Meteo...")
    out = {}
    for name,(lat,lon) in locs.items():
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&hourly=temperature_2m,apparent_temperature,precipitation,weathercode,windspeed_10m,windgusts_10m"
               f"&start_date=2026-03-06&end_date=2026-03-10&timezone=Atlantic/Reykjavik")
        try:
            r = requests.get(url, timeout=15).json()
            if "hourly" in r: out[name] = r["hourly"]; print(f"  ✓ {name}")
        except: pass
        time.sleep(0.3)
    with open(WEATHER_CACHE,"w") as f: json.dump(out, f)
    return out

def get_wx(wd, wloc, day, hour):
    if wloc not in wd: return None
    h = wd[wloc]; t = f"{DAY_DATES[day]}T{hour:02d}:00"
    try: i = h["time"].index(t)
    except ValueError: return None
    tc = h["temperature_2m"][i]; fc = h["apparent_temperature"][i]
    desc,emoji = WMO.get(h["weathercode"][i], ("Unknown","❓"))
    return {"tc":tc,"tf":round(tc*9/5+32,1),"fc":fc,"ff":round(fc*9/5+32,1),
            "p":h["precipitation"][i],"w":h["windspeed_10m"][i],"g":h["windgusts_10m"][i],
            "desc":desc,"emoji":emoji,"hour":hour}

# ═══════════════════════ ROUTING ═══════════════════════
def valhalla_route(locs):
    payload = {"locations":[{"lat":la,"lon":lo} for la,lo in locs],"costing":"auto","directions_options":{"units":"km"}}
    try:
        r = requests.post(VALHALLA_URL, json=payload, timeout=30); r.raise_for_status(); d = r.json()
        if "trip" not in d: return None
        cc = []
        for leg in d["trip"]["legs"]:
            c = pl_lib.decode(leg["shape"], 6)
            if cc and c and cc[-1]==c[0]: c=c[1:]
            cc.extend(c)
        return cc, d["trip"]["summary"]["length"]
    except: return None

def fetch_routes():
    if os.path.exists(ROUTE_CACHE):
        with open(ROUTE_CACHE) as f:
            c = json.load(f); routes = {int(k):v for k,v in c.items()}
            if len(routes)==5: print("✓ Routes loaded from cache."); return routes
    print("Fetching routes from Valhalla...")
    routes = {}
    for day in range(1,6):
        pts = [(la,lo) for _,la,lo,d,*_ in STOPS if d==day]
        ns = [n for n,_,_,d,*_ in STOPS if d==day]
        print(f"  Day {day}: {ns[0]} → {ns[-1]} ({len(pts)} stops)")
        res = valhalla_route(pts)
        if res: routes[day]=res[0]; print(f"    ✓ {len(res[0])} pts, {res[1]:.0f} km")
        else: routes[day]=pts; print(f"    ⚠ fallback")
        time.sleep(1)
    with open(ROUTE_CACHE,"w") as f: json.dump({str(k):v for k,v in routes.items()}, f)
    return routes

# ═══════════════════════ MAP ═══════════════════════
def popup_html(name, day, stype, notes, link, wx, lat=None, lon=None):
    c = DAY_COLORS[day]
    h = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;width:300px;line-height:1.5;">
    <div style="background:{c};color:white;padding:8px 12px;border-radius:6px 6px 0 0;margin:-13px -20px 10px -20px;">
      <strong style="font-size:14px;">{name}</strong><br>
      <span style="font-size:11px;opacity:0.9;">{DAY_LABELS[day]} · {stype.capitalize()}</span>
    </div>"""
    if wx:
        w=wx
        h+=f"""<div style="background:#f0f4f8;border-radius:6px;padding:8px 10px;margin-bottom:8px;font-size:12px;border-left:3px solid {c};">
      <div style="font-weight:600;margin-bottom:4px;">{w['emoji']} {w['desc']} at ~{w['hour']}:00</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:11px;color:#555;">
        <span>🌡️ {w['tc']:.0f}°C / {w['tf']:.0f}°F</span><span>🥶 Feels {w['fc']:.0f}°C / {w['ff']:.0f}°F</span>
        <span>💨 Wind {w['w']:.0f} km/h</span><span>💨 Gusts {w['g']:.0f} km/h</span>
        <span>🌧️ Precip {w['p']:.1f} mm</span>
      </div></div>"""
    h+=f'<div style="font-size:12px;color:#333;white-space:pre-wrap;">{notes}</div>'
    links_parts = []
    if link:
        links_parts.append(f'<a href="{link}" target="_blank" style="color:{c};text-decoration:none;font-size:12px;font-weight:600;">📖 Visitor Guide →</a>')
    if lat is not None and lon is not None:
        gmap = f"https://www.google.com/maps?q={lat},{lon}"
        links_parts.append(f'<a href="{gmap}" target="_blank" style="color:{c};text-decoration:none;font-size:12px;font-weight:600;">📍 Map</a>')
    if links_parts:
        h+=f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;display:flex;gap:16px;">{"".join(links_parts)}</div>'
    return h+"</div>"

def trail_popup(t):
    h=f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;width:280px;line-height:1.5;">
    <div style="background:{TRAIL_COLOR};color:white;padding:8px 12px;border-radius:6px 6px 0 0;margin:-13px -20px 10px -20px;">
      <strong style="font-size:14px;">🥾 {t['name']}</strong><br>
      <span style="font-size:11px;opacity:0.9;">{DAY_LABELS[t['day']]}</span>
    </div>
    <div style="font-size:12px;margin-bottom:6px;"><b>{t['distance']}</b> · <b>{t['time']}</b> · {t['difficulty']}<br>📈 {t['elevation']}</div>
    <div style="font-size:11px;color:#555;white-space:pre-wrap;margin-bottom:8px;">{t['notes']}</div>
    <div style="border-top:1px solid #eee;padding-top:8px;">
      <a href="{t['url']}" target="_blank" style="color:{TRAIL_COLOR};text-decoration:none;font-size:12px;font-weight:600;">🗺️ Trail Info & Map (AllTrails) →</a>
    </div></div>"""
    return h

def build_map(routes, weather):
    m = folium.Map(location=MAP_CENTER, zoom_start=ZOOM_START, tiles=None, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="🗺️ Street Map").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",attr="Esri",name="🏔️ Terrain").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",attr="Esri",name="🛰️ Satellite").add_to(m)

    dg = {d: FeatureGroup(name=DAY_LABELS[d], show=True) for d in range(1,6)}
    tg = FeatureGroup(name="🥾 Hiking Trails", show=True)
    gotg = FeatureGroup(name="🐉 GoT Filming Locations", show=False)
    altg = FeatureGroup(name="🔀 Alternative Routes", show=False)

    # Road routes
    for day, coords in routes.items():
        PolyLine(locations=coords, color=DAY_COLORS[day], weight=4, opacity=0.85, smooth_factor=1, tooltip=DAY_LABELS[day]).add_to(dg[day])

    # Hiking trails
    for t in TRAILS:
        tp = trail_popup(t)
        PolyLine(locations=t["waypoints"], color=TRAIL_COLOR, weight=3, opacity=0.9, dash_array="8 6",
                 tooltip=f"<b>🥾 {t['name']}</b><br>{t['distance']} · {t['time']}",
                 popup=Popup(tp, max_width=320)).add_to(tg)
        Marker(location=t["waypoints"][0],
               tooltip=f"🥾 {t['name']} — Trailhead",
               icon=Icon(color="orange",icon="shoe-prints",prefix="fa"),
               popup=Popup(tp, max_width=320)).add_to(tg)

    # Stop markers
    ICONS = {"overnight":("campground","green"),"hike":("person-hiking","orange"),
             "food":("utensils","purple"),"shop":("store","pink"),"logistics":("plane","gray")}
    DCOL = {1:"red",2:"blue",3:"darkgreen",4:"orange",5:"purple"}

    for name,lat,lon,day,st,notes,link,hr,wl in STOPS:
        ic,icol = ICONS.get(st, ("camera", DCOL.get(day,"blue")))
        wx = get_wx(weather, wl, day, hr)
        ph = popup_html(name, day, st, notes, link, wx, lat, lon)
        Marker(location=[lat,lon], popup=Popup(ph, max_width=340),
               tooltip=f"<b>{name}</b><br><small>{DAY_LABELS[day]}</small>",
               icon=Icon(color=icol, icon=ic, prefix="fa")).add_to(dg[day])
        # GoT filming location markers
        if "🐉" in notes:
            got_ph = popup_html(name, day, st, notes, link, wx, lat, lon)
            Marker(location=[lat,lon], popup=Popup(got_ph, max_width=340),
                   tooltip=f"<b>🐉 {name}</b><br><small>GoT Filming Location</small>",
                   icon=Icon(color="black",icon="shield",prefix="fa")).add_to(gotg)

    for fg in dg.values(): fg.add_to(m)
    tg.add_to(m)
    gotg.add_to(m)

    # Alternative routes
    for ar in ALT_ROUTES:
        ar_html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;width:280px;line-height:1.5;">
        <div style="background:{ALT_COLOR};color:white;padding:8px 12px;border-radius:6px 6px 0 0;margin:-13px -20px 10px -20px;">
          <strong style="font-size:14px;">🔀 {ar['name']}</strong><br>
          <span style="font-size:11px;opacity:0.9;">{DAY_LABELS[ar['day']]} · {ar['distance']} · {ar['time']}</span>
        </div>
        <div style="background:#fff3cd;border-radius:6px;padding:8px 10px;margin-bottom:8px;font-size:12px;border-left:3px solid #ffc107;">
          <div style="font-weight:600;">{ar['trigger']}</div>
        </div>
        <div style="font-size:12px;color:#333;white-space:pre-wrap;">{ar['notes']}</div>
        </div>"""
        PolyLine(locations=ar["waypoints"], color=ALT_COLOR, weight=3, opacity=0.8, dash_array="10 8",
                 tooltip=f"<b>🔀 {ar['name']}</b><br>{ar['trigger']}",
                 popup=Popup(ar_html, max_width=320)).add_to(altg)
        Marker(location=ar["waypoints"][0],
               tooltip=f"🔀 {ar['name']} — Start",
               icon=Icon(color="lightblue",icon="arrows-split-up-and-left",prefix="fa"),
               popup=Popup(ar_html, max_width=320)).add_to(altg)
    altg.add_to(m)
    LayerControl(collapsed=False).add_to(m)

    title = """<div style="position:fixed;top:10px;left:55px;z-index:1000;background:white;padding:10px 18px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">
    <div style="font-size:16px;font-weight:700;color:#2E5B8A;">🇮🇸 Iceland Road Trip — Interactive Map</div>
    <div style="font-size:12px;color:#666;margin-top:2px;">March 6–10, 2026 · 5 Days · ~1,200 km · Live weather forecast</div>
    <div style="font-size:10px;color:#999;margin-top:4px;">🏕️ Camp  🥾 Hike  🍽️ Food  🧶 Shop  📷 Attraction  ✈️ Logistics  🐉 GoT  🔀 Alt</div>
    <div style="font-size:9px;color:#bbb;margin-top:3px;">Roads: Valhalla/OSM · Weather: Open-Meteo ·
    <span style="color:#FF6B35;">━ ━ ━</span> Hiking trails · <span style="color:#4A90D9;">━ ━ ━</span> Alt routes · Toggle layers ↗</div></div>"""
    m.get_root().html.add_child(folium.Element(title))

    # Make layer control scrollable so all layers are visible
    layer_css = """<style>
    .leaflet-control-layers-overlays {
        max-height: 400px;
        overflow-y: auto;
    }
    </style>"""
    m.get_root().html.add_child(folium.Element(layer_css))

    return m

if __name__ == "__main__":
    routes = fetch_routes()
    weather = fetch_weather()
    print("\nBuilding interactive map...")
    m = build_map(routes, weather)
    out = "index.html"
    m.save(out)
    kb = os.path.getsize(out)/1024
    print(f"\n✓ Saved: {out} ({kb:.0f} KB)")
    print("  • Layer control: toggle days + hiking trails on/off")
    print("  • Click markers for weather + notes + visitor guide links")
    print("  • Dashed orange lines = hiking trails with AllTrails links")
    print("  • 3 basemaps: Street / Terrain / Satellite")
