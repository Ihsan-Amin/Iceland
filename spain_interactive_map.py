#!/usr/bin/env python3
"""
Portugal & Spain — Moorish Architecture Tour — Interactive Map
August 6–20, 2026

Built on the same framework as iceland_interactive_map.py:
  - Leaflet/Folium map with color-coded, toggleable layers
  - Rich marker popups with notes + official booking links + Google Maps
  - A full "Itinerary" agenda view (filter chips, skip toggles, delay tracking)
  - August climate-normal panels (matching the itinerary's heat outlook)

Requires: pip install folium polyline requests
Usage:    python3 spain_interactive_map.py
Output:   spain.html
"""

import folium
from folium import FeatureGroup, Marker, PolyLine, Popup, Icon, LayerControl
from folium.plugins import LocateControl
import polyline as pl_lib
import requests, json, time, os, hashlib

MAP_CENTER = [40.0, -5.6]
ZOOM_START = 6
VALHALLA_URL = "https://valhalla1.openstreetmap.de/route"
ROUTE_CACHE = "spain_route_cache.json"

# ─── Regions (map layers + colours) ───────────────────────────────────────
# Sub-cities (Sintra/Cordoba/Toledo/Transit) fold into a base region.
REGION_OF = {
    "Porto": "Porto", "Lisbon": "Lisbon", "Sintra": "Lisbon",
    "Seville": "Seville", "Cordoba": "Seville", "Setenil": "Seville", "Ronda": "Seville",
    "Granada": "Granada", "Madrid": "Madrid", "Toledo": "Madrid", "Segovia": "Madrid",
    "Transit": "Transit",
}
# Muted, earthy Anthropic-leaning palette — distinct hues, calm on ivory & deep grey.
REGION_COLORS = {
    "Porto": "#41827b", "Lisbon": "#4c72a0", "Seville": "#c15f3c",
    "Granada": "#b3812f", "Madrid": "#8c6183", "Transit": "#7d7770",
}
REGION_MARKER = {  # Leaflet.awesome-markers palette (nearest muted names)
    "Porto": "cadetblue", "Lisbon": "blue", "Seville": "red",
    "Granada": "orange", "Madrid": "darkpurple", "Transit": "gray",
}
REGION_ORDER = ["Porto", "Lisbon", "Seville", "Granada", "Madrid", "Transit"]

def region(city):
    return REGION_OF.get(city, "Madrid")
def rcolor(city):
    return REGION_COLORS[region(city)]

# ─── Days ──────────────────────────────────────────────────────────────────
DAY_DATES = {d: f"2026-08-{5+d:02d}" for d in range(1, 16)}  # 1→08/06 … 15→08/20
DAY_CITY = {1:"Transit",2:"Porto",3:"Porto",4:"Lisbon",5:"Sintra",6:"Lisbon",
            7:"Seville",8:"Cordoba",9:"Seville",10:"Granada",11:"Granada",
            12:"Madrid",13:"Madrid",14:"Segovia",15:"Transit"}
DAY_LABELS = {
    1:"Day 1 — Thu Aug 6: Depart Washington",
    2:"Day 2 — Fri Aug 7: Arrive Porto → Ribeira",
    3:"Day 3 — Sat Aug 8: Porto + port lodges",
    4:"Day 4 — Sun Aug 9: Train to Lisbon → Alfama",
    5:"Day 5 — Mon Aug 10: Sintra day trip",
    6:"Day 6 — Tue Aug 11: Belém + azulejos",
    7:"Day 7 — Wed Aug 12: Fly to Seville · Eclipse",
    8:"Day 8 — Thu Aug 13: Córdoba · Setenil · Ronda (guided tour)",
    9:"Day 9 — Fri Aug 14: Seville's Moorish core",
    10:"Day 10 — Sat Aug 15: Train to Granada → Albaicín",
    11:"Day 11 — Sun Aug 16: THE ALHAMBRA",
    12:"Day 12 — Mon Aug 17: Train to Madrid",
    13:"Day 13 — Tue Aug 18: Madrid full day",
    14:"Day 14 — Wed Aug 19: Toledo + Segovia tour · farewell",
    15:"Day 15 — Thu Aug 20: Fly home",
}

# ─── Per-day route in Google Maps (🗺 links straight from the itinerary) ────
DAY_MAP = {
 2:"https://www.google.com/maps/dir/?api=1&origin=Porto%20Airport%20OPO&destination=Adega%20Sao%20Nicolau%2C%20Porto&waypoints=Sheraton%20Porto%20Hotel%20%26%20Spa%2C%20Porto%7CRibeira%2C%20Porto%7CPonte%20Luis%20I%2C%20Porto&travelmode=driving",
 3:"https://www.google.com/maps/dir/?api=1&origin=Sheraton%20Porto%20Hotel%20%26%20Spa%2C%20Porto&destination=O%20Valentim%2C%20Matosinhos&waypoints=Livraria%20Lello%2C%20Porto%7CSao%20Bento%20Station%2C%20Porto%7CPalacio%20da%20Bolsa%2C%20Porto%7CMercado%20do%20Bolhao%2C%20Porto%7CGraham%27s%20Port%20Lodge%2C%20Vila%20Nova%20de%20Gaia&travelmode=walking",
 4:"https://www.google.com/maps/dir/?api=1&origin=Lisboa%20Santa%20Apolonia%20Station&destination=Taberna%20Sal%20Grosso%2C%20Lisbon&waypoints=Corinthia%20Lisbon%2C%20Lisbon%7CMiradouro%20de%20Santa%20Luzia%2C%20Lisbon%7CMuseu%20do%20Aljube%2C%20Lisbon%7CCastelo%20de%20Sao%20Jorge%2C%20Lisbon&travelmode=driving",
 5:"https://www.google.com/maps/dir/?api=1&origin=Sete%20Rios%20Station%2C%20Lisbon&destination=Tascantiga%2C%20Sintra&waypoints=Sintra%20Station%7CCastelo%20dos%20Mouros%2C%20Sintra%7CPalacio%20Nacional%20da%20Pena%2C%20Sintra&travelmode=transit",
 6:"https://www.google.com/maps/dir/?api=1&origin=Corinthia%20Lisbon%2C%20Lisbon&destination=Time%20Out%20Market%2C%20Lisbon&waypoints=Mosteiro%20dos%20Jeronimos%2C%20Lisbon%7CPasteis%20de%20Belem%2C%20Lisbon%7CEmbaixada%2C%20Principe%20Real%2C%20Lisbon%7CA%20Vida%20Portuguesa%2C%20Rua%20Anchieta%2C%20Lisbon%7CLargo%20do%20Carmo%2C%20Lisbon&travelmode=driving",
 7:"https://www.google.com/maps/dir/?api=1&origin=Seville%20Airport&destination=Bodega%20Santa%20Cruz%20Las%20Columnas%2C%20Seville&waypoints=Prado%20de%20San%20Sebastian%2C%20Seville%7CHotel%20Giralda%20Center%2C%20Seville%7CBarrio%20Santa%20Cruz%2C%20Seville&travelmode=driving",
 8:"https://www.google.com/maps/dir/?api=1&origin=Avenida%20de%20Menendez%20Pelayo%201%2C%20Sevilla&destination=Avenida%20de%20Menendez%20Pelayo%201%2C%20Sevilla&waypoints=Mezquita-Catedral%20de%20Cordoba%7CSetenil%20de%20las%20Bodegas%7CPuente%20Nuevo%2C%20Ronda&travelmode=driving",
 9:"https://www.google.com/maps/dir/?api=1&origin=Hotel%20Giralda%20Center%2C%20Seville&destination=Plaza%20de%20Espana%2C%20Seville&waypoints=Real%20Alcazar%2C%20Seville%7CCatedral%20de%20Sevilla%7CEl%20Rinconcillo%2C%20Seville%7CCasa%20de%20Pilatos%2C%20Seville%7CSetas%20de%20Sevilla&travelmode=walking",
 10:"https://www.google.com/maps/dir/?api=1&origin=Granada%20Railway%20Station&destination=Los%20Diamantes%2C%20Calle%20Navas%2C%20Granada&waypoints=Melia%20Granada%7CPlaza%20Nueva%2C%20Granada%7CMirador%20de%20San%20Nicolas%2C%20Granada&travelmode=driving",
 11:"https://www.google.com/maps/dir/?api=1&origin=Melia%20Granada&destination=Casa%20Juanillo%2C%20Sacromonte%2C%20Granada&waypoints=Alhambra%2C%20Granada%7CCapilla%20Real%20de%20Granada%7CCentro%20Federico%20Garcia%20Lorca%2C%20Granada&travelmode=walking",
 12:"https://www.google.com/maps/dir/?api=1&origin=Madrid%20Atocha%20Station&destination=Mercado%20de%20San%20Miguel%2C%20Madrid&waypoints=Calle%20de%20Felipe%20III%206%2C%20Madrid%7CLa%20Casa%20del%20Abuelo%2C%20Madrid%7CLa%20Latina%2C%20Madrid&travelmode=walking",
 13:"https://www.google.com/maps/dir/?api=1&origin=Calle%20de%20Felipe%20III%206%2C%20Madrid&destination=Templo%20de%20Debod%2C%20Madrid&waypoints=Museo%20Reina%20Sofia%2C%20Madrid%7CCuesta%20de%20Moyano%2C%20Madrid%7CMuralla%20Arabe%2C%20Madrid%7CChocolateria%20San%20Gines%2C%20Madrid%7CCasa%20Hernanz%2C%20Madrid%7CMuseo%20del%20Prado%2C%20Madrid&travelmode=walking",
 14:"https://www.google.com/maps/dir/?api=1&origin=Calle%20de%20Julio%20Camba%2013%2C%20Madrid&destination=Calle%20de%20Julio%20Camba%2013%2C%20Madrid&waypoints=Catedral%20de%20Toledo%7CAcueducto%20de%20Segovia%7CAlcazar%20de%20Segovia&travelmode=driving",
 15:"https://www.google.com/maps/dir/?api=1&origin=Calle%20de%20Felipe%20III%206%2C%20Madrid&destination=Adolfo%20Suarez%20Madrid-Barajas%20Airport&travelmode=driving",
}

# ─── August climate normals (from the itinerary heat outlook, NOT a forecast) ─
CLIMATE = {
 "Porto":  {"hi":"77°F / 25°C","lo":"61°F / 16°C","pat":"Mild, Atlantic breeze, possible AM fog","emoji":"🌤","warn":0},
 "Lisbon": {"hi":"83°F / 28°C","lo":"64°F / 18°C","pat":"Sunny, breezy and dry","emoji":"☀️","warn":0},
 "Sintra": {"hi":"75°F / 24°C","lo":"62°F / 17°C","pat":"Cooler hilltop, misty mornings","emoji":"🌤","warn":0},
 "Seville":{"hi":"97–102°F / 36–39°C","lo":"68°F / 20°C","pat":"Extreme dry heat; 104°F+ days routine","emoji":"🔥","warn":1},
 "Cordoba":{"hi":"100°F / 38°C","lo":"70°F / 21°C","pat":"Spain's hottest city — mornings only","emoji":"🔥","warn":1},
 "Setenil": {"hi":"93°F / 34°C","lo":"63°F / 17°C","pat":"Hot, but the cliff overhangs give real shade","emoji":"☀️","warn":1},
 "Ronda":  {"hi":"90°F / 32°C","lo":"61°F / 16°C","pat":"Cooler at 750 m; breezy on the gorge","emoji":"🌤","warn":0},
 "Granada":{"hi":"94°F / 34°C","lo":"63°F / 17°C","pat":"Very hot days, cooler nights (680 m)","emoji":"☀️","warn":1},
 "Madrid": {"hi":"92°F / 33°C","lo":"66°F / 19°C","pat":"Hot, dry, big daily swing","emoji":"☀️","warn":1},
 "Toledo": {"hi":"94°F / 34°C","lo":"66°F / 19°C","pat":"Hot, exposed stone streets","emoji":"☀️","warn":1},
 "Segovia":{"hi":"86°F / 30°C","lo":"57°F / 14°C","pat":"High meseta at 1,000 m — warm days, cool evenings","emoji":"🌤","warn":0},
 "Transit":{"hi":"—","lo":"—","pat":"Travel day","emoji":"✈️","warn":0},
}

# ─── Guides / weather links per region (shown in popups) ────────────────────
CITY_GUIDE = {
 "Porto":"https://visitporto.travel/en-GB/","Lisbon":"https://www.visitlisboa.com/en",
 "Sintra":"https://www.parquesdesintra.pt/en/","Seville":"https://visitasevilla.es/en",
 "Cordoba":"https://www.turismodecordoba.org/en","Granada":"https://www.granadatur.com/en/",
 "Setenil":"https://www.andalucia.org/en/setenil-de-las-bodegas","Ronda":"https://www.turismoderonda.es/en/",
 "Madrid":"https://www.esmadrid.com/en","Toledo":"https://toledomonumental.com",
 "Segovia":"https://www.turismodesegovia.com/en/","Transit":None,
}

# ─── Live weather (Open-Meteo) — same engine as the Iceland map ─────────────
# Forecasts only reach ~16 days out, so live data appears as the trip nears;
# until then (and if the fetch fails) each stop falls back to the climate panel.
WEATHER_CACHE = "spain_weather_cache.json"
CACHE_MAX_AGE_HOURS = 1
WX_COORD = {
 "Porto":(41.15,-8.61),"Lisbon":(38.72,-9.14),"Sintra":(38.79,-9.39),
 "Seville":(37.38,-5.99),"Cordoba":(37.88,-4.78),"Granada":(37.17,-3.60),
 "Setenil":(36.86,-5.18),"Ronda":(36.74,-5.17),
 "Madrid":(40.41,-3.70),"Toledo":(39.86,-4.02),"Segovia":(40.95,-4.12),
}
WX_TZ = {  # Portugal is WEST (UTC+1) in August, Spain is CEST (UTC+2)
 "Porto":"Europe/Lisbon","Lisbon":"Europe/Lisbon","Sintra":"Europe/Lisbon",
 "Seville":"Europe/Madrid","Cordoba":"Europe/Madrid","Granada":"Europe/Madrid",
 "Setenil":"Europe/Madrid","Ronda":"Europe/Madrid",
 "Madrid":"Europe/Madrid","Toledo":"Europe/Madrid","Segovia":"Europe/Madrid",
}
WMO = {
 0:("Clear sky","☀️"),1:("Mainly clear","🌤️"),2:("Partly cloudy","⛅"),3:("Overcast","☁️"),
 45:("Fog","🌫️"),48:("Rime fog","🌫️"),51:("Light drizzle","🌦️"),53:("Drizzle","🌦️"),
 55:("Dense drizzle","🌧️"),61:("Slight rain","🌦️"),63:("Rain","🌧️"),65:("Heavy rain","🌧️"),
 71:("Light snow","🌨️"),73:("Snow","🌨️"),75:("Heavy snow","❄️"),
 80:("Light showers","🌦️"),81:("Showers","🌧️"),82:("Heavy showers","⛈️"),
 95:("Thunderstorm","⛈️"),96:("T-storm + hail","⛈️"),99:("T-storm + heavy hail","⛈️"),
}

def fetch_weather():
    if os.path.exists(WEATHER_CACHE):
        age=time.time()-os.path.getmtime(WEATHER_CACHE)
        if age<CACHE_MAX_AGE_HOURS*3600:
            try:
                data=json.load(open(WEATHER_CACHE))
                print(f"✓ Weather from cache (expires in {int((CACHE_MAX_AGE_HOURS*3600-age)/60)} min).")
                return data
            except Exception: pass
    print("Fetching weather from Open-Meteo…")
    out={}
    for city,(lat,lon) in WX_COORD.items():
        url=(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
             f"&hourly=temperature_2m,apparent_temperature,precipitation,weathercode,windspeed_10m,windgusts_10m"
             f"&daily=sunrise,sunset&forecast_days=16&timezone={WX_TZ[city]}")
        try:
            r=requests.get(url,timeout=15).json()
            if "hourly" in r: out[city]={"hourly":r["hourly"],"daily":r.get("daily",{})}; print(f"  ✓ {city}")
            else: print(f"  – {city}: no hourly data")
        except Exception as e:
            print(f"  ⚠ {city}: {e}")
        time.sleep(0.3)
    try: json.dump(out,open(WEATHER_CACHE,"w"))
    except Exception: pass
    return out

def get_wx(weather, city, day, hour):
    """Return live forecast dict for a city at a given day+hour, or None.
    Guards every value so a null from the API can never crash formatting."""
    if not weather or city not in weather: return None
    h=weather[city].get("hourly")
    if not h or "time" not in h: return None
    t=f"{DAY_DATES[day]}T{hour:02d}:00"
    try: i=h["time"].index(t)
    except ValueError: return None
    def g(k):
        a=h.get(k)
        if not a or i>=len(a): return None
        return a[i]
    tc=g("temperature_2m"); fc=g("apparent_temperature")
    p=g("precipitation"); w=g("windspeed_10m"); gu=g("windgusts_10m"); wc=g("weathercode")
    if tc is None: return None  # no usable live reading → fall back to climate
    desc,emoji=WMO.get(wc,("—","🌡️"))
    def cf(v): return None if v is None else round(v*9/5+32)
    return {"tc":tc,"tf":cf(tc),"fc":fc,"ff":cf(fc),"p":p,"w":w,"g":gu,
            "desc":desc,"emoji":emoji,"hour":hour}

