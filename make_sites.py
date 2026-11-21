import json, random
from pathlib import Path
from shapely.geometry import shape, mapping

N_SITES = 60            # change this number for more or fewer sites
random.seed(42)

soils = json.loads(Path("data/soil_units.geojson").read_text(encoding="utf-8"))["features"]

SKIP = ("urban", "water", "pit", "dam", "gravel", "rock outcrop", "borrow")
CROPS = ["amandier", "noyer", "maïs", "luzerne", "pêcher", "tomate", "vigne",
         "blé", "coton", "pistachier", "oignon", "betterave"]   # SIMULATED

# Keep only agricultural polygons of a reasonable size
good = []
for f in soils:
    name = (f["properties"].get("muname") or "").lower()
    g = shape(f["geometry"])
    if not any(w in name for w in SKIP) and g.area > 1e-6:
        good.append((f, g))
print("agricultural polygons:", len(good))

# Try a large spacing first, then relax it until we reach N_SITES
sites, chosen = [], []
for min_dist in (0.015, 0.01, 0.007, 0.004):
    random.shuffle(good)
    for f, g in good:
        if len(sites) >= N_SITES:
            break
        p = g.representative_point()          # always inside the polygon
        if all(p.distance(q) > min_dist for q in chosen):
            chosen.append(p)
            n = len(sites) + 1
            sites.append({"type": "Feature", "geometry": mapping(p), "properties": {
                "name": f"Site {n:03d}",
                "soil_type": f["properties"]["muname"],   # real: USDA SSURGO
                "culture": random.choice(CROPS),          # simulated
                "mukey": f["properties"]["mukey"],
                "data_source": "soil: USDA SSURGO; culture: simulated"}})
    if len(sites) >= N_SITES:
        break

Path("data/points.geojson").write_text(json.dumps(
    {"type": "FeatureCollection", "features": sites}, ensure_ascii=False), encoding="utf-8")
print("sites created:", len(sites))
print("different soil types:", len({s["properties"]["soil_type"] for s in sites}))
