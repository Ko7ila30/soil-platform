# app.py — Flask application: routes and JSON serialisation.
#
# Design decisions:
#   - One psycopg2 connection is opened per request and closed in a
#     finally block so it always closes, even when an exception occurs.
#   - Dates (datetime.date) and Decimals are converted explicitly to
#     strings/floats before jsonify — Flask's default encoder does not
#     handle them reliably across versions.
#   - Stack traces, SQL text, and credentials are never sent to the browser.
#     Full errors are logged to stderr only.
#   - All error responses are JSON with a consistent shape:
#     {"error": "...", "errors": {...}}  (errors dict is optional)

import json
import logging
import os
from datetime import date
from decimal import Decimal

from flask import Flask, jsonify, render_template, request

import config
import db
import validators

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
from zones_api import zones_bp
app.register_blueprint(zones_bp)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _serial(obj):
    """Convert types that json.dumps cannot handle natively.

    - datetime.date  → "YYYY-MM-DD" string
    - decimal.Decimal → float

    Used in _row_to_dict and anywhere we build a plain dict before jsonify.
    """
    if isinstance(obj, date):
        return obj.isoformat()          # "YYYY-MM-DD"
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


def _safe_json(value):
    """Apply _serial to a single value (date or Decimal), pass others through."""
    if isinstance(value, (date, Decimal)):
        return _serial(value)
    return value


def _row_to_dict(cursor, row):
    """Zip cursor column names with a row tuple into a plain dict.

    All date and Decimal values are converted to JSON-safe types.
    """
    cols = [desc[0] for desc in cursor.description]
    return {col: _safe_json(val) for col, val in zip(cols, row)}


# ---------------------------------------------------------------------------
# Config object passed to the template
# ---------------------------------------------------------------------------

def _build_config_json():
    """Build the JSON object injected into index.html as window.CONFIG.

    The frontend reads this once at page load; nothing is hard-coded in JS.
    """
    return json.dumps({
        "perimeterName":  config.PERIMETER_NAME,
        "mapCenter":      [config.MAP_CENTER_LAT, config.MAP_CENTER_LON],
        "mapZoom":        config.MAP_ZOOM,
        "bbox":           config.BBOX,
        "cultureColours": config.CULTURE_COLOURS,
        "defaultColour":  config.DEFAULT_COLOUR,
        "cultures":       config.CULTURES,
        "soilTypes":      config.SOIL_TYPES,
        "soilTextures":   config.SOIL_TEXTURES,
        "waterStatuses":  config.WATER_STATUSES,
        "salinityLevels": config.SALINITY_LEVELS,
        "erosionTypes":   config.EROSION_TYPES,
        "irrigationModes":config.IRRIGATION_MODES,
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Ressource introuvable."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Méthode non autorisée."}), 405


@app.errorhandler(500)
def internal_error(e):
    logger.error("Unexpected server error: %s", e)
    return jsonify({"error": "Erreur interne du serveur."}), 500