# ═══════════════════════ STOPS ═══════════════════════
# (name, lat, lon, day, type, city, notes, link, hour, dur_min, anchor)
#  type → icon/colour.  🕌 moorish · ✊ history · ⭐ must-see · 📚 books · 🇪🇸 friend tip
S = [
# ---- Day 1: Depart Washington ----
("Capital One Lounge — IAD 🛋️",38.9528,-77.4558,1,"lounge","Transit",
 "🛋️ Before boarding — Capital One Lounge (free for all of you on Venture X, and the pick over Priority Pass). Main Terminal, just past security between the East & West checkpoints on the ticketing level, so you hit it before taking the AeroTrain out to the A/B international gates. Hot food, barista coffee, full bar. Open till 9 PM — your flight's 9:45 PM, so settle in ~7:15 and head to the gate by 9. ⚠️ Confirm it's out of its temporary limited-service refurb before counting on the full spread.",
 "https://www.capitalone.com/lounges/",19,90,True),
("IAD — Depart Washington ✈️",38.9531,-77.4565,1,"flight","Transit",
 "6:45 PM arrive IAD (3 hrs early). 9:45 PM Delta DL8752 (Air France metal) IAD→Paris CDG, land 11:15 AM; 2h45 layover, then DL8306 CDG→Porto (land 3:25 PM Fri). Sleep on the transatlantic leg — the plane nap is the jetlag strategy; pack a layer, the cabin runs cold. ⚠️ CDG lounge: on a Main Basic fare your only access is Priority Pass, and CDG's Air France lounges (the ones on your 2E→2F path) don't accept it — the lone PP option is the YOTELAIR nap-cabins in 2E, awkward to reach heading to the Schengen 2F gates. Plan to grab food near 2F rather than bank on a lounge.",
 "https://www.delta.com",21,0,True),

# ---- Day 2: Arrive Porto → Ribeira ----
("CDG — Paris layover ✈️",49.0097,2.5479,2,"flight","Transit",
 "✈️ Land 11:15 AM (Fri Aug 7) off the overnight DL8752, then a 2h45 layover before DL8306 to Porto at 2:00 PM. You arrive 2E and depart from the Schengen 2F gates, so allow ~30 min for the transfer and passport control — this is where you clear EU immigration for the whole trip, so keep passports handy. ⚠️ No usable lounge: on a Main Basic fare the Air France lounges are out and the only Priority Pass option is the YOTELAIR cabins back in 2E. Grab food near 2F and reset your watch: Paris and Porto are an hour apart, so 2:00 PM here is 1:00 PM there.",
 None,11,165,True),
("OPO Airport — Arrive Porto",41.2481,-8.6814,2,"flight","Porto",
 "Land 3:25 PM (Fri Aug 7). To Boavista: Metro Line E (violet) → Casa da Música ~25 min (€2.25 + Andante card) + 8–10 min walk, or taxi/Bolt €20–25. After a red-eye the taxi is worth it.",
 None,15,30,True),
("Sheraton Porto Hotel & Spa 🏨",41.1580,-8.6293,2,"hotel","Porto",
 "🏨 Aug 7–9 (BOOKED, $511.29). Boavista, 2.5 km from Ribeira. Premium Queen listed for 2 — call +351 22 040 4000 to arrange third-person bedding. Real pool + spa after the red-eye.",
 None,17,0,True),
("Ribeira riverfront",41.1408,-8.6110,2,"attraction","Porto",
 "Evening stroll along the Douro. ~5:45 PM from the hotel — taxi ~10 min €8, or metro to São Bento + walk down.",
 None,18,60,False),
("Dom Luís I Bridge 🌄",41.1399,-8.6094,2,"viewpoint","Porto",
 "Walk the upper deck across to Gaia for the classic skyline. 15-min walk up from Ribeira; sunset ~8:50 PM, plenty of light.",
 None,20,45,False),
("Jardim do Morro 🌄",41.1385,-8.6090,2,"viewpoint","Porto",
 "🌄 The postcard shot: the Dom Luís I bridge broadside with Ribeira's old town stacked across the Douro. A terraced garden right where the upper deck lands in Gaia — Porto's favourite sunset lawn, the first stop off the bridge. Free and open; grab it at golden hour. The Teleférico de Gaia cable car also drifts down past this same view to the quay (~€7 one-way).",
 None,20,25,False),
("Miradouro da Serra do Pilar 🌄",41.1373,-8.6098,2,"viewpoint","Porto",
 "🌄 The higher, wider panorama — the whole Ribeira waterfront and both decks of the bridge line up from this UNESCO-listed monastery terrace, a 3-min climb above Jardim do Morro. Catch it before the ~8:50 PM sunset (esplanade free; monastery dome/cloister ~€4).",
 None,20,30,False),
("Café Santiago (dinner)",41.1487,-8.6060,2,"food","Porto",
 "🍽 ~9 PM, after the sunset from the bridge — the Francesinha benchmark, ~€13; expect a short queue. Or book a river-view table in Ribeira. Early night after the red-eye.",
 None,21,60,False),

# ---- Day 3: Porto full day + port lodges ----
("Livraria Lello 📚",41.1470,-8.6146,3,"shop","Porto",
 "📚 9:00 AM timed entry (book ahead; €8 voucher credits toward a book). One of the world's most beautiful bookshops.",
 "https://www.livrarialello.pt",9,45,False),
("Clérigos Tower",41.1456,-8.6142,3,"attraction","Porto",
 "Baroque bell-tower climb, then the São Bento azulejo hall (free) 8-min walk downhill.",
 None,10,45,False),
("São Bento azulejo hall",41.1457,-8.6106,3,"moorish","Porto",
 "🕌 Blue-and-white azulejo tiles — the Portuguese craft that descends directly from Moorish tradition. Free station concourse.",
 None,10,20,False),
("Sé do Porto (Cathedral)",41.1426,-8.6115,3,"attraction","Porto",
 "The hilltop Romanesque cathedral above Ribeira — its Gothic cloister is lined with blue azulejos, and the terrace (Terreiro da Sé) opens a sweeping view over the old town. 5-min walk uphill from São Bento; free entry, cloister ~€3. Quick 25-min stop before the 11 AM Bolsa slot.",
 None,10,25,False),
("⭐ Palácio da Bolsa (Arab Room)",41.1414,-8.6153,3,"moorish","Porto",
 "🕌⭐ 11:00 AM guided visit (~€12, 45 min): the gilded Arab Room is a 19th-c. neo-Moorish fantasy — a perfect on-theme bonus.",
 "https://palaciodabolsa.com/en/",11,45,False),
("Mercado do Bolhão (lunch)",41.1497,-8.6062,3,"food","Porto",
 "🍽 12:30 PM graze the restored market counters, €8–15.",
 None,12,60,False),
("Casa Guedes 🥪",41.1477,-8.6045,3,"food","Porto",
 "🥪 A pernil sandwich — slow-roasted pork shank with melting Serra da Estrela cheese, ~€5. Anthony Bourdain filmed here (Parts Unknown) at the tiny original on Praça dos Poveiros. 4-min walk down from Bolhão; share one on the way to Gazela.",
 None,13,15,False),
("Cervejaria Gazela 🌭",41.1449,-8.6064,3,"food","Porto",
 "🌭 One cachorrinho each — the crisp, spicy mini hot-dogs Anthony Bourdain wolfed down here on camera. A Porto institution by Praça da Batalha, 5-min walk from Bolhão; ~15 min standing at the counter with a cold Super Bock. Open from noon, Mon–Sat.",
 None,13,15,False),
("Rua das Flores 🛍",41.1435,-8.6118,3,"shop","Porto",
 "⭐🛍 Shopping stroll: Claus Porto flagship (heritage soaps/leather) + Portuguese-cotton shops. Scout prices — the bigger haul is Lisbon Day 6.",
 None,14,45,False),
("✊ UNICEPE bookshop",41.1478,-8.6155,3,"history","Porto",
 "✊📚 Porto's student book cooperative, a left-wing institution since 1964, near Praça de Carlos Alberto. 15-min browse. If shut, Livraria Latina fills in.",
 None,15,20,False),
("🍷 Graham's 1890 Port Lodge",41.1360,-8.6210,3,"food","Porto",
 "🍷 4:00 PM guided tour + tasting (reserve, ~€25–45), Vila Nova de Gaia. Everyone's 18+, so it works for all three. Taylor's is the easier self-guided alt.",
 "https://www.grahams-port.com/visit-us",16,90,False),
("O Valentim (dinner, Matosinhos)",41.1830,-8.6960,3,"food","Porto",
 "🍽 Matosinhos grilled-fish row, €15–25. Metro Line A direct from Casa da Música ~20 min. Or the optional 6-Bridges river cruise (~€20) at 6 PM first.",
 None,20,90,False),

# ---- Day 4: Train to Lisbon → Alfama ----
("Porto Campanhã → Lisbon 🚆",41.1490,-8.5850,4,"train","Lisbon",
 "🚆 BOOKED — Intercidades 522, 08:45 Porto Campanhã → 12:00 Lisboa Santa Apolónia (2ª classe, Sun Aug 9). Taxi to Campanhã (NOT São Bento) ~12 min; drop bags / check in, then Alfama at 2.",
 "https://www.cp.pt/passageiros/en",9,195,True),
("Corinthia Lisbon 🏨",38.7370,-9.1656,4,"hotel","Lisbon",
 "🏨 Aug 9–12 (BOOKED, $802.14; fully refundable before Aug 8). Deluxe King — 1 king + sofa bed, fits 3. At Praça de Espanha / Sete Rios: a few minutes' walk to Sete Rios station, which is on the Blue-line metro AND the Sintra line (board there for Day 5, skipping Rossio). Premier Collection perks — $100 experience credit, daily breakfast for 2, WiFi, on-site spa. Check-in 2 PM, checkout noon on the 12th. A little out from the old town, but the metro links you straight in.",
 None,13,0,True),
("🕌 Alfama + Miradouro de Santa Luzia",38.7118,-9.1300,4,"moorish","Lisbon",
 "🕌 2:00 PM the old Moorish quarter (from Arabic al-hamma) — wander the lanes up to the tiled Santa Luzia terrace.",
 None,14,90,False),
("✊ Museu do Aljube",38.7107,-9.1330,4,"history","Lisbon",
 "✊ 4:00 PM (~€3, 45 min): the Estado Novo's political prison, now a museum of the dictatorship and the resistance — the essential primer before Largo do Carmo on Day 6.",
 None,16,45,False),
("🕌 Castelo de São Jorge",38.7139,-9.1335,4,"moorish","Lisbon",
 "🕌 5:30 PM (book online, ~€15): the Moorish-era citadel, for sweeping views over the city and river. Open till ~9 PM in summer — true golden light isn't until ~8 PM, so linger or come back later if you want it.",
 "https://castelodesaojorge.pt/en/",17,90,False),
("Tasca do Chico (fado + dinner)",38.7113,-9.1447,4,"food","Lisbon",
 "🍽 8:30 PM Alfama/Bairro Alto dinner; for fado, Tasca do Chico (cheap, authentic) or a booked show ~€20–35.",
 None,20,90,False),

# ---- Day 5: Sintra day trip ----
("Sete Rios → Sintra train 🚆",38.7397,-9.1689,5,"train","Sintra",
 "🚆 8:30 AM train to Sintra (every 20–30 min, Viva Viagem card; no advance booking). Sete Rios is a few minutes' walk from the Corinthia and sits right on the Sintra line, so board here instead of trekking to Rossio. Leave the hotel by 8:15. Sintra is Portugal's busiest day trip — the early train matters. (Coming back, ride through to Rossio for the evening.)",
 None,8,40,True),
("🕌 Castelo dos Mouros, Sintra",38.7925,-9.3888,5,"moorish","Sintra",
 "🕌 9:30 AM the 8th–9th c. Moorish hilltop fortress — Portugal's Moorish highlight. Bus 434 loop from Sintra station ~15 min + short climb.",
 "https://www.parquesdesintra.pt/en/",9,120,False),
("⭐ Pena Palace",38.7877,-9.3906,5,"attraction","Sintra",
 "⭐ 12:00 PM timed entry — book the official Pena + Moorish Castle combo (~€26) 1–2 weeks ahead; August sells out. Grounds rate above the interior if slots are tight.",
 "https://www.parquesdesintra.pt/en/",12,120,False),
("⭐ Quinta da Regaleira (optional)",38.7963,-9.3963,5,"attraction","Sintra",
 "⭐ 2:30 PM optional — the initiation well (~€15). 25-min walk downhill from town or ~€8 tuk-tuk from Pena.",
 None,14,90,False),
("A Ginjinha 🍒",38.7145,-9.1388,5,"food","Lisbon",
 "🍒 A €1.50 shot of ginjinha — Lisbon's sour-cherry liqueur — knocked back standing at this hole-in-the-wall by Rossio, pouring since 1840. Anthony Bourdain stopped here; ask for it 'com' (with a boozy cherry) or 'sem'. 5 min as you come off the Sintra train, then up to Bairro Alto.",
 None,18,10,False),
("Bairro Alto (evening)",38.7118,-9.1447,5,"food","Lisbon",
 "🍽 ~5 PM train back (~40 min). Bairro Alto is a 10-min uphill walk from Rossio or one Glória funicular ride; sunset drinks + dinner (Bonjardim piri-piri, Tasca do Manel).",
 None,19,90,False),

# ---- Day 6: Belém + azulejos ----
("⭐🕌 Jerónimos Monastery, Belém",38.6979,-9.2065,6,"moorish","Lisbon",
 "⭐ 9:30 AM at opening (book ahead, ~€18). Manueline masterpiece; then Belém Tower exterior and the original pastéis de Belém next door.",
 None,9,120,False),
("Pastéis de Belém",38.6975,-9.2032,6,"food","Lisbon",
 "🍽 The original custard tarts, since 1837 — €2–5 snack beside the monastery.",
 None,11,30,False),
("⭐ Oceanário de Lisboa",38.7634,-9.0938,6,"attraction","Lisbon",
 "⭐ 1:00 PM choose one: Oceanário (one of the world's best aquariums, ~€25, A/C, a guaranteed hit)…",
 "https://www.oceanario.pt/en",13,120,False),
("🕌 National Tile Museum (Azulejo)",38.7247,-9.1136,6,"moorish","Lisbon",
 "🕌 …or the Museu do Azulejo — the tile tradition is a direct Moorish inheritance, also A/C. (Alternative to the Oceanário.)",
 None,13,120,False),
("As Bifanas do Afonso 🥪",38.7121,-9.1356,6,"food","Lisbon",
 "🥪 A bifana pit stop — the garlicky slow-cooked pork sandwich Anthony Bourdain rated one of Lisbon's best, at this tiny standing counter on Rua da Madalena in Baixa (right on the Tram 28 line you're about to ride). ~€2.50, eat on your feet, 15 min. Open Mon–Sat.",
 None,15,15,False),
("⭐ Tram 28 / Ler Devagar 📚",38.7159,-9.1338,6,"attraction","Lisbon",
 "⭐ 4:00 PM ride tram 28 end-to-end through Graça/Alfama (board mid-afternoon to dodge pickpocket crowds) — or LX Factory + 📚 Ler Devagar, the bookshop in a former print works.",
 None,16,60,False),
("⭐🛍 Embaixada (Príncipe Real)",38.7169,-9.1487,6,"shop","Lisbon",
 "⭐🛍 5:30 PM Portuguese cotton/linen/leather run — Embaixada (Portuguese designers in a Neo-Moorish palace 🕌), then A Vida Portuguesa in Chiado. Ask every shop for the tax-free form.",
 None,17,60,False),
("✊ Largo do Carmo",38.7118,-9.1401,6,"history","Lisbon",
 "✊ 7:15 PM the square where the Carnation Revolution ended on 25 April 1974 — the regime surrendered here while soldiers carried carnations in their rifles. The ruined Carmo Convent above is Lisbon's most atmospheric shell.",
 None,19,20,False),
("Time Out Market (dinner)",38.7071,-9.1459,6,"food","Lisbon",
 "🍽 8:00 PM Time Out Market or Cais do Sodré. Pack for the early flight; check in online.",
 None,20,90,False),

# ---- Day 7: Lisbon AM → fly to Seville → Eclipse ----
("⭐ Calouste Gulbenkian Museum",38.7376,-9.1537,7,"museum","Lisbon",
 "⭐ 10:00 AM (~€14, 10-min walk) — one of Europe's great private collections, Egyptian to Lalique, with a strong Islamic-art room 🕌. A/C, in gardens. Open Wednesdays.",
 "https://gulbenkian.pt/museu/en/",10,150,False),
("LIS → Seville ✈️ (Ryanair FR3628)",38.7742,-9.1342,7,"flight","Seville",
 "✈️ 2:50 PM taxi to LIS. FR3628 departs 5:20 PM, 1h05 nonstop → land SVQ 7:25 PM (Spain +1h). Priority + 2 cabin + 3×10 kg checked bags already paid. Check the boarding pass for T2.",
 "https://www.ryanair.com",17,120,True),
("🌘 Solar eclipse — SVQ arrival",37.4180,-5.8931,7,"eclipse","Seville",
 "🌘 ECLIPSE DAY. Partial begins ~7:30 PM as you walk off the plane; maximum ~8:30 PM (~85–90% covered), the Sun 8–10° above the western horizon. Watch max from arrivals with a clear WESTERN view. Bring 3 pairs of ISO 12312-2 glasses from the US — sold out across Spain. Verify minutes at timeanddate.com/eclipse.",
 "https://www.timeanddate.com/eclipse/",20,60,False),
("Hotel Giralda Center 🏨",37.3833,-5.9822,7,"hotel","Seville",
 "🏨 Aug 12–15 (BOOKED, $516.60). San Bernardo — 1 double + 2 twins + sofa bed, the room genuinely built for 3. Rooftop pool. To hotel: Tussam EA bus €4 + walk, or taxi €25.",
 None,21,0,True),
("Barrio Santa Cruz — late tapas",37.3855,-5.9905,7,"food","Seville",
 "🍽 9:45 PM Santa Cruz lanes by night + rooftop drink with Giralda view (La Terraza de EME). 10:15 PM late tapas — Spanish dinner time from night one.",
 None,22,90,False),

# ---- Day 8: Córdoba · Setenil · Ronda (guided bus tour) ----
("🚌 Tour pickup — Prado de San Sebastián",37.3852,-5.9857,8,"bus","Seville",
 "🚌 BOOKED full-day guided tour: Córdoba + Setenil de las Bodegas + Ronda. Meet at the Touristic Bus Stop, Av. de Menéndez Pelayo 1. ⚠️ Be there 08:15 (15 min before) — departs 08:30 sharp and won't wait. ~8-min walk from the hotel. Long day: back here 21:30. Water, hat, sunscreen, real walking shoes.",
 None,8,15,True),
("🕌 Córdoba old town — guided walk",37.8785,-4.7800,8,"moorish","Cordoba",
 "🕌 10:15 AM, after the 1h45 coach ride — guided walking tour of the old town: the Judería's whitewashed lanes, the flower-hung patios, and the Roman bridge over the Guadalquivir. Córdoba is routinely Spain's hottest city (38–41°C); the guide sets the pace, so keep water on you.",
 "https://www.turismodecordoba.org/en",10,60,False),
("⭐🕌 Mezquita-Catedral, Córdoba",37.8790,-4.7794,8,"moorish","Cordoba",
 "🕌⭐ 11:15 AM — TICKETS BOOKED, guided tour of the Mosque-Cathedral. The great mosque's forest of red-and-white arches (8th–10th c.) with a Renaissance cathedral dropped into the middle of it. The centrepiece of the whole Moorish thread and the best thing in Córdoba.",
 "https://mezquita-catedraldecordoba.es/en/",11,60,False),
("Lunch in Córdoba (free time)",37.8846,-4.7772,8,"food","Cordoba",
 "🍽 12:15–13:30 free time for lunch. Salmorejo + flamenquín: Taberna Salinas (patio taberna since 1879), or Bar Santos' famous giant tortilla slice right by the Mezquita. ⚠️ Back at the coach by 13:30 — it leaves for Setenil without you.",
 None,12,75,False),
("Setenil de las Bodegas 🌄",36.8642,-5.1808,8,"attraction","Setenil",
 "🌄 15:15 arrive (1h45 coach). The town built INTO the rock — whitewashed houses tucked under vast overhanging cliffs along the Trejo, whole streets roofed by stone. Guided walk; Calle Cuevas del Sol is the famous stretch. Genuinely shady — a relief after Córdoba. Depart 16:00.",
 "https://www.andalucia.org/en/setenil-de-las-bodegas",15,45,False),
("⭐ Ronda — Puente Nuevo 🌄",36.7420,-5.1662,8,"viewpoint","Ronda",
 "⭐🌄 16:30 arrive (30-min drive). Guided walk across the Puente Nuevo — the 18th-c. bridge spanning the 120 m El Tajo gorge — plus the historic quarter and the clifftop miradores. At 750 m it's the coolest, breeziest stop of the day. 1h45 here; depart 18:15 for the 3h15 ride back.",
 "https://www.turismoderonda.es/en/",16,105,False),
("🚌 Back in Seville",37.3852,-5.9857,8,"bus","Seville",
 "🚌 21:30 drop-off at the same Touristic Bus Stop, ~8-min walk home. Thirteen hours door to door — Spanish kitchens are still going at 22:00 if you want late tapas in Santa Cruz, or just collapse. Tomorrow starts at 9:30, so there's no rush.",
 None,21,0,False),

# ---- Day 9: Seville's Moorish core ----
("🕌 Real Alcázar",37.3830,-5.9906,9,"moorish","Seville",
 "🕌 9:30 AM at opening — Spain's finest Mudéjar palace. Book the earliest slot 2+ weeks ahead on the OFFICIAL site (€15.50; resellers charge 2–3×). Allow 2.5h; add Cuarto Real Alto if offered.",
 "https://realalcazarsevilla.sacatuentrada.es/en",9,150,False),
("🕌 Cathedral + Giralda",37.3859,-5.9932,9,"moorish","Seville",
 "🕌 12:30 PM (~€13 timed) — climb the 12th-c. Almohad minaret; ramps, not stairs, built for a horse.",
 "https://www.catedraldesevilla.es",12,90,False),
("Siesta / pool 🏊",37.3833,-5.9822,9,"hotel","Seville",
 "☀️ 2:00–6:00 PM long lunch, siesta, pool — and you'll want it after yesterday's 13-hour tour. Heat protocol: sights 8:30–12:00, rest 14:00–18:00, back out after 19:00.",
 None,14,0,True),
("⭐🕌 Casa de Pilatos",37.3906,-5.9878,9,"moorish","Seville",
 "⭐🕌 6:30 PM (~€12) — Mudéjar-Renaissance mansion, gorgeous and nearly empty late-day. Or ⭐ Setas de Sevilla rooftop at sunset (~€15).",
 None,18,75,False),
("⭐ Plaza de España",37.3775,-5.9868,9,"attraction","Seville",
 "⭐ 8:30 PM in golden light (free), your closest big sight. Then optional Triana flamenco — Teatro Flamenco Triana or Casa de la Guitarra, €20–30. Pack tonight: the Granada train leaves 09:55 tomorrow.",
 None,20,60,False),

# ---- Day 10: Train to Granada → Albaicín ----
("Seville → Granada 🚆",37.3919,-5.9757,10,"train","Granada",
 "🚆 BOOKED — Avant 08295, 09:55 Sevilla Santa Justa → 12:35 Granada (Turista, Sat Aug 15). ⚠️ Assumption Day — glad it's locked in. Arrive 12:35; hotel check-in from 1:30.",
 "https://www.renfe.com/es/en",10,160,True),
("Meliá Granada 🏨",37.1735,-3.5990,10,"hotel","Granada",
 "🏨 Aug 15–17 (BOOKED, $438.50). Puerta Real — most central base of the trip. Premium Double booked for 3 — call +34 958 22 74 00 to add a bed. 15-min walk to Plaza Nueva. 1:30–6 PM check in, lunch, rest through the heat.",
 None,13,0,True),
("🕌 Albaicín → Mirador de San Nicolás 🌄",37.1809,-3.5924,10,"moorish","Granada",
 "🕌🌄 Head into the old Moorish quarter (UNESCO) ~7:30 PM and work your way up — but time it to be at the Mirador de San Nicolás railing for the ~9:08 PM sunset, when the light sets the Alhambra glowing with the Sierra Nevada behind. The single best free view of the trip; go early enough to claim a spot on the wall. 20–25 min uphill walk or C31/C32 minibus.",
 None,19,135,False),
("Calle Navas — free-tapas crawl",37.1740,-3.5975,10,"food","Granada",
 "🍽 ~9:30 PM free-tapas crawl on Calle Navas or Plaza Nueva (Granada eats late — a post-sunset start is normal) — a ~€3 drink still buys a tapa. Bodegas Castañeda, Los Diamantes, Bar Poë.",
 None,21,90,False),
("Taberna La Tana 🍷",37.1726,-3.5946,10,"food","Granada",
 "🍷 Anthony Bourdain's Granada tapas stop on 'Parts Unknown' — a snug Realejo wine bar (since 1993) with a 600-bottle cellar and a free tapa with every glass (~€3). A few doors off the Calle Navas crawl; the deepest wine list in town.",
 None,22,45,False),

# ---- Day 11: The Alhambra ----
("🕌 THE ALHAMBRA + Generalife",37.1760,-3.5881,11,"moorish","Granada",
 "🕌 8:00 AM (BOOKED, non-changeable). ⚠️ Be at the Nasrid Palaces gate 30 min before the printed slot — a missed window is forfeited. Passports scanned; screenshot the QR codes. Full circuit 3.5–4h: Nasrid Palaces → Alcazaba → Partal → Generalife. Stone stays cool until ~10 AM.",
 "https://tickets.alhambra-patronato.es/en/",8,240,False),
("Rest / pool 🏊",37.1735,-3.5990,11,"hotel","Granada",
 "☀️ 1:00–5:00 PM lunch, rest, pool. Los Manueles (famous croquetas) 5 min from the hotel.",
 None,13,0,True),
("⭐ Royal Chapel + Cathedral",37.1765,-3.5985,11,"attraction","Granada",
 "⭐ 5:00 PM (~€13; verify Sunday hours) — the tombs of Ferdinand and Isabella, the Reconquista's endpoint: the perfect counterweight to the morning. Or 🛁 Hammam Al Ándalus Arab baths (€45–75, book ahead).",
 "https://granada.hammamalandalus.com/en/",17,60,False),
("✊ Centro Federico García Lorca",37.1760,-3.6000,11,"history","Granada",
 "✊ Lorca — Spain's great leftist literary martyr — was executed by Francoist forces outside Granada in August 1936. His centre (often free); his summer house Huerta de San Vicente sits in a park 15 min south for the fuller pilgrimage.",
 None,17,45,False),
("Sacromonte — carmen dinner 🌄",37.1830,-3.5870,11,"food","Granada",
 "🍽 8:30 PM Sacromonte cave district; dinner at a carmen with Alhambra views — Carmen Mirador de Aixa or Casa Juanillo (in-budget). Reserve. The terrace catches the ~9:08 PM Alhambra sunset; later, the Perseids are still flying (just past their Aug 12–13 peak) and the young crescent Moon sets early for decent dark skies.",
 None,20,120,False),

# ---- Day 12: Train to Madrid ----
("Granada → Madrid 🚆",37.1918,-3.6089,12,"train","Madrid",
 "🚆 15:00 AVE Granada → Madrid, arrive 18:39 (~3h40 direct, ~€53). Picked over the 06:09 (too early after Sacromonte) and the 11:04 Alvia (bus-transfer interruption mid-route). ⚠️ Confirm arrival station — Atocha vs Chamartín. Slow Granada morning first.",
 "https://www.renfe.com/es/en",15,220,True),
("Airbnb — Plaza Mayor 🏨",40.4155,-3.7075,12,"hotel","Madrid",
 "🏨 Aug 17–20 (BOOKED, $651.36 paid). Calle de Felipe III 6, directly on Plaza Mayor. Check in ~7:15 PM after the train. Doorstep: Mercado de San Miguel 2 min, Botín 2 min, Casa Hernanz 3 min, Sol 4 min, Royal Palace 10 min. Save door codes offline; pack earplugs.",
 None,19,0,True),
("La Casa del Abuelo 🦐",40.4165,-3.7018,12,"food","Madrid",
 "🦐 Gambas al ajillo since 1906 — the sizzling garlic-shrimp tapa Anthony Bourdain came for, at the standing-room original off Puerta del Sol. Pair it with a chato of sweet 'vino del abuelo,' ~€12–15. Your first-night Madrid tapa, a few steps off Sol on the way to dinner.",
 None,20,20,False),
("La Latina → Mercado de San Miguel",40.4154,-3.7090,12,"food","Madrid",
 "🍽 8:30 PM La Latina tapas crawl → Plaza Mayor → Mercado de San Miguel (2 min from your door). 🇪🇸 Friend alt in Lavapiés: Taberna El Sur, near ✊ Traficantes de Sueños left bookshop.",
 None,20,120,False),

# ---- Day 13: Madrid full day ----
("✊ Reina Sofía (Guernica)",40.4079,-3.6947,13,"museum","Madrid",
 "✊ 10:00 AM (€12) — built around Picasso's Guernica, the century's great anti-fascist painting. 🇪🇸 One friend rates it over the Prado; the Prado is later today in its free window.",
 "https://www.museoreinasofia.es/en",10,105,False),
("📚 Cuesta de Moyano book stalls",40.4103,-3.6890,13,"history","Madrid",
 "📚 11:45 AM open-air secondhand book stalls (since 1925) on the rise between Atocha and Retiro — Madrid's classic radical-and-rare browse, 20 min, en route to the Muralla.",
 None,11,20,False),
("🕌 Muralla Árabe",40.4150,-3.7135,13,"moorish","Madrid",
 "🕌 12:30 PM the 9th-c. Arab wall below Almudena Cathedral, from Madrid's founding as Moorish Mayrit (free). 🇪🇸 From this low angle the cathedral finally shows real depth — the below-the-parks approach the friends recommend.",
 None,12,45,False),
("⭐ San Ginés churros",40.4165,-3.7065,13,"food","Madrid",
 "🍽⭐ 2:00 PM long lunch; San Ginés churros con chocolate (since 1894) for dessert, 12-min walk up Calle Mayor. Casa Revuelta (fried bacalao) 2 min from the Airbnb.",
 None,14,90,False),
("⭐🛍 Casa Hernanz → Gran Vía shops",40.4130,-3.7080,13,"shop","Madrid",
 "⭐🛍 4:30 PM Casa Hernanz (handmade espadrilles since 1845, from ~€15), then Gran Vía → Calle Fuencarral/Chueca for Spanish brands, or Calle de Serrano for leather (Loewe, Camper). Collect tax-free forms; refund at MAD DIVA kiosks tomorrow.",
 None,16,90,False),
("⭐ Museo del Prado",40.4138,-3.6921,13,"museum","Madrid",
 "⭐ 6:00 PM the Prado in its free window (Mon–Sat 18:00–20:00) — walk over from the Gran Vía shops, skip the ticket line and hit the greatest hits: Velázquez's Las Meninas, Goya's black paintings, Bosch's Garden of Earthly Delights (~1.5-hr focused loop). Then taxi to Debod for the sunset. The Reina Sofía this morning is its modern counterpart on the same Paseo del Prado axis.",
 "https://www.museodelprado.es/en",18,105,False),
("⭐ Templo de Debod (sunset) 🌄",40.4240,-3.7176,13,"attraction","Madrid",
 "⭐ 8:45 PM an actual 2nd-c. BC Egyptian temple — Madrid's best sunset spot, free, ~25 min on foot from the Airbnb and worth every step at dusk.",
 None,20,45,False),
# ---- Day 14: Toledo + Segovia guided coach tour (operator schedule) ----
("🚌 Tour meet-up — Ventas / Calle Julio Camba",40.4300,-3.6670,14,"bus","Madrid",
 "🚌 BOOKED full-day guided tour (Ibetours): Toledo then Segovia. Departure 08:30 from Ventas — the guide waits where Calle Julio Camba meets Calle de Alcalá. ⚠️ Be there ~08:15. Metro line 2 runs straight from Sol to Ventas (~10 min) then a 4-min walk, so leave the flat by 07:45; taxi ~12 min. Back in Madrid 19:45. Water, hat, real walking shoes.",
 None,8,15,True),
("🌄 Toledo panoramic tour (from the coach)",39.8500,-4.0230,14,"viewpoint","Toledo",
 "🌄 09:30 arrive Toledo — the coach first does the panoramic loop on the far bank, the classic postcard of the whole city stacked above the Tagus (this is the Mirador del Valle road). Have your camera ready; on a tour coach this is usually a short photo stop rather than a long one.",
 None,9,60,False),
("⭐ Toledo walking tour + Cathedral",39.8570,-4.0273,14,"attraction","Toledo",
 "⭐ 10:30–11:30 guided walk through the old town and into the cathedral. ⚠️ Cathedral entry is PAY ON SITE (~€12), not included — carry a card. Spain\'s High Gothic primate cathedral: the Transparente, the sacristy\'s El Grecos and a Goya.",
 "https://www.catedralprimada.es",10,60,False),
("⭐ Santo Tomé (El Greco) — free time",39.8574,-4.0283,14,"attraction","Toledo",
 "⭐ 11:30–12:30 FREE TIME, one hour only — spend it here first. Santo Tomé (~€4): El Greco\'s Burial of the Count of Orgaz, one canvas, ten minutes, and a 5-min walk from the cathedral. The single best use of a short window.",
 "https://santotome.org",11,30,False),
("🕌 Cristo de la Luz / Santa María la Blanca (free time)",39.8563,-4.0296,14,"moorish","Toledo",
 "🕌 Same 11:30–12:30 window, if Santo Tomé left you time. The Mudéjar synagogues Santa María la Blanca + El Tránsito are ~5 min further west; the mosque of 999 AD (Cristo de la Luz) is up at the north gate, ~15 min the other way. ⚠️ With one hour you realistically add ONE of these — pick the synagogues, they\'re closer. Skip the €12 wristband on a stop this short; pay singly. Coach leaves 12:30 sharp.",
 "https://toledomonumental.com",12,25,False),
("Lunch in Segovia",40.9489,-4.1189,14,"food","Segovia",
 "🍽 14:30 arrive Segovia after the 2-hr transfer, and lunch runs to 16:00. Segovia\'s one dish is cochinillo asado, suckling pig roasted until it\'s carved with the edge of a plate — Mesón de Cándido by the aqueduct is the famous one (~€30, book ahead), Mesón José María the locals\' pick. Eat quickly if you want the mirador (next stop).",
 None,14,90,False),
("Segovia Aqueduct + walking tour",40.9481,-4.1177,14,"attraction","Segovia",
 "🏛 16:00 guided walking tour, starting at the Roman aqueduct — 1st-c. AD, 167 arches, 28 m tall, assembled without a drop of mortar — then up through the old town toward the Alcázar.",
 "https://www.turismodesegovia.com/en/",16,60,False),
("⭐ Alcázar of Segovia",40.9526,-4.1327,14,"attraction","Segovia",
 "⭐ 17:00 admission, INCLUDED in the tour. The castle on the rock spur where the Eresma and Clamores meet — the silhouette behind Disney\'s Cinderella Castle. Climb the Torre de Juan II if there\'s time. Coach leaves Segovia 18:30.",
 "https://www.alcazardesegovia.com/en/",17,75,False),
("🌄 Mirador de la Pradera de San Marcos (optional)",40.9558,-4.1355,14,"viewpoint","Segovia",
 "🌄 OPTIONAL, on your own — THE lower view: a riverside glade by the Iglesia de San Marcos where the Alcázar rears over the treeline like a ship\'s prow. The Berserk / Disney angle, and it only works from below. ⚠️ GENUINELY TIGHT in this schedule — it\'s ~15 min down from the Alcázar and ~20 back up, against a 18:30 departure. Best play: cut lunch short (eat by 15:15), walk ahead to the Alcázar side and drop to the mirador while the 16:00 walking tour is still working up through town, then rejoin for the 17:00 admission. Clear it with the guide first.",
 None,18,30,False),
("🚌 Back in Madrid — tour drop-off",40.4300,-3.6670,14,"bus","Madrid",
 "🚌 19:45 drop-off back at Ventas / Calle Julio Camba. Metro line 2 Ventas → Sol (~10 min) puts you at Plaza Mayor by ~20:15 — a civilised hour for the farewell dinner around the corner.",
 None,19,0,False),
("Botín — farewell dinner",40.4147,-3.7085,14,"food","Madrid",
 "🍽 ~8:45 PM farewell dinner (BOOK AHEAD — 6-week waitlist): Botín, the world\'s oldest restaurant, cochinillo ~€45–50 pp, 2 min from your door. The 19:45 return leaves a comfortable hour to drop bags and change first. In-budget fallback: La Sanabresa, menú ~€15. Pack tonight; pre-book tomorrow\'s taxi.",
 None,20,120,False),

# ---- Day 15: Fly home ----
("Free Madrid morning",40.4155,-3.7075,15,"attraction","Madrid",
 "☕ Plaza Mayor at 9 AM is empty and beautiful — coffee on the square, San Ginés churros 3 min away. The 2:35 PM departure leaves room for one last sight.",
 None,9,60,True),
("Royal Palace (from below) + Campo del Moro",40.4180,-3.7143,15,"attraction","Madrid",
 "🇪🇸 ~10:00 AM last stop — the Royal Palace, done the way your friends advise: skip the interior (no time before the flight) and take the low approach via Plaza de Oriente / Cuesta de la Vega into the Campo del Moro gardens (free, open 10:00) for the façade with real depth. Back to Plaza Mayor by ~10:45 to grab bags; 11:00 taxi to MAD.",
 None,10,45,True),
("Sala VIP Cibeles (Priority Pass) — MAD 🛋️",40.4900,-3.5700,15,"lounge","Transit",
 "🛋️ Before the flight home — no Capital One lounge in Madrid, so Priority Pass: Sala VIP Cibeles, Terminal 1, airside past passport control by gates B26–B29 (stairs/lift up to level 2), with runway views and an outdoor terrace. Priority Pass caps you at 3 hours, which fits neatly between your ~11:35 AM arrival and the 2:35 PM flight. ⚠️ Check your boarding pass says T1 — if it's T2/T3, use the Sala VIP Puerta del Sol instead (also Priority Pass).",
 "https://www.prioritypass.com/lounges/spain/madrid-barajas/madc-sala-vip-cibeles",12,120,True),
("MAD → DCA ✈️ (depart 2:35 PM)",40.4936,-3.5668,15,"flight","Transit",
 "✈️ 11:00 AM taxi to MAD (flat €33, ~30 min) — arrive ~11:35, 3 hrs early. Claim VAT refunds at the DIVA kiosks airside (Spain has no minimum spend). Delta DL63 MAD→Boston 2:35 PM (land 4:31 PM), 3h34 layover, then DL5666 BOS→DCA (land 10:05 PM EDT). You land at DCA, not IAD. At BOS you clear US immigration/customs, then re-clear security for the domestic hop out of Terminal A — see the next stop for the Chase Sapphire Lounge you can use on your Venture X.",
 "https://www.delta.com",14,0,True),
("Chase Sapphire Lounge — BOS 🛋️",42.3665,-71.0175,15,"lounge","Transit",
 "🛋️ BOS layover — Chase Sapphire Lounge by The Club, in the Terminal B–C connector (gates B39–B40). Your Venture X Priority Pass gets each traveller 1 free visit per calendar year here ($75/person after that), so this is the one BOS lounge you can actually use. ⚠️ Catch: your DCA flight leaves Terminal A, which isn't airside-connected to B/C — so you'd clear security at B/C for the lounge, then exit and re-clear at A. Worth it if customs is quick and you've time to spare; otherwise head straight to A. Genuinely stunning space if you go.",
 "https://www.prioritypass.com/en-GB/lounges/united-states-of-america/logan-international/bos19-chase-sapphire-lounge-by-the-club",17,90,False),
]

