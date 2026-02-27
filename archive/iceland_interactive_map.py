
#!/usr/bin/env python3

"""
Iceland South Coast Road Trip — Interactive Map (v2)
March 6–10, 2026

Requires: pip install folium
Usage: python3 iceland_interactive_map.py
Output: iceland_interactive_map.html (open in any browser)

Features:
  - REAL road-following routes via Valhalla (OpenStreetMap) routing engine
  - Color-coded routes per day with toggleable layers
  - Clickable stop markers with popup info (name, day, notes, links)
  - Layer control to show/hide individual days
  - Overnight campsites highlighted
  - Multiple base map options (street, terrain, satellite)
"""

import folium
from folium import FeatureGroup, Marker, PolyLine, Popup, Icon, LayerControl
import json
import urllib.request
import urllib.parse
import time
import sys

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

MAP_CENTER = [63.85, -18.5]
ZOOM_START = 8

# Valhalla public routing endpoint (OpenStreetMap-based, no API key needed)
VALHALLA_URL = "https://valhalla1.openstreetmap.de/route"

DAY_COLORS = {
    1: "#E63946",  # Red
    2: "#457B9D",  # Steel blue
    3: "#2A9D8F",  # Teal
    4: "#D4A017",  # Gold
    5: "#7B2D8E",  # Purple
}

DAY_LABELS = {
    1: "Day 1 — Fri 3/6: KEF → Vík",
    2: "Day 2 — Sat 3/7: Vík → Skaftafell",
    3: "Day 3 — Sun 3/8: Skaftafell → Höfn → East",
    4: "Day 4 — Mon 3/9: Höfn → Skaftafell → Selfoss",
    5: "Day 5 — Tue 3/10: Selfoss → Golden Circle → KEF",
}

# ═══════════════════════════════════════════════════════════════════
# STOPS DATA
# Each stop: (name, lat, lon, day, type, notes, link)
#   type: "overnight" | "hike" | "food" | "shop" | "attraction" | "logistics"
# ═══════════════════════════════════════════════════════════════════

