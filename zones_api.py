"""
zones_api.py — Blueprint for zones endpoints and the /carte map page.

Registered in app.py as: app.register_blueprint(zones_bp)

Uses the project's own db.get_connection() / db.close_connection() so that
credentials always come from the same .env as the rest of the app.
"""

import json
import logging

from flask import Blueprint, jsonify, render_template, request

import db

logger = logging.getLogger(__name__)
zones_bp = Blueprint("zones_api", __name__)


# ---------------------------------------------------------------------------
# GET /api/zones
# Returns all zones as a GeoJSON FeatureCollection.
# Geometry is simplified (tolerance 0.0001 ≈ 10 m) to keep the payload
# light for ~2 000 polygons. Precision rounded to 5 decimal places.
# ---------------------------------------------------------------------------
@zones_bp.get("/api/zones")
def list_zones():
    """Return all zones as a simplified GeoJSON FeatureCollection.

    Why simplify? Sending full SSURGO polygon detail for 2 000 features
    would produce a multi-MB payload. At zoom 11-14, 0.0001 degree tolerance
    (about 10 m) is invisible to the user.
    """
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT jsonb_build_object(
                  'type', 'FeatureCollection',
                  'features', COALESCE(jsonb_agg(
                    jsonb_build_object(
                      'type',       'Feature',
                      'id',         id,
                      'geometry',   ST_AsGeoJSON(
                                      ST_SimplifyPreserveTopology(geom, 0.0001),
                                      5)::jsonb,
                      'properties', jsonb_build_object(
                        'id',          id,
                        'name',        name,
                        'zone_type',   zone_type,
                        'musym',       musym,
                        'mukey',       mukey,
                        'description', description,
                        'source',      source,
                        'created_by',  created_by
                      )
                    )
                  ), '[]'::jsonb)
                )
                FROM zones
            """)
            result = cur.fetchone()[0]
        return jsonify(result), 200

    except RuntimeError as exc:
        logger.error("list_zones DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("list_zones unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# GET /api/zones/<id>
# Returns one zone at full geometry precision (6 decimal places).
# ---------------------------------------------------------------------------
@zones_bp.get("/api/zones/<int:zid>")
def get_zone(zid):
    """Return one zone as a GeoJSON Feature at full precision, or 404."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT jsonb_build_object(
                  'type',       'Feature',
                  'id',         id,
                  'geometry',   ST_AsGeoJSON(geom, 6)::jsonb,
                  'properties', jsonb_build_object(
                    'id',          id,
                    'name',        name,
                    'zone_type',   zone_type,
                    'musym',       musym,
                    'mukey',       mukey,
                    'description', description,
                    'source',      source,
                    'created_by',  created_by
                  )
                )
                FROM zones WHERE id = %s
            """, (zid,))
            row = cur.fetchone()

        if not row or row[0] is None:
            return jsonify({"error": "Zone introuvable."}), 404
        return jsonify(row[0]), 200

    except RuntimeError as exc:
        logger.error("get_zone DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("get_zone unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# GET /carte
# Full-page interactive map (Phase 2).
# Passes config values so carte.html never hard-codes bbox or centre.
# ---------------------------------------------------------------------------
@zones_bp.get("/carte")
def carte():
    """Serve the full interactive map page."""
    import config
    return render_template(
        "carte.html",
        bbox_sw_lat=config.BBOX["lat_min"],
        bbox_sw_lon=config.BBOX["lon_min"],
        bbox_ne_lat=config.BBOX["lat_max"],
        bbox_ne_lon=config.BBOX["lon_max"],
        map_center_lat=config.MAP_CENTER_LAT,
        map_center_lon=config.MAP_CENTER_LON,
        map_zoom=config.MAP_ZOOM,
    )


@zones_bp.post("/api/zones")
def create_zone():
    """Create a new zone from a drawn GeoJSON polygon.

    Body: {name, zone_type, description, geojson}
    geojson is a GeoJSON geometry object (Polygon or MultiPolygon).
    Returns 201 + GeoJSON Feature on success.
    """
    import json as _json
    conn = None
    try:
        data    = request.get_json(silent=True) or {}
        errors  = {}

        name = str(data.get("name", "")).strip()
        if not name or len(name) < 2 or len(name) > 100:
            errors["name"] = "Le nom doit contenir entre 2 et 100 caractères."

        geojson = data.get("geojson")
        if not geojson or not isinstance(geojson, dict):
            errors["geojson"] = "Geometry required. Draw a polygon on the map first."

        if errors:
            return jsonify({"error": "Validation error.", "errors": errors}), 400

        zone_type   = str(data.get("zone_type", "unité de sol")).strip() or "unité de sol"
        description = str(data.get("description", "")).strip() or None
        geojson_str = _json.dumps(geojson)

        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO zones (name, zone_type, description, geom)
                VALUES (%s, %s, %s,
                        ST_Multi(ST_MakeValid(
                            ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                        )))
                RETURNING id, name, zone_type, description,
                          musym, mukey, source, created_by,
                          ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 0.0001), 5)::text
            """, (name, zone_type, description, geojson_str))
            row = cur.fetchone()
            conn.commit()

        feature = {
            "type": "Feature",
            "id":   row[0],
            "geometry": _json.loads(row[8]),
            "properties": {
                "id": row[0], "name": row[1], "zone_type": row[2],
                "description": row[3], "musym": row[4], "mukey": row[5],
                "source": row[6], "created_by": row[7]
            }
        }
        return jsonify(feature), 201

    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("create_zone error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)
