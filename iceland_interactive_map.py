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
from folium.plugins import LocateControl
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
# (name, lat, lon, day, type, notes, link, est_hour, weather_loc, is_immune_to_skipping, duration_minutes)
STOPS = [
    # ---- Day 1: KEF to Vík ----
    ("KEF Airport",63.985,-22.6056,1,"logistics",
     "Arrive via BWI 06:30 am (Flight FI642, Confirm: CAJIC8). Pick up campervan, stock up at Bónus. Depart ~7:30–9am.", None, 8, "KEF / Reykjanes", True, 0),
    ("Hveragerði",63.9966,-21.1876,1,"attraction",
     "Iceland's 'Hot Spring Town'. Geothermal Park. ~45 min from KEF.", None, 9, "Hveragerði", False, 60),
    ("Reykjadalur Hot River",64.0229,-21.2116,1,"hike",
     "BONUS HIKE: 7.4 km round trip, ~2–3 hrs. Natural warm river (36–40°C). Bring swimsuit + towel. Microspikes for icy patches.",
     "https://guidetoiceland.is/connect-with-locals/regina/reykjadalur-hot-spring-valley-in-south-iceland", 10, "Hveragerði", False, 180),
    ("Seljalandsfoss",63.6156,-19.9885,1,"attraction",
     "60m walk-behind waterfall. Full waterproofs. 45 min.",
     "https://guidetoiceland.is/travel-iceland/drive/seljalandsfoss", 13, "Seljalandsfoss", False, 45),
    ("Gljúfrabúi",63.6207,-19.9862,1,"attraction",
     "Hidden waterfall in canyon slot. 500m from Seljalandsfoss. 30 min.",
     "https://guidetoiceland.is/travel-iceland/drive/gljufrabui", 14, "Seljalandsfoss", False, 30),
    ("Skógafoss",63.5321,-19.5113,1,"attraction",
     "🐉 GoT: Wildling camp (S8). 370-step staircase. 45 min.",
     "https://guidetoiceland.is/travel-iceland/drive/skogafoss", 15, "Vík", False, 45),
    ("Dyrhólaey",63.4022,-19.1289,1,"attraction",
     "120m basalt sea arch. 45 min. ⚠️ Skip upper viewpoint if gusts >20 m/s.",
     "https://guidetoiceland.is/travel-iceland/drive/dyrholaey", 16, "Vík", False, 45),
    ("Reynisfjara",63.4044,-19.0695,1,"attraction",
     "🐉 GoT S7E5: Eastwatch-by-the-Sea. Basalt cave. ⚠️ SNEAKER WAVE WARNING.",
     "https://guidetoiceland.is/travel-iceland/drive/reynisfjara", 17, "Vík", False, 60),
    ("Súður-Vík (dinner)",63.419,-19.008,1,"food",
     "🍽️ Lamb soup ~2,800 ISK, fish & chips ~3,200 ISK. Alt: Black Crust Pizzeria ~3,500 ISK.",None,18,"Vík", False, 60),
    ("Vík 🏕️",63.4186,-19.006,1,"overnight",
     "🏕️ OVERNIGHT: Vík Campsite (Víkurbraut 5). Year-round, heated common room.",None,20,"Vík", True, 0),

    # ---- Day 2: Vík to Skaftafell ----
    ("Eldhraun Lava Field",63.67,-18.32,2,"attraction","World's largest lava flow in luminous green moss. 30 min.","https://guidetoiceland.is/travel-iceland/drive/eldhraun",9,"Vík", False, 30),
    ("Fjaðrárgljúfur Canyon",63.7712,-18.172,2,"attraction","🐉 GoT filming location. 2km rim trail, 100m-deep gorge. 1.5 hrs. Microspikes.","https://guidetoiceland.is/travel-iceland/drive/fjadrargljufur",10,"Kirkjubæjarklaustur", False, 90),
    ("Kirkjugolf",63.7875,-17.9959,2,"attraction","'Church Floor' — hexagonal basalt columns. 5-min walk.","https://guidetoiceland.is/travel-iceland/drive/kirkjugolfid",12,"Kirkjubæjarklaustur", False, 15),
    ("Systrafoss",63.7835,-17.9745,2,"attraction","Twin cascades above Kirkjubæjarklaustur. 30-min walk.","https://guidetoiceland.is/travel-iceland/drive/systrafoss",12,"Kirkjubæjarklaustur", False, 30),
    ("Svartifoss + Sjónarnipa Loop",64.0274,-16.9753,2,"hike","🥾 HIKE #1: 7.4 km, ~3 hrs. Basalt-column waterfall → Sjónarnipa glacier viewpoint → Sel turf house. Microspikes.\n\n🏕️ OVERNIGHT: Skaftafell Campsite (Vatnajökull NP, year-round).","https://guidetoiceland.is/travel-iceland/drive/svartifoss",14,"Skaftafell", False, 180),

    # ---- Day 3: Skaftafell to Höfn & East ----
    ("Svínafellsjökull",64.008,-16.875,3,"attraction","🐉 GoT: North of the Wall (S2–S3). Walk to glacier snout. 45 min.","https://guidetoiceland.is/travel-iceland/drive/svinafellsjokull",9,"Skaftafell", False, 45),
    ("Fjallsárlón",64.0167,-16.3667,3,"attraction","Quieter glacier lagoon with icebergs. 45 min.","https://guidetoiceland.is/travel-iceland/drive/fjallsarlon",10,"Jökulsárlón", False, 45),
    ("Jökulsárlón",64.0784,-16.2297,3,"attraction","Floating icebergs, possible seals. Crown jewel lagoon. 1 hr.","https://guidetoiceland.is/travel-iceland/drive/jokulsarlon",11,"Jökulsárlón", False, 60),
    ("Diamond Beach",64.044,-16.178,3,"attraction","Translucent ice on jet-black sand. 30 min.","https://guidetoiceland.is/travel-iceland/drive/diamond-beach",12,"Jökulsárlón", False, 30),
    ("Hofskirkja",64.1978,-15.9418,3,"attraction","Last surviving turf-roofed church. 15-min detour.","https://guidetoiceland.is/travel-iceland/drive/hofskirkja",13,"Höfn", False, 15),
    ("Hafnarbuðin (lunch)",64.254,-15.21,3,"food","🍽️ Langoustine baguette ~1,800 ISK (~$13). Cheapest langoustine in town. Free coffee.",None,13,"Höfn", False, 60),
    ("Stokksnes / Vestrahorn",64.249,-14.965,3,"attraction","Iconic mountain + black sand + Viking set. 💰 1,100 ISK/pp.","https://guidetoiceland.is/travel-iceland/drive/stokksnes",15,"Stokksnes", False, 90),
    ("Eystrahorn",64.319,-14.694,3,"attraction","Turnaround point. Walk the black sand base. 1 hr.","https://adventures.is/iceland/attractions/eystrahorn/",16,"Stokksnes", False, 60),
    ("Höfn 🏕️",64.2539,-15.2081,3,"overnight","🏕️ OVERNIGHT: Höfn Campsite – Hamrar. Year-round.",None,19,"Höfn", True, 0),

    # ---- Day 4: Höfn to Skaftafell & Selfoss ----
    ("Kristínartindar Summit",64.0169,-16.9669,4,"hike","🥾 HIKE #2: 17.9 km loop, ~6–8 hrs, summit 1,126m. 360° Vatnajökull panorama. Full winter gear. Backup: Skaftafellsheiði plateau.","https://adventures.is/iceland/attractions/kristinartindar/",10,"Skaftafell", False, 480),
    ("Núpsstaurskógur",63.9372,-17.505,4,"attraction","Iceland's largest native birch forest. 30-min walk.","https://guidetoiceland.is/travel-iceland/drive/nupsstadaskogur",15,"Kirkjubæjarklaustur", False, 30),
    ("Lómagnúpur",63.8971,-17.645,4,"attraction","Sheer 767m wall. ⚠️ Notorious sudden gusts.","https://guidetoiceland.is/travel-iceland/drive/lomagnupur",15,"Kirkjubæjarklaustur", False, 15),
    ("Þingborg Wool Shop 🧶",63.9333,-20.8167,4,"shop","🧶 Since 1991. Handknit lopapeysa, Icelandic sheep's wool. Tax-free receipt (15% VAT at KEF). 📍 Route 1, 8 km east of Selfoss.","https://www.south.is/en/service/thingborg-wool-processing",18,"Selfoss", False, 30),
    ("Selfoss 🏕️",63.9332,-21.003,4,"overnight","🏕️ OVERNIGHT: Selfoss Campsite. Year-round. Bónus, N1, pool.",None,19,"Selfoss", True, 0),

    # ---- Day 5: Golden Circle to KEF ----
    ("Þingvellir",64.2559,-21.1299,5,"attraction",
     "Tectonic rift valley. Almannagjá gorge, Öxarárfoss. 1.5–2 hrs.",
     "https://guidetoiceland.is/travel-iceland/drive/thingvellir", 8, "Þingvellir", True, 120),
    ("Þórufoss (optional)",64.2833,-21.0667,5,"attraction",
     "🐉 GoT S4E6: Drogon torches a goatherd's flock. Quiet 18m waterfall. ⚠️ Route 48 is gravel, may be icy — check road.is.",
     "https://guidetoiceland.is/travel-iceland/drive/thorufoss", 8, "Þingvellir", False, 30),
    ("Geysir",64.3103,-20.3024,5,"attraction",
     "Strokkur erupts every 5-10 mins. Active geothermal field. 1 hr.",
     "https://guidetoiceland.is/travel-iceland/drive/geysir", 10, "Geysir", False, 60),
    ("Gullfoss",64.3271,-20.1199,5,"attraction",
     "Massive two-tier waterfall. 45 mins. 10 min drive from Geysir.",
     "https://guidetoiceland.is/travel-iceland/drive/gullfoss", 11, "Geysir", False, 45),
    ("Hallgrímskirkja",64.1417,-21.9267,5,"attraction",
     "Reykjavík's iconic church tower.", None, 13, "Reykjavík", False, 30),
    ("Smékkleysa Records",64.1435,-21.928,5,"attraction",
     "🎵 Björk's Sugarcubes label. Record shop + coffee. 25–30 min.","https://www.instagram.com/smekkleysa/",13,"Reykjavík", False, 30),
    ("Harpa Concert Hall",64.1505,-21.9327,5,"attraction",
     "Geometric glass facade. Free lobby. Tours 2,750 ISK.","https://www.harpa.is/en",14,"Reykjavík", False, 30),
    ("Sun Voyager",64.1476,-21.9223,5,"attraction",
     "Iconic steel ship sculpture. Quick photo.","https://guidetoiceland.is/travel-iceland/drive/sun-voyager",15,"Reykjavík", False, 15),
    ("Icelandic Street Food",64.147,-21.931,5,"food",
     "Quick lamb soup in bread bowls or plokkfiskur before the airport.", None, 14, "Reykjavík", False, 60),
    ("KEF Departure ✈️",63.985,-22.6056,5,"logistics",
     "Return campervan exactly as scheduled. Depart 05:00 pm (Flight FI643 to BWI). Check-in ~2 hours prior.", None, 17, "KEF / Reykjanes", True, 0),
]

