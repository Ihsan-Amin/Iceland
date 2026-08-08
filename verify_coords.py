#!/usr/bin/env python3
"""Check every pinned stop against an authoritative geocoder.

The coordinates in spain_interactive_map.py were entered by hand. Most are
fine, but a wrong one is expensive: it throws off the drawn route, the walking
time between stops, and the 📍 Map link on the card. Graham's Port Lodge was
the example that surfaced it — its pin sat on the hillside behind the lodge,
which made the router take an 11 km detour for a 0.77 km hop.

This does NOT rewrite anything. It geocodes each stop and writes a report so
the deltas can be reviewed by eye: geocoders confidently return the wrong
thing often enough (a chain's other branch, a street of the same name in
another city) that blind auto-apply would trade one bad pin for another.

Runs on the GitHub runner — Nominatim is unreachable from the dev sandbox.
Usage: python3 verify_coords.py [--out spain_geocode_report.json]
"""
import json, re, sys, time, urllib.parse, urllib.request
from math import radians, sin, cos, asin, sqrt

UA = "iberia-itinerary-coord-check/1.0 (github.com/Ihsan-Amin/Iceland)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"

# Stops that are not lookup-able places: hotel bookends, transit markers,
# free-time blocks. Skipped rather than reported as failures.
SKIP = re.compile(
    r'^(Leave |Back to )|layover|Free Madrid morning|Siesta|Rest / pool'
    r'|free time\)$|— guided walk|walking tour|panoramic tour|Tour meet-up'
    r'|Tour pickup|Back in |drop-off|Solar eclipse|Lunch in |evening\)$',
    re.I)

# Where the stop's display name is not a searchable place name, give the
# geocoder something it can actually resolve. Left-hand side is the stop name.
QUERY = {
 "🌄 Pedra dos Gatinhos":              "Cais de Gaia, Vila Nova de Gaia, Portugal",
 "🚡 Teleférico de Gaia (cable car)":  "Teleferico de Gaia, Vila Nova de Gaia, Portugal",
 "Castro — Atelier de Pastéis de Nata 🥧": "Castro Atelier de Natas, Rua das Flores, Porto, Portugal",
 "Manteigaria — pastéis de nata ☕🥧":  "Manteigaria, Rua dos Clerigos, Porto, Portugal",
 "🚢 Six Bridges Douro cruise":        "Cais de Gaia, Vila Nova de Gaia, Portugal",
 "🍷 Taylor's Port Cellars":           "Taylor's Port, Rua do Choupelo, Vila Nova de Gaia, Portugal",
 "São Bento azulejo hall":             "Sao Bento railway station, Porto, Portugal",
 "Sé do Porto (Cathedral)":            "Se do Porto, Porto, Portugal",
 "✊ UNICEPE bookshop":                "UNICEPE, Praca de Carlos Alberto, Porto, Portugal",
 "Pastelaria Santo António 🥧":        "Rua do Milagre de Santo Antonio, Lisboa, Portugal",
 "🌄 Miradouro da Senhora do Monte":   "Miradouro da Senhora do Monte, Lisboa, Portugal",
 "🛍 Feira da Ladra flea market":      "Feira da Ladra, Campo de Santa Clara, Lisboa, Portugal",
 "🕌 Alfama + Miradouro de Santa Luzia":"Miradouro de Santa Luzia, Lisboa, Portugal",
 "⭐ Tram 28 / Ler Devagar 📚":         "Ler Devagar, LX Factory, Lisboa, Portugal",
 "Tascantiga — Sintra lunch 🍽":       "Tascantiga, Sintra, Portugal",
 "La Terraza de EME 🍸🌄":              "EME Catedral Mercer, Calle Alemanes, Sevilla, Spain",
 "🛍 Calle Sierpes & Calle Tetuán":    "Calle Sierpes, Sevilla, Spain",
 "Triana + Calle Betis 🌆":            "Calle Betis, Sevilla, Spain",
 "El Rinconcillo 🍷":                  "El Rinconcillo, Calle Gerona, Sevilla, Spain",
 "Bodega Romero 🥪":                   "Bodega Romero, Calle Harinas, Sevilla, Spain",
 "Bodega Santa Cruz — Las Columnas 🍤":"Bodega Santa Cruz Las Columnas, Sevilla, Spain",
 "Bodegas Castañeda 🍷":               "Bodegas Castaneda, Calle Almireceros, Granada, Spain",
 "Los Diamantes — Plaza Nueva 🐟":     "Los Diamantes, Plaza Nueva, Granada, Spain",
 "Taberna La Tana 🍷":                 "Taberna La Tana, Granada, Spain",
 "Casa Revuelta — late bacalao 🍺":    "Casa Revuelta, Calle de Latoneros, Madrid, Spain",
 "🛍 Antigua Casa Crespo (espadrilles)":"Antigua Casa Crespo, Calle del Divino Pastor, Madrid, Spain",
 "🛍 Gritos de Madrid (tiles)":        "Plaza Mayor, Madrid, Spain",
 "📚 Cuesta de Moyano book stalls":    "Cuesta de Moyano, Madrid, Spain",
 "⭐🛍 Casa Hernanz → Gran Vía shops":  "Casa Hernanz, Calle de Toledo, Madrid, Spain",
 "⭐ San Ginés churros":               "Chocolateria San Gines, Madrid, Spain",
 "🕌 Muralla Árabe":                   "Muralla arabe de Madrid, Cuesta de la Vega, Madrid, Spain",
 "⭐ Templo de Debod (sunset) 🌄":      "Templo de Debod, Madrid, Spain",
 "Royal Palace (from below) + Campo del Moro":"Campo del Moro, Madrid, Spain",
 "🌄 Mirador de la Pradera de San Marcos (optional)":"Pradera de San Marcos, Segovia, Spain",
 "O Valentim (dinner, Matosinhos)":    "O Valentim, Matosinhos, Portugal",
 "Café Santiago (dinner)":             "Cafe Santiago, Rua de Passos Manuel, Porto, Portugal",
 # Named-but-generic stops that ARE real places, and whose pins drive routing.
 # An explicit query here overrides the SKIP list below.
 "OPO Airport — Arrive Porto":         "Aeroporto Francisco Sa Carneiro, Porto, Portugal",
 "🌘 Solar eclipse — SVQ arrival":      "Aeropuerto de Sevilla, Spain",
 "🚌 Tour pickup — Prado de San Sebastián":"Prado de San Sebastian, Sevilla, Spain",
 "🕌 Córdoba old town — guided walk":   "Juderia, Cordoba, Spain",
 "Lunch in Córdoba (free time)":       "Calle Cardenal Herrero, Cordoba, Spain",
 "🚌 Tour meet-up — Ventas / Calle Julio Camba":"Calle de Julio Camba, Madrid, Spain",
 "🌄 Toledo panoramic tour (from the coach)":"Mirador del Valle, Toledo, Spain",
 "⭐ Toledo walking tour + Cathedral":  "Catedral de Toledo, Spain",
 "🕌 Cristo de la Luz / Santa María la Blanca (free time)":"Mezquita del Cristo de la Luz, Toledo, Spain",
 "Lunch in Segovia":                   "Plaza Mayor, Segovia, Spain",
 "Segovia Aqueduct + walking tour":    "Acueducto de Segovia, Spain",
 "Bairro Alto (evening)":              "Bairro Alto, Lisboa, Portugal",
}