# ---------------------------------------------------------------------------
# Routes — Phase 1
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Root route: redirect to the new home page."""
    from flask import redirect
    return redirect("/home")


@app.route("/legacy")
def legacy():
    """Original single-page Leaflet map (Phase 1–3 PDF project).

    Kept intact so the PDF assignment is still demonstrable.
    """
    return render_template("index.html", config_json=_build_config_json())


@app.route("/api/sites", methods=["GET"])
def get_sites():
    """Return all approved sites as a GeoJSON FeatureCollection.

    Each feature's properties include:
        id, name, culture, soil_type,
        observation_count (int),
        last_observation_date (YYYY-MM-DD string or null).

    ST_AsGeoJSON returns the geometry as a JSON string; we parse it
    so the final response is a proper nested object, not a string-within-JSON.
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

        features = []
        for row in rows:
            (sid, name, culture, soil_type,
             geom_json, obs_count, last_date) = row

            features.append({
                "type": "Feature",
                "geometry": json.loads(geom_json),   # parse the JSON string from PostGIS
                "properties": {
                    "id":                   sid,
                    "name":                 name,
                    "culture":              culture,
                    "soil_type":            soil_type,
                    "observation_count":    obs_count,
                    "last_observation_date": _safe_json(last_date),  # date → string or None
                },
            })

        return jsonify({"type": "FeatureCollection", "features": features}), 200

    except RuntimeError as exc:
        # DB unreachable — friendly 503
        logger.error("get_sites DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("get_sites unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/sites/<int:site_id>", methods=["GET"])
def get_site(site_id):
    """Return one site as a GeoJSON Feature, or 404 if not found."""
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
                WHERE s.id = %s AND s.status = 'approved'
                GROUP BY s.id, s.name, s.culture, s.soil_type, s.geom
            """, (site_id,))
            row = cur.fetchone()

        if row is None:
            return jsonify({"error": "Site introuvable."}), 404

        (sid, name, culture, soil_type,
         geom_json, obs_count, last_date) = row

        feature = {
            "type": "Feature",
            "geometry": json.loads(geom_json),
            "properties": {
                "id":                    sid,
                "name":                  name,
                "culture":               culture,
                "soil_type":             soil_type,
                "observation_count":     obs_count,
                "last_observation_date": _safe_json(last_date),
            },
        }
        return jsonify(feature), 200

    except RuntimeError as exc:
        logger.error("get_site DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("get_site unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# Routes — Phase 2 (observation form)
# ---------------------------------------------------------------------------

@app.route("/api/options", methods=["GET"])
def get_options():
    """Return all dropdown lists and the site list for the observation form.

    The frontend calls this once at page load to populate every <select>.
    Lists come from config.py — the single source of truth.
    The sites list is fetched from the DB (name + id only).
    """
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name FROM sites WHERE status = 'approved' ORDER BY name"
            )
            sites_list = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
    except RuntimeError as exc:
        logger.error("get_options DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("get_options unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)

    return jsonify({
        "sites":          sites_list,
        "cultures":       config.CULTURES,
        "soilTypes":      config.SOIL_TYPES,
        "soilTextures":   config.SOIL_TEXTURES,
        "waterStatuses":  config.WATER_STATUSES,
        "salinityLevels": config.SALINITY_LEVELS,
        "erosionTypes":   config.EROSION_TYPES,
        "irrigationModes":config.IRRIGATION_MODES,
    }), 200


@app.route("/api/sites/<int:site_id>/observations", methods=["GET"])
def get_observations(site_id):
    """Return all observations for a site, newest first.

    Returns 404 if the site does not exist.
    Dates are returned as YYYY-MM-DD strings; Decimals as floats.
    """
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            # Check the site exists first.
            cur.execute(
                "SELECT id FROM sites WHERE id = %s AND status = 'approved'",
                (site_id,)
            )
            if cur.fetchone() is None:
                return jsonify({"error": "Site introuvable."}), 404

            cur.execute("""
                SELECT
                    id, site_id, contributor_name, observation_date,
                    soil_texture, water_status, salinity, erosion,
                    culture, irrigation_mode,
                    ph, ec_dsm, organic_matter_pct, remark,
                    created_at
                FROM observations
                WHERE site_id = %s
                ORDER BY observation_date DESC, created_at DESC
            """, (site_id,))
            rows = cur.fetchall()
            observations = [_row_to_dict(cur, row) for row in rows]

        return jsonify(observations), 200

    except RuntimeError as exc:
        logger.error("get_observations DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("get_observations unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/sites/<int:site_id>/observations", methods=["POST"])
def create_observation(site_id):
    """Create a new observation for a site.

    Expects a JSON body with the observation fields.
    Validates server-side; returns 400 with per-field French errors on failure.
    Returns 201 with the new observation on success.
    """
    conn = None
    try:
        data = request.get_json(silent=True) or {}

        # Server-side validation (pure, no DB).
        cleaned, errors = validators.validate_observation(data)
        if errors:
            return jsonify({
                "error": "Veuillez vérifier les champs du formulaire.",
                "errors": errors,
            }), 400

        conn = db.get_connection()
        with conn.cursor() as cur:
            # Verify the site exists.
            cur.execute(
                "SELECT id FROM sites WHERE id = %s AND status = 'approved'",
                (site_id,)
            )
            if cur.fetchone() is None:
                return jsonify({"error": "Site introuvable."}), 404

            cur.execute("""
                INSERT INTO observations
                    (site_id, contributor_name, observation_date,
                     soil_texture, water_status, salinity, erosion,
                     culture, irrigation_mode,
                     ph, ec_dsm, organic_matter_pct, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, site_id, contributor_name, observation_date,
                          soil_texture, water_status, salinity, erosion,
                          culture, irrigation_mode,
                          ph, ec_dsm, organic_matter_pct, remark, created_at
            """, (
                site_id,
                cleaned["contributor_name"],
                cleaned["observation_date"],
                cleaned["soil_texture"],
                cleaned["water_status"],
                cleaned["salinity"],
                cleaned["erosion"],
                cleaned["culture"],
                cleaned["irrigation_mode"],
                cleaned.get("ph"),
                cleaned.get("ec_dsm"),
                cleaned.get("organic_matter_pct"),
                cleaned.get("remark"),
            ))
            new_row = cur.fetchone()
            result = _row_to_dict(cur, new_row)
            conn.commit()

        return jsonify(result), 201

    except RuntimeError as exc:
        if conn:
            conn.rollback()
        logger.error("create_observation DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.error("create_observation unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# Routes — Phase 3 (add a new site)
# ---------------------------------------------------------------------------

@app.route("/api/sites", methods=["POST"])
def create_site():
    """Create a new observation site from a clicked map point.

    Expects JSON body: {name, culture, soil_type, longitude, latitude}.
    Validates coordinates against the configured bounding box.
    Returns the new site as a GeoJSON Feature on success (201).

    Geometry note:
        ST_MakePoint(longitude, latitude) — longitude (X) comes FIRST.
        PostGIS uses (X=longitude, Y=latitude); Leaflet gives (lat, lng).
        Always pass longitude as the first argument to ST_MakePoint.
    """
    conn = None
    try:
        data = request.get_json(silent=True) or {}

        cleaned, errors = validators.validate_new_site(data, config.BBOX)
        if errors:
            return jsonify({
                "error": "Veuillez vérifier les champs du formulaire.",
                "errors": errors,
            }), 400

        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sites (name, culture, soil_type, geom, status)
                VALUES (
                    %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    'approved'
                )
                RETURNING
                    id, name, culture, soil_type,
                    ST_AsGeoJSON(geom)::text AS geom_json,
                    0 AS observation_count,
                    NULL::date AS last_observation_date
            """, (
                cleaned["name"],
                cleaned["culture"],
                cleaned["soil_type"],
                cleaned["longitude"],   # X = longitude (PostGIS convention)
                cleaned["latitude"],    # Y = latitude
            ))
            row = cur.fetchone()
            conn.commit()

        (sid, name, culture, soil_type,
         geom_json, obs_count, last_date) = row

        feature = {
            "type": "Feature",
            "geometry": json.loads(geom_json),
            "properties": {
                "id":                    sid,
                "name":                  name,
                "culture":               culture,
                "soil_type":             soil_type,
                "observation_count":     obs_count,
                "last_observation_date": None,
            },
        }
        return jsonify(feature), 201

    except RuntimeError as exc:
        if conn:
            conn.rollback()
        logger.error("create_site DB error: %s", exc)
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.error("create_site unexpected error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# Routes — Edit, delete, geometry updates (Phase 4)
# ---------------------------------------------------------------------------

@app.route("/api/sites/<int:site_id>", methods=["PUT"])
def update_site(site_id):
    """Update a site's attributes (name, culture, soil_type).

    Validates the same lists as the create endpoint.
    Returns the updated site properties as JSON (200) or 400/404.
    """
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        errors = {}

        name = str(data.get("name", "")).strip()
        if not name or len(name) < 3 or len(name) > 100:
            errors["name"] = "Le nom doit contenir entre 3 et 100 caractères."

        culture = str(data.get("culture", "")).strip()
        if culture not in config.CULTURES:
            errors["culture"] = "Valeur de culture non valide."

        soil_type = str(data.get("soil_type", "")).strip()
        if soil_type not in config.SOIL_TYPES:
            errors["soil_type"] = "Type de sol non valide."

        if errors:
            return jsonify({"error": "Validation error.", "errors": errors}), 400

        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM sites WHERE id = %s AND status = 'approved'",
                (site_id,)
            )
            if cur.fetchone() is None:
                return jsonify({"error": "Site introuvable."}), 404

            cur.execute(
                "UPDATE sites SET name=%s, culture=%s, soil_type=%s WHERE id=%s "
                "RETURNING id, name, culture, soil_type, mukey, source",
                (name, culture, soil_type, site_id)
            )
            row = cur.fetchone()
            conn.commit()

        return jsonify({
            "id": row[0], "name": row[1], "culture": row[2],
            "soil_type": row[3], "mukey": row[4], "source": row[5]
        }), 200

    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("update_site error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/sites/<int:site_id>", methods=["DELETE"])
def delete_site(site_id):
    """Delete a site and all its observations (CASCADE in schema)."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM sites WHERE id = %s", (site_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Site introuvable."}), 404
            cur.execute("DELETE FROM sites WHERE id = %s", (site_id,))
            conn.commit()
        return jsonify({"ok": True}), 200
    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("delete_site error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/sites/<int:site_id>/geometry", methods=["PUT"])
def update_site_geometry(site_id):
    """Move a site's point geometry to new coordinates.

    Body: {longitude, latitude} — longitude first (PostGIS convention).
    Validates that the point is inside the configured bounding box.
    """
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        cleaned, errors = validators.validate_new_site(data, config.BBOX)
        if errors:
            return jsonify({"error": "Invalid coordinates.", "errors": errors}), 400

        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM sites WHERE id = %s", (site_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Site introuvable."}), 404
            # ST_MakePoint(longitude, latitude) — X=lon, Y=lat
            cur.execute(
                "UPDATE sites SET geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326) WHERE id = %s",
                (cleaned["longitude"], cleaned["latitude"], site_id)
            )
            conn.commit()
        return jsonify({"ok": True}), 200

    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("update_site_geometry error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/zones/<int:zone_id>", methods=["PUT"])
def update_zone(zone_id):
    """Update a zone's attributes (name, zone_type, description)."""
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        errors = {}

        name = str(data.get("name", "")).strip()
        if not name or len(name) < 2 or len(name) > 100:
            errors["name"] = "Le nom doit contenir entre 2 et 100 caractères."

        zone_type   = str(data.get("zone_type", "unité de sol")).strip() or "unité de sol"
        description = str(data.get("description", "")).strip() or None

        if errors:
            return jsonify({"error": "Validation error.", "errors": errors}), 400

        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM zones WHERE id = %s", (zone_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Zone introuvable."}), 404
            cur.execute(
                "UPDATE zones SET name=%s, zone_type=%s, description=%s WHERE id=%s "
                "RETURNING id, name, zone_type, description, musym, mukey, source",
                (name, zone_type, description, zone_id)
            )
            row = cur.fetchone()
            conn.commit()

        return jsonify({
            "id": row[0], "name": row[1], "zone_type": row[2],
            "description": row[3], "musym": row[4], "mukey": row[5], "source": row[6]
        }), 200

    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("update_zone error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/zones/<int:zone_id>", methods=["DELETE"])