# ═══════════════════════ PARKING ═══════════════════════
# (parking_lat, parking_lon, notes)  — where you actually park the campervan
PARKING = {
    "KEF Airport":          (63.9857,-22.6230, "KEF rental car return / pickup area"),
    "Hveragerði":           (63.9966,-21.1876, "Town centre parking, free"),
    "Reykjadalur Hot River":(64.0193,-21.2116, "Reykjadalur trailhead car park, free"),
    "Seljalandsfoss":       (63.6154,-19.9907, "Seljalandsfoss main car park"),
    "Gljúfrabúi":           (63.6154,-19.9907, "Same lot as Seljalandsfoss — 500m walk"),
    "Skógafoss":            (63.5297,-19.5113, "Skógafoss car park at base of falls"),
    "Dyrhólaey":            (63.4035,-19.1330, "Dyrhólaey lower car park (upper may close in wind)"),
    "Reynisfjara":          (63.4037,-19.0664, "Reynisfjara beach car park by café"),
    "Súður-Vík (dinner)":   (63.4190,-19.0080, "Street parking in Vík village"),
    "Vík 🏕️":              (63.4186,-19.0060, "Vík Campsite, Víkurbraut 5"),
    "Eldhraun Lava Field":  (63.6700,-18.3200, "Roadside pullout on Route 1"),
    "Fjaðrárgljúfur Canyon":(63.7712,-18.1720, "Fjaðrárgljúfur car park off Route 1"),
    "Kirkjugolf":           (63.7890,-17.9959, "Small car park by church, Kirkjubæjarklaustur"),
    "Systrafoss":           (63.7850,-17.9745, "Kirkjubæjarklaustur village parking"),
    "Svartifoss + Sjónarnipa Loop":(64.0169,-16.9669, "Skaftafell Visitor Centre car park"),
    "Svínafellsjökull":     (64.0080,-16.8810, "Svínafellsjökull car park off Route 1"),
    "Fjallsárlón":          (64.0167,-16.3750, "Fjallsárlón car park"),
    "Jökulsárlón":          (64.0480,-16.1790, "Jökulsárlón main car park (east side)"),
    "Diamond Beach":        (64.0440,-16.1780, "Diamond Beach car park (south side of bridge)"),
    "Hofskirkja":           (64.1978,-15.9418, "Roadside pullout at church"),
    "Hafnarbuðin (lunch)":  (64.2540,-15.2100, "Höfn harbour parking"),
    "Stokksnes / Vestrahorn":(64.2530,-14.9700, "Viking Café car park (pay 1,100 ISK)"),
    "Eystrahorn":           (64.3190,-14.6940, "Roadside pullout / gravel track end"),
    "Höfn 🏕️":             (64.2539,-15.2081, "Höfn Campsite – Hamrar"),
    "Kristínartindar Summit":(64.0169,-16.9669, "Skaftafell Visitor Centre car park"),
    "Núpsstaurskógur":      (63.9372,-17.5050, "Roadside pullout on Route 1"),
    "Lómagnúpur":           (63.8971,-17.6450, "Roadside viewpoint pullout"),
    "Þingborg Wool Shop 🧶":(63.9333,-20.8167, "Parking at shop on Route 1"),
    "Selfoss 🏕️":          (63.9332,-21.0030, "Selfoss Campsite"),
    "Þingvellir":           (64.2559,-21.1187, "Þingvellir P1 car park, 💰 750 ISK"),
    "Þórufoss (optional)":  (64.2833,-21.0667, "Small pullout by waterfall"),
    "Geysir":               (64.3103,-20.3024, "Geysir car park, 💰 1,000 ISK"),
    "Gullfoss":             (64.3260,-20.1270, "Gullfoss upper car park, free"),
    "Hallgrímskirkja":      (64.1400,-21.9280, "Skólavörðustígur street parking / P1 zone"),
    "Smékkleysa Records":   (64.1400,-21.9280, "Same Reykjavík parking — walk"),
    "Harpa Concert Hall":   (64.1400,-21.9280, "Same Reykjavík parking — walk"),
    "Sun Voyager":          (64.1400,-21.9280, "Same Reykjavík parking — walk"),
    "Icelandic Street Food":(64.1400,-21.9280, "Same Reykjavík parking — walk"),
    "KEF Departure ✈️":     (63.9857,-22.6230, "KEF Airport Departure Terminal"),
}

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
        "weather_loc":"Skaftafell","est_hour":10,
        "link":"https://guidetoiceland.is/travel-iceland/drive/skaftafell",
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
        "weather_loc":"Þingvellir","est_hour":8,
        "link":"https://guidetoiceland.is/travel-iceland/drive/thorufoss",
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
        "weather_loc":"Vík","est_hour":16,
        "link":"https://guidetoiceland.is/travel-iceland/drive/dyrholaey",
        "waypoints":[
            (63.4022,-19.1289),(63.3990,-19.1250),(63.3970,-19.1220),
        ],
    },
]