STOPS = [
    # ── Day 1: KEF → Vík ──
    ("KEF Airport", 63.985, -22.6056, 1, "logistics",
     "Pick up campervan, stock up at Bónus supermarket. Depart ~7:30–9am.",
     None),
    ("Hveragerði", 63.9966, -21.1876, 1, "attraction",
     "Iceland's 'Hot Spring Town'. Walk through the Hveragerði Geothermal Park. ~45 min from KEF.",
     None),
    ("Reykjadalur Hot River", 64.0229, -21.2116, 1, "hike",
     "🥾 BONUS HIKE: 6.4 km round trip, ~2 hrs. Hike up geothermal valley to natural warm river (36–40°C). Bring bathing suit + towel. Microspikes for icy patches.",
     "https://guidetoiceland.is/connect-with-locals/regina/reykjadalur-hot-spring-valley-in-south-iceland"),
    ("Seljalandsfoss", 63.6156, -19.9885, 1, "attraction",
     "60m walk-behind waterfall. Expect spray + rain = full waterproofs. 45 min.",
     "https://guidetoiceland.is/travel-iceland/drive/seljalandsfoss"),
    ("Gljúfrabúi", 63.6207, -19.9862, 1, "attraction",
     "Hidden waterfall inside a canyon slot, 500m from Seljalandsfoss. 30 min. Wear waterproofs.",
     "https://guidetoiceland.is/travel-iceland/drive/gljufrabui"),
    ("Skógafoss", 63.5321, -19.5113, 1, "attraction",
     "🐉 GoT: Wildling camp (S8). Climb the 370-step staircase for glacier and coast views. 45 min.",
     "https://guidetoiceland.is/travel-iceland/drive/skogafoss"),
    ("Dyrhólaey", 63.4022, -19.1289, 1, "attraction",
     "120m basalt sea arch, sweeping black sand panorama. 45 min. ⚠️ Skip upper viewpoint if gusts >20 m/s.",
     "https://guidetoiceland.is/travel-iceland/drive/dyrholaey"),
    ("Reynisfjara", 63.4044, -19.0695, 1, "attraction",
     "🐉 GoT S7E5: coastline near Eastwatch-by-the-Sea. Basalt column cave, Reynisdrangar sea stacks. 45 min. ⚠️ SNEAKER WAVE WARNING: Never turn your back on the ocean.",
     "https://guidetoiceland.is/travel-iceland/drive/reynisfjara"),
    ("Súður-Vík (dinner)", 63.419, -19.008, 1, "food",
     "🍽️ Dinner rec: Local hillside favorite. Lamb soup ~2,800 ISK, fish & chips ~3,200 ISK. Alt: Black Crust Pizzeria for charcoal-crust pizza ~3,500 ISK.",
     None),
    ("Vík 🏕️", 63.4186, -19.006, 1, "overnight",
     "🏕️ OVERNIGHT: Vík Campsite (Víkurbraut 5). Year-round, heated common room, walking distance to village.",
     None),

    # ── Day 2: Vík → Skaftafell ──
    ("Eldhraun Lava Field", 63.67, -18.32, 2, "attraction",
     "World's largest lava flow carpeted in luminous green moss. 30 min roadside stop.",
     "https://guidetoiceland.is/travel-iceland/drive/eldhraun"),
    ("Kirkjugolf", 63.7875, -17.9959, 2, "attraction",
     "'Church Floor' — hexagonal basalt columns, natural pavement. 5-min walk from parking.",
     "https://guidetoiceland.is/travel-iceland/drive/kirkjugolfid"),
    ("Systrafoss", 63.7835, -17.9745, 2, "attraction",
     "Twin cascades above Kirkjubæjarklaustur. 30-min walk.",
     "https://guidetoiceland.is/travel-iceland/drive/systrafoss"),
    ("Fjaðrárgljúfur Canyon", 63.7712, -18.172, 2, "attraction",
     "🐉 GoT filming location. 2km rim trail above 100m-deep gorge. 1.5 hrs. Microspikes recommended.",
     "https://guidetoiceland.is/travel-iceland/drive/fjadrargljufur"),
    ("Svartifoss + Sjónarnipa 🏕️", 64.0274, -16.9753, 2, "hike",
     "🥾 HIKE #1: Svartifoss–Sjónarnipa Loop. 6.4 km, ~3 hrs. Basalt-column waterfall + panoramic glacier views from Sjónarnipa ridge. Microspikes strongly recommended.\n\n🏕️ OVERNIGHT: Skaftafell Campsite (inside Vatnajökull NP, year-round, heated facilities).",
     "https://guidetoiceland.is/travel-iceland/drive/svartifoss"),

    # ── Day 3: Skaftafell → Höfn → East ──
    ("Svínafellsjökull", 64.008, -16.875, 3, "attraction",
     "🐉 GoT: North of the Wall / Fist of the First Men (S2–S3). Walk to glacier snout for up-close ice views. 45 min.",
     "https://guidetoiceland.is/travel-iceland/drive/svinafellsjokull"),
    ("Fjallsárlón", 64.0167, -16.3667, 3, "attraction",
     "Quieter sibling to Jökulsárlón. Glacier lagoon with icebergs. 45 min.",
     "https://guidetoiceland.is/travel-iceland/drive/fjallsarlon"),
    ("Jökulsárlón", 64.0784, -16.2297, 3, "attraction",
     "Floating blue-white icebergs, possible harbor seals. Iceland's crown jewel lagoon. 1 hr.",
     "https://guidetoiceland.is/travel-iceland/drive/jokulsarlon"),
    ("Diamond Beach", 64.044, -16.178, 3, "attraction",
     "Translucent ice blocks on jet-black sand. 5 min from Jökulsárlón. 30 min.",
     "https://guidetoiceland.is/travel-iceland/drive/diamond-beach"),
    ("Hofskirkja", 64.1978, -15.9418, 3, "attraction",
     "Iceland's last surviving turf-roofed church. 15-min detour.",
     "https://guidetoiceland.is/travel-iceland/drive/hofskirkja"),
    ("Hafnarbuðin (lunch)", 64.254, -15.21, 3, "food",
     "🍽️ Lunch rec: Harbour-side diner, budget langoustine. Langoustine baguette ~1,800 ISK (~$13) — cheapest langoustine in the lobster capital. Free coffee. Locals eat here.",
     None),
    ("Höfn", 64.2539, -15.2081, 3, "logistics",
     "Fuel, groceries. The lobster capital of Iceland.",
     None),
    ("Stokksnes / Vestrahorn", 64.249, -14.965, 3, "attraction",
     "Iconic mountain over black sand dunes + Viking village film set. 45 min. 💰 1,100 ISK/pp (~$8) at Viking Café.",
     "https://guidetoiceland.is/travel-iceland/drive/stokksnes"),
    ("Eystrahorn / Krossanesfjall", 64.319, -14.694, 3, "attraction",
     "Turnaround point. Walk the black sand base of the dramatic mountain. 1 hr.",
     "https://adventures.is/iceland/attractions/eystrahorn/"),
    ("Höfn 🏕️", 64.2539, -15.2081, 3, "overnight",
     "🏕️ OVERNIGHT: Höfn Campsite – Hamrar. Year-round, full facilities, walking distance to town.",
     None),

    # ── Day 4: Höfn → Skaftafell hike → Selfoss ──
    ("Kristínartindar Summit", 64.035, -16.95, 4, "hike",
     "🥾 HIKE #2: Kristínartindar Summit Trail. 10 km, ~4 hrs, moderate-strenuous. Climbs to 1,126m for 360° panorama over Vatnajökull. Full winter gear: microspikes, wind shell, warm layers.",
     "https://adventures.is/iceland/attractions/kristinartindar/"),
    ("Núpsstaurskógur", 63.9372, -17.505, 4, "attraction",
     "Iceland's largest native birch forest at Lómagnúpur base. 30-min walk.",
     "https://guidetoiceland.is/travel-iceland/drive/nupsstadaskogur"),
    ("Lómagnúpur", 63.8971, -17.645, 4, "attraction",
     "Sheer 767m wall. Roadside photo, 15 min. ⚠️ Notorious for sudden powerful gusts.",
     "https://guidetoiceland.is/travel-iceland/drive/lomagnupur"),
    ("Þingborg Wool Shop 🧶", 63.9333, -20.8167, 4, "shop",
     "🧶 Local-run wool shop since 1991, in a 1927 schoolhouse. Authentic handknit lopapeysa sweaters, sheepskins, blankets. Knitted by local women from Icelandic sheep's wool — not tourist shops. Prices lower than Reykjavík. Ask for tax-free receipt (reclaim 15% VAT at KEF). 15–20 min.\n\n📍 Route 1, 8 km east of Selfoss.",
     "https://www.south.is/en/service/thingborg-wool-processing"),
    ("Selfoss 🏕️", 63.9332, -21.003, 4, "overnight",
     "🏕️ OVERNIGHT: Selfoss Campsite. Year-round, full facilities. Proper town: Bónus supermarket, N1 fuel, restaurants, Sundhöllin pool.",
     None),

    # ── Day 5: Selfoss → Golden Circle → Reykjavík → KEF ──
    ("Þingvellir", 64.2559, -21.1299, 5, "attraction",
     "🐉 GoT S4: Almannagjá Gorge = mountain pass to the Bloody Gate (Vale of Arryn). Walk the rift valley + Öxarárfoss trail. UNESCO site. 1 hr. 💰 Parking 750 ISK.",
     "https://guidetoiceland.is/travel-iceland/drive/thingvellir"),
    ("Geysir", 64.3103, -20.3024, 5, "attraction",
     "Strokkur erupts every 6–10 min. 45 min. 💰 Parking 1,000 ISK/vehicle. No entrance fee.",
     "https://guidetoiceland.is/travel-iceland/drive/geysir"),
    ("Gullfoss", 64.3271, -20.1199, 5, "attraction",
     "Iceland's most powerful two-tier waterfall. 45 min. 💰 Free entry, free parking.",
     "https://guidetoiceland.is/travel-iceland/drive/gullfoss"),
    ("Hallgrímskirkja", 64.1417, -21.9267, 5, "attraction",
     "🗽 Statue of Leif Erikson + iconic church tower. Church entry free. Tower: 1,500 ISK/adult (~$11). Hours: 10am–4:45pm. 20–25 min.",
     "https://www.hallgrimskirkja.is/en-gb"),
    ("Smékkleysa Records", 64.1435, -21.9280, 5, "attraction",
     "🎵 Founded 1986 by The Sugarcubes (Björk). Legendary indie label / record shop / coffee bar. Browse vinyl from Sigur Rós, Björk, Múm, GusGus. Great espresso. 25–30 min.",
     "https://www.instagram.com/smekkleysa/"),
    ("Harpa Concert Hall", 64.1505, -21.9327, 5, "attraction",
     "Stunning geometric glass facade, harbour views. Free to enter lobby. Guided tours 2,750 ISK if available. 20 min.",
     "https://www.harpa.is/en"),
    ("Sun Voyager", 64.1476, -21.9223, 5, "attraction",
     "Iconic steel ship silhouette sculpture on the waterfront. Quick photo.",
     "https://guidetoiceland.is/travel-iceland/drive/sun-voyager"),
    ("Icelandic Street Food (lunch)", 64.1470, -21.9310, 5, "food",
     "🍽️ Lunch rec: Lamb soup in bread bowl with unlimited refills + free waffles. ~2,500–3,000 ISK (~$18–21). Best budget lunch in Reykjavík.\n\n💡 Pro tip: Start with shellfish soup (not refillable), then switch to lamb/tomato for free refills. Free brownies and carrot cake at the counter.",
     "https://www.icelandicstreetfood.com/"),
    ("Reykjavík", 64.1466, -21.9426, 5, "logistics",
     "Capital city. ~2.5 hr window for sightseeing (12:45pm–3:15pm).",
     None),
    ("KEF Departure ✈️", 63.985, -22.6056, 5, "logistics",
     "Drop off campervan ~4pm. Flight departs 5pm.",
     None),
]