def delete_zone(zone_id):
    """Delete a zone."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM zones WHERE id = %s", (zone_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Zone introuvable."}), 404
            cur.execute("DELETE FROM zones WHERE id = %s", (zone_id,))
            conn.commit()
        return jsonify({"ok": True}), 200
    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("delete_zone error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/zones/<int:zone_id>/geometry", methods=["PUT"])
def update_zone_geometry(zone_id):
    """Replace a zone's polygon geometry.

    Body: {geojson: <GeoJSON geometry object>}
    Wraps in ST_Multi and validates with ST_MakeValid.
    """
    conn = None
    try:
        data = request.get_json(silent=True) or {}
        geojson = data.get("geojson")
        if not geojson or not isinstance(geojson, dict):
            return jsonify({"error": "Invalid geometry.", "errors": {"geojson": "GeoJSON geometry required."}}), 400

        import json as _json
        geojson_str = _json.dumps(geojson)

        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM zones WHERE id = %s", (zone_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Zone introuvable."}), 404

            cur.execute(
                "UPDATE zones SET geom = ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))) "
                "WHERE id = %s",
                (geojson_str, zone_id)
            )
            conn.commit()
        return jsonify({"ok": True}), 200

    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("update_zone_geometry error: %s", exc)
        return jsonify({"error": "Erreur interne du serveur."}), 500
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# Tables API — paginated lists for the Tables page
# ---------------------------------------------------------------------------

@app.route("/api/table/sites", methods=["GET"])
def table_sites():
    """Return sites as a JSON array for the Tables page.

    Query params: page (1-based, default 1), per_page (default 50), q (name search).
    """
    conn = None
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
        q        = request.args.get("q", "").strip()
        offset   = (page - 1) * per_page

        conn = db.get_connection()
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    "SELECT count(*) FROM sites WHERE name ILIKE %s",
                    (f"%{q}%",)
                )
            else:
                cur.execute("SELECT count(*) FROM sites")
            total = cur.fetchone()[0]

            if q:
                cur.execute("""
                    SELECT s.id, s.name, s.culture, s.soil_type,
                           s.mukey, s.source, s.status,
                           COUNT(o.id) AS obs_count,
                           ST_Y(s.geom) AS lat, ST_X(s.geom) AS lon
                    FROM sites s
                    LEFT JOIN observations o ON o.site_id = s.id
                    WHERE s.name ILIKE %s
                    GROUP BY s.id ORDER BY s.id
                    LIMIT %s OFFSET %s
                """, (f"%{q}%", per_page, offset))
            else:
                cur.execute("""
                    SELECT s.id, s.name, s.culture, s.soil_type,
                           s.mukey, s.source, s.status,
                           COUNT(o.id) AS obs_count,
                           ST_Y(s.geom) AS lat, ST_X(s.geom) AS lon
                    FROM sites s
                    LEFT JOIN observations o ON o.site_id = s.id
                    GROUP BY s.id ORDER BY s.id
                    LIMIT %s OFFSET %s
                """, (per_page, offset))

            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, [_safe_json(v) for v in row]))
                    for row in cur.fetchall()]

        return jsonify({"total": total, "page": page, "per_page": per_page, "rows": rows}), 200

    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("table_sites error: %s", exc)
        return jsonify({"error": "Erreur interne."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/table/zones", methods=["GET"])
def table_zones():
    """Return zones (attributes only, no geometry) for the Tables page.

    Paginated: page, per_page, q.
    """
    conn = None
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
        q        = request.args.get("q", "").strip()
        offset   = (page - 1) * per_page

        conn = db.get_connection()
        with conn.cursor() as cur:
            where = "WHERE name ILIKE %s" if q else ""
            params_count = (f"%{q}%",) if q else ()
            cur.execute(f"SELECT count(*) FROM zones {where}", params_count)
            total = cur.fetchone()[0]

            sql = f"""
                SELECT id, name, zone_type, musym, mukey,
                       description, source, created_at
                FROM zones {where}
                ORDER BY id LIMIT %s OFFSET %s
            """
            params = (f"%{q}%", per_page, offset) if q else (per_page, offset)
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, [_safe_json(v) for v in row]))
                    for row in cur.fetchall()]

        return jsonify({"total": total, "page": page, "per_page": per_page, "rows": rows}), 200

    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("table_zones error: %s", exc)
        return jsonify({"error": "Erreur interne."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/table/observations", methods=["GET"])
def table_observations():
    """Return observations for the Tables page. Paginated."""
    conn = None
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
        q        = request.args.get("q", "").strip()
        offset   = (page - 1) * per_page

        conn = db.get_connection()
        with conn.cursor() as cur:
            if q:
                cur.execute(
                    "SELECT count(*) FROM observations o JOIN sites s ON s.id=o.site_id "
                    "WHERE s.name ILIKE %s OR o.contributor_name ILIKE %s",
                    (f"%{q}%", f"%{q}%")
                )
            else:
                cur.execute("SELECT count(*) FROM observations")
            total = cur.fetchone()[0]

            if q:
                cur.execute("""
                    SELECT o.id, s.name AS site_name, o.contributor_name,
                           o.observation_date, o.soil_texture, o.water_status,
                           o.salinity, o.erosion, o.culture, o.irrigation_mode,
                           o.ph, o.ec_dsm, o.organic_matter_pct, o.remark
                    FROM observations o
                    JOIN sites s ON s.id = o.site_id
                    WHERE s.name ILIKE %s OR o.contributor_name ILIKE %s
                    ORDER BY o.observation_date DESC, o.id DESC
                    LIMIT %s OFFSET %s
                """, (f"%{q}%", f"%{q}%", per_page, offset))
            else:
                cur.execute("""
                    SELECT o.id, s.name AS site_name, o.contributor_name,
                           o.observation_date, o.soil_texture, o.water_status,
                           o.salinity, o.erosion, o.culture, o.irrigation_mode,
                           o.ph, o.ec_dsm, o.organic_matter_pct, o.remark
                    FROM observations o
                    JOIN sites s ON s.id = o.site_id
                    ORDER BY o.observation_date DESC, o.id DESC
                    LIMIT %s OFFSET %s
                """, (per_page, offset))

            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, [_safe_json(v) for v in row]))
                    for row in cur.fetchall()]

        return jsonify({"total": total, "page": page, "per_page": per_page, "rows": rows}), 200

    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.error("table_observations error: %s", exc)
        return jsonify({"error": "Erreur interne."}), 500
    finally:
        db.close_connection(conn)


@app.route("/api/observations/<int:obs_id>", methods=["DELETE"])
def delete_observation(obs_id):
    """Delete one observation."""
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM observations WHERE id = %s", (obs_id,))
            if cur.fetchone() is None:
                return jsonify({"error": "Observation introuvable."}), 404
            cur.execute("DELETE FROM observations WHERE id = %s", (obs_id,))
            conn.commit()
        return jsonify({"ok": True}), 200
    except RuntimeError as exc:
        if conn: conn.rollback()
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        if conn: conn.rollback()
        logger.error("delete_observation error: %s", exc)
        return jsonify({"error": "Erreur interne."}), 500
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# Page routes (new design system)
# ---------------------------------------------------------------------------

def _get_lang():
    """Read the preferred language from the browser cookie.

    Returns 'en', 'fr', or 'ar'. Defaults to 'en'.
    The cookie is set by the setLang() JS function in base.html.
    """
    lang = request.cookies.get("lang", "en")
    return lang if lang in ("en", "fr", "ar") else "en"


def _get_stats():
    """Fetch live counts for the home page stats panel.

    Returns a dict with zones, sites, observations, contributors.
    Falls back to zeros if the DB is unreachable (home page still loads).
    """
    conn = None
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                  (SELECT count(*) FROM sites)        AS sites,
                  (SELECT count(*) FROM observations) AS observations,
                  (SELECT count(DISTINCT contributor_name)
                   FROM observations)                 AS contributors
            """)
            row = cur.fetchone()
            # zones table may not exist yet (before Phase 1 migration)
            try:
                cur.execute("SELECT count(*) FROM zones")
                zones = cur.fetchone()[0]
            except Exception:
                conn.rollback()
                zones = 0
        return {
            "zones":        zones,
            "sites":        row[0],
            "observations": row[1],
            "contributors": row[2],
        }
    except Exception:
        return {"zones": 0, "sites": 0, "observations": 0, "contributors": 0}
    finally:
        db.close_connection(conn)


