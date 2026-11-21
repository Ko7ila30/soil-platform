"""
test_api.py — Integration tests for the Flask API endpoints.

Requires the Docker database to be running (docker compose up -d).
If the database is unreachable, ALL tests in this file are skipped with a
clear message — they are never marked as failures due to infrastructure.

Test data safety:
  - Every site or observation created by a test uses a name or contributor
    prefixed with "TEST_" so it can be identified and deleted.
  - A module-level autouse fixture deletes all TEST_ records at the end of the
    test session, even if individual tests fail.
  - Tests NEVER truncate or drop any table.

Run:
    cd soil-platform
    .venv\\Scripts\\python -m pytest tests/test_api.py -v
"""

import sys
from pathlib import Path
from datetime import date

import pytest

# Allow importing from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Check DB reachability before importing app (avoids confusing errors)
# ---------------------------------------------------------------------------

def _db_reachable():
    """Return True if the Docker database can be connected to."""
    try:
        import db as db_module
        conn = db_module.get_connection()
        db_module.close_connection(conn)
        return True
    except Exception:
        return False


DB_AVAILABLE = _db_reachable()

skip_if_no_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="Docker database is not reachable — start it with: docker compose up -d",
)

# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Create a Flask test client for the whole module."""
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Cleanup fixture — runs once after all tests in this module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Delete all TEST_ records from the database after the test session."""
    yield  # run all tests first

    if not DB_AVAILABLE:
        return

    import db as db_module
    conn = None
    try:
        conn = db_module.get_connection()
        with conn.cursor() as cur:
            # Delete observations linked to TEST_ sites first (FK constraint)
            cur.execute("""
                DELETE FROM observations
                WHERE site_id IN (
                    SELECT id FROM sites WHERE name LIKE 'TEST_%'
                )
            """)
            # Delete observations with TEST_ contributor names (from other sites)
            cur.execute(
                "DELETE FROM observations WHERE contributor_name LIKE 'TEST_%'"
            )
            # Delete TEST_ sites
            cur.execute("DELETE FROM sites WHERE name LIKE 'TEST_%'")
        conn.commit()
    except Exception as e:
        print(f"\nWarning: cleanup_test_data failed: {e}")
        if conn:
            conn.rollback()
    finally:
        db_module.close_connection(conn)


# ---------------------------------------------------------------------------
# Phase 1 — GET /api/sites
# ---------------------------------------------------------------------------

@skip_if_no_db
class TestGetSites:
    def test_status_200(self, client):
        r = client.get("/api/sites")
        assert r.status_code == 200

    def test_geojson_type(self, client):
        data = client.get("/api/sites").get_json()
        assert data["type"] == "FeatureCollection"

    def test_has_features(self, client):
        data = client.get("/api/sites").get_json()
        assert isinstance(data["features"], list)
        assert len(data["features"]) >= 18   # seed has 18 sites

    def test_feature_properties(self, client):
        data = client.get("/api/sites").get_json()
        feature = data["features"][0]
        props = feature["properties"]
        assert "id"                   in props
        assert "name"                 in props
        assert "culture"              in props
        assert "soil_type"            in props
        assert "observation_count"    in props
        assert "last_observation_date" in props

    def test_geometry_type(self, client):
        data = client.get("/api/sites").get_json()
        geom = data["features"][0]["geometry"]
        assert geom["type"] == "Point"
        # GeoJSON coordinates are [longitude, latitude]
        assert len(geom["coordinates"]) == 2


# ---------------------------------------------------------------------------
# Phase 1 — GET /api/sites/<id>
# ---------------------------------------------------------------------------

@skip_if_no_db
class TestGetOneSite:
    def _first_site_id(self, client):
        data = client.get("/api/sites").get_json()
        return data["features"][0]["properties"]["id"]

    def test_known_site_200(self, client):
        sid = self._first_site_id(client)
        r = client.get(f"/api/sites/{sid}")
        assert r.status_code == 200

    def test_known_site_is_feature(self, client):
        sid = self._first_site_id(client)
        data = client.get(f"/api/sites/{sid}").get_json()
        assert data["type"] == "Feature"

    def test_unknown_site_404(self, client):
        r = client.get("/api/sites/999999")
        assert r.status_code == 404

    def test_404_body_is_json(self, client):
        data = client.get("/api/sites/999999").get_json()
        assert "error" in data


# ---------------------------------------------------------------------------
# Phase 2 — GET /api/options
# ---------------------------------------------------------------------------

@skip_if_no_db
class TestGetOptions:
    def test_status_200(self, client):
        r = client.get("/api/options")
        assert r.status_code == 200

    def test_all_keys_present(self, client):
        data = client.get("/api/options").get_json()
        for key in ["sites", "cultures", "soilTypes", "soilTextures",
                    "waterStatuses", "salinityLevels", "erosionTypes",
                    "irrigationModes"]:
            assert key in data, f"Missing key: {key}"

    def test_sites_list_non_empty(self, client):
        data = client.get("/api/options").get_json()
        assert len(data["sites"]) >= 18


# ---------------------------------------------------------------------------
# Phase 2 — GET /api/sites/<id>/observations
# ---------------------------------------------------------------------------

@skip_if_no_db
class TestGetObservations:
    def _first_site_id(self, client):
        data = client.get("/api/sites").get_json()
        return data["features"][0]["properties"]["id"]

    def test_known_site_200(self, client):
        sid = self._first_site_id(client)
        r = client.get(f"/api/sites/{sid}/observations")
        assert r.status_code == 200

    def test_returns_list(self, client):
        sid = self._first_site_id(client)
        data = client.get(f"/api/sites/{sid}/observations").get_json()
        assert isinstance(data, list)

    def test_unknown_site_404(self, client):
        r = client.get("/api/sites/999999/observations")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Phase 2 — POST /api/sites/<id>/observations
# ---------------------------------------------------------------------------

@skip_if_no_db
class TestCreateObservation:
    def _first_site_id(self, client):
        data = client.get("/api/sites").get_json()
        return data["features"][0]["properties"]["id"]

    def _valid_payload(self):
        return {
            "contributor_name": "TEST_Contributor",
            "observation_date": date.today().isoformat(),
            "soil_texture":     "équilibrée",
            "water_status":     "engorgé",
            "salinity":         "croûtes de sel visibles",
            "erosion":          "aucune",
            "culture":          "tomate",
            "irrigation_mode":  "goutte-à-goutte",
        }

    def test_valid_observation_201(self, client):
        sid = self._first_site_id(client)
        r = client.post(
            f"/api/sites/{sid}/observations",
            json=self._valid_payload(),
        )
        assert r.status_code == 201

    def test_response_has_id(self, client):
        sid = self._first_site_id(client)
        data = client.post(
            f"/api/sites/{sid}/observations",
            json=self._valid_payload(),
        ).get_json()
        assert "id" in data

    def test_missing_required_field_400(self, client):
        sid = self._first_site_id(client)
        payload = self._valid_payload()
        del payload["contributor_name"]
        r = client.post(f"/api/sites/{sid}/observations", json=payload)
        assert r.status_code == 400

    def test_400_has_errors_dict(self, client):
        sid = self._first_site_id(client)
        payload = self._valid_payload()
        del payload["contributor_name"]
        data = client.post(
            f"/api/sites/{sid}/observations", json=payload
        ).get_json()
        assert "errors" in data
        assert "contributor_name" in data["errors"]

    def test_bad_ph_400(self, client):
        sid = self._first_site_id(client)
        payload = self._valid_payload()
        payload["ph"] = 15.0
        r = client.post(f"/api/sites/{sid}/observations", json=payload)
        assert r.status_code == 400

    def test_future_date_400(self, client):
        from datetime import timedelta
        sid = self._first_site_id(client)
        payload = self._valid_payload()
        payload["observation_date"] = (
            date.today() + timedelta(days=1)
        ).isoformat()
        r = client.post(f"/api/sites/{sid}/observations", json=payload)
        assert r.status_code == 400

    def test_unknown_site_404(self, client):
        r = client.post(
            "/api/sites/999999/observations",
            json=self._valid_payload(),
        )
        assert r.status_code == 404

    def test_accent_round_trip(self, client):
        """Save and read back accented French values without corruption."""
        sid = self._first_site_id(client)
        payload = {
            "contributor_name": "TEST_Accent_User",
            "observation_date": date.today().isoformat(),
            "soil_texture":     "équilibrée",
            "water_status":     "engorgé",
            "salinity":         "croûtes de sel visibles",
            "erosion":          "aucune",
            "culture":          "olivier",
            "irrigation_mode":  "goutte-à-goutte",
            "remark":           "Données avec accents: é è ê â ç",
        }
        r = client.post(f"/api/sites/{sid}/observations", json=payload)
        assert r.status_code == 201
        data = r.get_json()
        assert data["soil_texture"]  == "équilibrée"
        assert data["water_status"]  == "engorgé"
        assert data["salinity"]      == "croûtes de sel visibles"
        assert data["irrigation_mode"] == "goutte-à-goutte"
        assert data["remark"]        == "Données avec accents: é è ê â ç"


# ---------------------------------------------------------------------------
# Phase 3 — POST /api/sites
# ---------------------------------------------------------------------------

@skip_if_no_db
class TestCreateSite:
    def _valid_payload(self):
        from config import BBOX
        return {
            "name":      "TEST_Nouveau Site",
            "culture":   "maïs",
            "soil_type": "sableux",
            "longitude": (BBOX["lon_min"] + BBOX["lon_max"]) / 2,
            "latitude":  (BBOX["lat_min"] + BBOX["lat_max"]) / 2,
        }

    def test_valid_site_201(self, client):
        r = client.post("/api/sites", json=self._valid_payload())
        assert r.status_code == 201

    def test_response_is_geojson_feature(self, client):
        data = client.post("/api/sites", json=self._valid_payload()).get_json()
        assert data["type"] == "Feature"
        assert "geometry" in data
        assert "properties" in data

    def test_missing_name_400(self, client):
        payload = self._valid_payload()
        del payload["name"]
        r = client.post("/api/sites", json=payload)
        assert r.status_code == 400

    def test_outside_bbox_400(self, client):
        from config import BBOX
        payload = self._valid_payload()
        payload["longitude"] = BBOX["lon_min"] - 1.0   # clearly outside
        r = client.post("/api/sites", json=payload)
        assert r.status_code == 400

    def test_outside_bbox_french_message(self, client):
        from config import BBOX
        payload = self._valid_payload()
        payload["longitude"] = BBOX["lon_min"] - 1.0
        data = client.post("/api/sites", json=payload).get_json()
        assert "errors" in data
        # The error message must be in French and mention the perimeter
        assert "périmètre" in data["errors"].get("longitude", "").lower()

    def test_coordinate_order(self, client):
        """Verify that longitude is stored as ST_X and latitude as ST_Y.

        This is the most important geometry test: PostGIS uses X=longitude,
        Y=latitude, but it's easy to accidentally swap them (Leaflet gives
        lat/lng, PostGIS expects lon/lat).
        """
        import db as db_module

        known_lon = 10.555
        known_lat = 35.915
        payload = {
            "name":      "TEST_CoordOrder",
            "culture":   "olivier",
            "soil_type": "limoneux",
            "longitude": known_lon,
            "latitude":  known_lat,
        }
        r = client.post("/api/sites", json=payload)
        assert r.status_code == 201
        site_id = r.get_json()["properties"]["id"]

        conn = None
        try:
            conn = db_module.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ST_X(geom), ST_Y(geom) FROM sites WHERE id = %s",
                    (site_id,)
                )
                stored_lon, stored_lat = cur.fetchone()
        finally:
            db_module.close_connection(conn)

        assert abs(stored_lon - known_lon) < 1e-6, (
            f"ST_X (longitude) is {stored_lon}, expected {known_lon}. "
            "Coordinate order is wrong — check ST_MakePoint argument order."
        )
        assert abs(stored_lat - known_lat) < 1e-6, (
            f"ST_Y (latitude) is {stored_lat}, expected {known_lat}."
        )