# ═══════════════════════════════════════════════════════════════════
# ROUTE WAYPOINTS PER DAY
# These are the ordered stops the driving route must pass through.
# Valhalla computes actual road geometry between them.
# Format: list of (lat, lon) tuples per day.
# ═══════════════════════════════════════════════════════════════════

ROUTE_WAYPOINTS = {
    1: [
        (63.985, -22.6056),    # KEF
        (63.9966, -21.1876),   # Hveragerði
        (64.0229, -21.2116),   # Reykjadalur trailhead
        (63.9966, -21.1876),   # Back to Hveragerði (rejoin Route 1)
        (63.6156, -19.9885),   # Seljalandsfoss
        (63.6207, -19.9862),   # Gljúfrabúi
        (63.5321, -19.5113),   # Skógafoss
        (63.4022, -19.1289),   # Dyrhólaey
        (63.4044, -19.0695),   # Reynisfjara
        (63.4186, -19.006),    # Vík
    ],
    2: [
        (63.4186, -19.006),    # Vík
        (63.67, -18.32),       # Eldhraun
        (63.7712, -18.172),    # Fjaðrárgljúfur
        (63.7875, -17.9959),   # Kirkjugolf
        (63.7835, -17.9745),   # Systrafoss
        (64.0274, -16.9753),   # Svartifoss / Skaftafell
    ],
    3: [
        (64.0274, -16.9753),   # Skaftafell
        (64.008, -16.875),     # Svínafellsjökull
        (64.0167, -16.3667),   # Fjallsárlón
        (64.0784, -16.2297),   # Jökulsárlón
        (64.044, -16.178),     # Diamond Beach
        (64.1978, -15.9418),   # Hofskirkja
        (64.2539, -15.2081),   # Höfn
        (64.249, -14.965),     # Stokksnes
        (64.319, -14.694),     # Eystrahorn
        (64.249, -14.965),     # Back to Stokksnes
        (64.2539, -15.2081),   # Höfn overnight
    ],
    4: [
        (64.2539, -15.2081),   # Höfn
        (64.035, -16.95),      # Kristínartindar / Skaftafell area
        (63.9372, -17.505),    # Núpsstaurskógur
        (63.8971, -17.645),    # Lómagnúpur
        (63.9333, -20.8167),   # Þingborg Wool Shop
        (63.9332, -21.003),    # Selfoss
    ],
    5: [
        (63.9332, -21.003),    # Selfoss
        (64.2559, -21.1299),   # Þingvellir
        (64.3103, -20.3024),   # Geysir
        (64.3271, -20.1199),   # Gullfoss
        (64.3103, -20.3024),   # Back through Geysir
        (64.2559, -21.1299),   # Back through Þingvellir
        (64.1466, -21.9426),   # Reykjavík
        (63.985, -22.6056),    # KEF
    ],
}