@app.route("/home")
def home():
    """New design-system home page."""
    return render_template(
        "home.html",
        lang=_get_lang(),
        config=config,
        stats=_get_stats(),
        current_user=None,   # replaced in Phase 3 with session user
    )


@app.route("/map")
def map_page():
    """Map page stub — full implementation in Phase 2."""
    return render_template(
        "map_page.html",
        lang=_get_lang(),
        current_user=None,
    )


@app.route("/tables")
def tables_page():
    """Tables page — sites, zones and observations with counts."""
    conn = None
    counts = {"sites": 0, "zones": 0, "observations": 0}
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM sites")
            counts["sites"] = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM observations")
            counts["observations"] = cur.fetchone()[0]
            try:
                cur.execute("SELECT count(*) FROM zones")
                counts["zones"] = cur.fetchone()[0]
            except Exception:
                conn.rollback()
    except Exception:
        pass
    finally:
        db.close_connection(conn)

    return render_template(
        "tables_page.html",
        lang=_get_lang(),
        current_user=None,
        counts=counts,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    # Inside Docker, bind to 0.0.0.0 so the container port is reachable.
    # Locally (direct python app.py), bind to 127.0.0.1 only.
    # The HOST env var is set to 0.0.0.0 in docker-compose.yml.
    host  = os.environ.get("FLASK_HOST", "127.0.0.1")
    port  = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") != "production"
    app.run(host=host, port=port, debug=debug)