# ═══════════════════════ INTERCITY LEGS (route polylines) ═══════════════════
# Train legs trace the real rail corridor via intermediate stations/junctions;
# the flight leg stays a direct great-circle dashed line.
LEGS = [
 {"name":"Porto → Lisbon","mode":"train","day":4,"note":"Alfa Pendular · ~3h · Linha do Norte",
  "a":(41.1490,-8.5850),"b":(38.7139,-9.1224),
  "via":[(41.0075,-8.6410),(40.6430,-8.6400),(40.2220,-8.4350),(39.9130,-8.6280),
         (39.4650,-8.4720),(39.2630,-8.6870),(38.9550,-8.9900)]},  # Espinho·Aveiro·Coimbra·Pombal·Entroncamento·Santarém·VFXira
 {"name":"Lisbon → Seville","mode":"flight","day":7,"note":"Ryanair FR3628 · 1h05",
  "a":(38.7742,-9.1342),"b":(37.4180,-5.8931)},
 # Day 8 guided-coach legs (Setenil → Ronda is short enough to street-route as a segment)
 {"name":"Seville → Córdoba","mode":"bus","day":8,"min":105,"note":"Tour coach · 08:30–10:15 · A-4 via Carmona & Écija",
  "a":(37.3852,-5.9857),"b":(37.8785,-4.7800),
  "via":[(37.4716,-5.6417),(37.5417,-5.0825),(37.6733,-4.9317)]},
 {"name":"Córdoba → Setenil","mode":"bus","day":8,"min":105,"note":"Tour coach · 13:30–15:15 · south through the campiña",
  "a":(37.8785,-4.7800),"b":(36.8642,-5.1808),
  "via":[(37.5500,-4.6500),(37.1500,-4.7500),(36.9800,-4.9500),(36.9000,-5.1000)]},
 {"name":"Ronda → Seville","mode":"bus","day":8,"min":195,"note":"Tour coach · 18:15–21:30 · A-374/A-375 via Algodonales",
  "a":(36.7420,-5.1662),"b":(37.3852,-5.9857),
  "via":[(36.8850,-5.4050),(36.9800,-5.5800),(37.1800,-5.7800)]},
 {"name":"Seville → Granada","mode":"train","day":10,"note":"Renfe Avant · direct ~2h40 via Antequera",
  "a":(37.3919,-5.9757),"b":(37.1918,-3.6089),
  "via":[(37.2950,-5.4400),(37.2380,-5.1000),(37.1600,-4.6100),(37.1800,-4.1000),(37.1900,-3.7500)]},  # Osuna·Antequera-Santa Ana
 {"name":"Granada → Madrid","mode":"train","day":12,"note":"AVE via Antequera & Córdoba · ~3h20",
  "a":(37.1918,-3.6089),"b":(40.4067,-3.6906),
  "via":[(37.1600,-4.6100),(37.8400,-4.8100),(37.8918,-4.7908),(38.3800,-4.4000),
         (38.6900,-4.1070),(38.9860,-3.9270),(39.8600,-3.7300)]},  # Antequera·Córdoba·Puertollano·Ciudad Real
 # Day 14 guided coach: Madrid → Segovia → Toledo → Madrid
 # No hand-placed waypoints here: they dragged the coach off the motorway
 # (Madrid→Segovia came out 155 km against a real ~92). Let the router pick.
 {"name":"Madrid → Toledo","mode":"bus","day":14,"min":60,"note":"Tour coach · 08:30–09:30 · A-42 south · ~75 km",
  "a":(40.4300,-3.6670),"b":(39.8500,-4.0230)},
 {"name":"Toledo → Segovia","mode":"bus","day":14,"min":120,"note":"Tour coach · 12:30–14:30 · round the west of Madrid · ~165 km",
  "a":(39.8570,-4.0273),"b":(40.9481,-4.1177)},
 {"name":"Segovia → Madrid","mode":"bus","day":14,"min":75,"note":"Tour coach · 18:30–19:45 · AP-61/AP-6 over the Guadarrama · ~92 km",
  "a":(40.9481,-4.1177),"b":(40.4300,-3.6670)},
 # Transatlantic + US flight legs. Drawn on their day layer; the timeline
 # selector frames these only when you pick Day 1 or Day 15 (see build_scrubber),
 # so the rest of the trip keeps its Iberia-only zoom.
 {"name":"Washington → Paris","mode":"flight","day":1,"far":True,"note":"Delta DL8752 (Air France) · IAD→CDG · ~7h30 overnight",
  "a":(38.9531,-77.4565),"b":(49.0097,2.5479)},
 {"name":"Paris → Porto","mode":"flight","day":2,"far":True,"min":145,"note":"Delta DL8306 · CDG→OPO · 14:00–15:25 · ~2h25",
  "a":(49.0097,2.5479),"b":(41.2481,-8.6814)},
 {"name":"Madrid → Boston","mode":"flight","day":15,"far":True,"note":"Delta DL63 · MAD→BOS · transatlantic ~8h",
  "a":(40.4936,-3.5668),"b":(42.3656,-71.0096)},
 {"name":"Boston → Washington","mode":"flight","day":15,"far":True,"note":"Delta DL5666 · BOS→DCA · ~1h30",
  "a":(42.3656,-71.0096),"b":(38.8512,-77.0402)},
]

# ─── Transport modes: colour + line style + routing engine per mode ─────────
# walk/taxi/bus follow real streets (Valhalla/OSM, cached); metro/tram/train/
# flight run on rails or air, so they are drawn as clean direct hops.
MODE_STYLE = {
 "walk":  {"color":"#5f8b57","dash":"1 7","w":3,"label":"🚶 Walk","costing":"pedestrian","spd":4.8},
 "taxi":  {"color":"#cc8642","dash":None, "w":4,"label":"🚕 Taxi","costing":"auto","spd":22},
 "bus":   {"color":"#3c8f8a","dash":None, "w":4,"label":"🚌 Bus","costing":"bus","spd":15},
 "metro": {"color":"#4a6fa5","dash":"7 6","w":4,"label":"🚇 Metro","costing":None,"spd":30},
 "tram":  {"color":"#8a6193","dash":"7 6","w":4,"label":"🚊 Tram","costing":None,"spd":14},
 "train": {"color":"#b8503a","dash":None, "w":4,"label":"🚆 Train","costing":None,"spd":90},
 "flight":{"color":"#7d7770","dash":"10 8","w":4,"label":"✈️ Flight","costing":None,"spd":700},
}
# Mode used to REACH each stop from the previous stop that day (default = walk).
# Straight from the itinerary's stated transport for each hop.
MODE_TO = {
 "Ribeira riverfront":"taxi",
 "🍷 Graham's 1890 Port Lodge":"taxi",
 "O Valentim (dinner, Matosinhos)":"metro",
 "🕌 Alfama + Miradouro de Santa Luzia":"metro",
 "As Bifanas do Afonso 🥪":"metro",
 "⭐ Pena Palace":"bus",
 "⭐ Oceanário de Lisboa":"taxi",
 "🕌 National Tile Museum (Azulejo)":"taxi",
 "⭐ Tram 28 / Ler Devagar 📚":"tram",
 "⭐🛍 Embaixada (Príncipe Real)":"walk",   # no clean single metro line to Príncipe Real
 "Hotel Giralda Center 🏨":"taxi",
 "⭐ Ronda — Puente Nuevo 🌄":"bus",
 "🕌 Albaicín → Mirador de San Nicolás 🌄":"bus",
 "Rest / pool 🏊":"taxi",
 "Sacromonte — carmen dinner 🌄":"taxi",
 "🕌 Muralla Árabe":"taxi",
 "⭐ Templo de Debod (sunset) 🌄":"taxi",
 "Botín — farewell dinner":"metro",
 "🚌 Tour meet-up — Ventas / Calle Julio Camba":"metro",
 "Lunch in Segovia":"walk",
 "Sala VIP Cibeles (Priority Pass) — MAD 🛋️":"taxi",
}

def arrive_mode(day, name, first):
    if first: return None
    return MODE_TO.get(name, "walk")

# Named coordinates for transfer hops (hotels, stations, airports)
_C = {
 "OPO":(41.2481,-8.6814),"Sheraton":(41.1580,-8.6293),"Campanha":(41.1490,-8.5850),"Lello":(41.1470,-8.6146),
 "Corinthia":(38.7370,-9.1656),"SeteRios":(38.7397,-9.1689),"SantaApolonia":(38.7139,-9.1224),"Rossio":(38.7143,-9.1400),
 "SintraSt":(38.7986,-9.3866),"Castelo":(38.7925,-9.3888),"Regaleira":(38.7963,-9.3963),
 "BairroAlto":(38.7118,-9.1447),"Jeronimos":(38.6979,-9.2065),"Gulbenkian":(38.7376,-9.1537),"LIS":(38.7742,-9.1342),
 "Giralda":(37.3833,-5.9822),"Alcazar":(37.3830,-5.9906),"SantaJusta":(37.3919,-5.9757),
 "BusStop":(37.3852,-5.9857),
 "CordobaSt":(37.8918,-4.7908),"Mezquita":(37.8790,-4.7794),
 "GranadaSt":(37.1918,-3.6089),"Melia":(37.1735,-3.5990),"Alhambra":(37.1760,-3.5881),
 "Atocha":(40.4067,-3.6906),"Airbnb":(40.4155,-3.7075),"ReinaSofia":(40.4079,-3.6947),
 "ToledoSt":(39.8628,-4.0273),"Cristo":(39.8607,-4.0247),"MAD":(40.4936,-3.5668),
 "JulioCamba":(40.4300,-3.6670),
}
# Connective hops the stop-to-stop logic can't derive: getting from the hotel to
# the station/airport (and from the arrival station to the first stop), plus the
# day-trip train legs. This is where the "gaps" were.
TRANSFERS = [
 (2,"taxi","OPO","Sheraton"),
 (4,"taxi","Sheraton","Campanha"),              # hotel → station, last day in Porto
 (4,"metro","SantaApolonia","Corinthia"),          # arrival station → hotel
 (5,"walk","Corinthia","SeteRios"),
 (5,"train","SeteRios","SintraSt"),
 (5,"bus","SintraSt","Castelo"),
 (5,"walk","Regaleira","SintraSt"),
 (5,"train","SintraSt","Rossio"),
 (7,"taxi","Gulbenkian","LIS"),                  # hotel-area → airport, last day in Lisbon
 (10,"taxi","Giralda","SantaJusta"),             # hotel → station, last day in Seville
 (10,"taxi","GranadaSt","Melia"),
 (12,"taxi","Melia","GranadaSt"),                # hotel → station, last day in Granada
 (12,"taxi","Atocha","Airbnb"),          # arriving with luggage
]
_LABEL = {
 "OPO":"OPO Airport","Sheraton":"Sheraton Porto","Campanha":"Porto Campanhã","Lello":"Livraria Lello",
 "Corinthia":"Corinthia Lisbon","SeteRios":"Sete Rios station","SantaApolonia":"Santa Apolónia","Rossio":"Rossio station",
 "SintraSt":"Sintra station","Castelo":"Castelo dos Mouros","Regaleira":"Quinta da Regaleira",
 "BairroAlto":"Bairro Alto","Jeronimos":"Jerónimos, Belém","Gulbenkian":"Gulbenkian Museum","LIS":"LIS Airport",
 "Giralda":"Hotel Giralda","Alcazar":"Real Alcázar","SantaJusta":"Sevilla Santa Justa",
 "BusStop":"Tour bus stop (Menéndez Pelayo)",
 "CordobaSt":"Córdoba station","Mezquita":"Mezquita-Catedral",
 "GranadaSt":"Granada station","Melia":"Meliá Granada","Alhambra":"The Alhambra",
 "Atocha":"Madrid Atocha","Airbnb":"Plaza Mayor Airbnb","ReinaSofia":"Reina Sofía",
 "ToledoSt":"Toledo station","Cristo":"Cristo de la Luz","MAD":"MAD Airport",
 "JulioCamba":"Tour meet-up (Calle Julio Camba)",
}

