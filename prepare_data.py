import json, sys
from pathlib import Path
import requests
from shapely import make_valid, wkt
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

OUT = Path("data"); OUT.mkdir(exist_ok=True)
W, S, E, N = -121.05, 37.32, -120.70, 37.60          # lon/lat window
DWR = "https://gis.water.ca.gov/arcgis/rest/services"
DISTRICTS = f"{DWR}/Boundaries/i03_WaterDistricts/MapServer/0"
SDA = "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest"

def save(name, feats):
    (OUT / name).write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                       ensure_ascii=False), encoding="utf-8")
    print(f"OK  {name}: {len(feats)} features")

def step(title, fn):
    print(f"\n--- {title}")
    try: fn()
    except Exception as e: print(f"FAILED: {type(e).__name__}: {str(e)[:400]}")

def arcgis(layer, bounds):
    p = {"geometry": ",".join(map(str, bounds)), "geometryType": "esriGeometryEnvelope",
         "inSR": 4326, "spatialRel": "esriSpatialRelIntersects", "where": "1=1",
         "returnIdsOnly": "true", "f": "json"}
    r = requests.get(layer + "/query", params=p, timeout=120); r.raise_for_status()
    ids = r.json().get("objectIds") or []
    print("ids found:", len(ids))
    feats = []
    for i in range(0, len(ids), 100):
        r = requests.get(layer + "/query", params={
            "objectIds": ",".join(map(str, ids[i:i+100])), "outFields": "*",
            "outSR": 4326, "f": "geojson"}, timeout=120)
        r.raise_for_status(); feats += r.json().get("features", [])
    return feats

study = {"geom": box(W, S, E, N)}      # fallback if the district step fails

def district():
    feats = arcgis(DISTRICTS, (W, S, E, N))
    if feats: print("sample properties:", list(feats[0]["properties"].keys())[:12])
    turlock = [f for f in feats if "turlock" in json.dumps(f["properties"]).lower()]
    if not turlock: raise RuntimeError("No feature mentions Turlock")
    study["geom"] = unary_union([make_valid(shape(f["geometry"])) for f in turlock]) \
                    .intersection(box(W, S, E, N))
    save("district_boundary.geojson", turlock)

def soils():
    feats, seen = [], set()
    nx = ny = 3
    for i in range(nx):
        for j in range(ny):
            tile = box(W + (E-W)*i/nx, S + (N-S)*j/ny, W + (E-W)*(i+1)/nx, S + (N-S)*(j+1)/ny)
            sql = f"""SELECT p.mupolygonkey, p.mukey, m.musym, m.muname,
                      p.mupolygongeo.STAsText() AS g
                      FROM mupolygon p JOIN mapunit m ON m.mukey = p.mukey
                      WHERE p.mupolygonkey IN (SELECT * FROM
                      SDA_Get_Mupolygonkey_from_intersection_with_WktWgs84('{tile.wkt}'))"""
            r = requests.post(SDA, json={"query": sql, "format": "JSON+COLUMNNAME"}, timeout=180)
            r.raise_for_status()
            rows = r.json().get("Table", [])
            print(f"tile {i},{j}: {max(len(rows)-1, 0)} rows")
            if len(rows) < 2: continue
            cols = rows[0]
            for row in rows[1:]:
                d = dict(zip(cols, row))
                if d["mupolygonkey"] in seen: continue
                seen.add(d["mupolygonkey"])
                g = make_valid(wkt.loads(d.pop("g"))).simplify(0.00005)
                if g.intersects(study["geom"]):
                    feats.append({"type": "Feature", "geometry": mapping(g), "properties": d})
    save("soil_units.geojson", feats)

def wells():  # optional context layer only
    WELLS = f"{DWR}/Geoscientific/i08_GroundwaterStations_EnterpriseWaterManagement/MapServer/0"
    feats = [f for f in arcgis(WELLS, (W, S, E, N))
             if f.get("geometry") and study["geom"].covers(shape(f["geometry"]))]
    save("wells.geojson", feats)

def countries():
    url = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
           "geojson/ne_110m_admin_0_countries.geojson")
    r = requests.get(url, timeout=120); r.raise_for_status()
    save("countries.geojson", [{"type": "Feature", "geometry": f["geometry"],
         "properties": {"name": f["properties"]["NAME"]}} for f in r.json()["features"]])

step("1. District boundary", district)
step("2. SSURGO soil units", soils)
step("3. Wells (optional)", wells)
step("4. Countries", countries)