# ═══════════════════════ WEATHER ═══════════════════════
def fetch_weather():
    locs = {}
    for s in STOPS:
        wl = s[8]
        if wl not in locs: locs[wl] = (s[1], s[2])
        
    if os.path.exists(WEATHER_CACHE):
        age_seconds = time.time() - os.path.getmtime(WEATHER_CACHE)
        if age_seconds < CACHE_MAX_AGE_HOURS * 3600:
            try:
                with open(WEATHER_CACHE) as f: cached_data = json.load(f)
                # Check if all required locations are currently in the cache
                if all(loc in cached_data for loc in locs):
                    print(f"✓ Weather loaded from cache (expires in {int((CACHE_MAX_AGE_HOURS * 3600 - age_seconds) / 60)} min).")
                    return cached_data
                else:
                    print("⟳ Weather cache missing some locations — fetching fresh data...")
            except: pass
        else:
            print("⟳ Weather cache expired — fetching fresh data...")

    for s in STOPS:
        wl = s[8]
        if wl not in locs: locs[wl] = (s[1], s[2])
    print("Fetching weather from Open-Meteo...")
    out = {}
    for name,(lat,lon) in locs.items():
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
               f"&hourly=temperature_2m,apparent_temperature,precipitation,weathercode,windspeed_10m,windgusts_10m"
               f"&daily=sunrise,sunset"
               f"&start_date=2026-03-06&end_date=2026-03-10&timezone=Atlantic/Reykjavik")
        try:
            r = requests.get(url, timeout=15).json()
            if "hourly" in r: out[name] = {"hourly": r["hourly"], "daily": r.get("daily", {})}; print(f"  ✓ {name}")
        except: pass
        time.sleep(0.3)
    with open(WEATHER_CACHE,"w") as f: json.dump(out, f)
    return out

def get_wx(wd, wloc, day, hour):
    if wloc not in wd: return None
    h = wd[wloc].get("hourly"); t = f"{DAY_DATES[day]}T{hour:02d}:00"
    if not h: return None
    try: i = h["time"].index(t)
    except ValueError: return None
    tc = h["temperature_2m"][i]; fc = h["apparent_temperature"][i]
    desc,emoji = WMO.get(h["weathercode"][i], ("Unknown","❓"))
    return {"tc":tc,"tf":round(tc*9/5+32,1),"fc":fc,"ff":round(fc*9/5+32,1),
            "p":h["precipitation"][i],"w":h["windspeed_10m"][i],"g":h["windgusts_10m"][i],
            "desc":desc,"emoji":emoji,"hour":hour}

def get_sun_hours(wd, wloc, day):
    if wloc not in wd: return None, None
    d = wd[wloc].get("daily")
    if not d: return None, None
    try: 
        i = d["time"].index(DAY_DATES[day])
        sr = int(d["sunrise"][i].split("T")[1].split(":")[0])
        ss = int(d["sunset"][i].split("T")[1].split(":")[0])
        return sr, ss
    except: return None, None

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
    import hashlib
    routes_cache_data = {}
    if os.path.exists(ROUTE_CACHE):
        try:
            with open(ROUTE_CACHE) as f: routes_cache_data = json.load(f)
        except: pass
    print("Fetching routes from Valhalla (with hash caching)...")
    routes = {}
    for day in range(1,6):
        # Use parking coordinates for routing (where you actually drive to)
        pts = []
        ns = []
        for name,la,lo,d,*_ in STOPS:
            if d != day: continue
            p = PARKING.get(name)
            coord = (p[0], p[1]) if p else (la, lo)
            # Skip duplicate consecutive coords (shared parking lots)
            if not pts or (round(coord[0],4), round(coord[1],4)) != (round(pts[-1][0],4), round(pts[-1][1],4)):
                pts.append(coord)
            ns.append(name)
        print(f"  Day {day}: {ns[0]} → {ns[-1]} ({len(pts)} stops)")
        day_hash = hashlib.md5(str(pts).encode('utf-8')).hexdigest()
        if day_hash in routes_cache_data:
            routes[day] = routes_cache_data[day_hash]
            print(f"    ✓ Loaded from cache (hash: {day_hash[:8]})")
            continue
            
        # Split long routes into overlapping chunks to avoid Valhalla timeouts
        if len(pts) <= 6:
            res = valhalla_route(pts)
            if res: routes[day]=res[0]; routes_cache_data[day_hash]=res[0]; print(f"    ✓ {len(res[0])} pts, {res[1]:.0f} km")
            else: routes[day]=pts; print(f"    ⚠ fallback")
        else:
            all_coords = []
            total_km = 0
            chunk_size = 5
            ok = True
            for i in range(0, len(pts)-1, chunk_size-1):
                chunk = pts[i:i+chunk_size]
                if len(chunk) < 2: break
                res = valhalla_route(chunk)
                if res:
                    cc = res[0]
                    if all_coords and cc and all_coords[-1]==cc[0]: cc=cc[1:]
                    all_coords.extend(cc)
                    total_km += res[1]
                else:
                    ok = False; break
                time.sleep(0.5)
            if ok and all_coords:
                routes[day]=all_coords; routes_cache_data[day_hash]=all_coords; print(f"    ✓ {len(all_coords)} pts, {total_km:.0f} km (chunked)")
            else:
                routes[day]=pts; print(f"    ⚠ fallback")
        time.sleep(1)
    with open(ROUTE_CACHE,"w") as f: json.dump(routes_cache_data, f)
    return routes

# ═══════════════════════ MAP ═══════════════════════
def popup_html(name, day, stype, notes, link, wx, lat=None, lon=None):
    c = DAY_COLORS[day]
    h = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:300px;width:calc(100vw - 80px);line-height:1.5;">
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
        links_parts.append(f'<a href="{link}" target="_blank" style="color:{c};text-decoration:none;font-size:13px;font-weight:600;padding:4px 0;">📖 Visitor Guide →</a>')
    if lat is not None and lon is not None:
        gmap = f"https://www.google.com/maps?q={lat},{lon}"
        links_parts.append(f'<a href="{gmap}" target="_blank" style="color:{c};text-decoration:none;font-size:13px;font-weight:600;padding:4px 0;">📍 Map</a>')
    if links_parts:
        h+=f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;display:flex;gap:16px;flex-wrap:wrap;">{"".join(links_parts)}</div>'
    return h+"</div>"