# ─── Hotel bookends ─────────────────────────────────────────────────────────
# Which bed each day starts from and returns to, so every day reads
# hotel → … → hotel. Markers are only inserted when the day doesn't already
# begin/end at that hotel (so Botín, 2 min from the Madrid door, adds nothing).
DAY_HOTEL = {
 2:(None,"Sheraton"),      3:("Sheraton","Sheraton"),  4:("Sheraton","Corinthia"),
 5:("Corinthia","Corinthia"), 6:("Corinthia","Corinthia"), 7:("Corinthia","Giralda"),
 8:("Giralda","Giralda"),  9:("Giralda","Giralda"),    10:("Giralda","Melia"),
 11:("Melia","Melia"),     12:("Melia","Airbnb"),      13:("Airbnb","Airbnb"),
 14:("Airbnb","Airbnb"),   15:("Airbnb",None),
}
HOTEL_LABEL = {
 "Sheraton":"the Sheraton","Corinthia":"the Corinthia","Giralda":"the Giralda Center",
 "Melia":"the Meliá","Airbnb":"the Plaza Mayor flat",
}
HOTEL_CITY = {"Sheraton":"Porto","Corinthia":"Lisbon","Giralda":"Seville",
              "Melia":"Granada","Airbnb":"Madrid"}
# Transport for the first hop out ("out") and the last hop back ("in"); default walk.
HOTEL_MODE = {
 (3,"out"):"metro", (6,"out"):"taxi", (11,"out"):"bus",
 (2,"in"):"taxi", (3,"in"):"metro", (4,"in"):"taxi", (5,"in"):"taxi",
 (6,"in"):"taxi", (11,"in"):"taxi",
}

def _with_hotel_bookends(stops):
    """Insert 'Leave …' / 'Back to …' hotel markers so each day is a closed loop."""
    out=[]
    for d in range(1,16):
        ds=[s for s in stops if s[3]==d]
        if not ds: continue
        start,end=DAY_HOTEL.get(d,(None,None))
        if start and _haversine((ds[0][1],ds[0][2]), _C[start])>0.15:
            la,lo=_C[start]
            ds.insert(0,(f"Leave {HOTEL_LABEL[start]}",la,lo,d,"hotel",HOTEL_CITY[start],
                f"🏨 Head out from {HOTEL_LABEL[start]} to start the day.",None,
                max(0,ds[0][8]-1),0,False))
        if end and _haversine((ds[-1][1],ds[-1][2]), _C[end])>0.15:
            la,lo=_C[end]
            ds.append((f"Back to {HOTEL_LABEL[end]}",la,lo,d,"hotel",HOTEL_CITY[end],
                f"🏨 Wind down — back to {HOTEL_LABEL[end]} for the night.",None,
                min(23,ds[-1][8]+1),0,False))
        out.extend(ds)
    return out

# Metro/tram hops can't be street-routed (Valhalla has no rail), so trace them
# through the real intermediate stations of the line they ride. Keyed by the
# segment's (from, to) names; drawn as a polyline through these station coords.
SEG_VIA = {
 # ── Madrid Metro · line 2 along Calle de Alcalá (Sol ↔ Ventas) ──
 #   Sol·Sevilla·Banco de España·Retiro·Príncipe de Vergara·Goya·Manuel Becerra·Ventas
 ("Leave the Plaza Mayor flat","🚌 Tour meet-up — Ventas / Calle Julio Camba"):
   [(40.4169,-3.7033),(40.4188,-3.6988),(40.4190,-3.6944),(40.4206,-3.6889),
    (40.4237,-3.6790),(40.4254,-3.6768),(40.4276,-3.6690),(40.4306,-3.6633)],
 ("🚌 Back in Madrid — tour drop-off","Botín — farewell dinner"):
   [(40.4306,-3.6633),(40.4276,-3.6690),(40.4254,-3.6768),(40.4237,-3.6790),
    (40.4206,-3.6889),(40.4190,-3.6944),(40.4188,-3.6988),(40.4169,-3.7033)],
 # ── Lisbon Metro · Blue line (Santa Apolónia ↔ Praça de Espanha) ──
 #   Terreiro do Paço · Baixa-Chiado · Restauradores · Avenida · Marquês · Parque · São Sebastião
 ("Santa Apolónia","Corinthia Lisbon"):
   [(38.7076,-9.1349),(38.7107,-9.1394),(38.7147,-9.1416),(38.7199,-9.1451),(38.7247,-9.1503),(38.7277,-9.1495),(38.7371,-9.1543)],
 ("Corinthia Lisbon 🏨","🕌 Alfama + Miradouro de Santa Luzia"):
   [(38.7371,-9.1543),(38.7277,-9.1495),(38.7247,-9.1503),(38.7199,-9.1451),(38.7147,-9.1416),(38.7107,-9.1394),(38.7076,-9.1349)],
 ("🕌 National Tile Museum (Azulejo)","As Bifanas do Afonso 🥪"):
   [(38.7139,-9.1224),(38.7076,-9.1349)],                       # Santa Apolónia → Terreiro do Paço
 # ── Porto Metro · Line A, following Carolina Michaëlis / Lapa / Trindade ──
 ("Leave the Sheraton","Livraria Lello 📚"):
   [(41.1580,-8.6295),(41.1575,-8.6218),(41.1592,-8.6152),(41.1522,-8.6094),(41.1487,-8.6111)],  # Casa da Música·Carolina Michaëlis·Lapa·Trindade·Aliados
 # Line A back east to Boavista; the hotel sits beside Casa da Música
 ("O Valentim (dinner, Matosinhos)","Back to the Sheraton"):
   [(41.1880,-8.6790),(41.1868,-8.6700),(41.1855,-8.6600),(41.1810,-8.6560),
    (41.1745,-8.6500),(41.1700,-8.6440),(41.1637,-8.6390),(41.1580,-8.6295)],
 # Gaia → bridge → Trindade, change to Line A and curve NW out to the Matosinhos coast
 # ── Road corridors: without these the router loops the long way round ──
 ("🌘 Solar eclipse — SVQ arrival","Hotel Giralda Center 🏨"):
   [(37.4150,-5.9050),(37.4020,-5.9450)],                        # straight down the A-4 into Seville
 ("🍷 Graham's 1890 Port Lodge","O Valentim (dinner, Matosinhos)"):
   # line D over the bridge: Jardim do Morro·São Bento·Aliados·Trindade, then
   # line A: Lapa·Carolina Michaëlis·Casa da Música·Francos·Ramalde·Viso·
   #         Sete Bicas·Senhora da Hora·Vasco da Gama·Estádio do Mar
   [(41.1383,-8.6089),(41.1457,-8.6106),(41.1487,-8.6111),(41.1522,-8.6094),
    (41.1592,-8.6152),(41.1575,-8.6218),(41.1580,-8.6295),(41.1637,-8.6390),
    (41.1700,-8.6440),(41.1745,-8.6500),(41.1810,-8.6560),(41.1855,-8.6600),
    (41.1868,-8.6700),(41.1880,-8.6790)],
}

# Real-world durations that beat any router estimate (booked schedules, etc.).
SEG_MIN = {
 ("Setenil de las Bodegas 🌄","⭐ Ronda — Puente Nuevo 🌄"):30,   # the tour's own 16:00→16:30
 # Long airport runs: the public router returns motorway-less times (60–115 min
 # for drives that really take 20–30). Use the real-world figures instead.
 ("🌘 Solar eclipse — SVQ arrival","Hotel Giralda Center 🏨"):20,
 ("Royal Palace (from below) + Campo del Moro","Sala VIP Cibeles (Priority Pass) — MAD 🛋️"):30,
 ("Gulbenkian Museum","LIS Airport"):20,
}

def _haversine(a, b):
    from math import radians, sin, cos, asin, sqrt
    la1,lo1,la2,lo2=map(radians,[a[0],a[1],b[0],b[1]])
    h=sin((la2-la1)/2)**2+cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
    return 2*6371*asin(sqrt(h))

S = _with_hotel_bookends(S)   # every day now reads hotel → … → hotel

def build_segments():
    """Ordered intra-day hops between consecutive place-stops, plus the explicit
    hotel↔station↔airport transfers. Skips hops into/out of a train/flight stop
    (those are the intercity legs) and any accidental >20 km teleport line."""
    segs=[]
    for d in range(1,16):
        ds=[s for s in S if s[3]==d]
        for i in range(1,len(ds)):
            prev,cur=ds[i-1],ds[i]
            if prev[4] in ("train","flight") or cur[4] in ("train","flight"): continue
            a,b=(prev[1],prev[2]),(cur[1],cur[2])
            if _haversine(a,b)>20: continue   # inter-city jump → handled by a leg/transfer
            if cur[0].startswith("Back to "):    mode=HOTEL_MODE.get((d,"in"),"walk")
            elif prev[0].startswith("Leave "):   mode=HOTEL_MODE.get((d,"out"),MODE_TO.get(cur[0],"walk"))
            else:                                mode=MODE_TO.get(cur[0],"walk")
            sg={"day":d,"mode":mode,
                "a":a,"b":b,"from":prev[0],"to":cur[0]}
            v=SEG_VIA.get((sg["from"],sg["to"]))
            if v: sg["via"]=v
            segs.append(sg)
    for d,mode,fa,fb in TRANSFERS:
        sg={"day":d,"mode":mode,"a":_C[fa],"b":_C[fb],
            "from":_LABEL[fa],"to":_LABEL[fb],"transfer":True}
        v=SEG_VIA.get((sg["from"],sg["to"]))
        if v: sg["via"]=v
        segs.append(sg)
    return segs

def valhalla_route(a, b, costing):
    """Return (coords, seconds) following the street network, or None."""
    payload={"locations":[{"lat":a[0],"lon":a[1]},{"lat":b[0],"lon":b[1]}],
             "costing":costing,"directions_options":{"units":"km"}}
    try:
        r=requests.post(VALHALLA_URL,json=payload,timeout=30); r.raise_for_status(); d=r.json()
        if "trip" not in d: return None
        cc=[]
        for leg in d["trip"]["legs"]:
            c=pl_lib.decode(leg["shape"],6)
            if cc and c and cc[-1]==c[0]: c=c[1:]
            cc.extend(c)
        secs=d["trip"].get("summary",{}).get("time")
        return (cc, secs) if cc else None
    except Exception:
        return None

def _poly_len(coords):
    return sum(_haversine(coords[i],coords[i+1]) for i in range(len(coords)-1)) if len(coords)>1 else 0.0

def _est_minutes(coords, mode):
    km=_poly_len(coords); spd=MODE_STYLE[mode]["spd"]
    if not spd: return 1
    mins=km/spd*60
    # rail isn't door-to-door: add walking to the platform, waiting and exiting
    mins+={"metro":5,"tram":4}.get(mode,0)
    return max(1, round(mins))

def catmull_rom(pts, n=22, alpha=0.5):
    """Centripetal Catmull-Rom spline through the waypoints → smooth rail curve."""
    pts=[list(p) for p in pts]
    if len(pts)<3: return pts
    P=[pts[0]]+pts+[pts[-1]]
    def dist(a,b): return (((a[0]-b[0])**2+(a[1]-b[1])**2)**0.5) or 1e-9
    out=[]
    for i in range(1,len(P)-2):
        p0,p1,p2,p3=P[i-1],P[i],P[i+1],P[i+2]
        t0=0.0; t1=t0+dist(p0,p1)**alpha; t2=t1+dist(p1,p2)**alpha; t3=t2+dist(p2,p3)**alpha
        for k in range(n):
            t=t1+(t2-t1)*(k/n)
            def L(a,b,ta,tb):
                r=0.0 if tb==ta else (t-ta)/(tb-ta)
                return [a[0]+(b[0]-a[0])*r, a[1]+(b[1]-a[1])*r]
            A1=L(p0,p1,t0,t1); A2=L(p1,p2,t1,t2); A3=L(p2,p3,t2,t3)
            B1=L(A1,A2,t0,t2); B2=L(A2,A3,t1,t3)
            C=L(B1,B2,t1,t2)
            out.append([round(C[0],5),round(C[1],5)])
    out.append([round(pts[-1][0],5),round(pts[-1][1],5)])
    return out

def flight_arc(a, b, n=26, k=0.11):
    """Gentle upward (northward) bow so flight paths read differently from
    land travel — a quadratic Bézier with the control point lifted north of
    the midpoint, scaled to the leg length (peak ≈ k/2 · chord)."""
    alat,alon=a; blat,blon=b
    mlat=(alat+blat)/2; mlon=(alon+blon)/2
    chord=((blon-alon)**2+(blat-alat)**2)**0.5
    clat=mlat + k*chord      # lift the control point north → arcs upward
    clon=mlon
    out=[]
    for i in range(n+1):
        t=i/n; u=1-t
        lat=u*u*alat + 2*u*t*clat + t*t*blat
        lon=u*u*alon + 2*u*t*clon + t*t*blon
        out.append([round(lat,4),round(lon,4)])
    return out

def build_paths():
    cache={}
    if os.path.exists(ROUTE_CACHE):
        try: cache=json.load(open(ROUTE_CACHE))
        except Exception: cache={}
    legs=[]
    for lg in LEGS:
        fallback=[list(lg["a"])]+[list(v) for v in lg.get("via",[])]+[list(lg["b"])]
        if lg["mode"]=="flight":
            pts=flight_arc(lg["a"], lg["b"])           # gentle upward arc
        elif lg["mode"]=="bus":
            # Coach legs run on real roads → street-route them (cached), routing
            # through the via points so the corridor matches the tour's actual line.
            pts=[]; ok=True
            for i in range(len(fallback)-1):
                a,b=tuple(fallback[i]),tuple(fallback[i+1])
                key=hashlib.md5(f'leg{a}{b}bus'.encode()).hexdigest()
                ce=cache.get(key)
                if isinstance(ce, dict): part=ce["c"]
                else:
                    res=valhalla_route(a,b,"bus")
                    if res:
                        part,secs=res; cache[key]={"c":part,"t":secs}; time.sleep(0.4)
                    else: ok=False; break
                if pts and part and pts[-1]==part[0]: part=part[1:]
                pts.extend(part)
            if not ok or not pts: pts=fallback      # straight fallback until a networked run
        else:
            pts=fallback
            if lg["mode"]=="train": pts=catmull_rom(pts)   # smooth rail curve
        legs.append((lg,pts))
    print("Resolving intra-city paths…")
    segs=[]; routed=0
    for sg in build_segments():
        costing=MODE_STYLE[sg["mode"]]["costing"]
        via=sg.get("via")
        coords=[list(sg["a"])]+[list(v) for v in (via or [])]+[list(sg["b"])]; secs=None
        if costing:
            # Route each consecutive pair, so a `via` corridor is honoured on roads
            # too (the plain a→b route sometimes takes an absurd detour).
            chain=[tuple(sg["a"])]+[tuple(v) for v in (via or [])]+[tuple(sg["b"])]
            parts=[]; tot=0.0; ok=True
            for i in range(len(chain)-1):
                a,b=chain[i],chain[i+1]
                key=hashlib.md5(f'{a}{b}{costing}'.encode()).hexdigest()
                ce=cache.get(key); part=None; t=None
                if isinstance(ce, dict): part=ce["c"]; t=ce.get("t")
                else:
                    res=valhalla_route(a,b,costing)
                    if res:
                        part,t=res; cache[key]={"c":part,"t":t}; time.sleep(0.4)
                    elif isinstance(ce, list) and len(chain)==2:
                        part=ce                      # old coords-only cache
                if part is None: ok=False; break
                if parts and part and parts[-1]==part[0]: part=part[1:]
                parts.extend(part)
                tot=None if (t is None or tot is None) else tot+t
            if ok and parts:
                coords=parts; secs=tot; routed+=1
        sg["min"]=max(1, round(secs/60)) if secs is not None else _est_minutes(coords, sg["mode"])
        sg["min"]=SEG_MIN.get((sg["from"],sg["to"]), sg["min"])   # known real-world timings win
        segs.append((sg,coords))
    try: json.dump(cache,open(ROUTE_CACHE,"w"))
    except Exception: pass
    print(f"  {routed}/{len(segs)} intra-city hops street-routed (rest drawn direct)")
    return {"legs":legs,"segs":segs}

# ═══════════════════════ THEME / ICON HELPERS ═══════════════════════
TYPE_ICON = {  # (fa icon, override marker colour or None → use region colour)
 "hotel":("bed",None),"flight":("plane","gray"),"train":("train","gray"),
 "food":("utensils","purple"),"shop":("bag-shopping","pink"),
 "moorish":("mosque","darkred"),"history":("fist-raised","black"),
 "museum":("palette",None),"attraction":("camera",None),
 "viewpoint":("binoculars",None),"church":("church",None),"eclipse":("sun","black"),
 "lounge":("couch","darkblue"),"bus":("bus","gray"),
}
TYPE_EMOJI = {"hotel":"🏨","flight":"✈️","train":"🚆","food":"🍽️","shop":"🛍️",
 "moorish":"🕌","history":"✊","museum":"🎨","attraction":"📷","viewpoint":"🌄",
 "church":"⛪","eclipse":"🌘","lounge":"🛋️","bus":"🚌"}

def is_moorish(notes): return "🕌" in notes
def is_history(notes): return "✊" in notes
def is_food(st):       return st=="food"

def climate_block(city, c):
    cl=CLIMATE.get(city, CLIMATE["Madrid"])
    warn=""
    if cl["warn"]:
        warn=('<div style="grid-column:1/-1;margin-top:4px;color:var(--accent);font-weight:600;">'
              '🥵 Heat protocol: sights 8:30–12:00 · rest 14:00–18:00 · out after 19:00</div>')
    return (f'<div style="background:color-mix(in srgb,var(--accent) 9%,var(--panel));border-radius:10px;padding:9px 11px;margin-bottom:10px;'
            f'font-size:12px;border:1px solid var(--line);color:var(--ink2);">'
            f'<div style="font-weight:600;margin-bottom:4px;color:var(--ink);">{cl["emoji"]} Typical {city} in August · {cl["pat"]}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:11px;">'
            f'<span>🌡️ Avg high {cl["hi"]}</span><span>🌙 Avg low {cl["lo"]}</span>{warn}</div></div>')

def _n0(v, unit=""):
    return "—" if v is None else f"{v:.0f}{unit}"

def wx_block(wx, c):
    """Live-forecast panel shown when Open-Meteo has data for the slot."""
    temp=f'{_n0(wx["tc"],"°C")} / {_n0(wx["tf"])}°F'
    feels='' if wx["fc"] is None else f'<span>🥶 Feels {_n0(wx["fc"],"°C")} / {_n0(wx["ff"])}°F</span>'
    precip='—' if wx["p"] is None else f'{wx["p"]:.1f} mm'
    return (f'<div style="background:color-mix(in srgb,#2e9b57 12%,var(--panel));border-radius:10px;padding:9px 11px;margin-bottom:10px;'
            f'font-size:12px;border:1px solid var(--line);color:var(--ink2);">'
            f'<div style="font-weight:600;margin-bottom:4px;color:var(--ink);">🔴 Live · {wx["emoji"]} {wx["desc"]} at ~{wx["hour"]:02d}:00</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:2px 12px;font-size:11px;">'
            f'<span>🌡️ {temp}</span>{feels}'
            f'<span>💨 Wind {_n0(wx["w"]," km/h")}</span><span>💨 Gusts {_n0(wx["g"]," km/h")}</span>'
            f'<span>🌧️ Precip {precip}</span></div></div>')

