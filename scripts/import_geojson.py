"""
import_geojson.py -- Load real SSURGO soil units and observation sites into the DB.

Run once after a fresh database start (or after docker compose down -v + up -d):
    python scripts/import_geojson.py

What it does:
  1. Truncates observations, sites, zones (CASCADE) and resets sequences.
  2. Loads data/soil_units.geojson (~2000 USDA SSURGO polygons) into zones.
  3. Loads data/points.geojson (60 sites) into sites.

Geometry notes:
  - Zones: ST_Multi wraps the geometry as MultiPolygon (matches the column type).
            ST_MakeValid fixes any self-intersections from the source data.
  - Sites: GeoJSON coordinates are [longitude, latitude] -- PostGIS ST_GeomFromGeoJSON
           preserves this order (X=longitude, Y=latitude). Correct.

All data marked created_by = NULL (reference data, editable by admin only).
"""

import json
import sys
from pathlib import Path

# Allow running from any directory
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
from config import DB_SETTINGS


def load_geojson(path):
    """Read a GeoJSON file and return its features list."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)["features"]


def main():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
    except Exception as exc:
        print(f"ERROR: Could not connect: {exc}")
        sys.exit(1)

    cur = conn.cursor()

    # ------------------------------------------------------------------
    # Clear existing data (order matters: observations -> sites -> zones)
    # RESTART IDENTITY resets serial counters back to 1.
    # ------------------------------------------------------------------
    print("Clearing existing data...")
    cur.execute("TRUNCATE observations, sites, zones RESTART IDENTITY CASCADE")

    # ------------------------------------------------------------------
    # Import soil units (zones)
    # ------------------------------------------------------------------
    zones_path = ROOT / "data" / "soil_units.geojson"
    if not zones_path.exists():
        print(f"ERROR: {zones_path} not found. Run prepare_data.py first.")
        sys.exit(1)

    print(f"Loading zones from {zones_path}...")
    features = load_geojson(zones_path)
    zone_count = 0
    skipped = 0

    for f in features:
        p = f["properties"]
        name = p.get("muname") or "non renseigne"
        desc = "Symbole : " + str(p.get("musym") or "")
        mukey  = p.get("mukey")
        musym  = p.get("musym")
        source = p.get("data_source")
        geom_json = json.dumps(f["geometry"])

        try:
            cur.execute("""
                INSERT INTO zones
                    (name, zone_type, description, mukey, musym, source, geom)
                VALUES (%s, 'unite de sol', %s, %s, %s, %s,
                        ST_Multi(ST_MakeValid(
                            ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                        )))
            """, (name, desc, mukey, musym, source, geom_json))
            zone_count += 1
        except Exception as exc:
            conn.rollback()   # roll back this feature only
            skipped += 1
            if skipped <= 5:   # only print first 5 errors to avoid spam
                print(f"  Skipped zone '{name}': {exc}")

    print(f"  Zones inserted: {zone_count}  |  skipped: {skipped}")

    # ------------------------------------------------------------------
    # Import observation sites (points)
    # ------------------------------------------------------------------
    sites_path = ROOT / "data" / "points.geojson"
    if not sites_path.exists():
        print(f"ERROR: {sites_path} not found. Run make_sites.py first.")
        sys.exit(1)

    print(f"Loading sites from {sites_path}...")
    features = load_geojson(sites_path)
    site_count = 0

    for f in features:
        p = f["properties"]
        name      = p.get("name") or "Site sans nom"
        culture   = p.get("culture") or "non renseigne"
        soil_type = p.get("soil_type") or "non renseigne"
        mukey     = p.get("mukey")
        source    = p.get("data_source")
        geom_json = json.dumps(f["geometry"])  # GeoJSON [lon, lat] -- correct order for PostGIS

        cur.execute("""
            INSERT INTO sites
                (name, culture, soil_type, mukey, source, geom, status)
            VALUES (%s, %s, %s, %s, %s,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                    'approved')
        """, (name, culture, soil_type, mukey, source, geom_json))
        site_count += 1

    print(f"  Sites inserted: {site_count}")

    # ------------------------------------------------------------------
    # Commit and report final counts
    # ------------------------------------------------------------------
    conn.commit()

    cur.execute("SELECT count(*) FROM zones")
    final_zones = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM sites")
    final_sites = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("\n--- Import complete ---")
    print(f"  zones : {final_zones}")
    print(f"  sites : {final_sites}")
    print("\nNext step: python scripts/seed_observations.py")


if __name__ == "__main__":
    main()