def trail_popup(t):
    h=f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:280px;width:calc(100vw - 80px);line-height:1.5;">
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
    pkg = FeatureGroup(name="🅿️ Parking", show=False)

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
    for name,lat,lon,day,st,notes,link,hr,wl,is_immune,dur in STOPS:
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

    # Parking markers (deduplicated by coords)
    seen_parking = set()
    for name,lat,lon,day,st,notes,link,hr,wl,is_immune,dur in STOPS:
        p = PARKING.get(name)
        if not p: continue
        plat, plon, pnotes = p
        coord_key = (round(plat,4), round(plon,4))
        if coord_key in seen_parking: continue
        seen_parking.add(coord_key)
        # Find all stops sharing this parking
        shared = [n for n,*_ in STOPS if PARKING.get(n) and (round(PARKING[n][0],4), round(PARKING[n][1],4)) == coord_key]
        gmap = f"https://www.google.com/maps?q={plat},{plon}"
        dc = DAY_COLORS.get(day, "#666")
        ph = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:280px;width:calc(100vw - 80px);line-height:1.5;">
        <div style="background:#2E7D32;color:white;padding:8px 12px;border-radius:6px 6px 0 0;margin:-13px -20px 10px -20px;">
          <strong style="font-size:14px;">🅿️ Parking</strong><br>
          <span style="font-size:11px;opacity:0.9;">{DAY_LABELS[day]}</span>
        </div>
        <div style="font-size:12px;color:#333;margin-bottom:6px;"><b>{'</b>, <b>'.join(shared)}</b></div>
        <div style="font-size:12px;color:#555;">{pnotes}</div>
        <div style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;"><a href="{gmap}" target="_blank" style="color:#2E7D32;text-decoration:none;font-size:13px;font-weight:600;padding:4px 0;">📍 Navigate to Parking</a></div>
        </div>"""
        Marker(location=[plat,plon],
               tooltip=f"🅿️ Parking: {shared[0]}",
               icon=Icon(color="green",icon="square-parking",prefix="fa"),
               popup=Popup(ph, max_width=320)).add_to(pkg)
    pkg.add_to(m)

    # Alternative routes
    for ar in ALT_ROUTES:
        day = ar['day']
        c = ALT_COLOR
        lat, lon = ar['waypoints'][0]
        wx = get_wx(weather, ar['weather_loc'], day, ar['est_hour'])
        gmap = f"https://www.google.com/maps?q={lat},{lon}"

        ar_html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:300px;width:calc(100vw - 80px);line-height:1.5;">
        <div style="background:{c};color:white;padding:8px 12px;border-radius:6px 6px 0 0;margin:-13px -20px 10px -20px;">
          <strong style="font-size:14px;">🔀 {ar['name']}</strong><br>
          <span style="font-size:11px;opacity:0.9;">{DAY_LABELS[day]} · {ar['distance']} · {ar['time']}</span>
        </div>"""

        # Weather block
        if wx:
            w = wx
            ar_html += f"""<div style="background:#f0f4f8;border-radius:6px;padding:8px 10px;margin-bottom:8px;font-size:12px;border-left:3px solid {c};">
          <div style="font-weight:600;margin-bottom:4px;">{w['emoji']} {w['desc']} at ~{w['hour']}:00</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:11px;color:#555;">
            <span>🌡️ {w['tc']:.0f}°C / {w['tf']:.0f}°F</span><span>🥶 Feels {w['fc']:.0f}°C / {w['ff']:.0f}°F</span>
            <span>💨 Wind {w['w']:.0f} km/h</span><span>💨 Gusts {w['g']:.0f} km/h</span>
            <span>🌧️ Precip {w['p']:.1f} mm</span>
          </div></div>"""

        # Trigger condition
        ar_html += f"""<div style="background:#fff3cd;border-radius:6px;padding:8px 10px;margin-bottom:8px;font-size:12px;border-left:3px solid #ffc107;">
          <div style="font-weight:600;">{ar['trigger']}</div>
        </div>"""

        # Notes
        ar_html += f'<div style="font-size:12px;color:#333;white-space:pre-wrap;">{ar["notes"]}</div>'

        # Links: Visitor Guide + Google Maps
        links_parts = []
        if ar.get('link'):
            links_parts.append(f'<a href="{ar["link"]}" target="_blank" style="color:{c};text-decoration:none;font-size:12px;font-weight:600;">📖 Visitor Guide →</a>')
        links_parts.append(f'<a href="{gmap}" target="_blank" style="color:{c};text-decoration:none;font-size:12px;font-weight:600;">📍 Map</a>')
        links_joined = "\n".join(links_parts)
        ar_html += f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #eee;display:flex;gap:16px;">{links_joined}</div>'
        ar_html += '</div>'

        PolyLine(locations=ar["waypoints"], color=ALT_COLOR, weight=3, opacity=0.8, dash_array="10 8",
                 tooltip=f"<b>🔀 {ar['name']}</b><br>{ar['trigger']}",
                 popup=Popup(ar_html, max_width=340)).add_to(altg)
        Marker(location=ar["waypoints"][0],
               tooltip=f"🔀 {ar['name']} — Start",
               icon=Icon(color="lightblue",icon="arrows-split-up-and-left",prefix="fa"),
               popup=Popup(ar_html, max_width=340)).add_to(altg)
    altg.add_to(m)
    LayerControl(collapsed=True).add_to(m)
    LocateControl(position="topleft", strings={"title": "See my location"}).add_to(m)

    title = """<div id="map-title" style="position:fixed;top:10px;left:55px;z-index:1000;background:white;padding:10px 18px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:calc(100vw - 120px);">
    <div style="font-size:16px;font-weight:700;color:#2E5B8A;">🇮🇸 Iceland Road Trip — Interactive Map</div>
    <div class="title-sub" style="font-size:12px;color:#666;margin-top:2px;">March 6–10, 2026 · 5 Days · ~1,200 km · Live weather forecast</div>
    <div class="title-legend" style="font-size:10px;color:#999;margin-top:4px;">🏕️ Camp  🥾 Hike  🍽️ Food  🧶 Shop  📷 Attraction  ✈️ Logistics  🐉 GoT  🔀 Alt  🅿️ P</div>
    <div class="title-credits" style="font-size:9px;color:#bbb;margin-top:3px;">Roads: Valhalla/OSM · Weather: Open-Meteo ·
    <span style="color:#FF6B35;">━ ━ ━</span> Hiking trails · <span style="color:#4A90D9;">━ ━ ━</span> Alt routes · Toggle layers ↗</div></div>"""
    m.get_root().html.add_child(folium.Element(title))

    # Responsive CSS for mobile + desktop
    responsive_css = """<style>
    /* Layer control */
    .leaflet-control-layers-overlays {
        max-height: 400px;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
    }
    /* Mobile-friendly popup scrolling */
    .leaflet-popup-content {
        -webkit-overflow-scrolling: touch;
        touch-action: pan-y;
    }
    /* Popup close button — larger touch target */
    .leaflet-popup-close-button {
        font-size: 22px !important;
        width: 30px !important;
        height: 30px !important;
        padding: 4px !important;
    }
    /* Mobile: screens under 600px */
    @media (max-width: 600px) {
        /* Compact title bar */
        #map-title {
            left: 10px !important;
            top: 6px !important;
            padding: 6px 12px !important;
            max-width: calc(100vw - 70px) !important;
        }
        #map-title > div:first-child {
            font-size: 13px !important;
        }
        .title-sub {
            font-size: 10px !important;
        }
        .title-legend, .title-credits {
            display: none !important;
        }
        /* Layer control compact */
        .leaflet-control-layers {
            max-width: 200px;
        }
        .leaflet-control-layers-overlays {
            max-height: 250px;
            font-size: 11px;
        }
        .leaflet-control-layers label {
            margin-bottom: 2px;
        }
        /* Popup sizing */
        .leaflet-popup-content-wrapper {
            max-width: calc(100vw - 40px) !important;
        }
        .leaflet-popup-content {
            margin: 10px 12px !important;
            max-width: calc(100vw - 70px) !important;
        }
        /* Larger markers for touch */
        .leaflet-marker-icon {
            transform-origin: center bottom;
        }
    }
    /* Middle screens: tablets */
    @media (min-width: 601px) and (max-width: 1024px) {
        #map-title {
            max-width: 400px !important;
        }
        .title-credits {
            display: none !important;
        }
    }
    </style>"""
    m.get_root().html.add_child(folium.Element(responsive_css))

    # ═══════════════════════ AGENDA VIEW ═══════════════════════
    # Pre-render all cards server-side (no client-side JS templating)
    TYPE_ICONS = {"overnight":"🏕️","hike":"🥾","food":"🍽️","shop":"🧶","logistics":"✈️","attraction":"📷"}

    # Build alt route lookup by main stop name
    alt_lookup = {}
    for ar in ALT_ROUTES:
        if ar["day"] == 4 and "Skaftafellsheiði" in ar["name"]: alt_lookup["Kristínartindar Summit"] = ar
        if ar["day"] == 5 and "Þórufoss" in ar["name"]: alt_lookup["Þingvellir"] = ar
        if ar["day"] == 1 and "Dyrhólaey" in ar["name"]: alt_lookup["Dyrhólaey"] = ar

    def _trunc_notes(notes, c):
        if len(notes) > 130:
            short_n = notes[:125].rsplit(" ", 1)[0] + "..."
            short_n = short_n.replace("\n", "<br>")
            full_n = notes.replace("\n", "<br>")
            return f"""<span style="display:inline">{short_n} </span><a href="#" onclick="this.previousElementSibling.style.display='none';this.nextElementSibling.style.display='inline';this.style.display='none';return false;" style="color:{c};font-weight:600;text-decoration:none;">Read More ↓</a><span style="display:none">{full_n} <a href="#" onclick="var p=this.parentElement;p.style.display='none';p.previousElementSibling.style.display='inline';p.previousElementSibling.previousElementSibling.style.display='inline';return false;" style="color:#666;text-decoration:none;">Hide ↑</a></span>"""
        return notes.replace("\n", "<br>")

    def _card(name, day, st, notes, link, wx, lat, lon, hr, parking, is_got):
        # We find duration & immune dynamically from STOPS array based on name
        dur = 60
        immune = "false"
        for s in STOPS:
            if s[0] == name:
                immune = "true" if s[9] else "false"
                dur = s[10]
                break
                
        c = DAY_COLORS[day]
        icon = TYPE_ICONS.get(st, "📷")
        tstr = f"{hr:02d}:00"
        gmap = f"https://www.google.com/maps?q={lat},{lon}"
        ga = "true" if is_got else "false"
        
        is_skip = "true" if any(k in name for k in ["Reykjadalur", "Dyrhólaey", "Þórufoss", "Kerið"]) else "false"
        sid = f"d{day}h{hr}"
        
        h = f'<div class="sc" id="{sid}" data-id="{sid}" data-day="{day}" data-type="{st}" data-hour="{hr}" data-got="{ga}" data-skip="{is_skip}" data-immune="{immune}" data-dur="{dur}" style="border-left-color:{c}">'
        h += f'<div style="display:flex;align-items:baseline;gap:10px;justify-content:space-between;width:100%">'
        h += f'<div style="display:flex;align-items:baseline;gap:10px"><div class="st">{tstr}</div>'
        h += f'<div><span class="sn">{icon} {name}</span><br><span class="stp">{st}</span></div></div>'
        if immune == "false":
            h += f'<button class="stog" onclick="togSkip(\'{sid}\', event)" style="background:transparent;border:1px solid #ddd;color:#666;border-radius:6px;padding:4px 8px;font-size:11px;cursor:pointer;height:24px;">➖ Remove</button>'
        h += '</div>'

        if wx:
            h += f'<div class="sw" style="border-left:3px solid {c}">'
            h += f'<div style="grid-column:1/-1;font-weight:600;margin-bottom:2px">{wx["emoji"]} {wx["desc"]} at ~{wx["hour"]}:00</div>'
            h += f'<span>🌡️ {wx["tc"]:.0f}°C / {wx["tf"]:.0f}°F</span><span>🥶 Feels {wx["fc"]:.0f}°C / {wx["ff"]:.0f}°F</span>'
            h += f'<span>💨 Wind {wx["w"]:.0f} km/h</span><span>💨 Gusts {wx["g"]:.0f} km/h</span>'
            h += f'<span>🌧️ {wx["p"]:.1f} mm</span></div>'

        sn = _trunc_notes(notes, c)
        h += f'<div class="snt">{sn}</div>'
        h += '<div class="sl">'
        if link: h += f'<a href="{link}" target="_blank" style="color:{c}">📖 Guide →</a>'
        h += f'<a href="{gmap}" target="_blank" style="color:{c}">📍 Map</a>'
        if parking:
            pg = f"https://www.google.com/maps?q={parking[0]},{parking[1]}"
            h += f'<a href="{pg}" target="_blank" style="color:#2E7D32">🅿️ Parking</a>'
        h += '</div></div>'
        return h

    def _alt_card(ar):
        wx = get_wx(weather, ar["weather_loc"], ar["day"], ar["est_hour"])
        gmap = f"https://www.google.com/maps?q={ar['waypoints'][0][0]},{ar['waypoints'][0][1]}"
        
        is_skip = "true" if any(k in ar["name"] for k in ["Reykjadalur", "Dyrhólaey", "Þórufoss", "Kerið"]) else "false"
        sid = f"a{ar['day']}h{ar['est_hour']}"
        
        # Parse duration string roughly to minutes (e.g. "1 hr 15 mins" -> 75, "1.5 hrs" -> 90, "30 min" -> 30)
        dur = 60
        ts = str(ar.get("time","")).lower()
        if "min" in ts and "hr" not in ts:
            dur = int(''.join(filter(str.isdigit, ts)) or 30)
        elif "hr" in ts:
            import re
            m = re.match(r'(?:(\d+)\s*hr)?\s*(?:(\d+)\s*min)?', ts)
            if m: dur = int(m.group(1) or 0)*60 + int(m.group(2) or 0)
        if dur == 0: dur = 60

        h = f'<div class="sc ac" id="{sid}" data-id="{sid}" data-day="{ar["day"]}" data-hour="{ar["est_hour"]}" data-skip="{is_skip}" data-immune="false" data-dur="{dur}">'
        h += f'<div style="display:flex;justify-content:space-between;align-items:start;"><div class="ab">🔀 ALTERNATIVE / DETOUR</div>'
        h += f'<button class="stog" onclick="togSkip(\'{sid}\', event)" style="background:transparent;border:1px solid #4A90D9;color:#4A90D9;border-radius:6px;padding:4px 8px;font-size:11px;cursor:pointer;">➖ Remove</button></div>'
        h += f'<div class="sn">🔀 {ar["name"]}</div>'
        h += f'<div class="stp">{ar["distance"]} · {ar["time"]}</div>'
        if wx:
            h += '<div class="sw" style="border-left:3px solid #4A90D9">'
            h += f'<div style="grid-column:1/-1;font-weight:600;margin-bottom:2px">{wx["emoji"]} {wx["desc"]}</div>'
            h += f'<span>🌡️ {wx["tc"]:.0f}°C / {wx["tf"]:.0f}°F</span>'
            h += f'<span>💨 Wind {wx["w"]:.0f} km/h</span></div>'
        sn = _trunc_notes(ar["notes"], "#4A90D9")
        h += f'<div class="snt">{sn}</div>'
        h += '<div class="sl">'
        if ar.get("link"): h += f'<a href="{ar["link"]}" target="_blank" style="color:#4A90D9">📖 Guide →</a>'
        h += f'<a href="{gmap}" target="_blank" style="color:#4A90D9">📍 Map</a>'
        h += '</div></div>'
        return h

    # Build timeline cards
    tl = ""
    # Day Cards
    for i in range(1, 6):
        tl += f'<div class="dh" data-day="{i}"><div class="dd" style="background:{DAY_COLORS[i]}"></div>Day {i}</div>'
        
        # Inject alt routes for the day before normal stops
        for d in ALT_ROUTES:
            if d["day"] == i and d["est_hour"] < 12:
                tl += _alt_card(d)

        for name,lat,lon,day,st,notes,link,hr,wl,is_immune,dur in STOPS:
            if day == i:
                wx = get_wx(weather, wl, day, hr)
                park = PARKING.get(name, "")
                is_got = "\U0001F409" in notes # Check if dragon emoji is in notes for GoT
                
                # Check for alt routes at same hour
                has_alt = False
                if name in alt_lookup:
                    ac = alt_lookup[name]
                    tl += f'<div class="ar">{_card(name, day, st, notes, link, wx, lat, lon, hr, park, is_got)}{_alt_card(ac)}</div>'
                    has_alt = True
                
                if not has_alt:
                    tl += _card(name, day, st, notes, link, wx, lat, lon, hr, park, is_got)

    dd_js = "{" + ",".join(f'{k}:"{v}"' for k,v in DAY_DATES.items()) + "}"

    agenda_el = f"""
    <div id="vtog">
      <button id="bm" onclick="sv('map')">🗺️ Map</button>
      <button id="ba" onclick="sv('agenda')">📋 Itinerary</button>
    </div>
    <div id="av">
      <div class="ah"><div style="font-size:22px;font-weight:700">🇮🇸 Iceland South Coast</div>
        <div style="font-size:13px;opacity:0.8;margin-top:4px">March 6–10, 2026 · 5 Days · ~1,200 km</div></div>
      <div id="af">
        <button class="fp active" data-f="all" onclick="tf(this)">All</button>
        <button class="fp active" data-f="d1" onclick="tf(this)" style="border-color:#E63946;color:#E63946">Day 1</button>
        <button class="fp active" data-f="d2" onclick="tf(this)" style="border-color:#457B9D;color:#457B9D">Day 2</button>
        <button class="fp active" data-f="d3" onclick="tf(this)" style="border-color:#2A9D8F;color:#2A9D8F">Day 3</button>
        <button class="fp active" data-f="d4" onclick="tf(this)" style="border-color:#D4A017;color:#D4A017">Day 4</button>
        <button class="fp active" data-f="d5" onclick="tf(this)" style="border-color:#7B2D8E;color:#7B2D8E">Day 5</button>
        <button class="fp active" data-f="hike" onclick="tf(this)">🥾 Hikes</button>
        <button class="fp active" data-f="food" onclick="tf(this)">🍽️ Food</button>
        <button class="fp active" data-f="got" onclick="tf(this)">🐉 GoT</button>
      </div>
      <div id="atl">{tl}</div>
      <div style="padding:20px;text-align:center;font-size:11px;color:#999">Weather: Open-Meteo · Routes: Valhalla/OSM · All times Iceland (UTC+0)</div>
      
      <!-- Overtime / Delay Tracking UI -->
      <div id="d-fab" onclick="togMenu()" style="position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:28px;background:#E63946;color:white;display:flex;align-items:center;justify-content:center;font-size:32px;box-shadow:0 4px 16px rgba(230,57,70,0.4);cursor:pointer;z-index:100;transition:transform 0.2s;">+</div>
      <div id="d-menu" style="display:none;position:fixed;bottom:90px;right:24px;background:white;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);padding:8px;z-index:99;flex-direction:column;gap:4px;">
        <button onclick="opAdd()" style="padding:12px 16px;border:none;background:transparent;text-align:left;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px;color:#333;">⏱ Add Delay / Stop</button>
        <button onclick="opRem()" style="padding:12px 16px;border:none;background:transparent;text-align:left;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px;color:#666;">Undo / Remove Delay</button>
      </div>

      <!-- Add Delay Modal -->
      <div id="d-add-mod" class="mod-ov" style="display:none;">
        <div class="mod-bx">
          <div style="font-size:18px;font-weight:700;margin-bottom:12px;">Add Weather Delay / Stop</div>
          <div style="font-size:13px;color:#666;margin-bottom:16px;">This will shift all remaining scheduled items today downwards.</div>
          
          <div style="display:flex;gap:12px;margin-bottom:12px;">
            <div style="flex:1">
              <label style="font-size:12px;font-weight:600;color:#555;">Day:</label>
              <select id="v-day" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:4px;">
                <option value="1">Day 1</option>
                <option value="2">Day 2</option>
                <option value="3">Day 3</option>
                <option value="4">Day 4</option>
                <option value="5">Day 5</option>
              </select>
            </div>
            <div style="flex:1">
              <label style="font-size:12px;font-weight:600;color:#555;">Start Time:</label>
              <select id="v-time" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:4px;">
                {"".join(f'<option value="{h}">{h:02d}:00</option>' for h in range(6, 24))}
              </select>
            </div>
          </div>

          <label style="font-size:12px;font-weight:600;color:#555;">Duration (minutes):</label><br>
          <div style="display:flex;gap:8px;margin-top:6px;margin-bottom:16px;">
            <button class="mbtn" onclick="setD(15)">15m</button>
            <button class="mbtn" onclick="setD(30)">30m</button>
            <button class="mbtn" onclick="setD(45)">45m</button>
            <button class="mbtn" onclick="setD(60)">1h</button>
            <input type="number" id="v-dur" style="width:70px;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;" value="15">
          </div>
          <label style="font-size:12px;font-weight:600;color:#555;">Reason (Optional):</label>
          <input type="text" id="v-rsn" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:6px;margin-bottom:20px;" placeholder="e.g., Road closure, extra photos...">
          <div style="display:flex;justify-content:flex-end;gap:12px;">
            <button onclick="clsMod()" style="padding:10px 16px;border:none;background:transparent;color:#666;font-weight:600;cursor:pointer;">Cancel</button>
            <button onclick="svDel()" style="padding:10px 20px;border:none;background:#2E5B8A;color:white;border-radius:8px;font-weight:600;cursor:pointer;">Apply Delay</button>
          </div>
        </div>
      </div>

      <!-- Remove Delay Modal -->
      <div id="d-rem-mod" class="mod-ov" style="display:none;">
        <div class="mod-bx">
          <div style="font-size:18px;font-weight:700;margin-bottom:12px;">Remove a Delay</div>
          <div id="v-del-list" style="max-height:200px;overflow-y:auto;margin-bottom:16px;font-size:13px;"></div>
          <div style="display:flex;justify-content:flex-end;">
            <button onclick="clsMod()" style="padding:10px 16px;border:none;background:#2E5B8A;color:white;border-radius:8px;font-weight:600;cursor:pointer;">Close</button>
          </div>
        </div>
      </div>

    </div>
    <style>
    #vtog{{position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:2000;display:flex;background:rgba(255,255,255,0.95);backdrop-filter:blur(12px);border-radius:24px;padding:3px;box-shadow:0 2px 12px rgba(0,0,0,0.15);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}}
    #vtog button{{padding:8px 20px;border:none;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.3s}}
    #vtog button:focus{{outline:none}}
    #bm{{background:#2E5B8A;color:white}}
    #ba{{background:transparent;color:#666}}
    #av{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;z-index:1500;background:#f8f9fb;overflow-y:auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}}
    .ah{{padding:60px 20px 12px;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);color:white;text-align:center}}
    #af{{padding:12px 16px;background:white;border-bottom:1px solid #e8eaed;display:flex;flex-wrap:wrap;gap:6px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.06)}}
    .fp{{padding:6px 14px;border:1.5px solid #ddd;border-radius:16px;font-size:12px;font-weight:500;cursor:pointer;background:white;color:#888;transition:all 0.2s}}
    .fp.active{{background:#f0f4ff;border-color:currentColor;font-weight:600}}
    .fp[data-f="all"].active{{background:#e8eaed;border-color:#666;color:#333}}
    #atl{{padding:16px;max-width:700px;margin:0 auto}}
    .dh{{display:flex;align-items:center;gap:12px;padding:16px 0 8px;margin-top:8px;font-size:15px;font-weight:700}}
    .dd{{width:14px;height:14px;border-radius:50%;flex-shrink:0}}
    .sc{{background:white;border-radius:12px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);border-left:4px solid #ddd;transition:all 0.2s}}
    .sc:hover{{box-shadow:0 3px 12px rgba(0,0,0,0.1);transform:translateY(-1px)}}
    .sc.now{{box-shadow:0 0 0 2px #2E5B8A,0 3px 12px rgba(46,91,138,0.2)}}
    .st{{font-size:13px;font-weight:700;color:#333;font-variant-numeric:tabular-nums;min-width:48px}}
    .sn{{font-size:14px;font-weight:600;color:#111}}
    .stp{{font-size:11px;color:#888;text-transform:capitalize}}
    .snt{{font-size:12px;color:#555;margin-top:6px;line-height:1.5}}
    .sw{{background:#f5f7fa;border-radius:8px;padding:8px 10px;margin-top:8px;font-size:11px;display:grid;grid-template-columns:1fr 1fr;gap:2px 10px}}
    .sl{{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;padding-top:8px;border-top:1px solid #f0f0f0}}
    .sl a{{font-size:12px;font-weight:600;text-decoration:none;padding:4px 0}}
    .ar{{display:flex;gap:10px;margin-bottom:10px}}
    .ar .sc{{flex:1;margin-bottom:0}}
    .ac{{background:#f0f6ff;border-color:#4A90D9}}
    .ab{{display:inline-block;font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;background:#ffc107;color:#333;margin-bottom:6px}}
    .mod-ov{{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.4);z-index:3000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}}
    .mod-bx{{background:white;border-radius:16px;padding:24px;width:90%;max-width:360px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}}
    .mbtn{{padding:8px 12px;background:#f0f4f8;border:1px solid #dde3ea;border-radius:6px;font-weight:600;color:#2E5B8A;cursor:pointer;flex:1}}
    .mbtn:hover{{background:#e2e8f0;border-color:#cbd5e1}}
    .d-itm{{display:flex;justify-content:space-between;align-items:center;background:#f9f9f9;padding:12px;border-radius:8px;margin-bottom:8px;border:1px solid #eee}}
    .rm-btn{{background:#ffebee;color:#c62828;border:none;padding:6px 12px;border-radius:6px;font-weight:600;cursor:pointer}}
    .time-adj{{color:#e63946;font-weight:700;font-size:11px;display:block;margin-top:2px}}
    .time-adj.time-sub{{color:#4caf50;}}
    .skip-rec{{background:#fff3cd;border-left:4px solid #ffc107;padding:10px 12px;border-radius:0 6px 6px 0;margin-bottom:12px;font-size:12px;font-weight:600;color:#856404;display:flex;align-items:center;gap:8px}}
    .sc.skipped {{ opacity: 0.5; filter: grayscale(1); }}
    .sc.skipped .sn, .sc.skipped .stp, .sc.skipped .snt {{ text-decoration: line-through; }}
    .sc.skipped .stog {{ color: #111 !important; border-color: #111 !important; }}
    @media(max-width:600px){{ #vtog{{top:auto;bottom:24px;}} #vtog button{{padding:6px 14px;font-size:12px;}}.ar{{flex-direction:column}}.sc{{padding:12px 14px}} #af{{padding:10px 12px}}}}
    </style>
    <script>
    var DD={dd_js};
    window.dels = JSON.parse(localStorage.getItem('ic_dels')) || [];
    window.skips = JSON.parse(localStorage.getItem('ic_skips')) || [];
    function togMenu(){{var m=document.getElementById('d-menu'); m.style.display=m.style.display==='none'?'flex':'none';}}
    
    function togSkip(sid, e) {{
       if(e) e.preventDefault();
       var idx = window.skips.indexOf(sid);
       if(idx === -1) window.skips.push(sid);
       else window.skips.splice(idx, 1);
       localStorage.setItem('ic_skips', JSON.stringify(window.skips));
       applyDelays();
    }}
    
    function opAdd(){{
      document.getElementById('d-menu').style.display='none'; 
      document.getElementById('d-add-mod').style.display='flex';
      var activeDay = 1;
      var dhs = document.querySelectorAll('.dh');
      for(var i=0; i<dhs.length; i++) {{ if(dhs[i].style.display !== 'none') {{ activeDay = parseInt(dhs[i].getAttribute('data-day')); break; }} }}
      document.getElementById('v-day').value = activeDay;
      var h = new Date().getUTCHours();
      if(h >= 6 && h <= 23) document.getElementById('v-time').value = h;
    }}
    function opRem(){{document.getElementById('d-menu').style.display='none'; buildRemList(); document.getElementById('d-rem-mod').style.display='flex';}}
    function clsMod(){{document.querySelectorAll('.mod-ov').forEach(m=>m.style.display='none');}}
    function setD(m){{document.getElementById('v-dur').value=m;}}
    
    function svDel(){{
      var mins = parseInt(document.getElementById('v-dur').value);
      var rsn = document.getElementById('v-rsn').value || 'Weather/Overtime';
      var day = parseInt(document.getElementById('v-day').value);
      var hr = parseInt(document.getElementById('v-time').value);
      if(isNaN(mins) || mins<=0) return;
      window.dels.push({{id: Date.now(), day: day, hr: hr, mins: mins, rsn: rsn}});
      localStorage.setItem('ic_dels', JSON.stringify(window.dels));
      document.getElementById('v-dur').value=15; document.getElementById('v-rsn').value='';
      clsMod();
      applyDelays();
    }}
    
    function buildRemList(){{
      var h='';
      if(window.dels.length===0) h='<div style="color:#888;text-align:center;padding:20px;">No delays added yet.</div>';
      else {{
        window.dels.forEach(d=> {{
          h+=`<div class="d-itm">
            <div><strong style="color:#2E5B8A">Day ${{d.day}} @ ${{d.hr}}:00</strong>: ${{d.mins}}m<br><span style="color:#666;font-size:11px">${{d.rsn}}</span></div>
            <button class="rm-btn" onclick="rmDel(${{d.id}})">Remove</button>
          </div>`;
        }});
      }}
      document.getElementById('v-del-list').innerHTML=h;
    }}
    
    function rmDel(id){{ window.dels = window.dels.filter(d=>d.id!==id); localStorage.setItem('ic_dels', JSON.stringify(window.dels)); buildRemList(); applyDelays(); }}

    function applyDelays() {{
      // Reset all times and skip recommendations first
      document.querySelectorAll('.time-adj, .skip-rec, .injected-delay').forEach(e=>e.remove());
      var cards = document.querySelectorAll('.sc:not(.injected-delay)');
      cards.forEach(c=> {{
        c.classList.remove('skipped');
        var sid = c.getAttribute('data-id');
        if(sid && window.skips.includes(sid)) {{
           c.classList.add('skipped');
           var btn = c.querySelector('.stog');
           if(btn) btn.innerHTML = '➕ Restore';
        }} else {{
           var btn = c.querySelector('.stog');
           if(btn) btn.innerHTML = '➖ Remove';
        }}
        
        var stEl = c.querySelector('.st');
        if(stEl && stEl.dataset.orig) stEl.innerHTML = stEl.dataset.orig;
      }});

      // Always process skips, even if delays are 0
      if(window.dels.length===0 && window.skips.length===0) return;

      // Inject visual delay blocks
      window.dels.forEach(d => {{
         var dc = document.createElement('div');
         dc.className = 'sc injected-delay';
         dc.setAttribute('data-day', d.day);
         dc.setAttribute('data-hour', d.hr);
         dc.setAttribute('data-delay-id', d.id);
         dc.style.borderLeftColor = '#E63946';
         dc.style.backgroundColor = '#fff0f1';
         dc.style.marginBottom = '10px';
         var hrStr = String(d.hr).padStart(2,'0') + ':00';
         dc.innerHTML = `
           <div style="display:flex;align-items:baseline;gap:10px">
             <div class="st">${{hrStr}}</div>
             <div><span class="sn" style="color:#C62828">🛑 Added Stop / Delay</span><br><span class="stp">${{d.mins}} minutes (${{d.rsn}})</span></div>
           </div>`;
           
         var inserted = false;
         for(var i=0; i<cards.length; i++) {{
            var c = cards[i];
            var cd = parseInt(c.getAttribute('data-day'));
            var ch = parseInt(c.getAttribute('data-hour'));
            if(cd === d.day && ch >= d.hr) {{
               c.parentNode.insertBefore(dc, c);
               inserted = true; break;
            }} else if(cd > d.day) {{
               c.parentNode.insertBefore(dc, c);
               inserted = true; break;
            }}
         }}
         if(!inserted) document.getElementById('atl').appendChild(dc);
      }});

      // Collect all cards including the newly injected ones for time shifting
      var allCards = document.querySelectorAll('.sc');
      
      // We must calculate cumulative shifts per day
      var dayShifts = {{1: [], 2: [], 3: [], 4: [], 5: []}};
      
      // Calculate active delay events
      window.dels.forEach(d => dayShifts[d.day].push({{type: 'add', hr: d.hr, mins: d.mins, id: d.id}}));
      
      // Calculate skipped events
      cards.forEach(c => {{
         var sid = c.getAttribute('data-id');
         if(sid && window.skips.includes(sid)) {{
             var cDay = parseInt(c.getAttribute('data-day'));
             var cHrk = parseInt(c.getAttribute('data-hour'));
             var cDur = parseInt(c.getAttribute('data-dur') || 60);
             if(dayShifts[cDay]) dayShifts[cDay].push({{type: 'sub', hr: cHrk, mins: cDur, id: sid}});
         }}
      }});

      allCards.forEach(c=> {{
        var dAttr = c.getAttribute('data-day');
        var hAttr = c.getAttribute('data-hour');
        if(!dAttr || !hAttr) return;
        
        var cardDay = parseInt(dAttr);
        var cardHr = parseInt(hAttr);
        var delayId = c.getAttribute('data-delay-id');
        var isImmune = c.getAttribute('data-immune') === 'true';
        
        var mins = 0;
        var shifts = dayShifts[cardDay] || [];
        shifts.forEach(sh => {{
            // Additive delays affect events scheduled at or after them
            if(sh.type === 'add' && cardHr >= sh.hr && String(sh.id) !== delayId) mins += sh.mins;
            // Subtractive removes affect events scheduled strictly AFTER them
            if(sh.type === 'sub' && cardHr > sh.hr) mins -= sh.mins;
        }});
        
        if(isImmune) return; // Immune cards (flights/camps) never shift time
        if(mins === 0) return;

        var stEl = c.querySelector('.st');
        if(!stEl) return;
        if(!stEl.dataset.orig) stEl.dataset.orig = stEl.innerHTML;
        
        var newTotalMins = (cardHr * 60) + mins;
        var newH = Math.floor(newTotalMins / 60);
        var newM = newTotalMins % 60;
        // Keep realistic clock boundaries
        if(newH < 0) {{ newH = 0; newM = 0; }}
        if(newH > 23) {{ newH = 23; newM = 59; }}
        
        var tStr = String(newH).padStart(2,'0') + ':' + String(newM).padStart(2,'0');
        
        var sign = mins > 0 ? '+' : '';
        var tCls = mins < 0 ? 'time-adj time-sub' : 'time-adj';
        stEl.innerHTML = `${{tStr}} <span class="${{tCls}}">${{sign}}${{mins}}m</span>`;
        
        // Only inject generic skip warning on ACTUAL cards, not the injected delay blocks
        if(newH >= 17 && !delayId) {{
           if(c.getAttribute('data-skip') === 'true' && !c.querySelector('.skip-rec')) {{
               var rec = document.createElement('div');
               rec.className = 'skip-rec';
               rec.innerHTML = '⚠️ Running late! Consider skipping this detour.';
               c.insertBefore(rec, c.firstChild);
           }}
        }}
      }});
      
      af(); // Re-run filter logic to ensure injected cards respect Day tab toggles
    }}

    function sv(v){{var m=document.querySelector('.folium-map');var a=document.getElementById('av');var t=document.getElementById('map-title');var bm=document.getElementById('bm');var ba=document.getElementById('ba');if(v==='agenda'){{if(m)m.style.display='none';if(t)t.style.display='none';a.style.display='block';bm.style.background='transparent';bm.style.color='#666';ba.style.background='#2E5B8A';ba.style.color='white';asc();}}else{{if(m)m.style.display='block';if(t)t.style.display='block';a.style.display='none';bm.style.background='#2E5B8A';bm.style.color='white';ba.style.background='transparent';ba.style.color='#666';}}}}
    var _f=new Set(['all','d1','d2','d3','d4','d5','hike','food','got']);
    function tf(b){{var f=b.getAttribute('data-f');if(f==='all'){{_f=new Set(['all','d1','d2','d3','d4','d5','hike','food','got']);var ps=document.querySelectorAll('.fp');for(var i=0;i<ps.length;i++){{ps[i].className='fp active';}}}}else{{if(b.className.indexOf('active')>=0){{b.className='fp';_f.delete(f);}}else{{b.className='fp active';_f.add(f);}}if(f.charAt(0)==='d'){{var ok=_f.has('d1')&&_f.has('d2')&&_f.has('d3')&&_f.has('d4')&&_f.has('d5');var ab=document.querySelector('[data-f="all"]');if(ok){{ab.className='fp active';_f.add('all');}}else{{ab.className='fp';_f.delete('all');}}}}}}af();}}
    function af(){{var cs=document.querySelectorAll('#atl .sc');var hs=document.querySelectorAll('#atl .dh');var ars=document.querySelectorAll('#atl .ar');for(var i=0;i<cs.length;i++){{var c=cs[i];if(c.parentElement.className.indexOf('ar')>=0)continue;var d=c.getAttribute('data-day');var tp=c.getAttribute('data-type');var gt=c.getAttribute('data-got');var dok=_f.has('d'+d);var tok=true;if(tp==='hike'&&!_f.has('hike'))tok=false;if(tp==='food'&&!_f.has('food'))tok=false;if(gt==='true'&&!_f.has('got'))tok=false;c.style.display=(dok&&tok)?'':'none';}}for(var i=0;i<ars.length;i++){{var r=ars[i];var mc=r.querySelector('.sc[data-day]');r.style.display=(mc&&mc.style.display==='none')?'none':'';}}for(var i=0;i<hs.length;i++){{var h=hs[i];h.style.display=_f.has('d'+h.getAttribute('data-day'))?'':'none';}}}}
    function asc(){{var n=new Date();var uh=n.getUTCHours();var today=n.getUTCFullYear()+'-'+String(n.getUTCMonth()+1).padStart(2,'0')+'-'+String(n.getUTCDate()).padStart(2,'0');var td=null;for(var k in DD){{if(DD[k]===today)td=parseInt(k);}}if(!td)return;var cs=document.querySelectorAll('.sc[data-hour]');for(var i=0;i<cs.length;i++){{var c=cs[i];var cd=parseInt(c.getAttribute('data-day'));var ch=parseInt(c.getAttribute('data-hour'));if((cd===td&&ch>=uh)||cd>td){{c.className+=' now';setTimeout(function(){{c.scrollIntoView({{behavior:'smooth',block:'center'}});}},200);return;}}}}}}
    if ('serviceWorker' in navigator) {{
      window.addEventListener('load', function() {{
        navigator.serviceWorker.register('sw.js').then(function(r) {{
          console.log('SW registered: ', r.scope);
        }}).catch(function(e) {{
          console.log('SW fail: ', e);
        }});
      }});
    }}
    applyDelays();
    </script>
    """
    m.get_root().html.add_child(folium.Element(agenda_el))



    return m

if __name__ == "__main__":
    routes = fetch_routes()
    weather = fetch_weather()
    print("\nBuilding interactive map...")
    m = build_map(routes, weather)
    out = "index.html"
    m.save(out)
    
    # Clean up trailing slashes for perfect HTML5 validation
    import re
    with open(out, 'r', encoding='utf-8') as f:
        html = f.read()
    html = re.sub(r'(<(meta|link|img|br|hr|input)[^>]*?)\s*/>', r'\1>', html)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
        
    kb = os.path.getsize(out)/1024
    print(f"\n✓ Saved: {out} ({kb:.0f} KB)")
    print("  • Layer control: toggle days + hiking trails on/off")
    print("  • Click markers for weather + notes + visitor guide links")
    print("  • Dashed orange lines = hiking trails with AllTrails links")
    print("  • 3 basemaps: Street / Terrain / Satellite")