# ═══════════════════════ POPUPS ═══════════════════════
# Standardized high-quality visitor guides (Wikipedia) — the Spain/Portugal
# analogue of the Iceland map's guidetoiceland links. Keyed by exact stop name.
GUIDE = {
 "Ribeira riverfront":"https://en.wikipedia.org/wiki/Ribeira_(Porto)",
 "Dom Luís I Bridge 🌄":"https://en.wikipedia.org/wiki/Dom_Luís_I_Bridge",
 "Livraria Lello 📚":"https://en.wikipedia.org/wiki/Lello_Bookstore",
 "Clérigos Tower":"https://en.wikipedia.org/wiki/Clérigos_Church",
 "São Bento azulejo hall":"https://en.wikipedia.org/wiki/São_Bento_railway_station",
 "⭐ Palácio da Bolsa (Arab Room)":"https://en.wikipedia.org/wiki/Palácio_da_Bolsa",
 "🕌 Alfama + Miradouro de Santa Luzia":"https://en.wikipedia.org/wiki/Alfama",
 "✊ Museu do Aljube":"https://en.wikipedia.org/wiki/Aljube",
 "🕌 Castelo de São Jorge":"https://en.wikipedia.org/wiki/São_Jorge_Castle",
 "🕌 Castelo dos Mouros, Sintra":"https://en.wikipedia.org/wiki/Castle_of_the_Moors",
 "⭐ Pena Palace":"https://en.wikipedia.org/wiki/Pena_Palace",
 "⭐ Quinta da Regaleira (optional)":"https://en.wikipedia.org/wiki/Quinta_da_Regaleira",
 "⭐🕌 Jerónimos Monastery, Belém":"https://en.wikipedia.org/wiki/Jerónimos_Monastery",
 "🕌 National Tile Museum (Azulejo)":"https://en.wikipedia.org/wiki/National_Tile_Museum",
 "⭐ Tram 28 / Ler Devagar 📚":"https://en.wikipedia.org/wiki/Trams_in_Lisbon",
 "✊ Largo do Carmo":"https://en.wikipedia.org/wiki/Carmo_Convent_(Lisbon)",
 "⭐ Calouste Gulbenkian Museum":"https://en.wikipedia.org/wiki/Calouste_Gulbenkian_Museum",
 "⭐ Oceanário de Lisboa":"https://en.wikipedia.org/wiki/Lisbon_Oceanarium",
 "🕌 Real Alcázar":"https://en.wikipedia.org/wiki/Alcázar_of_Seville",
 "🕌 Cathedral + Giralda":"https://en.wikipedia.org/wiki/Seville_Cathedral",
 "⭐🕌 Casa de Pilatos":"https://en.wikipedia.org/wiki/Casa_de_Pilatos",
 "⭐ Plaza de España":"https://en.wikipedia.org/wiki/Plaza_de_España,_Seville",
 "🕌 Mezquita-Catedral, Cordoba":"https://en.wikipedia.org/wiki/Mosque–Cathedral_of_Córdoba",
 "Alcázar + Judería + Roman bridge":"https://en.wikipedia.org/wiki/Alcázar_de_los_Reyes_Cristianos",
 "⭐ Palacio de Viana (patios)":"https://en.wikipedia.org/wiki/Palacio_de_Viana",
 "🕌 Albaicín → Mirador de San Nicolás 🌄":"https://en.wikipedia.org/wiki/Albaicín",
 "🕌 THE ALHAMBRA + Generalife":"https://en.wikipedia.org/wiki/Alhambra",
 "⭐ Royal Chapel + Cathedral":"https://en.wikipedia.org/wiki/Royal_Chapel_of_Granada",
 "✊ Centro Federico García Lorca":"https://en.wikipedia.org/wiki/Federico_García_Lorca",
 "Sacromonte — carmen dinner 🌄":"https://en.wikipedia.org/wiki/Sacromonte",
 "Royal Palace + Campo del Moro":"https://en.wikipedia.org/wiki/Royal_Palace_of_Madrid",
 "✊ Reina Sofía (Guernica)":"https://en.wikipedia.org/wiki/Museo_Reina_Sofía",
 "🕌 Muralla Árabe":"https://en.wikipedia.org/wiki/Walls_of_Madrid",
 "⭐ Templo de Debod (sunset) 🌄":"https://en.wikipedia.org/wiki/Temple_of_Debod",
 "🕌 Mezquita del Cristo de la Luz":"https://en.wikipedia.org/wiki/Mosque_of_Cristo_de_la_Luz",
 "🕌 Santa María la Blanca + El Tránsito":"https://en.wikipedia.org/wiki/Santa_María_la_Blanca",
 "⭐ Santo Tomé (El Greco) + Cathedral":"https://en.wikipedia.org/wiki/The_Burial_of_the_Count_of_Orgaz",
 "Free Madrid morning":"https://en.wikipedia.org/wiki/Plaza_Mayor,_Madrid",
}
GUIDE_STOPS = set(GUIDE)   # which sightseeing stops get a Visitor Guide
# Better than Wikipedia: independent expert planner (Rick Steves) + official
# national tourism (Spain.info / VisitPortugal), keyed by city.
RS_CITY = {
 "Porto":"https://www.ricksteves.com/europe/portugal/porto",
 "Lisbon":"https://www.ricksteves.com/europe/portugal/lisbon",
 "Sintra":"https://www.ricksteves.com/europe/portugal/sintra",
 "Seville":"https://www.ricksteves.com/europe/spain/seville",
 "Cordoba":"https://www.ricksteves.com/europe/spain/cordoba",
 "Granada":"https://www.ricksteves.com/europe/spain/granada",
 "Madrid":"https://www.ricksteves.com/europe/spain/madrid",
 "Toledo":"https://www.ricksteves.com/europe/spain/toledo",
}
OFFICIAL_GUIDE = {
 "Porto":"https://www.visitportugal.com/en/destinos/porto-e-o-norte",
 "Lisbon":"https://www.visitportugal.com/en/destinos/lisboa-region",
 "Sintra":"https://www.visitportugal.com/en/destinos/lisboa-region/sintra",
 "Seville":"https://www.spain.info/en/destination/seville/",
 "Cordoba":"https://www.spain.info/en/destination/cordoba/",
 "Granada":"https://www.spain.info/en/destination/granada/",
 "Madrid":"https://www.spain.info/en/destination/madrid/",
 "Toledo":"https://www.spain.info/en/destination/toledo/",
}
PT_CITIES = {"Porto","Lisbon","Sintra"}
def official_label(city):
    return "🇵🇹 VisitPortugal →" if city in PT_CITIES else "🇪🇸 Spain.info →"
def guide_links(name, city, c, small=False):
    """Return the Rick Steves + official-tourism guide <a> tags for a stop."""
    if name not in GUIDE_STOPS: return []
    fs = '' if small else 'font-size:12.5px;'
    out=[]
    og=OFFICIAL_GUIDE.get(city); rs=RS_CITY.get(city)
    if rs: out.append(f'<a href="{rs}" target="_blank" style="color:{c};text-decoration:none;{fs}font-weight:600;">🎒 Rick Steves →</a>')
    if og: out.append(f'<a href="{og}" target="_blank" style="color:{c};text-decoration:none;{fs}font-weight:600;">{official_label(city)}</a>')
    return out
# Official booking / info pages to fill in where a stop had none (incl. the
# Sintra suburban train — the one remaining rail leg without a booking link).
BOOKINFO = {
 "Sete Rios → Sintra train 🚆":"https://www.cp.pt/passageiros/en",
 "Royal Palace (from below) + Campo del Moro":"https://www.patrimonionacional.es",
 "Sé do Porto (Cathedral)":"https://www.diocese-porto.pt/pt/se-catedral-do-porto/",
 "Clérigos Tower":"https://www.torredosclerigos.pt/en/",
 "✊ Museu do Aljube":"https://www.museudoaljube.pt",
 "⭐ Quinta da Regaleira (optional)":"https://www.regaleira.pt/en/",
 "⭐🕌 Jerónimos Monastery, Belém":"https://www.patrimoniocultural.gov.pt",
 "🕌 National Tile Museum (Azulejo)":"https://www.museudoazulejo.gov.pt",
 "⭐🕌 Casa de Pilatos":"https://www.fundacionmedinaceli.org",
 "🕌 Santa María la Blanca + El Tránsito":"https://toledomonumental.com",
 "⭐ Santo Tomé (El Greco) + Cathedral":"https://santotome.org",
}

def popup_html(name, day, st, city, notes, link, lat, lon, wx=None):
    c=rcolor(city)
    link = link or BOOKINFO.get(name)
    h=(f'<div style="font-family:var(--sans);max-width:300px;width:calc(100vw - 80px);line-height:1.55;">'
       f'<div style="background:{c};color:white;padding:11px 14px;">'
       f'<span class="pop-h">{name}</span><br>'
       f'<span style="font-size:11px;opacity:0.92;">{DAY_LABELS[day]} · {st.capitalize()}</span></div>'
       f'<div style="padding:12px 14px 13px 14px;">')
    if wx:
        h+=wx_block(wx, c)
    elif city in CLIMATE and city!="Transit":
        h+=climate_block(city, c)
    h+=f'<div style="font-size:12.5px;color:var(--ink2);white-space:pre-wrap;">{notes}</div>'
    parts=[]
    if link:
        parts.append(f'<a href="{link}" target="_blank" style="color:{c};text-decoration:none;font-size:12.5px;font-weight:600;">🔗 Book / Info →</a>')
    parts += guide_links(name, city, c)
    parts.append(f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" style="color:{c};text-decoration:none;font-size:12.5px;font-weight:600;">📍 Map</a>')
    if day in DAY_MAP:
        parts.append(f'<a href="{DAY_MAP[day]}" target="_blank" style="color:{c};text-decoration:none;font-size:12.5px;font-weight:600;">🗺 Day route</a>')
    h+=f'<div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--line);display:flex;gap:14px;flex-wrap:wrap;">{"".join(parts)}</div>'
    return h+"</div></div>"

# ═══════════════════════ MAP ═══════════════════════
DAY_LAYER = {d: f"Day {d} — {DAY_DATES[d][5:].replace('-','/')} · {DAY_CITY[d]}" for d in range(1,16)}

def build_map(paths, weather):
    m=folium.Map(location=MAP_CENTER, zoom_start=ZOOM_START, tiles=None,
                 control_scale=False, zoom_snap=0.25, zoom_delta=0.5)
    folium.TileLayer("OpenStreetMap", name="🗺️ Street Map").add_to(m)
    folium.TileLayer(tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",attr="© OpenStreetMap contributors © CARTO",name="🌙 Dark Matter").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",attr="Esri",name="🏔️ Terrain").add_to(m)
    folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",attr="Esri",name="🛰️ Satellite").add_to(m)

    # One toggleable layer per day (markers + that day's paths)
    dg={d: FeatureGroup(name=DAY_LAYER[d], show=True) for d in range(1,16)}
    moor=FeatureGroup(name="🕌 Moorish & Mudéjar sites", show=False)
    hist=FeatureGroup(name="✊ Political & literary history", show=False)
    hotels=FeatureGroup(name="🏨 Hotels", show=False)

    # Intercity legs (rail/air) → their travel day's layer
    for lg,coords in paths["legs"]:
        stl=MODE_STYLE[lg["mode"]]
        # Long-haul flights (transatlantic + US) carry a class so the scrubber
        # can hide them on the "All 15 days" overview.
        pl_kw={"className":"farflight"} if lg.get("far") else {}
        PolyLine(locations=coords, color=stl["color"], weight=5, opacity=0.9, smooth_factor=1,
                 dash_array=stl["dash"], **pl_kw,
                 tooltip=f"<b>{stl['label']}: {lg['name']}</b><br>{lg['note']}").add_to(dg[lg["day"]])

    # Intra-city hops (walk/taxi/metro/…) → their day's layer, styled by mode
    for sg,coords in paths["segs"]:
        stl=MODE_STYLE[sg["mode"]]
        PolyLine(locations=coords, color=stl["color"], weight=stl["w"], opacity=0.85, smooth_factor=1,
                 dash_array=stl["dash"],
                 tooltip=f"<b>{stl['label']} · {sg['min']} min</b><br>{sg['from']} → {sg['to']}").add_to(dg[sg["day"]])

    # Stop markers
    for name,lat,lon,day,st,city,notes,link,hr,dur,anchor in S:
        ic,ocol=TYPE_ICON.get(st,("camera",None))
        col=ocol or REGION_MARKER[region(city)]
        wx=get_wx(weather, city, day, hr)
        ph=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx), max_width=340)
        Marker(location=[lat,lon], popup=ph,
               tooltip=f"<b>{TYPE_EMOJI.get(st,'📷')} {name}</b><br><small>{DAY_LABELS[day]}</small>",
               icon=Icon(color=col, icon=ic, prefix="fa")).add_to(dg[day])
        if is_moorish(notes):
            Marker(location=[lat,lon], popup=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx),max_width=340),
                   tooltip=f"<b>🕌 {name}</b>", icon=Icon(color="darkred",icon="mosque",prefix="fa")).add_to(moor)
        if is_history(notes):
            Marker(location=[lat,lon], popup=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx),max_width=340),
                   tooltip=f"<b>✊ {name}</b>", icon=Icon(color="black",icon="fist-raised",prefix="fa")).add_to(hist)
        if st=="hotel" and "🏨" in name:
            Marker(location=[lat,lon], popup=Popup(popup_html(name,day,st,city,notes,link,lat,lon,wx),max_width=340),
                   tooltip=f"<b>🏨 {name}</b>", icon=Icon(color="green",icon="bed",prefix="fa")).add_to(hotels)

    for d in range(1,16): dg[d].add_to(m)
    moor.add_to(m); hist.add_to(m); hotels.add_to(m)
    LayerControl(collapsed=True).add_to(m)
    LocateControl(position="topleft", strings={"title":"See my location"}).add_to(m)

    title="""<div id="map-title" style="position:fixed;top:10px;left:55px;z-index:1000;background:white;padding:10px 18px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;max-width:calc(100vw - 120px);">
    <div class="mt-t">Portugal &amp; Spain</div>
    <div class="title-sub" style="font-size:12px;margin-top:3px;">Aug 6–20, 2026 · 15 Days<span class="title-route"> · Porto → Lisbon → Seville → Granada → Madrid</span></div>
    <div class="title-legend" style="font-size:10px;margin-top:5px;">🕌 Moorish  ✊ History  🏨 Hotel  🍽️ Food  🛍️ Shop  🌄 View  🌘 Eclipse</div>
    <div class="title-legend" style="font-size:10px;color:#999;margin-top:2px;">Paths: <span style="color:#5f8b57;font-weight:700">━ 🚶Walk</span>  <span style="color:#cc8642;font-weight:700">━ 🚕Taxi</span>  <span style="color:#4a6fa5;font-weight:700">┄ 🚇Metro</span>  <span style="color:#8a6193;font-weight:700">┄ 🚊Tram</span>  <span style="color:#3c8f8a;font-weight:700">━ 🚌Bus</span>  <span style="color:#b8503a;font-weight:700">━ 🚆Train</span>  <span style="color:#7d7770;font-weight:700">┄ ✈️Flight</span></div></div>"""
    m.get_root().html.add_child(folium.Element(title))
    m.get_root().html.add_child(folium.Element(RESPONSIVE_CSS))
    m.get_root().html.add_child(folium.Element(build_agenda(weather, paths)))
    m.get_root().html.add_child(folium.Element(build_scrubber()))
    m.get_root().html.add_child(folium.Element(build_vscrubber()))
    m.get_root().html.add_child(folium.Element(build_popup_fit()))
    m.get_root().html.add_child(folium.Element(build_theme()))
    return m

RESPONSIVE_CSS = """<style>
.leaflet-control-layers-overlays{max-height:400px;overflow-y:auto;-webkit-overflow-scrolling:touch;}
.leaflet-popup-content-wrapper{padding:0 !important;overflow:hidden;}
.leaflet-popup-content{margin:0 !important;-webkit-overflow-scrolling:touch;touch-action:pan-y;}
.leaflet-popup-close-button{font-size:22px !important;width:30px !important;height:30px !important;padding:4px !important;color:white !important;z-index:1;}
@media (max-width:600px){
 #map-title{left:10px !important;top:6px !important;padding:6px 12px !important;max-width:calc(100vw - 70px) !important;}
 #map-title > div:first-child{font-size:13px !important;}
 .title-sub{font-size:10px !important;} .title-legend,.title-credits{display:none !important;}
 .leaflet-control-layers{max-width:210px;} .leaflet-control-layers-overlays{max-height:250px;font-size:11px;}
 .leaflet-popup-content-wrapper{max-width:calc(100vw - 40px) !important;}
 .leaflet-popup-content{max-width:calc(100vw - 70px) !important;}
}
@media (min-width:601px) and (max-width:1024px){ #map-title{max-width:440px !important;} .title-credits{display:none !important;}}
/* Tablets. A width breakpoint cannot catch these — an iPad in landscape reports
   ~1366-1408 CSS px, indistinguishable from a laptop — so key off the input
   device instead. Touch + no hover is true for every iPad and phone and false
   for a desktop browser. */
@media (hover:none) and (pointer:coarse){
 /* the full legend is desktop detail; on a tablet it eats the top-left corner
    of the map and swallows whatever the day zoom frames underneath it */
 .title-legend{display:none !important;}
 .title-credits{display:none !important;}
 #map-title{max-width:min(420px, calc(100vw - 80px)) !important;padding:7px 13px !important;}
 #map-title > div:first-child{font-size:15px !important;}
 .title-sub{font-size:11px !important;}
}
</style>"""

# ═══════════════════════ AGENDA VIEW ═══════════════════════
def _trunc(notes, c):
    if len(notes) > 150:
        short=notes[:145].rsplit(" ",1)[0]+"…"
        short=short.replace("\n","<br>"); full=notes.replace("\n","<br>")
        return (f'<span style="display:inline">{short} </span>'
                f'<a href="#" onclick="this.previousElementSibling.style.display=\'none\';this.nextElementSibling.style.display=\'inline\';this.style.display=\'none\';return false;" style="color:{c};font-weight:600;text-decoration:none;">Read More ↓</a>'
                f'<span style="display:none">{full} '
                f'<a href="#" onclick="var p=this.parentElement;p.style.display=\'none\';p.previousElementSibling.style.display=\'inline\';p.previousElementSibling.previousElementSibling.style.display=\'inline\';return false;" style="color:#666;text-decoration:none;">Hide ↑</a></span>')
    return notes.replace("\n","<br>")

def _card(name,lat,lon,day,st,city,notes,link,hr,dur,anchor,wx=None,arrive=None):
    c=rcolor(city); reg=region(city)
    icon=TYPE_EMOJI.get(st,"📷"); tstr=f"{hr:02d}:00"
    sid=f"d{day}h{hr}s{st}"
    immune="true" if anchor else "false"
    mo="true" if is_moorish(notes) else "false"
    hi="true" if is_history(notes) else "false"
    h =f'<div class="sc" id="{sid}" data-id="{sid}" data-day="{day}" data-city="{reg}" data-type="{st}" data-hour="{hr}" data-moor="{mo}" data-hist="{hi}" data-immune="{immune}" data-dur="{dur}" style="border-left-color:{c}">'
    if arrive:
        amode, amin = arrive
        stl=MODE_STYLE[amode]
        h+=f'<div class="amode" style="color:{stl["color"]}">↳ {amin}m {stl["label"]} from previous stop</div>'
    h+='<div style="display:flex;align-items:baseline;gap:10px;justify-content:space-between;width:100%">'
    h+=f'<div style="display:flex;align-items:baseline;gap:10px"><div class="st">{tstr}</div>'
    h+=f'<div><span class="sn">{icon} {name}</span><br><span class="stp">{st}</span></div></div>'
    if not anchor:
        h+=f'<button class="stog" onclick="togSkip(\'{sid}\', event)">➖ Remove</button>'
    h+='</div>'
    if wx:
        feels='' if wx["fc"] is None else f'<span>🥶 Feels {_n0(wx["fc"],"°C")} / {_n0(wx["ff"])}°F</span>'
        h+=f'<div class="sw sw-live" style="border-left:3px solid {c}">'
        h+=f'<div style="grid-column:1/-1;font-weight:600;margin-bottom:2px">🔴 Live · {wx["emoji"]} {wx["desc"]} at ~{wx["hour"]:02d}:00</div>'
        h+=f'<span>🌡️ {_n0(wx["tc"],"°C")} / {_n0(wx["tf"])}°F</span>{feels}'
        h+=f'<span>💨 Wind {_n0(wx["w"]," km/h")}</span><span>💨 Gusts {_n0(wx["g"]," km/h")}</span></div>'
    elif city in CLIMATE and city!="Transit":
        cl=CLIMATE[city]
        h+=f'<div class="sw" style="border-left:3px solid {c}">'
        h+=f'<div style="grid-column:1/-1;font-weight:600;margin-bottom:2px">{cl["emoji"]} Typical {city} · {cl["pat"]}</div>'
        h+=f'<span>🌡️ High {cl["hi"]}</span><span>🌙 Low {cl["lo"]}</span></div>'
    h+=f'<div class="snt">{_trunc(notes,c)}</div>'
    link = link or BOOKINFO.get(name)
    h+='<div class="sl">'
    if link: h+=f'<a href="{link}" target="_blank" style="color:{c}">🔗 Book / Info →</a>'
    for g in guide_links(name, city, c, small=True): h+=g
    h+=f'<a href="https://www.google.com/maps?q={lat},{lon}" target="_blank" style="color:{c}">📍 Map</a>'
    if day in DAY_MAP: h+=f'<a href="{DAY_MAP[day]}" target="_blank" style="color:{c}">🗺 Day route</a>'
    h+='</div></div>'
    return h

