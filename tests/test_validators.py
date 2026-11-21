"""
test_validators.py — Unit tests for validators.py.

No database or Flask server required. All tests run against pure Python functions.

Run:
    cd soil-platform
    .venv\\Scripts\\python -m pytest tests/test_validators.py -v
"""

import math
from datetime import date, timedelta

import pytest
import sys
from pathlib import Path

# Allow importing from the project root when pytest is run from soil-platform/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validators import validate_observation, validate_new_site
from config import BBOX


# ---------------------------------------------------------------------------
# Fixtures: minimal valid payloads to build test cases from
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_obs():
    """A fully valid observation payload (all required fields, no optional)."""
    return {
        "contributor_name": "Test User",
        "observation_date": date.today().isoformat(),
        "soil_texture":     "limoneuse",
        "water_status":     "frais",
        "salinity":         "absente",
        "erosion":          "aucune",
        "culture":          "olivier",
        "irrigation_mode":  "goutte-à-goutte",
    }


@pytest.fixture
def valid_site():
    """A fully valid new-site payload with coordinates inside the bbox."""
    return {
        "name":      "TEST_Site Valide",
        "culture":   "olivier",
        "soil_type": "limoneux",
        # Centre of the bbox
        "longitude": (BBOX["lon_min"] + BBOX["lon_max"]) / 2,
        "latitude":  (BBOX["lat_min"] + BBOX["lat_max"]) / 2,
    }


# ---------------------------------------------------------------------------
# validate_new_site — name
# ---------------------------------------------------------------------------

class TestSiteName:
    def test_valid_name(self, valid_site):
        _, errors = validate_new_site(valid_site)
        assert "name" not in errors

    def test_name_too_short(self, valid_site):
        valid_site["name"] = "AB"   # 2 chars — minimum is 3
        _, errors = validate_new_site(valid_site)
        assert "name" in errors

    def test_name_exactly_min(self, valid_site):
        valid_site["name"] = "ABC"  # 3 chars — just valid
        _, errors = validate_new_site(valid_site)
        assert "name" not in errors

    def test_name_exactly_max(self, valid_site):
        valid_site["name"] = "A" * 100
        _, errors = validate_new_site(valid_site)
        assert "name" not in errors

    def test_name_too_long(self, valid_site):
        valid_site["name"] = "A" * 101
        _, errors = validate_new_site(valid_site)
        assert "name" in errors

    def test_name_blank(self, valid_site):
        valid_site["name"] = "   "
        _, errors = validate_new_site(valid_site)
        assert "name" in errors

    def test_name_missing(self, valid_site):
        del valid_site["name"]
        _, errors = validate_new_site(valid_site)
        assert "name" in errors


# ---------------------------------------------------------------------------
# validate_new_site — culture and soil_type
# ---------------------------------------------------------------------------

class TestSiteDropdowns:
    def test_invalid_culture(self, valid_site):
        valid_site["culture"] = "INVALID_CULTURE"
        _, errors = validate_new_site(valid_site)
        assert "culture" in errors

    def test_missing_culture(self, valid_site):
        del valid_site["culture"]
        _, errors = validate_new_site(valid_site)
        assert "culture" in errors

    def test_invalid_soil_type(self, valid_site):
        valid_site["soil_type"] = "caillou"
        _, errors = validate_new_site(valid_site)
        assert "soil_type" in errors

    def test_missing_soil_type(self, valid_site):
        del valid_site["soil_type"]
        _, errors = validate_new_site(valid_site)
        assert "soil_type" in errors


# ---------------------------------------------------------------------------
# validate_new_site — coordinates
# ---------------------------------------------------------------------------