# ═══════════════════════════════════════════════════════════════════
# VALHALLA ROUTING
# ═══════════════════════════════════════════════════════════════════

def decode_polyline6(encoded):
    """Decode Valhalla's encoded polyline (precision 1e-6) to list of (lat, lon)."""
    result = []
    index = 0
    lat = 0
    lng = 0
    while index < len(encoded):
        shift = 0
        res = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            res |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat += (~(res >> 1) if (res & 1) else (res >> 1))

        shift = 0
        res = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            res |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lng += (~(res >> 1) if (res & 1) else (res >> 1))

        result.append((lat / 1e6, lng / 1e6))
    return result


def get_route_geometry(waypoints, day_num):
    """
    Call Valhalla routing API to get road-following geometry.
    Returns list of (lat, lon) tuples tracing actual roads.
    """
    MAX_LOCS = 20
    all_coords = []

    for chunk_start in range(0, len(waypoints), MAX_LOCS - 1):
        chunk = waypoints[chunk_start:chunk_start + MAX_LOCS]
        if len(chunk) < 2:
            break

        locations = [{"lat": lat, "lon": lon} for lat, lon in chunk]
        params = {
            "locations": locations,
            "costing": "auto",
            "directions_options": {"units": "km"},
        }

        url = VALHALLA_URL + "?json=" + urllib.parse.quote(json.dumps(params))

        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "IcelandTripMap/1.0")
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.load(resp)

            for leg in data["trip"]["legs"]:
                decoded = decode_polyline6(leg["shape"])
                if all_coords and decoded:
                    decoded = decoded[1:]
                all_coords.extend(decoded)

            dist_km = data["trip"]["summary"]["length"]
            time_hrs = data["trip"]["summary"]["time"] / 3600
            print(f"  Day {day_num} chunk: {len(chunk)} waypoints → "
                  f"{len(all_coords)} road points, {dist_km:.0f} km, {time_hrs:.1f} hrs")

        except Exception as e:
            print(f"  ⚠️ Day {day_num} routing failed: {e}")
            print(f"     Falling back to straight lines for this chunk.")
            all_coords.extend(chunk)

        time.sleep(1.0)

    return all_coords