def build_agenda(weather, paths):
    # Inbound transport for each stop = the path segment that ENDS at it (keyed by
    # rounded coord + day). Covers first stops too (via the hotel→first-stop transfer).
    inbound={}
    for lg,coords in paths["legs"]:          # coach/rail/air arrivals count too
        if lg.get("min"):
            b=lg["b"]; inbound[(lg["day"], round(b[0],4), round(b[1],4))]=(lg["mode"], lg["min"])
    for sg,coords in paths["segs"]:
        b=sg["b"]
        inbound[(sg["day"], round(b[0],4), round(b[1],4))]=(sg["mode"], sg["min"])
    tl=""
    for i in range(1,16):
        city=DAY_CITY[i]; c=REGION_COLORS[region(city)]
        tl+=f'<div class="dh" data-day="{i}" data-city="{region(city)}"><div class="dd" style="background:{c}"></div>{DAY_LABELS[i]}</div>'
        day_stops=[stp for stp in S if stp[3]==i]
        for stp in day_stops:
            wx=get_wx(weather, stp[5], stp[3], stp[8])  # city, day, hour
            # arrive chip: mode+minutes of the hop into this stop (not on journey stops)
            arrive=None
            if stp[4] not in ("train","flight"):
                arrive=inbound.get((stp[3], round(stp[1],4), round(stp[2],4)))
            tl+=_card(*stp, wx=wx, arrive=arrive)

    dd_js="{"+",".join(f'{k}:"{v}"' for k,v in DAY_DATES.items())+"}"
    day_opts="".join(f'<option value="{d}">Day {d} · {DAY_DATES[d][5:].replace("-","/")}</option>' for d in range(1,16))

    return f"""
    <div id="vtog">
      <button id="bm" class="on" onclick="sv('map')">🗺️ Map</button>
      <button id="ba" onclick="sv('agenda')">📋 Itinerary</button>
    </div>
    <div id="av">
      <div class="ah">
        <div class="ah-t">Portugal &amp; Spain</div>
        <div class="ah-s">Aug 6–20, 2026 · 15 days</div>
        <div class="ah-r">Porto → Lisbon → Seville → Granada → Madrid</div>
      </div>
      <div id="af">
        <button class="fp active" data-f="all" onclick="tf(this)">All</button>
        <button class="fp active" data-f="Porto" onclick="tf(this)" style="--c:{REGION_COLORS['Porto']}">Porto</button>
        <button class="fp active" data-f="Lisbon" onclick="tf(this)" style="--c:{REGION_COLORS['Lisbon']}">Lisbon</button>
        <button class="fp active" data-f="Seville" onclick="tf(this)" style="--c:{REGION_COLORS['Seville']}">Seville</button>
        <button class="fp active" data-f="Granada" onclick="tf(this)" style="--c:{REGION_COLORS['Granada']}">Granada</button>
        <button class="fp active" data-f="Madrid" onclick="tf(this)" style="--c:{REGION_COLORS['Madrid']}">Madrid</button>
        <button class="fp active" data-f="moor" onclick="tf(this)">🕌 Moorish</button>
        <button class="fp active" data-f="food" onclick="tf(this)">🍽️ Food</button>
        <button class="fp active" data-f="hist" onclick="tf(this)">✊ History</button>
        <input id="af-q" type="search" inputmode="search" autocomplete="off"
               placeholder="Search stops…" aria-label="Search the itinerary" oninput="af()">
      </div>
      <div id="af-none">No stops match — try a different word or clear the filters.</div>
      <div id="atl">{tl}
        <div style="max-width:700px;margin:8px auto 0;padding:0 4px">
          <div class="infocard">
            <b>☀️ August heat is the #1 hazard.</b> Porto &amp; Lisbon are comfortable; Andalusia (Aug 12–16) is the danger zone — Seville/Cordoba run 100–108°F. Heat protocol: sights 8:30–12:00, siesta 14:00–18:00, out after 19:00. Re-check <a href="https://www.aemet.es/en" target="_blank">aemet.es</a> (Spain) / <a href="https://www.ipma.pt/en/" target="_blank">ipma.pt</a> (Portugal) 48 h before each leg.<br><span style="color:#2e7d5b;font-weight:600">🔴 Live forecast:</span> each stop shows a live Open-Meteo reading once its day is within the ~16-day forecast window (refreshed hourly); until then it shows the August climate normal.
          </div>
          <div class="infocard">
            <b>🎟️ Locked bookings:</b> Alhambra General — morning Sun Aug 16 (non-changeable). Ryanair FR3628 Lisbon→Seville, Aug 12 5:20 PM. All hotels + Madrid Airbnb booked. Book the 5 rail legs now on <a href="https://www.cp.pt/passageiros/en" target="_blank">cp.pt</a> / <a href="https://www.renfe.com/es/en" target="_blank">renfe.com</a> — the Aug 15 holiday Granada train sells first.
          </div>
          <div class="infocard">
            <b>🌘 Aug 12 eclipse:</b> deep partial (~85–90%) over Seville, beginning minutes after you land. Pack 3 pairs of ISO 12312-2 glasses from the US.
          </div>
        </div>
      </div>
      <div style="padding:22px 20px 30px;text-align:center;font-size:11px;color:var(--ink3)">Climate normals from the itinerary heat outlook · Routes: Valhalla/OSM · Times are local · Skip/delay state saved on this device</div>

      <div id="d-fab" onclick="togMenu()" style="position:fixed;bottom:24px;right:24px;width:54px;height:54px;border-radius:27px;background:var(--brand);color:#fff;display:flex;align-items:center;justify-content:center;font-size:30px;box-shadow:0 6px 18px rgba(204,120,92,0.4);cursor:pointer;z-index:100;">+</div>
      <div id="d-menu" style="display:none;position:fixed;bottom:90px;right:24px;background:white;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.15);padding:8px;z-index:99;flex-direction:column;gap:4px;">
        <button onclick="opAdd()" style="padding:12px 16px;border:none;background:transparent;text-align:left;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px;color:#333;">⏱ Add Delay / Stop</button>
        <button onclick="opRem()" style="padding:12px 16px;border:none;background:transparent;text-align:left;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px;color:#666;">Undo / Remove Delay</button>
      </div>

      <div id="d-add-mod" class="mod-ov" style="display:none;">
        <div class="mod-bx">
          <div style="font-size:18px;font-weight:700;margin-bottom:12px;">Add Delay / Extra Stop</div>
          <div style="font-size:13px;color:#666;margin-bottom:16px;">Shifts all later scheduled items that day downward.</div>
          <div style="display:flex;gap:12px;margin-bottom:12px;">
            <div style="flex:1"><label style="font-size:12px;font-weight:600;color:#555;">Day:</label>
              <select id="v-day" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:4px;">{day_opts}</select></div>
            <div style="flex:1"><label style="font-size:12px;font-weight:600;color:#555;">Start Time:</label>
              <select id="v-time" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:4px;">{"".join(f'<option value="{h}">{h:02d}:00</option>' for h in range(6,24))}</select></div>
          </div>
          <label style="font-size:12px;font-weight:600;color:#555;">Duration (minutes):</label><br>
          <div style="display:flex;gap:8px;margin-top:6px;margin-bottom:16px;">
            <button class="mbtn" onclick="setD(15)">15m</button><button class="mbtn" onclick="setD(30)">30m</button>
            <button class="mbtn" onclick="setD(45)">45m</button><button class="mbtn" onclick="setD(60)">1h</button>
            <input type="number" id="v-dur" style="width:70px;padding:8px;border:1px solid #ddd;border-radius:6px;font-size:14px;" value="15">
          </div>
          <label style="font-size:12px;font-weight:600;color:#555;">Reason (optional):</label>
          <input type="text" id="v-rsn" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid #ddd;border-radius:6px;font-size:14px;margin-top:6px;margin-bottom:20px;" placeholder="e.g., long lunch, siesta ran over…">
          <div style="display:flex;justify-content:flex-end;gap:12px;">
            <button onclick="clsMod()" style="padding:10px 16px;border:none;background:transparent;color:#666;font-weight:600;cursor:pointer;">Cancel</button>
            <button onclick="svDel()" style="padding:10px 20px;border:none;background:var(--brand);color:white;border-radius:9px;font-weight:600;cursor:pointer;">Apply</button>
          </div>
        </div>
      </div>
      <div id="d-rem-mod" class="mod-ov" style="display:none;">
        <div class="mod-bx">
          <div style="font-size:18px;font-weight:700;margin-bottom:12px;">Remove a Delay</div>
          <div id="v-del-list" style="max-height:200px;overflow-y:auto;margin-bottom:16px;font-size:13px;"></div>
          <div style="display:flex;justify-content:flex-end;"><button onclick="clsMod()" style="padding:10px 16px;border:none;background:var(--brand);color:white;border-radius:9px;font-weight:600;cursor:pointer;">Close</button></div>
        </div>
      </div>
    </div>
    <style>
    /* height:fit-content matters — the mobile/standalone blocks below pin `bottom`,
       and a fixed element with BOTH top and bottom set stretches to fill the screen.
       Sizing it to its content makes that over-constrained case resolve to `top`
       instead of turning the switcher into a full-height column. */
    #vtog{{position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:2000;display:flex;height:fit-content;background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:4px;box-shadow:var(--shadow);font-family:var(--sans)}}
    #vtog button{{padding:8px 20px;border:none;border-radius:18px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.25s;color:var(--ink2);background:transparent}}
    #vtog button:focus{{outline:none}}
    #vtog button.on{{background:var(--brand);color:#fff}}
    #av{{display:none;position:fixed;inset:0;z-index:1500;background:var(--bg);overflow-y:auto;font-family:var(--sans);color:var(--ink);-webkit-font-smoothing:antialiased}}
    .ah{{padding:58px 22px 24px;background:var(--bg);border-bottom:1px solid var(--line);text-align:center}}
    .ah-t{{font-family:var(--serif);font-size:30px;font-weight:600;letter-spacing:-0.4px;color:var(--ink)}}
    .ah-s{{font-size:13px;margin-top:8px;font-weight:500;color:var(--ink2)}}
    .ah-r{{font-size:11.5px;margin-top:7px;color:var(--ink3);letter-spacing:0.2px}}
    #af{{padding:11px 14px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:7px;position:sticky;top:0;z-index:100}}
    .fp{{padding:6px 13px;border:1.5px solid var(--line);border-radius:18px;font-size:12px;
      font-weight:600;cursor:pointer;background:transparent;color:var(--ink3);opacity:0.55;
      transition:all 0.18s;-webkit-tap-highlight-color:transparent}}
    .fp:hover{{opacity:0.82}}
    /* search sits on the same row as the chips and shares their shape */
    #af-q{{flex:1 1 130px;min-width:110px;max-width:260px;padding:6px 13px;
      border:1px solid var(--line);border-radius:18px;font-size:12px;font-weight:600;
      background:var(--panel);color:var(--ink);font-family:var(--sans);
      outline:none;transition:all 0.18s;-webkit-appearance:none;appearance:none}}
    #af-q::placeholder{{color:var(--ink3);font-weight:500}}
    #af-q:focus{{border-color:var(--brand);box-shadow:0 0 0 3px color-mix(in srgb,var(--brand) 18%,transparent)}}
    #af-q::-webkit-search-cancel-button{{-webkit-appearance:none;height:14px;width:14px;
      background:var(--ink3);cursor:pointer;
      -webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z'/%3E%3C/svg%3E") center/contain no-repeat}}
    #af-none{{display:none;max-width:700px;margin:26px auto;padding:0 18px;
      text-align:center;font-size:13px;color:var(--ink3)}}
    /* On phones the field collapses to just the magnifier so it costs almost no
       room in the sticky bar, and expands when tapped (or while it holds text). */
    @media(max-width:600px){{
      #af-q{{flex:0 0 34px;width:34px;min-width:34px;max-width:34px;padding:6px;
        color:transparent;cursor:pointer;
        background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23928c84' stroke-width='2.2' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='M20 20l-4-4'/%3E%3C/svg%3E");
        background-repeat:no-repeat;background-position:center;background-size:15px 15px;
        transition:flex-basis .2s,max-width .2s,padding .2s}}
      #af-q::placeholder{{color:transparent}}
      #af-q:focus,#af-q:not(:placeholder-shown){{
        flex:1 1 150px;max-width:100%;padding:6px 13px 6px 30px;color:var(--ink);
        background-position:10px center;cursor:text}}
      #af-q:focus::placeholder{{color:var(--ink3)}}
    }}
    
    /* muted fill — darkened rather than lightened, so white text keeps its
       contrast in both themes and the chip reads calm instead of neon */
    .fp.active{{opacity:1;font-weight:650;box-shadow:none;color:rgba(255,255,255,0.94);
      background:color-mix(in srgb,var(--c,var(--brand)) 84%,#000);
      border-color:color-mix(in srgb,var(--c,var(--brand)) 84%,#000)}}
    :root[data-theme="dark"] .fp.active{{color:rgba(255,255,255,0.90);
      background:color-mix(in srgb,var(--c,var(--brand)) 66%,#000);
      border-color:color-mix(in srgb,var(--c,var(--brand)) 72%,#000)}}
    .fp[data-f="all"].active{{background:var(--ink);border-color:var(--ink);color:var(--bg)}}
    #atl{{padding:16px 14px 4px;max-width:680px;margin:0 auto}}
    .dh{{display:flex;align-items:center;gap:11px;padding:24px 2px 11px;font-family:var(--serif);font-size:17px;font-weight:600;color:var(--ink);letter-spacing:-0.2px}}
    .dh:first-child{{padding-top:10px}}
    .dd{{width:10px;height:10px;border-radius:50%;flex-shrink:0;box-shadow:0 0 0 3px color-mix(in srgb,var(--ink) 6%,transparent)}}
    .sc{{position:relative;background:var(--panel);border-radius:16px;padding:16px 17px 15px;margin-bottom:12px;box-shadow:var(--shadow);border:1px solid var(--line);border-left:3px solid var(--line);transition:transform 0.18s,box-shadow 0.18s,border-color 0.18s}}
    .sc:hover{{border-color:color-mix(in srgb,var(--ink) 16%,var(--line));transform:translateY(-1px)}}
    .sc.now{{box-shadow:0 0 0 2px var(--brand),var(--shadow)}}
    .amode{{display:inline-flex;align-items:center;gap:4px;font-size:10.5px;font-weight:700;margin-bottom:10px;padding:3px 10px;border-radius:20px;background:color-mix(in srgb,var(--ink) 5%,transparent);letter-spacing:0.2px}}
    .st{{font-size:12.5px;font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums;min-width:46px;letter-spacing:0.3px}}
    .sn{{font-size:15px;font-weight:600;color:var(--ink);line-height:1.3}}
    .stp{{font-size:10px;color:var(--ink3);text-transform:uppercase;letter-spacing:0.8px;font-weight:600;margin-top:3px;display:inline-block}}
    .snt{{font-size:12.5px;color:var(--ink2);margin-top:8px;line-height:1.6}}
    .stog{{flex-shrink:0;background:transparent;border:1px solid var(--line);color:var(--ink3);border-radius:9px;padding:4px 9px;font-size:11px;font-weight:600;cursor:pointer;height:26px;transition:all 0.15s}}
    .stog:hover{{border-color:var(--accent);color:var(--accent)}}
    .sw{{background:color-mix(in srgb,var(--accent) 8%,var(--panel));border-radius:11px;padding:9px 11px;margin-top:10px;font-size:11px;display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;color:var(--ink2)}}
    .sw div,.sw span{{color:var(--ink2)}}
    .sw-live{{background:color-mix(in srgb,#2e9b57 12%,var(--panel))}}
    .sl{{display:flex;gap:16px;flex-wrap:wrap;margin-top:11px;padding-top:11px;border-top:1px solid var(--line)}}
    .sl a{{font-size:12px;font-weight:600;text-decoration:none;padding:1px 0;opacity:0.92}}
    .sl a:hover{{opacity:1}}
    .infocard{{background:var(--panel);border-radius:16px;padding:15px 17px;margin-bottom:12px;box-shadow:var(--shadow);border:1px solid var(--line);border-left:3px solid var(--brand);font-size:12px;color:var(--ink2);line-height:1.65}}
    .infocard b{{color:var(--ink)}}
    .infocard a{{color:var(--accent);font-weight:600;text-decoration:none}}
    .mod-ov{{position:fixed;inset:0;background:rgba(20,17,14,0.5);z-index:3000;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}}
    .mod-bx{{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:20px;padding:24px;width:90%;max-width:360px;box-shadow:0 16px 44px rgba(0,0,0,0.3)}}
    .mod-bx div{{color:var(--ink)}} .mod-bx label{{color:var(--ink2) !important}}
    .mod-bx input,.mod-bx select{{background:var(--panel2);color:var(--ink);border:1px solid var(--line)}}
    .mbtn{{padding:8px 12px;background:var(--accent-soft);border:1px solid var(--line);border-radius:9px;font-weight:600;color:var(--accent);cursor:pointer;flex:1}}
    .d-itm{{display:flex;justify-content:space-between;align-items:center;background:var(--panel2);padding:12px;border-radius:10px;margin-bottom:8px;border:1px solid var(--line)}}
    .rm-btn{{background:color-mix(in srgb,#c0392b 16%,var(--panel));color:#c0392b;border:none;padding:6px 12px;border-radius:9px;font-weight:600;cursor:pointer}}
    .time-adj{{color:#d9694a;font-weight:700;font-size:11px;display:block;margin-top:2px}}
    .time-adj.time-sub{{color:#2e9b57}}
    .skip-rec{{background:color-mix(in srgb,#e0a800 14%,var(--panel));border:1px solid color-mix(in srgb,#e0a800 30%,var(--panel));border-left:3px solid #e0a800;padding:9px 12px;border-radius:10px;margin-bottom:11px;font-size:11.5px;font-weight:600;color:var(--ink)}}
    .sc.skipped{{opacity:0.5;filter:grayscale(0.8)}}
    .sc.skipped .sn,.sc.skipped .stp,.sc.skipped .snt{{text-decoration:line-through}}
    .sc.skipped .stog{{color:var(--ink) !important;border-color:var(--ink) !important}}
    @media(max-width:600px){{ #vtog{{top:auto;bottom:98px}} #vtog button{{padding:6px 14px;font-size:12px}} .sc{{padding:13px 14px}} #af{{padding:10px 12px;position:static !important}} .ah{{padding:50px 16px 20px}} .ah-t{{font-size:26px}} }}
    /* Same on tablets: a pinned filter bar costs too much of the screen while
       scrolling, and on an iPad it also collided with the top-centred view
       switcher. Keyed off touch input rather than width — an iPad in landscape
       is as wide as a laptop. barH() reads the computed position, so unsticking
       it here automatically stops day-jumps reserving room for it. */
    @media (hover:none) and (pointer:coarse){{ #af{{position:static !important}} }}
    </style>
    <script>
    var DD={dd_js};
    window.dels=JSON.parse(localStorage.getItem('sp_dels'))||[];
    window.skips=JSON.parse(localStorage.getItem('sp_skips'))||[];
    function togMenu(){{var m=document.getElementById('d-menu');m.style.display=m.style.display==='none'?'flex':'none';}}
    function togSkip(sid,e){{if(e)e.preventDefault();var i=window.skips.indexOf(sid);if(i===-1)window.skips.push(sid);else window.skips.splice(i,1);localStorage.setItem('sp_skips',JSON.stringify(window.skips));applyDelays();}}
    function opAdd(){{document.getElementById('d-menu').style.display='none';document.getElementById('d-add-mod').style.display='flex';var ad=1;var dhs=document.querySelectorAll('.dh');for(var i=0;i<dhs.length;i++){{if(dhs[i].style.display!=='none'){{ad=parseInt(dhs[i].getAttribute('data-day'));break;}}}}document.getElementById('v-day').value=ad;var h=new Date().getHours();if(h>=6&&h<=23)document.getElementById('v-time').value=h;}}
    function opRem(){{document.getElementById('d-menu').style.display='none';buildRemList();document.getElementById('d-rem-mod').style.display='flex';}}
    function clsMod(){{document.querySelectorAll('.mod-ov').forEach(function(m){{m.style.display='none';}});}}
    function setD(m){{document.getElementById('v-dur').value=m;}}
    function svDel(){{var mins=parseInt(document.getElementById('v-dur').value);var rsn=document.getElementById('v-rsn').value||'Delay/Overtime';var day=parseInt(document.getElementById('v-day').value);var hr=parseInt(document.getElementById('v-time').value);if(isNaN(mins)||mins<=0)return;window.dels.push({{id:Date.now(),day:day,hr:hr,mins:mins,rsn:rsn}});localStorage.setItem('sp_dels',JSON.stringify(window.dels));document.getElementById('v-dur').value=15;document.getElementById('v-rsn').value='';clsMod();applyDelays();}}
    function buildRemList(){{var h='';if(window.dels.length===0)h='<div style="color:var(--ink3);text-align:center;padding:20px;">No delays added yet.</div>';else{{window.dels.forEach(function(d){{h+='<div class="d-itm"><div><strong style="color:var(--accent)">Day '+d.day+' @ '+d.hr+':00</strong>: '+d.mins+'m<br><span style="color:var(--ink2);font-size:11px">'+d.rsn+'</span></div><button class="rm-btn" onclick="rmDel('+d.id+')">Remove</button></div>';}});}}document.getElementById('v-del-list').innerHTML=h;}}
    function rmDel(id){{window.dels=window.dels.filter(function(d){{return d.id!==id;}});localStorage.setItem('sp_dels',JSON.stringify(window.dels));buildRemList();applyDelays();}}
    function applyDelays(){{
      document.querySelectorAll('.time-adj,.skip-rec,.injected-delay').forEach(function(e){{e.remove();}});
      var cards=document.querySelectorAll('.sc:not(.injected-delay)');
      cards.forEach(function(c){{c.classList.remove('skipped');var sid=c.getAttribute('data-id');var btn=c.querySelector('.stog');if(sid&&window.skips.includes(sid)){{c.classList.add('skipped');if(btn)btn.innerHTML='➕ Restore';}}else if(btn)btn.innerHTML='➖ Remove';var stEl=c.querySelector('.st');if(stEl&&stEl.dataset.orig)stEl.innerHTML=stEl.dataset.orig;}});
      if(window.dels.length===0&&window.skips.length===0)return;
      window.dels.forEach(function(d){{var dc=document.createElement('div');dc.className='sc injected-delay';dc.setAttribute('data-day',d.day);dc.setAttribute('data-hour',d.hr);dc.setAttribute('data-delay-id',d.id);dc.style.borderLeftColor='var(--brand)';dc.style.background='var(--accent-soft)';var hrStr=String(d.hr).padStart(2,'0')+':00';dc.innerHTML='<div style="display:flex;align-items:baseline;gap:10px"><div class="st">'+hrStr+'</div><div><span class="sn" style="color:var(--accent)">🛑 Added Stop / Delay</span><br><span class="stp">'+d.mins+' minutes ('+d.rsn+')</span></div></div>';var ins=false;for(var i=0;i<cards.length;i++){{var c=cards[i];var cd=parseInt(c.getAttribute('data-day'));var ch=parseInt(c.getAttribute('data-hour'));if(cd===d.day&&ch>=d.hr){{c.parentNode.insertBefore(dc,c);ins=true;break;}}else if(cd>d.day){{c.parentNode.insertBefore(dc,c);ins=true;break;}}}}if(!ins)document.getElementById('atl').appendChild(dc);}});
      var allCards=document.querySelectorAll('.sc');var dayShifts={{}};for(var k=1;k<=15;k++)dayShifts[k]=[];
      window.dels.forEach(function(d){{dayShifts[d.day].push({{type:'add',hr:d.hr,mins:d.mins,id:d.id}});}});
      cards.forEach(function(c){{var sid=c.getAttribute('data-id');if(sid&&window.skips.includes(sid)){{var cD=parseInt(c.getAttribute('data-day'));var cH=parseInt(c.getAttribute('data-hour'));var cDur=parseInt(c.getAttribute('data-dur')||60);if(dayShifts[cD])dayShifts[cD].push({{type:'sub',hr:cH,mins:cDur,id:sid}});}}}});
      allCards.forEach(function(c){{var dA=c.getAttribute('data-day');var hA=c.getAttribute('data-hour');if(!dA||!hA)return;var cardDay=parseInt(dA);var cardHr=parseInt(hA);var delayId=c.getAttribute('data-delay-id');var isImmune=c.getAttribute('data-immune')==='true';var mins=0;(dayShifts[cardDay]||[]).forEach(function(sh){{if(sh.type==='add'&&cardHr>=sh.hr&&String(sh.id)!==delayId)mins+=sh.mins;if(sh.type==='sub'&&cardHr>sh.hr)mins-=sh.mins;}});if(isImmune)return;if(mins===0)return;var stEl=c.querySelector('.st');if(!stEl)return;if(!stEl.dataset.orig)stEl.dataset.orig=stEl.innerHTML;var tot=cardHr*60+mins;var nh=Math.floor(tot/60);var nm=tot%60;if(nh<0){{nh=0;nm=0;}}if(nh>23){{nh=23;nm=59;}}var tStr=String(nh).padStart(2,'0')+':'+String(nm).padStart(2,'0');var sign=mins>0?'+':'';var tCls=mins<0?'time-adj time-sub':'time-adj';stEl.innerHTML=tStr+' <span class="'+tCls+'">'+sign+mins+'m</span>';if(nh>=19&&!delayId){{if(!c.querySelector('.skip-rec')&&c.getAttribute('data-immune')!=='true'){{var rec=document.createElement('div');rec.className='skip-rec';rec.innerHTML='⚠️ Running late — dinner is drifting past 21:30. Consider trimming a stop.';c.insertBefore(rec,c.firstChild);}}}}}});
      af();
    }}
    function sv(v){{var m=document.querySelector('.folium-map');var a=document.getElementById('av');var t=document.getElementById('map-title');var bm=document.getElementById('bm');var ba=document.getElementById('ba');var vt=document.getElementById('vtog');if(v==='agenda'){{if(m)m.style.display='none';if(t)t.style.display='none';a.style.display='block';bm.classList.remove('on');ba.classList.add('on');if(vt)vt.classList.add('agenda-mode');asc();}}else{{if(m)m.style.display='block';if(t)t.style.display='block';a.style.display='none';bm.classList.add('on');ba.classList.remove('on');if(vt)vt.classList.remove('agenda-mode');}}}}
    var CITIES=['Porto','Lisbon','Seville','Granada','Madrid'];
    var _f=new Set(['all'].concat(CITIES).concat(['moor','food','hist']));
    function tf(b){{var f=b.getAttribute('data-f');if(f==='all'){{_f=new Set(['all'].concat(CITIES).concat(['moor','food','hist']));document.querySelectorAll('.fp').forEach(function(p){{p.className='fp active';}});}}else{{if(b.className.indexOf('active')>=0){{b.className='fp';_f.delete(f);}}else{{b.className='fp active';_f.add(f);}}if(CITIES.indexOf(f)>=0){{var ok=CITIES.every(function(x){{return _f.has(x);}});var ab=document.querySelector('[data-f="all"]');if(ok){{ab.className='fp active';_f.add('all');}}else{{ab.className='fp';_f.delete('all');}}}}}}af();}}
    function af(){{
      var qi=document.getElementById('af-q');
      var q=qi?qi.value.trim().toLowerCase():'';
      var cs=document.querySelectorAll('#atl .sc');var hs=document.querySelectorAll('#atl .dh');
      var hit={{}},shown=0;
      for(var i=0;i<cs.length;i++){{
        var c=cs[i];var ci=c.getAttribute('data-city');var tp=c.getAttribute('data-type');
        var mo=c.getAttribute('data-moor');var hi=c.getAttribute('data-hist');
        if(!ci)continue;
        var cityOk=(ci==='Transit')||_f.has(ci);
        var tok=true;
        if(tp==='food'&&!_f.has('food'))tok=false;
        if(mo==='true'&&!_f.has('moor'))tok=false;
        if(hi==='true'&&!_f.has('hist'))tok=false;
        // search matches anything in the card: name, notes, city, times, links
        var qok=!q||(c.textContent||'').toLowerCase().indexOf(q)>=0;
        var vis=cityOk&&tok&&qok;
        c.style.display=vis?'':'none';
        if(vis){{hit[c.getAttribute('data-day')]=1;shown++;}}
      }}
      for(var j=0;j<hs.length;j++){{
        var h=hs[j];var hc=h.getAttribute('data-city');
        // while searching, drop day headings that have nothing left under them
        var hv=(hc==='Transit'||_f.has(hc))&&(!q||hit[h.getAttribute('data-day')]);
        h.style.display=hv?'':'none';
      }}
      var nn=document.getElementById('af-none');
      if(nn) nn.style.display=shown?'none':'block';
    }}
    function asc(){{var n=new Date();var uh=n.getHours();var today=n.getFullYear()+'-'+String(n.getMonth()+1).padStart(2,'0')+'-'+String(n.getDate()).padStart(2,'0');var td=null;for(var k in DD){{if(DD[k]===today)td=parseInt(k);}}if(!td)return;var cs=document.querySelectorAll('.sc[data-hour]');for(var i=0;i<cs.length;i++){{var c=cs[i];var cd=parseInt(c.getAttribute('data-day'));var ch=parseInt(c.getAttribute('data-hour'));if((cd===td&&ch>=uh)||cd>td){{c.className+=' now';(function(el){{setTimeout(function(){{el.scrollIntoView({{behavior:'smooth',block:'center'}});}},200);}})(c);return;}}}}}}
    if('serviceWorker' in navigator){{window.addEventListener('load',function(){{
      navigator.serviceWorker.register('sw.js',{{updateViaCache:'none'}}).then(function(reg){{
        reg.update();                       // check for a new worker on every load
        // when a new worker takes control, reload once so the fresh page shows
        var reloaded=false;
        navigator.serviceWorker.addEventListener('controllerchange',function(){{
          if(reloaded) return; reloaded=true; window.location.reload();
        }});
      }}).catch(function(){{}});
    }});}}
    applyDelays();
    </script>
    """