COUNTRY = {"Porto":"Portugal","Lisbon":"Portugal","Sintra":"Portugal",
           "Seville":"Spain","Cordoba":"Spain","Granada":"Spain","Madrid":"Spain",
           "Toledo":"Spain","Segovia":"Spain","Setenil":"Spain","Ronda":"Spain"}

def haversine(a, b):
    la1,lo1,la2,lo2 = map(radians,[a[0],a[1],b[0],b[1]])
    h = sin((la2-la1)/2)**2 + cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
    return 2*6371000*asin(sqrt(h))          # metres

def clean(name):
    """Strip emoji, leading markers and trailing parentheticals for a query."""
    n = re.sub(r'[\U0001F000-\U0001FAFF←-⯿️‍]', '', name)
    n = re.sub(r'\s*\([^)]*\)\s*$', '', n)
    n = n.replace('→',' ').replace('+',' ').replace('—',' ')
    return ' '.join(n.split())

def geocode(q):
    url = NOMINATIM + "?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 3, "addressdetails": 0})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    out = "spain_geocode_report.json"
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out")+1]

    src = open("spain_interactive_map.py", encoding="utf-8").read()
    ns = {}
    i = src.index("S = ["); j = src.index("\n]", i)+2
    exec(src[i:j], ns)                        # raw S, before hotel bookends
    stops = ns["S"]

    seen, rows = set(), []
    for st in stops:
        name, lat, lon, day, typ, city = st[0], st[1], st[2], st[3], st[4], st[5]
        # An explicit query wins over every skip rule: those entries exist
        # precisely because the display name is generic but the pin is real
        # and drives routing (airports, the coach pickup points, the Toledo
        # and Segovia monuments the tour cards are named after).
        if name in seen: continue
        if name not in QUERY and (SKIP.search(name) or city == "Transit"
                                  or typ in ("flight","lounge")):
            continue
        seen.add(name)
        q = QUERY.get(name) or f"{clean(name)}, {city}, {COUNTRY.get(city,'')}"
        row = {"name": name, "day": day, "city": city, "query": q,
               "current": [lat, lon], "candidates": [], "error": None}
        try:
            for hit in geocode(q):
                glat, glon = float(hit["lat"]), float(hit["lon"])
                row["candidates"].append({
                    "lat": round(glat,6), "lon": round(glon,6),
                    "metres_off": round(haversine((lat,lon),(glat,glon))),
                    "display": hit.get("display_name","")[:120],
                    "class": hit.get("class"), "type": hit.get("type")})
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        rows.append(row)
        print(f'{row["name"][:44]:<44} '
              + (row["error"] or
                 (f'{row["candidates"][0]["metres_off"]:>6} m off  {row["candidates"][0]["display"][:60]}'
                  if row["candidates"] else 'NO MATCH')), flush=True)
        time.sleep(1.1)                       # Nominatim: max 1 request/second

    json.dump(rows, open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    far = [r for r in rows if r["candidates"] and r["candidates"][0]["metres_off"] > 150]
    print(f'\n{len(rows)} stops checked, {len(far)} more than 150 m from the geocoder, '
          f'{len([r for r in rows if not r["candidates"]])} with no match')

if __name__ == "__main__":
    main()