class TestSiteCoordinates:
    def test_valid_coords_centre(self, valid_site):
        _, errors = validate_new_site(valid_site)
        assert "longitude" not in errors
        assert "latitude" not in errors

    def test_longitude_too_low(self, valid_site):
        valid_site["longitude"] = -181.0
        _, errors = validate_new_site(valid_site)
        assert "longitude" in errors

    def test_longitude_too_high(self, valid_site):
        valid_site["longitude"] = 181.0
        _, errors = validate_new_site(valid_site)
        assert "longitude" in errors

    def test_latitude_too_low(self, valid_site):
        valid_site["latitude"] = -91.0
        _, errors = validate_new_site(valid_site)
        assert "latitude" in errors

    def test_latitude_too_high(self, valid_site):
        valid_site["latitude"] = 91.0
        _, errors = validate_new_site(valid_site)
        assert "latitude" in errors

    def test_longitude_outside_bbox(self, valid_site):
        valid_site["longitude"] = BBOX["lon_min"] - 0.01
        _, errors = validate_new_site(valid_site)
        assert "longitude" in errors

    def test_latitude_outside_bbox(self, valid_site):
        valid_site["latitude"] = BBOX["lat_max"] + 0.01
        _, errors = validate_new_site(valid_site)
        assert "latitude" in errors

    def test_longitude_at_bbox_min(self, valid_site):
        valid_site["longitude"] = BBOX["lon_min"]
        _, errors = validate_new_site(valid_site)
        assert "longitude" not in errors

    def test_longitude_at_bbox_max(self, valid_site):
        valid_site["longitude"] = BBOX["lon_max"]
        _, errors = validate_new_site(valid_site)
        assert "longitude" not in errors

    def test_longitude_nan(self, valid_site):
        valid_site["longitude"] = float("nan")
        _, errors = validate_new_site(valid_site)
        assert "longitude" in errors

    def test_longitude_infinity(self, valid_site):
        valid_site["longitude"] = float("inf")
        _, errors = validate_new_site(valid_site)
        assert "longitude" in errors

    def test_latitude_nan(self, valid_site):
        valid_site["latitude"] = float("nan")
        _, errors = validate_new_site(valid_site)
        assert "latitude" in errors

    def test_longitude_missing(self, valid_site):
        del valid_site["longitude"]
        _, errors = validate_new_site(valid_site)
        assert "longitude" in errors

    def test_latitude_missing(self, valid_site):
        del valid_site["latitude"]
        _, errors = validate_new_site(valid_site)
        assert "latitude" in errors

    def test_non_numeric_longitude(self, valid_site):
        valid_site["longitude"] = "not_a_number"
        _, errors = validate_new_site(valid_site)
        assert "longitude" in errors


# ---------------------------------------------------------------------------
# validate_observation — required text fields
# ---------------------------------------------------------------------------

class TestObsContributorName:
    def test_valid(self, valid_obs):
        _, errors = validate_observation(valid_obs)
        assert "contributor_name" not in errors

    def test_too_short(self, valid_obs):
        valid_obs["contributor_name"] = "A"   # 1 char — min is 2
        _, errors = validate_observation(valid_obs)
        assert "contributor_name" in errors

    def test_exactly_min(self, valid_obs):
        valid_obs["contributor_name"] = "AB"  # 2 chars — OK
        _, errors = validate_observation(valid_obs)
        assert "contributor_name" not in errors

    def test_exactly_max(self, valid_obs):
        valid_obs["contributor_name"] = "A" * 100
        _, errors = validate_observation(valid_obs)
        assert "contributor_name" not in errors

    def test_too_long(self, valid_obs):
        valid_obs["contributor_name"] = "A" * 101
        _, errors = validate_observation(valid_obs)
        assert "contributor_name" in errors

    def test_blank(self, valid_obs):
        valid_obs["contributor_name"] = "   "
        _, errors = validate_observation(valid_obs)
        assert "contributor_name" in errors

    def test_missing(self, valid_obs):
        del valid_obs["contributor_name"]
        _, errors = validate_observation(valid_obs)
        assert "contributor_name" in errors