def build_popup_fit():
    """Keep marker cards inside the clear area of the screen.

    Leaflet auto-pans an opening popup into view, but it only knows about the
    map edges — not the floating title bar, view switcher and timeline layered
    on top. So a card would settle underneath them and get covered. Teaching it
    the real clear region fixes the placement without shrinking the card or
    making it scroll internally (which just hides the text)."""
    return r"""
    <style>
    /* Slightly tighter leading on phones — a real height saving, unlike a
       max-height, which only hides the text behind an inner scrollbar. */
    @media(max-width:600px){
      .leaflet-popup-content > div{line-height:1.46 !important;}
    }
    </style>
    <script>
    (function(){
      function apply(){
        if(!window.L||!L.Popup||!L.point) return false;
        var small=window.matchMedia('(max-width:600px)').matches;
        // top: title card.  bottom: view switcher + day timeline.
        L.Popup.mergeOptions({
          autoPanPaddingTopLeft:     L.point(12, small? 78 : 100),
          autoPanPaddingBottomRight: L.point(12, small? 200 : 150),
          autoPan:true, keepInView:false
        });
        return true;
      }
      if(!apply()){
        var n=0, t=setInterval(function(){ if(apply()||++n>40) clearInterval(t); },100);
      }
      window.addEventListener('resize',apply);
      window.addEventListener('orientationchange',function(){ setTimeout(apply,250); });

      // On a touch screen there is no hover, so a marker tap fires the tooltip
      // AND the popup — the tooltip just repeats the popup's title in the
      // corner. Drop it for markers only; route lines keep theirs, since the
      // transit mode and duration have nowhere else to show.
      function noHover(){ return window.matchMedia('(hover:none)').matches; }
      function strip(l){
        try{
          if(l.getLatLng && l.unbindTooltip) l.unbindTooltip();   // marker, not a path
          if(l.eachLayer) l.eachLayer(strip);
        }catch(e){}
      }
      function tidy(){
        if(!window.L||!noHover()) return false;
        var mp=null;
        for(var k in window){ try{ if(window[k] instanceof L.Map){ mp=window[k]; break; } }catch(e){} }
        if(!mp) return false;
        mp.eachLayer(strip);
        mp.on('layeradd',function(e){ if(noHover()) strip(e.layer); });  // day layers toggle
        return true;
      }
      if(!tidy()){
        var n2=0, t2=setInterval(function(){ if(tidy()||++n2>40) clearInterval(t2); },100);
      }
    })();
    </script>
    """

def build_vscrubber():
    """Vertical day rail for the itinerary view — the agenda's answer to the
    map's horizontal scrubber. Tap or drag to scroll to a day; it also tracks
    your position as you scroll."""
    days=[{"d":d,"date":f"{int(DAY_DATES[d][5:7])}/{int(DAY_DATES[d][8:10])}",
           "city":DAY_CITY[d],"color":REGION_COLORS[region(DAY_CITY[d])]} for d in range(1,16)]
    html=r"""
    <div id="vscrub" aria-label="Jump to a day">
      <div id="vs-flag"></div>
      <div id="vs-rail"></div>
    </div>
    <style>
    #vscrub{position:fixed;right:10px;top:50%;transform:translateY(-50%);z-index:1600;
      display:none;flex-direction:row;align-items:center;font-family:var(--sans);
      touch-action:none;user-select:none;-webkit-user-select:none}
    body.ag-on #vscrub{display:flex}
    #vs-rail{display:flex;flex-direction:column;gap:3px;padding:9px 6px;border-radius:16px;
      background:color-mix(in srgb,var(--panel) 84%,transparent);backdrop-filter:blur(10px);
      border:1px solid var(--line);box-shadow:var(--shadow)}
    .vs-tick{width:26px;height:14px;border:none;background:transparent;padding:0;cursor:pointer;
      display:flex;align-items:center;justify-content:center}
    .vs-tick i{display:block;width:13px;height:3px;border-radius:2px;background:var(--c);
      opacity:.42;transition:width .15s,height .15s,opacity .15s}
    .vs-tick:hover i{opacity:.85}
    .vs-tick.act i{width:22px;height:5px;opacity:1}
    #vs-flag{position:absolute;right:46px;white-space:nowrap;font-size:12px;font-weight:700;
      color:#fff;background:var(--brand);padding:5px 11px;border-radius:9px;opacity:0;
      transition:opacity .16s;pointer-events:none;box-shadow:var(--shadow)}
    #vs-flag.on{opacity:1}
    @media(max-width:600px){
      #vscrub{right:3px}
      .vs-tick{width:22px;height:13px}
      .vs-tick i{width:11px}
      .vs-tick.act i{width:18px}
      #vs-flag{right:34px;font-size:11px;padding:4px 9px}
      /* behave like a native scrollbar: appear while scrolling, fade out when
         idle so the rail never sits on top of the cards */
      body.ag-on #vscrub{opacity:0;pointer-events:none;
        transition:opacity .28s ease;}
      body.ag-on #vscrub.vis{opacity:1;pointer-events:auto;}
    }
    @media(max-height:540px){ .vs-tick{height:10px} }
    </style>
    <script>
    (function(){
      var VD=__VDAYS__;
      var box=document.getElementById('vscrub'), rail=document.getElementById('vs-rail');
      var flag=document.getElementById('vs-flag'), av=document.getElementById('av');
      if(!box||!rail||!av) return;
      var ticks=[];
      VD.forEach(function(o){
        var b=document.createElement('button');
        b.type='button'; b.className='vs-tick'; b.setAttribute('data-day',o.d);
        b.title='Day '+o.d+' · '+o.city;
        b.innerHTML='<i style="--c:'+o.color+'"></i>';
        rail.appendChild(b); ticks.push(b);
      });
      function head(d){ return av.querySelector('.dh[data-day="'+d+'"]'); }
      function barH(){
        // only reserve room when the filter bar is actually pinned; on phones it
        // now scrolls away with the header, so reserving its height would
        // overshoot every day-jump by ~119px
        var b=document.getElementById('af'); if(!b) return 0;
        var pos=getComputedStyle(b).position;
        return (pos==='sticky'||pos==='fixed') ? b.getBoundingClientRect().height : 0;
      }
      function mark(d){
        for(var i=0;i<ticks.length;i++) ticks[i].classList.toggle('act', i+1===d);
        var o=VD[d-1]; if(!o) return;
        flag.textContent='Day '+o.d+' · '+o.date+' · '+o.city;
        var t=ticks[d-1];
        if(t) flag.style.top=(t.offsetTop+rail.offsetTop-2)+'px';
      }
      function goTo(d,smooth){
        var h=head(d); if(!h){ mark(d); return; }
        var top=Math.max(0, av.scrollTop + h.getBoundingClientRect().top
                            - av.getBoundingClientRect().top - barH() - 10);
        // Always jump instantly. Chrome's smooth animation both stalls ~2000px
        // short on long jumps and keeps running into the next tap, which made
        // rapid tapping/dragging land on the wrong day.
        av.scrollTop=top;
        mark(d);
      }
      var ft=null;
      function flash(){ flag.classList.add('on'); clearTimeout(ft);
        ft=setTimeout(function(){ flag.classList.remove('on'); },1200); }
      // Reveal the rail while the user is scrolling or using it, then let it
      // fade back out — on phones it would otherwise cover the cards.
      var hideT=null;
      function showRail(hold){
        box.classList.add('vis'); clearTimeout(hideT);
        if(!hold) hideT=setTimeout(function(){
          if(!drag) box.classList.remove('vis');
        },1500);
      }
      ticks.forEach(function(t){
        t.addEventListener('click',function(e){
          e.preventDefault(); e.stopPropagation();
          goTo(+t.getAttribute('data-day'),true); flash(); showRail();
        });
      });
      var drag=false;
      function dayFromY(y){
        // snap to the nearest tick centre — a linear fraction of the rail is
        // off by one, because the rail has padding and inter-tick gaps
        var best=1, bd=Infinity;
        for(var i=0;i<ticks.length;i++){
          var r=ticks[i].getBoundingClientRect();
          var dist=Math.abs((r.top+r.height/2)-y);
          if(dist<bd){ bd=dist; best=i+1; }
        }
        return best;
      }
      rail.addEventListener('pointerdown',function(e){
        drag=true; try{ rail.setPointerCapture(e.pointerId); }catch(_){}
        showRail(true); goTo(dayFromY(e.clientY),false); flag.classList.add('on'); e.preventDefault();
      });
      rail.addEventListener('pointermove',function(e){ if(drag) goTo(dayFromY(e.clientY),false); });
      window.addEventListener('pointerup',function(){ if(drag){ drag=false; flash(); showRail(); } });
      var raf=null;
      av.addEventListener('scroll',function(){
        showRail();
        if(raf||drag) return;
        raf=requestAnimationFrame(function(){
          raf=null; if(drag) return;
          var limit=av.getBoundingClientRect().top+barH()+16, best=1;
          for(var i=0;i<VD.length;i++){
            var h=head(VD[i].d); if(!h) continue;
            if(h.getBoundingClientRect().top<=limit) best=VD[i].d;
          }
          mark(best);
        });
      },{passive:true});
      function sync(){
        var on=getComputedStyle(av).display!=='none';
        document.body.classList.toggle('ag-on', on);
      }
      try{ new MutationObserver(sync).observe(av,{attributes:true,attributeFilter:['style','class']}); }catch(e){}
      sync(); mark(1);
    })();
    </script>
    """
    return html.replace("__VDAYS__", json.dumps(days))