# ═══════════════════════════════════════════════════════════════════
# MAP BUILDING
# ═══════════════════════════════════════════════════════════════════

TYPE_ICONS = {
    "overnight":  ("campground",    "green"),
    "hike":       ("person-hiking", "orange"),
    "food":       ("utensils",      "purple"),
    "shop":       ("store",         "pink"),
    "attraction": ("camera",        "blue"),
    "logistics":  ("plane",         "gray"),
}


def build_popup_html(name, day, stop_type, notes, link):
    """Build a styled HTML popup for a stop marker."""
    color = DAY_COLORS[day]
    type_label = stop_type.capitalize()

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                width: 280px; line-height: 1.5;">
        <div style="background: {color}; color: white; padding: 8px 12px;
                    border-radius: 6px 6px 0 0; margin: -13px -20px 10px -20px;">
            <strong style="font-size: 14px;">{name}</strong><br>
            <span style="font-size: 11px; opacity: 0.9;">
                {DAY_LABELS[day]} &nbsp;·&nbsp; {type_label}
            </span>
        </div>
        <div style="font-size: 12px; color: #333; padding: 0 0 4px 0; white-space: pre-wrap;">{notes}</div>
    """
    if link:
        html += f"""
        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee;">
            <a href="{link}" target="_blank"
               style="color: {color}; text-decoration: none; font-size: 12px; font-weight: 600;">
                📖 Visitor Guide →
            </a>
        </div>
        """
    html += "</div>"
    return html


def create_map(route_geometries):
    """Build the folium map with route lines and stop markers."""
    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=ZOOM_START,
        tiles=None,
        control_scale=True,
    )

    # Tile layers
    folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Terrain",
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Satellite",
    ).add_to(m)

    # Feature groups per day
    day_groups = {}
    for day in range(1, 6):
        fg = FeatureGroup(name=DAY_LABELS[day], show=True)
        day_groups[day] = fg

    # Route lines (real road geometry)
    for day, coords in route_geometries.items():
        color = DAY_COLORS[day]
        PolyLine(
            locations=coords,
            color=color,
            weight=4,
            opacity=0.8,
            smooth_factor=1.0,
            tooltip=DAY_LABELS[day],
        ).add_to(day_groups[day])

    # Stop markers
    for name, lat, lon, day, stop_type, notes, link in STOPS:
        icon_name, _ = TYPE_ICONS.get(stop_type, ("circle-info", "blue"))

        popup_html = build_popup_html(name, day, stop_type, notes, link)
        popup = Popup(popup_html, max_width=320)

        if stop_type == "overnight":
            icon_obj = Icon(color="green", icon=icon_name, prefix="fa")
        elif stop_type == "hike":
            icon_obj = Icon(color="orange", icon=icon_name, prefix="fa")
        elif stop_type == "food":
            icon_obj = Icon(color="purple", icon=icon_name, prefix="fa")
        elif stop_type == "shop":
            icon_obj = Icon(color="pink", icon=icon_name, prefix="fa")
        elif stop_type == "logistics":
            icon_obj = Icon(color="gray", icon=icon_name, prefix="fa")
        else:
            day_icon_colors = {1: "red", 2: "blue", 3: "green", 4: "orange", 5: "purple"}
            icon_obj = Icon(
                color=day_icon_colors.get(day, "blue"),
                icon=icon_name, prefix="fa",
            )

        Marker(
            location=[lat, lon],
            popup=popup,
            tooltip=f"<b>{name}</b><br><small>{DAY_LABELS[day]}</small>",
            icon=icon_obj,
        ).add_to(day_groups[day])

    for fg in day_groups.values():
        fg.add_to(m)

    LayerControl(collapsed=False).add_to(m)

    # Title overlay
    title_html = """
    <div style="position: fixed; top: 10px; left: 55px; z-index: 1000;
                background: white; padding: 10px 18px; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
        <div style="font-size: 16px; font-weight: 700; color: #2E5B8A;">
            🇮🇸 Iceland Road Trip
        </div>
        <div style="font-size: 12px; color: #666; margin-top: 2px;">
            March 6–10, 2026 · 5 Days · ~1,200 km
        </div>
        <div style="font-size: 10px; color: #999; margin-top: 4px;">
            🏕️ Overnight &nbsp; 🥾 Hike &nbsp; 🍽️ Food &nbsp; 🧶 Shop &nbsp; 📷 Attraction
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("═" * 60)
    print(" Iceland Interactive Map — v2 (real road routing)")
    print("═" * 60)

    print("\n📡 Fetching road-following routes from Valhalla (OpenStreetMap)...")
    print("   (This calls a free public API — takes ~10 seconds)\n")

    route_geometries = {}
    total_points = 0
    for day in range(1, 6):
        waypoints = ROUTE_WAYPOINTS[day]
        print(f"Day {day}: {len(waypoints)} waypoints...")
        coords = get_route_geometry(waypoints, day)
        route_geometries[day] = coords
        total_points += len(coords)

    print(f"\n✓ Total road points: {total_points:,}")

    print("\n🗺️  Building interactive map...")
    m = create_map(route_geometries)

    output_path = "iceland_interactive_map.html"
    m.save(output_path)

    print(f"\n✓ Saved: {output_path}")
    print("  Open in any browser. Use the layer control (top-right) to toggle days.")
    print("  Click any marker for popup details + visitor guide links.")
    print("  Routes follow actual roads via OpenStreetMap/Valhalla routing.")