# ---------------------------------------------------------------------------
# validate_observation — date
# ---------------------------------------------------------------------------

class TestObsDate:
    def test_today_valid(self, valid_obs):
        valid_obs["observation_date"] = date.today().isoformat()
        _, errors = validate_observation(valid_obs)
        assert "observation_date" not in errors

    def test_past_date_valid(self, valid_obs):
        valid_obs["observation_date"] = "2024-01-15"
        _, errors = validate_observation(valid_obs)
        assert "observation_date" not in errors

    def test_future_date_rejected(self, valid_obs):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        valid_obs["observation_date"] = tomorrow
        _, errors = validate_observation(valid_obs)
        assert "observation_date" in errors

    def test_invalid_format_rejected(self, valid_obs):
        valid_obs["observation_date"] = "30/05/2026"  # DD/MM/YYYY not accepted
        _, errors = validate_observation(valid_obs)
        assert "observation_date" in errors

    def test_missing_date_rejected(self, valid_obs):
        del valid_obs["observation_date"]
        _, errors = validate_observation(valid_obs)
        assert "observation_date" in errors

    def test_nonsense_string_rejected(self, valid_obs):
        valid_obs["observation_date"] = "not-a-date"
        _, errors = validate_observation(valid_obs)
        assert "observation_date" in errors


# ---------------------------------------------------------------------------
# validate_observation — controlled vocabulary fields
# ---------------------------------------------------------------------------

class TestObsDropdowns:
    @pytest.mark.parametrize("field,valid_val,invalid_val", [
        ("soil_texture",    "argileuse",             "clay"),
        ("water_status",    "engorgé",               "wet"),
        ("salinity",        "croûtes de sel visibles","high"),
        ("erosion",         "rigoles",               "heavy"),
        ("culture",         "tomate",                "UNKNOWN"),
        ("irrigation_mode", "goutte-à-goutte",       "drip"),
    ])
    def test_invalid_value_rejected(self, valid_obs, field, valid_val, invalid_val):
        valid_obs[field] = invalid_val
        _, errors = validate_observation(valid_obs)
        assert field in errors

    @pytest.mark.parametrize("field,valid_val,invalid_val", [
        ("soil_texture",    "argileuse",             "clay"),
        ("water_status",    "engorgé",               "wet"),
        ("salinity",        "croûtes de sel visibles","high"),
        ("erosion",         "rigoles",               "heavy"),
        ("culture",         "tomate",                "UNKNOWN"),
        ("irrigation_mode", "goutte-à-goutte",       "drip"),
    ])
    def test_valid_value_accepted(self, valid_obs, field, valid_val, invalid_val):
        valid_obs[field] = valid_val
        _, errors = validate_observation(valid_obs)
        assert field not in errors

    @pytest.mark.parametrize("field", [
        "soil_texture", "water_status", "salinity",
        "erosion", "culture", "irrigation_mode",
    ])
    def test_missing_required_field(self, valid_obs, field):
        del valid_obs[field]
        _, errors = validate_observation(valid_obs)
        assert field in errors


# ---------------------------------------------------------------------------
# validate_observation — optional numeric fields
# ---------------------------------------------------------------------------

