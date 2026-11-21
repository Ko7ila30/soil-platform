# validators.py — Pure server-side validation functions.
#
# Design rules:
#   - No imports from Flask, db, or any I/O library.
#     These are plain Python functions; they can be tested without a server.
#   - Each function returns (cleaned_data, errors).
#     cleaned_data: dict of validated, type-converted values (or {} on error).
#     errors:       dict mapping field name -> French error message string.
#                   Empty dict means validation passed.
#   - All error messages are in French (displayed to the user).
#   - Code comments are in English (for the developer).

import math
from datetime import date, datetime

from config import (
    BBOX,
    CULTURES,
    EROSION_TYPES,
    IRRIGATION_MODES,
    SALINITY_LEVELS,
    SOIL_TEXTURES,
    SOIL_TYPES,
    WATER_STATUSES,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _require_text(data, field, min_len, max_len, label):
    """Validate a required text field: non-blank, length within [min_len, max_len].

    Returns (cleaned_string_or_None, error_message_or_None).
    """
    value = data.get(field, "")
    if value is None:
        value = ""
    value = str(value).strip()
    if not value:
        return None, f"Le champ « {label} » est obligatoire."
    if len(value) < min_len:
        return None, (
            f"Le champ « {label} » doit contenir au moins {min_len} caractère(s)."
        )
    if len(value) > max_len:
        return None, (
            f"Le champ « {label} » ne doit pas dépasser {max_len} caractères."
        )
    return value, None


def _require_choice(data, field, allowed, label):
    """Validate a required dropdown field: value must be in allowed list.

    Returns (cleaned_value_or_None, error_message_or_None).
    """
    value = data.get(field, "")
    if value is None:
        value = ""
    value = str(value).strip()
    if not value:
        return None, f"Le champ « {label} » est obligatoire."
    if value not in allowed:
        return None, (
            f"Valeur non valide pour « {label} ». "
            f"Choisissez parmi : {', '.join(allowed)}."
        )
    return value, None


def _optional_number(data, field, label, min_val, max_val):
    """Validate an optional numeric field.

    - If absent or empty string: returns (None, None) — field is optional.
    - If present: must be a finite number within [min_val, max_val].

    Returns (float_or_None, error_message_or_None).
    """
    raw = data.get(field)

    # Treat empty string the same as absent.
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None, None

    # Try to convert to float.
    try:
        value = float(raw)
    except (ValueError, TypeError):
        return None, f"« {label} » doit être un nombre."

    # Reject NaN and Infinity — they cannot be stored in NUMERIC columns.
    if not math.isfinite(value):
        return None, f"« {label} » doit être un nombre fini."

    if value < min_val or value > max_val:
        return None, (
            f"« {label} » doit être compris entre {min_val} et {max_val}."
        )
    return value, None


def _require_date(data, field, label):
    """Validate a required date field.

    - Must be present and non-empty.
    - Must parse as YYYY-MM-DD.
    - Must not be in the future.

    Returns (date_object_or_None, error_message_or_None).
    """
    raw = data.get(field, "")
    if raw is None:
        raw = ""
    raw = str(raw).strip()
    if not raw:
        return None, f"Le champ « {label} » est obligatoire."

    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None, f"« {label} » doit être une date valide (JJ/MM/AAAA)."

    if parsed > date.today():
        return None, f"« {label} » ne peut pas être dans le futur."

    return parsed, None


# ---------------------------------------------------------------------------
# validate_observation
# ---------------------------------------------------------------------------

def validate_observation(data):
    """Validate the data submitted for a new observation (Part 2).

    Args:
        data (dict): raw values from the JSON request body.
                     site_id is NOT validated here; the route checks it.

    Returns:
        tuple: (cleaned_dict, errors_dict)
               cleaned_dict has Python-typed values ready for the INSERT.
               errors_dict maps field names to French error messages.
               If errors_dict is non-empty, the INSERT must not proceed.
    """
    errors = {}
    cleaned = {}

    # --- contributor_name: required, 2–100 chars ---
    v, e = _require_text(data, "contributor_name", 2, 100, "Nom du contributeur")
    if e:
        errors["contributor_name"] = e
    else:
        cleaned["contributor_name"] = v

    # --- observation_date: required, not in the future ---
    v, e = _require_date(data, "observation_date", "Date de l'observation")
    if e:
        errors["observation_date"] = e
    else:
        cleaned["observation_date"] = v

    # --- soil_texture: required, controlled vocabulary ---
    v, e = _require_choice(data, "soil_texture", SOIL_TEXTURES, "Texture du sol")
    if e:
        errors["soil_texture"] = e
    else:
        cleaned["soil_texture"] = v

    # --- water_status: required, controlled vocabulary ---
    v, e = _require_choice(data, "water_status", WATER_STATUSES, "État hydrique du sol")
    if e:
        errors["water_status"] = e
    else:
        cleaned["water_status"] = v

    # --- salinity: required, controlled vocabulary ---
    v, e = _require_choice(data, "salinity", SALINITY_LEVELS, "Salinité apparente")
    if e:
        errors["salinity"] = e
    else:
        cleaned["salinity"] = v

    # --- erosion: required, controlled vocabulary ---
    v, e = _require_choice(data, "erosion", EROSION_TYPES, "Érosion observée")
    if e:
        errors["erosion"] = e
    else:
        cleaned["erosion"] = v

    # --- culture: required, controlled vocabulary ---
    v, e = _require_choice(data, "culture", CULTURES, "Culture en place")
    if e:
        errors["culture"] = e
    else:
        cleaned["culture"] = v

    # --- irrigation_mode: required, controlled vocabulary ---
    v, e = _require_choice(
        data, "irrigation_mode", IRRIGATION_MODES, "Mode d'irrigation"
    )
    if e:
        errors["irrigation_mode"] = e
    else:
        cleaned["irrigation_mode"] = v

    # --- ph: optional, 0–14 ---
    v, e = _optional_number(data, "ph", "pH", 0.0, 14.0)
    if e:
        errors["ph"] = e
    else:
        cleaned["ph"] = v  # None if not provided

    # --- ec_dsm: optional, >= 0 ---
    # Using a large upper bound (9999.99 fits NUMERIC(6,2)) to allow valid CE values.
    v, e = _optional_number(data, "ec_dsm", "Conductivité électrique CE", 0.0, 9999.99)
    if e:
        errors["ec_dsm"] = e
    else:
        cleaned["ec_dsm"] = v

    # --- organic_matter_pct: optional, 0–100 ---
    v, e = _optional_number(data, "organic_matter_pct", "Matière organique", 0.0, 100.0)
    if e:
        errors["organic_matter_pct"] = e
    else:
        cleaned["organic_matter_pct"] = v

    # --- remark: optional, up to 1000 chars ---
    remark = data.get("remark")
    if remark is None or (isinstance(remark, str) and remark.strip() == ""):
        cleaned["remark"] = None
    else:
        remark = str(remark).strip()
        if len(remark) > 1000:
            errors["remark"] = "La remarque ne doit pas dépasser 1000 caractères."
        else:
            cleaned["remark"] = remark

    return cleaned, errors


# ---------------------------------------------------------------------------
# validate_new_site
# ---------------------------------------------------------------------------

def validate_new_site(data, bbox=None):
    """Validate the data submitted for a new observation site (Part 3).

    Args:
        data (dict): raw values from the JSON request body.
                     Expected keys: name, culture, soil_type, longitude, latitude.
        bbox (dict or None): bounding box with keys lon_min, lon_max, lat_min, lat_max.
                             If None, the bbox check from config.BBOX is skipped
                             (useful in unit tests that want to test other rules).

    Returns:
        tuple: (cleaned_dict, errors_dict)
    """
    if bbox is None:
        bbox = BBOX

    errors = {}
    cleaned = {}

    # --- name: required, 3–100 chars ---
    v, e = _require_text(data, "name", 3, 100, "Nom du site")
    if e:
        errors["name"] = e
    else:
        cleaned["name"] = v

    # --- culture: required, controlled vocabulary ---
    v, e = _require_choice(data, "culture", CULTURES, "Culture")
    if e:
        errors["culture"] = e
    else:
        cleaned["culture"] = v

    # --- soil_type: required, controlled vocabulary ---
    v, e = _require_choice(data, "soil_type", SOIL_TYPES, "Type de sol")
    if e:
        errors["soil_type"] = e
    else:
        cleaned["soil_type"] = v

    # --- longitude: required, finite float, -180..180, inside bbox ---
    lon_raw = data.get("longitude")
    if lon_raw is None or (isinstance(lon_raw, str) and str(lon_raw).strip() == ""):
        errors["longitude"] = "La longitude est obligatoire."
    else:
        try:
            lon = float(lon_raw)
        except (ValueError, TypeError):
            lon = None
            errors["longitude"] = "La longitude doit être un nombre."

        if lon is not None:
            if not math.isfinite(lon):
                errors["longitude"] = "La longitude doit être un nombre fini."
            elif lon < -180 or lon > 180:
                errors["longitude"] = "La longitude doit être comprise entre -180 et 180."
            elif lon < bbox["lon_min"] or lon > bbox["lon_max"]:
                errors["longitude"] = (
                    f"Le point est en dehors du périmètre autorisé "
                    f"(longitude entre {bbox['lon_min']} et {bbox['lon_max']})."
                )
            else:
                cleaned["longitude"] = lon

    # --- latitude: required, finite float, -90..90, inside bbox ---
    lat_raw = data.get("latitude")
    if lat_raw is None or (isinstance(lat_raw, str) and str(lat_raw).strip() == ""):
        errors["latitude"] = "La latitude est obligatoire."
    else:
        try:
            lat = float(lat_raw)
        except (ValueError, TypeError):
            lat = None
            errors["latitude"] = "La latitude doit être un nombre."

        if lat is not None:
            if not math.isfinite(lat):
                errors["latitude"] = "La latitude doit être un nombre fini."
            elif lat < -90 or lat > 90:
                errors["latitude"] = "La latitude doit être comprise entre -90 et 90."
            elif lat < bbox["lat_min"] or lat > bbox["lat_max"]:
                errors["latitude"] = (
                    f"Le point est en dehors du périmètre autorisé "
                    f"(latitude entre {bbox['lat_min']} et {bbox['lat_max']})."
                )
            else:
                cleaned["latitude"] = lat

    return cleaned, errors