def build_scrubber():
    def _largest_cluster(coords):
        # single-link group a day's stops by ~6° proximity, return the biggest
        # group — frames the day's MAIN location (DC for Day 1, Madrid for
        # Day 15) and drops lone transatlantic outliers from the default fit.
        clusters=[]
        for p in coords:
            placed=False
            for c in clusters:
                if any(abs(p[0]-q[0])<6 and abs(p[1]-q[1])<6 for q in c):
                    c.append(p); placed=True; break
            if not placed: clusters.append([p])
        return max(clusters, key=len) if clusters else []
    days=[]
    for d in range(1,16):
        allpts=[[round(s[1],5),round(s[2],5)] for s in S if s[3]==d]
        days.append({"d":d,
                     "date":f"{int(DAY_DATES[d][5:7])}/{int(DAY_DATES[d][8:10])}",
                     "city":DAY_CITY[d],
                     "color":REGION_COLORS[region(DAY_CITY[d])],
                     "pts":_largest_cluster(allpts),          # default day zoom = main cluster
                     "stops":[{"lat":round(s[1],5),"lon":round(s[2],5),"name":s[0]}
                              for s in S if s[3]==d]})         # ordered → drives the stop-stepper
    # Bounding box of every Iberian stop — the whole-trip view fits THIS rather
    # than a fixed zoom, so it packs in as tightly as the screen allows and
    # ignores the Washington/Paris/Boston outliers entirely.
    ib=[(s[1],s[2]) for s in S if -10.0<=s[2]<=0.0 and 35.0<=s[1]<=44.0]
    ALLB=[[min(p[0] for p in ib), min(p[1] for p in ib)],
          [max(p[0] for p in ib), max(p[1] for p in ib)]]
    DAYS_JS=json.dumps(days)
    html=r"""
    <div id="scrub" role="group" aria-label="Trip day timeline">
      <div id="scrub-top">
        <button id="scrub-all" class="on" type="button">All 15 days</button>
        <span id="scrub-label">Aug 6–20 · whole trip</span>
        <div id="scrub-step" class="dis" aria-label="Step through the day's stops">
          <button id="step-prev" type="button" title="Previous stop" aria-label="Previous stop">‹</button>
          <button id="step-focus" type="button" title="Focus this day's stops" aria-label="Focus stops">◎</button>
          <button id="step-next" type="button" title="Next stop" aria-label="Next stop">›</button>
        </div>
      </div>
      <div id="scrub-track">
        <div id="scrub-line"></div>
        <div id="scrub-thumb"></div>
      </div>
    </div>
    <style>
    #scrub{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:1000;
      width:min(94vw,860px);background:var(--panel);border:1px solid var(--line);backdrop-filter:blur(12px);
      border-radius:16px;box-shadow:var(--shadow);padding:10px 16px 14px;
      font-family:var(--sans);box-sizing:border-box;touch-action:none;}
    #scrub-top{display:flex;align-items:center;gap:12px;margin-bottom:6px;}
    #scrub-all{border:1px solid var(--line);background:transparent;color:var(--ink2);border-radius:20px;
      padding:4px 12px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .15s;}
    #scrub-all.on{background:var(--brand);color:#fff;border-color:var(--brand);}
    #scrub-label{font-size:13px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1 1 auto;min-width:0;}
    #scrub-label b{color:var(--accent);font-weight:700;}
    #scrub-step{display:flex;align-items:center;gap:5px;margin-left:auto;flex-shrink:0;}
    #scrub-step button{width:27px;height:27px;border-radius:8px;border:1px solid var(--line);
      background:transparent;color:var(--brand);font-size:16px;line-height:1;cursor:pointer;
      display:flex;align-items:center;justify-content:center;padding:0;transition:all .15s;}
    #scrub-step button:hover:not(:disabled){background:var(--brand);color:#fff;border-color:var(--brand);}
    #scrub-step #step-focus{font-size:14px;}
    #scrub-step button:disabled,#scrub-step.dis button{opacity:0.32;cursor:default;}
    body.hide-far path.farflight{display:none !important;}
    #scrub-track{position:relative;height:40px;margin:0 12px;cursor:pointer;}
    #scrub-line{position:absolute;top:19px;left:0;right:0;height:5px;border-radius:3px;
      background:linear-gradient(90deg,#41827b,#4c72a0,#c15f3c,#b3812f,#8c6183);opacity:0.88;}
    .scrub-tick{position:absolute;top:9px;transform:translateX(-50%);background:transparent;border:none;
      padding:0;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px;width:22px;}
    .scrub-tick .tk-bar{width:3px;height:14px;border-radius:2px;background:var(--c);opacity:0.5;transition:all .15s;}
    .scrub-tick .tk-n{font-size:9px;color:var(--ink3);font-weight:600;transition:color .15s;}
    .scrub-tick.act .tk-bar{opacity:1;height:20px;width:4px;}
    .scrub-tick.act .tk-n{color:var(--ink);}
    #scrub-thumb{position:absolute;top:11px;width:22px;height:22px;border-radius:50%;
      background:var(--brand);border:3px solid var(--panel);box-shadow:0 2px 8px rgba(0,0,0,0.35);
      transform:translateX(-50%);transition:left .12s ease,opacity .12s;opacity:0;pointer-events:none;z-index:3;}
    @media(max-width:600px){
      #scrub{bottom:12px;padding:8px 12px 12px;width:96vw;}
      #scrub-label{font-size:12px;}
      .scrub-tick .tk-n{font-size:8px;}
    }
    </style>
    <script>
    (function(){
      var DAYS=__DAYS__, N=DAYS.length, sel='all', dragging=false, stopIdx=-1;
      var track=document.getElementById('scrub-track');
      var thumb=document.getElementById('scrub-thumb');
      var line=document.getElementById('scrub-line');
      var lab=document.getElementById('scrub-label');
      var allb=document.getElementById('scrub-all');
      var stepWrap=document.getElementById('scrub-step');
      var bPrev=document.getElementById('step-prev');
      var bFocus=document.getElementById('step-focus');
      var bNext=document.getElementById('step-next');
      var GRAD='linear-gradient(90deg,#41827b,#4c72a0,#c15f3c,#b3812f,#8c6183)';
      var MC=[40.0,-5.6], MZ=6, AB=__ALLB__, _map=null;
      function getMap(){
        if(_map) return _map;
        if(!window.L) return null;
        for(var k in window){ try{ if(window[k] && window[k] instanceof L.Map){ _map=window[k]; break; } }catch(e){} }
        return _map;
      }
      function fitAll(mp){
        // fitBounds works off the container size, so a fit run before the map
        // has been laid out silently falls back to the old fixed zoom.
        try{ mp.invalidateSize(false); }catch(e){}
        var sm=window.matchMedia('(max-width:600px)').matches;
        try{
          // the whole-trip view is deliberately tighter than a day fit — it only
          // has to clear the chrome, not leave breathing room around a cluster
          var o=fitPad(mp);
          mp.fitBounds(L.latLngBounds(AB),
            {paddingTopLeft:[16, Math.min(o.paddingTopLeft[1], sm?90:96)],
             paddingBottomRight:[16, Math.min(o.paddingBottomRight[1], sm?182:128)]});
        }catch(e){ mp.setView(MC, MZ); }
      }
      // Tablet = touch input at desktop-ish width. iPads report ~1366-1408 CSS px
      // in landscape, so width alone cannot tell one from a laptop.
      function isTablet(){
        return window.matchMedia('(hover:none) and (pointer:coarse)').matches
            && !window.matchMedia('(max-width:600px)').matches;
      }
      // Measure the floating chrome rather than guessing at it. The old fixed
      // [70,110] cleared the title card on a phone and on a desktop, but not on
      // a tablet, where the card is both taller and wider — the first stops of
      // a day ended up underneath it.
      // A marker is anchored at its point but drawn ~41px ABOVE it, so padding
      // only to the bottom of the key still lets the topmost pin ride up
      // underneath it. Clear the pin's own height plus a little air.
      var PIN=41;
      function fitPad(mp){
        var sz=mp.getSize(), padT=100, padB=150, padX=isTablet()?40:24;
        var tl=document.getElementById('map-title');
        if(tl){
          var r=tl.getBoundingClientRect();
          if(r.height) padT=Math.round(r.bottom+PIN+8);
        }
        var sc=document.getElementById('scrub');
        if(sc){
          var b=sc.getBoundingClientRect();
          if(b.height) padB=Math.round(sz.y-b.top+16);
        }
        // never let the two together swallow the viewport on a short window
        var cap=Math.round(sz.y*0.40);
        return {paddingTopLeft:[padX, Math.min(padT,cap)],
                paddingBottomRight:[padX, Math.min(padB,cap)]};
      }
      function zoomTo(s){
        var mp=getMap(); if(!mp) return;
        if(s==='all'){ fitAll(mp); return; }
        var pts=(DAYS[s-1]||{}).pts;
        if(!pts||!pts.length){ mp.setView(MC, MZ); return; }
        var tab=isTablet();
        if(pts.length===1){ mp.setView(pts[0], tab?12:13); return; }
        var o=fitPad(mp); o.maxZoom = tab?13:14;   // a notch wider on tablets
        try{ mp.fitBounds(L.latLngBounds(pts), o); }
        catch(e){ mp.setView(pts[0], tab?11:12); }
      }
      function curStops(){ return (sel!=='all'&&DAYS[sel-1])?(DAYS[sel-1].stops||[]):[]; }
      function updateStepUI(){
        var st=curStops(), active=(sel!=='all');
        stepWrap.classList.toggle('dis', !active);
        // arrows also roll over to the prev/next DAY at the ends of a day
        bPrev.disabled=!active || !(stopIdx>0 || sel>1);
        bNext.disabled=!active || !(stopIdx<st.length-1 || sel<N);
      }
      function openStopCard(s){
        // open the marker popup for the stepped-to stop; closes any prior one
        var mp=getMap(); if(!mp||!s) return;
        mp.closePopup();
        var best=null, bd=9e9;
        mp.eachLayer(function(l){
          if(l&&l.getLatLng&&l.getPopup&&l.getPopup()){
            var ll=l.getLatLng(), d=Math.abs(ll.lat-s.lat)+Math.abs(ll.lng-s.lon);
            if(d<bd){bd=d;best=l;}
          }
        });
        if(best&&bd<0.0008) best.openPopup();
      }
      function focusStop(){
        var st=curStops(); if(!st.length) return;
        var mp=getMap(); if(!mp){updateStepUI();return;}
        var s=st[stopIdx]; if(!s){updateStepUI();return;}
        // A long hop from the previous stop (e.g. the transatlantic leg to
        // Boston) zooms out to frame the flight path; otherwise centre the stop.
        if(stopIdx>0){
          var p=st[stopIdx-1];
          if(Math.abs(s.lat-p.lat)>4||Math.abs(s.lon-p.lon)>4){
            var mlat=(s.lat+p.lat)/2, mlon=(s.lon+p.lon)/2;
            var chord=Math.sqrt(Math.pow(s.lon-p.lon,2)+Math.pow(s.lat-p.lat,2));
            var peak=[mlat+0.055*chord, mlon];   // matches the flight-path bow
            try{ mp.fitBounds(L.latLngBounds([[p.lat,p.lon],[s.lat,s.lon],peak]),
                 {paddingTopLeft:[50,95],paddingBottomRight:[50,130],maxZoom:8}); }catch(e){}
            lab.textContent='Day '+sel+' · '+(stopIdx+1)+'/'+st.length+' · '+s.name;
            openStopCard(s); updateStepUI(); return;
          }
        }
        mp.setView([s.lat,s.lon], 15);
        lab.textContent='Day '+sel+' · '+(stopIdx+1)+'/'+st.length+' · '+s.name;
        openStopCard(s); updateStepUI();
      }
      function pos(i){return N<2?0:(i/(N-1))*100;}
      DAYS.forEach(function(o,i){
        var t=document.createElement('button');
        t.type='button';t.className='scrub-tick';t.style.left=pos(i)+'%';t.style.setProperty('--c',o.color);
        t.innerHTML='<span class="tk-bar"></span><span class="tk-n">'+o.d+'</span>';
        t.addEventListener('click',function(e){e.stopPropagation();pick(o.d);});
        track.appendChild(t);
      });
      function setDayLayers(s){
        var labs=document.querySelectorAll('.leaflet-control-layers-overlays label');
        labs.forEach(function(lb){
          var m=lb.textContent.trim().match(/^Day\s+(\d+)/); if(!m)return;
          var d=parseInt(m[1]), inp=lb.querySelector('input'); if(!inp)return;
          var want=(s==='all')||(d===s);
          if(inp.checked!==want) inp.click();
        });
      }
      function pick(s){
        sel=s; stopIdx=-1;
        var _mp=getMap(); if(_mp) _mp.closePopup();   // clear any stepped-open card
        if(s==='all'){allb.classList.add('on');thumb.style.opacity=0;line.style.background=GRAD;
          lab.textContent='Aug 6–20 · whole trip';document.body.classList.add('hide-far');}
        else{allb.classList.remove('on');var o=DAYS[s-1];
          thumb.style.opacity=1;thumb.style.left=pos(s-1)+'%';thumb.style.background=o.color;
          line.style.background='#e6e6e6';
          lab.innerHTML='<b>Day '+s+'</b> · '+o.date+' · '+o.city;document.body.classList.remove('hide-far');}
        var ticks=document.querySelectorAll('.scrub-tick');
        for(var k=0;k<ticks.length;k++){ticks[k].classList.toggle('act',sel!=='all'&&k===s-1);}
        setDayLayers(s);
        zoomTo(s);
        updateStepUI();
      }
      function dayFromX(x){var r=track.getBoundingClientRect();var f=(x-r.left)/r.width;
        f=Math.max(0,Math.min(1,f));return Math.round(f*(N-1))+1;}
      track.addEventListener('pointerdown',function(e){dragging=true;
        try{track.setPointerCapture(e.pointerId);}catch(_){}pick(dayFromX(e.clientX));e.preventDefault();});
      track.addEventListener('pointermove',function(e){if(dragging)pick(dayFromX(e.clientX));});
      window.addEventListener('pointerup',function(){dragging=false;});
      allb.addEventListener('click',function(){pick('all');});
      [400,1200].forEach(function(ms){ setTimeout(function(){
        var mp=getMap(); if(mp&&sel==='all') fitAll(mp);
      },ms); });
      window.addEventListener('resize',function(){
        var mp=getMap(); if(mp&&sel==='all') fitAll(mp);
      });
      bFocus.addEventListener('click',function(e){e.stopPropagation();
        if(sel==='all')return; stopIdx=0; focusStop();});
      bNext.addEventListener('click',function(e){e.stopPropagation();
        if(sel==='all')return; var st=curStops();
        if(stopIdx<st.length-1){stopIdx++;focusStop();}
        else if(sel<N){pick(sel+1);}});          // past last stop → next day overview
      bPrev.addEventListener('click',function(e){e.stopPropagation();
        if(sel==='all')return;
        if(stopIdx>0){stopIdx--;focusStop();}
        else if(sel>1){pick(sel-1);}});           // before first stop → prev day overview
      pick('all');
    })();
    </script>
    """
    return html.replace("__DAYS__", DAYS_JS).replace("__ALLB__", json.dumps(ALLB))

def build_theme():
    # Anthropic-style system: warm ivory (light) + deep Claude-Code grey (dark).
    return r"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,600&display=swap" rel="stylesheet">
    <button id="theme-tog" type="button" aria-label="Toggle dark mode" title="Toggle dark mode">🌙</button>
    <style>
    :root{
      --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
      --serif:'Fraunces','Iowan Old Style','Palatino Linotype',Georgia,serif;
      --bg:#f4f1ea; --panel:#fffdf8; --panel2:#eeeae0; --line:#e5e0d4;
      --ink:#211f1b; --ink2:#6d6759; --ink3:#9c9483;
      --accent:#bd5b36; --accent-soft:#f4e8e0; --brand:#cc785c;
      --shadow:0 1px 2px rgba(40,32,24,0.05),0 2px 14px rgba(40,32,24,0.04);
    }
    :root[data-theme="dark"]{
      --bg:#111113; --panel:#1a1a1c; --panel2:#222225; --line:#2c2c30;
      --ink:#ededee; --ink2:#9a9a9e; --ink3:#6b6b70;
      --accent:#e0876a; --accent-soft:#241d18; --brand:#d97757;
      --shadow:0 1px 2px rgba(0,0,0,0.45);
    }
    html,body{background:var(--bg);}
    /* ── Full-bleed on iOS Safari ──
       Folium sets html/body to height:100%, which Safari resolves to the SMALL
       viewport (the strip above its toolbar) — leaving a dead band at the
       bottom. Filling the LARGE viewport instead lets the map and the itinerary
       run behind the translucent toolbar, the way a native page does.
       On desktop and Android lvh == vh, so nothing changes there. */
    html,body{height:100vh;overscroll-behavior:none;margin:0;padding:0;}
    /* pin the map to the true screen corners so it also covers the status-bar
       and home-indicator strips rather than stopping at the safe-area edges */
    .folium-map{position:fixed;top:0;left:0;width:100vw;height:100vh;}
    @supports (height:100lvh){
      html,body{height:100lvh;}
      .folium-map{height:100lvh;}
      #av{bottom:auto;height:100lvh;}
    }
    #theme-tog{position:fixed;top:calc(12px + env(safe-area-inset-top));right:12px;z-index:2600;width:40px;height:40px;border-radius:50%;
      border:1px solid var(--line);background:var(--panel);color:var(--ink);box-shadow:var(--shadow);
      font-size:17px;cursor:pointer;display:flex;align-items:center;justify-content:center;line-height:1;padding:0;transition:transform .18s;}
    #theme-tog:hover{transform:scale(1.07);}
    /* Clears the theme toggle, which sits at top:12 and is 40px tall. It has to
       track the same safe-area inset the toggle uses — installed to the Home
       Screen the inset is non-zero, and a flat 52px left the layers control
       sitting underneath the toggle by exactly the inset. */
    .leaflet-top.leaflet-right{margin-top:calc(52px + env(safe-area-inset-top));}
    /* Map title box → panel + serif */
    #map-title{background:var(--panel) !important;border:1px solid var(--line);border-radius:12px !important;
      box-shadow:var(--shadow) !important;}
    .mt-t{font-family:var(--serif);font-size:18px;font-weight:600;color:var(--ink);letter-spacing:-0.2px;}
    #map-title .title-sub{color:var(--ink2) !important;}
    #map-title .title-legend,#map-title .title-credits{color:var(--ink3) !important;}
    /* Marker popups → panel + serif header, theme-aware */
    .leaflet-popup-content-wrapper{background:var(--panel) !important;border:1px solid var(--line);
      border-radius:16px !important;box-shadow:0 10px 34px rgba(0,0,0,0.20) !important;color:var(--ink);}
    .leaflet-popup-tip{background:var(--panel) !important;box-shadow:none !important;}
    .leaflet-popup-content{color:var(--ink);}
    .pop-h{font-family:var(--serif);font-size:15px;font-weight:600;letter-spacing:-0.1px;}
    /* Leaflet chrome */
    #av{background:var(--bg);}
    :root[data-theme="dark"] .leaflet-container{background:#0b0b0c;}
    .leaflet-control-layers{background:var(--panel) !important;color:var(--ink) !important;border:1px solid var(--line) !important;border-radius:14px !important;box-shadow:0 8px 28px rgba(0,0,0,0.16) !important;}
    .leaflet-control-layers-expanded{padding:10px 12px !important;}
    .leaflet-control-layers label{color:var(--ink);font-size:13px;margin-bottom:2px;display:flex;align-items:center;}
    .leaflet-control-layers label span{padding-left:2px;}
    .leaflet-control-layers input{accent-color:var(--brand);margin-right:5px;}
    .leaflet-control-layers-separator{border-top:1px solid var(--line) !important;margin:8px -4px;}
    :root[data-theme="dark"] .leaflet-control-layers-toggle{filter:invert(0.85) hue-rotate(180deg);}
    :root[data-theme="dark"] .leaflet-bar a{background:var(--panel);color:var(--ink);border-bottom-color:var(--line);}
    :root[data-theme="dark"] .leaflet-bar a:hover{background:var(--panel2);}
    :root[data-theme="dark"] .leaflet-control-attribution{background:rgba(26,26,28,0.85) !important;color:var(--ink3) !important;}
    :root[data-theme="dark"] .leaflet-control-attribution a{color:var(--ink2) !important;}
    /* Hover tooltips → panel card */
    .leaflet-tooltip{background:var(--panel) !important;border:1px solid var(--line) !important;color:var(--ink) !important;border-radius:9px !important;box-shadow:0 4px 16px rgba(0,0,0,0.18) !important;font-family:var(--sans) !important;font-size:12px !important;padding:6px 10px !important;}
    .leaflet-tooltip small{color:var(--ink2) !important;}
    .leaflet-tooltip-top:before{border-top-color:var(--line) !important;}
    .leaflet-tooltip-bottom:before{border-bottom-color:var(--line) !important;}
    .leaflet-tooltip-left:before{border-left-color:var(--line) !important;}
    .leaflet-tooltip-right:before{border-right-color:var(--line) !important;}
    /* Hide the km/mi scale control */
    .leaflet-control-scale{display:none !important;}
    /* Delay menu (inline-styled) */
    :root[data-theme="dark"] #d-menu{background:var(--panel) !important;}
    :root[data-theme="dark"] #d-menu button{color:var(--ink) !important;}
    /* ── Mobile / iOS Safari layout fixes ── */
    @media(max-width:600px){
      /* keep zoom/locate below the title header instead of over it */
      .leaflet-top.leaflet-left{margin-top:62px;}
      #map-title{max-width:calc(100vw - 66px) !important;}
      #map-title .mt-t{font-size:16px;}
      #map-title .title-route{display:none;}          /* shorten the sub line on phones */
      /* respect the home-bar / Safari toolbar safe area */
      #scrub{bottom:calc(12px + env(safe-area-inset-bottom)) !important;}
      #vtog{top:auto !important;bottom:calc(118px + env(safe-area-inset-bottom)) !important;}  /* clears the ~95px scrubber sitting 12px up */
      #vtog.agenda-mode{top:auto !important;bottom:calc(16px + env(safe-area-inset-bottom)) !important;}  /* low, tab-bar style, in the itinerary */
      #d-fab{bottom:calc(24px + env(safe-area-inset-bottom)) !important;}
      /* shrink the OSM/CARTO credit and sit it flush on the very bottom edge */
      .leaflet-control-attribution{font-size:8px !important;line-height:1.2 !important;
        padding:0 5px !important;opacity:0.6;margin:0 !important;border-radius:0 !important;}
      .leaflet-control-attribution img{height:7px !important;width:auto !important;}
      .leaflet-bottom.leaflet-right{bottom:0 !important;margin-bottom:0 !important;}
      /* reserve the top-right corner so the sticky filter chips never slide
         underneath the floating dark-mode toggle when the itinerary scrolls */
      #af{padding-right:62px !important;}
    }
    /* The page now fills the LARGE viewport, so anything pinned to the bottom
       would hide behind Safari's floating toolbar. (100lvh - 100dvh) is exactly
       the height of the chrome currently on screen — 0 when it retracts — so the
       controls ride just above it and follow it as it hides and reappears. */
    @supports (height:100dvh) and (height:100lvh){
      @media(max-width:600px){
        /* (100lvh - 100dvh) is the on-screen browser chrome, which ALREADY
           spans the home indicator — adding the safe-area inset on top of it
           double-counted ~34px and floated everything too high. Take whichever
           is larger instead: the toolbar when it's out, the inset when it isn't. */
        /* --chrome = how far up from the bottom the floating UI must sit.
           With the toolbar out we trim 40px off its measured height (it left a
           visible gap); with it retracted we fall back to just clearing the
           home indicator. max() keeps whichever is larger, so the controls can
           never slide under the search bar or off the bottom of the screen. */
        :root{--chrome:max(100lvh - 100dvh - 40px, env(safe-area-inset-bottom) + 6px);}
        #scrub{bottom:calc(var(--chrome) + 2px) !important;}
        #vtog{top:auto !important;bottom:calc(var(--chrome) + 106px) !important;}
        #vtog.agenda-mode{top:auto !important;bottom:calc(var(--chrome) + 8px) !important;}
        #d-fab{bottom:calc(var(--chrome) + 14px) !important;}
        /* left-hand bottom controls ride above the toolbar; the attribution
           deliberately stays flush on the true bottom edge */
        .leaflet-bottom.leaflet-left{margin-bottom:calc(100lvh - 100dvh) !important;}
        /* the itinerary is a fixed pane — pin it to the real screen corners so
           it fills behind the status bar and home indicator like the map does */
        #av{top:0 !important;bottom:auto !important;height:100lvh !important;}
        /* header sits just under the status bar rather than a fixed 50px down */
        .ah{padding-top:calc(env(safe-area-inset-top) + 12px) !important;}
      }
    }
    /* Installed to the Home Screen there is no browser chrome at all, so the
       page truly fills the display — but the status bar now floats OVER it,
       and there is no bottom toolbar to allow for. */
    @media all and (display-mode:standalone){
      /* True at every width, because standalone always puts content under the
         status bar — iPad included. */
      #map-title{top:calc(10px + env(safe-area-inset-top)) !important;}
      #theme-tog{top:calc(12px + env(safe-area-inset-top)) !important;}
      /* 58px is the desktop allowance for the top-centred switcher; on phones the
         switcher lives at the bottom, so 16px is all the header needs. */
      .ah{padding-top:calc(env(safe-area-inset-top) + 58px) !important;}
      /* content runs under the status bar here, so the sticky filter bar has to
         park below it rather than at y=0 — otherwise it sits under the clock
         and collides with the dark-mode toggle */
      #af{top:env(safe-area-inset-top) !important;padding-right:62px !important;}
      /* Everything below re-stacks the floating controls the way phones need
         them (switcher above the scrubber, both hugging the bottom edge). On a
         tablet the window is desktop-shaped and the desktop placement is right,
         so this must NOT leak past 600px — unguarded, it pinned `bottom` on a
         switcher that still had `top:12px` and stretched it down the screen. */
      @media(max-width:600px){
        .ah{padding-top:calc(env(safe-area-inset-top) + 16px) !important;}
        .leaflet-top.leaflet-left{margin-top:calc(62px + env(safe-area-inset-top)) !important;}
        #scrub{bottom:calc(env(safe-area-inset-bottom) + 10px) !important;}
        #vtog{top:auto !important;bottom:calc(env(safe-area-inset-bottom) + 114px) !important;}
        #vtog.agenda-mode{top:auto !important;bottom:calc(env(safe-area-inset-bottom) + 12px) !important;}
        #d-fab{bottom:calc(env(safe-area-inset-bottom) + 20px) !important;}
      }
    }
    </style>
    <script>
    (function(){
      var KEY='trip_theme';
      function basemap(dark){
        var labs=document.querySelectorAll('.leaflet-control-layers-base label');
        for(var i=0;i<labs.length;i++){
          var t=labs[i].textContent.trim(), inp=labs[i].querySelector('input'); if(!inp)continue;
          var want = dark ? /Dark/.test(t) : /Street/.test(t);
          if(want && !inp.checked){ inp.click(); }
        }
      }
      function apply(theme, switchmap){
        document.documentElement.setAttribute('data-theme', theme);
        var b=document.getElementById('theme-tog'); if(b) b.textContent = (theme==='dark')?'☀️':'🌙';
        var tc=document.querySelector('meta[name=theme-color]'); if(tc) tc.content=(theme==='dark')?'#111113':'#f4f1ea';
        if(switchmap) setTimeout(function(){ basemap(theme==='dark'); }, 60);
      }
      var saved=null; try{ saved=localStorage.getItem(KEY); }catch(_){}
      var sysDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      var theme = saved || (sysDark?'dark':'light');
      apply(theme, false);
      window.addEventListener('load', function(){ setTimeout(function(){ basemap(theme==='dark'); }, 500); });
      var btn=document.getElementById('theme-tog');
      if(btn) btn.addEventListener('click', function(){
        var next=(document.documentElement.getAttribute('data-theme')==='dark')?'light':'dark';
        try{ localStorage.setItem(KEY,next); }catch(_){}
        apply(next, true);
      });
    })();
    </script>
    """

if __name__=="__main__":
    paths=build_paths()
    weather=fetch_weather()
    print("\nBuilding interactive map…")
    m=build_map(paths, weather)
    out="spain.html"
    m.save(out)
    import re
    html=open(out,encoding="utf-8").read()
    html=re.sub(r'(<(meta|link|img|br|hr|input)[^>]*?)\s*/>', r'\1>', html)
    # iOS: extend content under the Safari toolbars + tint the browser UI
    # Replace folium's multi-line viewport meta outright. Appending to it left a
    # newline inside content="…", which iOS Safari fails to parse — so
    # viewport-fit=cover was ignored and the page got inset by the safe areas,
    # leaving dead bands under the status bar and home indicator.
    html=re.sub(r'<meta\s+name="viewport"[^>]*>',
                '<meta name="viewport" content="width=device-width, initial-scale=1.0, '
                'maximum-scale=1.0, user-scalable=no, viewport-fit=cover">',
                html, count=1)
    # Installable-app metadata. Safari always reserves the status-bar strip for a
    # normal tab — no site can draw under it. Added to the Home Screen, though,
    # the page runs standalone with no browser chrome at all: genuinely edge to
    # edge, and it keeps working offline via the service worker.
    html=html.replace('</head>',
        '    <meta name="theme-color" content="#111113">\n'
        '    <meta name="apple-mobile-web-app-capable" content="yes">\n'
        '    <meta name="mobile-web-app-capable" content="yes">\n'
        '    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
        '    <meta name="apple-mobile-web-app-title" content="Iberia 2026">\n'
        '    <link rel="manifest" href="manifest.json">\n'
        '</head>', 1)
    open(out,"w",encoding="utf-8").write(html)
    print(f"\n✓ Saved: {out} ({os.path.getsize(out)/1024:.0f} KB)")