class TestObsPh:
    def test_ph_absent_ok(self, valid_obs):
        # Optional — not present is fine
        _, errors = validate_observation(valid_obs)
        assert "ph" not in errors

    def test_ph_empty_string_ok(self, valid_obs):
        valid_obs["ph"] = ""
        _, errors = validate_observation(valid_obs)
        assert "ph" not in errors

    def test_ph_zero_ok(self, valid_obs):
        valid_obs["ph"] = 0.0
        _, errors = validate_observation(valid_obs)
        assert "ph" not in errors

    def test_ph_fourteen_ok(self, valid_obs):
        valid_obs["ph"] = 14.0
        _, errors = validate_observation(valid_obs)
        assert "ph" not in errors

    def test_ph_below_zero_rejected(self, valid_obs):
        valid_obs["ph"] = -0.1
        _, errors = validate_observation(valid_obs)
        assert "ph" in errors

    def test_ph_above_fourteen_rejected(self, valid_obs):
        valid_obs["ph"] = 14.1
        _, errors = validate_observation(valid_obs)
        assert "ph" in errors

    def test_ph_nan_rejected(self, valid_obs):
        valid_obs["ph"] = float("nan")
        _, errors = validate_observation(valid_obs)
        assert "ph" in errors

    def test_ph_infinity_rejected(self, valid_obs):
        valid_obs["ph"] = float("inf")
        _, errors = validate_observation(valid_obs)
        assert "ph" in errors

    def test_ph_string_non_numeric_rejected(self, valid_obs):
        valid_obs["ph"] = "acid"
        _, errors = validate_observation(valid_obs)
        assert "ph" in errors


class TestObsEc:
    def test_ec_absent_ok(self, valid_obs):
        _, errors = validate_observation(valid_obs)
        assert "ec_dsm" not in errors

    def test_ec_zero_ok(self, valid_obs):
        valid_obs["ec_dsm"] = 0.0
        _, errors = validate_observation(valid_obs)
        assert "ec_dsm" not in errors

    def test_ec_negative_rejected(self, valid_obs):
        valid_obs["ec_dsm"] = -0.01
        _, errors = validate_observation(valid_obs)
        assert "ec_dsm" in errors

    def test_ec_nan_rejected(self, valid_obs):
        valid_obs["ec_dsm"] = float("nan")
        _, errors = validate_observation(valid_obs)
        assert "ec_dsm" in errors


class TestObsOrganicMatter:
    def test_om_absent_ok(self, valid_obs):
        _, errors = validate_observation(valid_obs)
        assert "organic_matter_pct" not in errors

    def test_om_zero_ok(self, valid_obs):
        valid_obs["organic_matter_pct"] = 0.0
        _, errors = validate_observation(valid_obs)
        assert "organic_matter_pct" not in errors

    def test_om_hundred_ok(self, valid_obs):
        valid_obs["organic_matter_pct"] = 100.0
        _, errors = validate_observation(valid_obs)
        assert "organic_matter_pct" not in errors

    def test_om_above_hundred_rejected(self, valid_obs):
        valid_obs["organic_matter_pct"] = 100.1
        _, errors = validate_observation(valid_obs)
        assert "organic_matter_pct" in errors

    def test_om_negative_rejected(self, valid_obs):
        valid_obs["organic_matter_pct"] = -0.1
        _, errors = validate_observation(valid_obs)
        assert "organic_matter_pct" in errors

    def test_om_nan_rejected(self, valid_obs):
        valid_obs["organic_matter_pct"] = float("nan")
        _, errors = validate_observation(valid_obs)
        assert "organic_matter_pct" in errors


# ---------------------------------------------------------------------------
# validate_observation — remark
# ---------------------------------------------------------------------------

class TestObsRemark:
    def test_remark_absent_ok(self, valid_obs):
        _, errors = validate_observation(valid_obs)
        assert "remark" not in errors

    def test_remark_empty_string_ok(self, valid_obs):
        valid_obs["remark"] = ""
        _, errors = validate_observation(valid_obs)
        assert "remark" not in errors

    def test_remark_exactly_max_ok(self, valid_obs):
        valid_obs["remark"] = "A" * 1000
        _, errors = validate_observation(valid_obs)
        assert "remark" not in errors

    def test_remark_too_long(self, valid_obs):
        valid_obs["remark"] = "A" * 1001
        _, errors = validate_observation(valid_obs)
        assert "remark" in errors

    def test_remark_none_ok(self, valid_obs):
        valid_obs["remark"] = None
        _, errors = validate_observation(valid_obs)
        assert "remark" not in errors
