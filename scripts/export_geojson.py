"""
export_geojson.py — Export all approved sites from the database to data/sites.geojson.

Purpose:
    The PDF assignment allows storing data as a vector file (GeoJSON) in addition
    to the spatial database. This script produces that file from the live DB.
    It is a one-time (or on-demand) export; the Flask app always reads from the DB.

Usage (from soil-platform/ with the venv activated):
    python scripts/export_geojson.py

Output:
    data/sites.geojson   — UTF-8 GeoJSON FeatureCollection

Dependencies:
    Only the standard library (json, os, pathlib) + psycopg2.
    No pandas, no GeoPandas, no extra installs.
"""

import json
import os
import sys
from pathlib import Path

# Allow importing db.py and config.py from the project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db  # noqa: E402  (import after sys.path change)


def export_sites_geojson(output_path: Path) -> None:
    """Read all approved sites from the DB and write them as GeoJSON.

    Args:
        output_path: Path object for the output file.
                     Parent directories must already exist.

    Why use ST_AsGeoJSON in SQL rather than building the geometry manually?
    PostGIS's ST_AsGeoJSON is the authoritative way to serialise a PostGIS
    geometry to GeoJSON format; doing it manually would risk lon/lat order errors.
    """
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    s.id,
                    s.name,
                    s.culture,
                    s.soil_type,
                    ST_AsGeoJSON(s.geom)::text   AS geom_json,
                    COUNT(o.id)                  AS observation_count,
                    MAX(o.observation_date)      AS last_observation_date
                FROM sites s
                LEFT JOIN observations o ON o.site_id = s.id
                WHERE s.status = 'approved'
                GROUP BY s.id, s.name, s.culture, s.soil_type, s.geom
                ORDER BY s.id
            """)
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
    finally:
        db.close_connection(conn)

    features = []
    for row in rows:
        record = dict(zip(col_names, row))

        # ST_AsGeoJSON returns a JSON string; parse it into a dict.
        geometry = json.loads(record["geom_json"])

        # Convert non-JSON-serialisable types explicitly.
        props = {
            "id":                   record["id"],
            "name":                 record["name"],
            "culture":              record["culture"],
            "soil_type":            record["soil_type"],
            "observation_count":    record["observation_count"],
            # date → ISO string; None stays None
            "last_observation_date": (
                record["last_observation_date"].isoformat()
                if record["last_observation_date"] else None
            ),
        }

        features.append({
            "type":       "Feature",
            "geometry":   geometry,
            "properties": props,
        })

    geojson = {
        "type":     "FeatureCollection",
        "features": features,
    }

    # Write as UTF-8 — encoding= is required on Windows where the default
    # code page (cp1252) would corrupt accented characters like é, è, â.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(features)} site(s) to {output_path}")


if __name__ == "__main__":
    out = ROOT / "data" / "sites.geojson"
    export_sites_geojson(out)
