# config.py — Single source of truth for all application constants.
#
# Rules:
#   - Never duplicate these values in JavaScript, SQL, or templates.
#   - Flask passes them to pages as template variables or a JSON block.
#   - The CHECK constraint lists in schema.sql MUST match the lists here.
#     A "KEEP IN SYNC" comment appears in both files.

# ------------------------------------------------------------------
# Study area: Turlock irrigated perimeter, Central Valley, California
# ------------------------------------------------------------------
PERIMETER_NAME = "Turlock, Californie"

MAP_CENTER_LAT = 37.46
MAP_CENTER_LON = -120.875
MAP_ZOOM = 11

# Bounding box — WGS84, used for site/zone validation and map fitBounds.
BBOX = {
    "lon_min": -121.05,
    "lon_max": -120.70,
    "lat_min":  37.32,
    "lat_max":  37.60,
}

# DB connection settings dict (used by import scripts).
# The Flask app uses db.py which reads from .env directly.
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DB_SETTINGS = {
    "host":     os.getenv("POSTGRES_HOST", "localhost"),
    "port":     int(os.getenv("POSTGRES_PORT", 5433)),
    "dbname":   os.getenv("POSTGRES_DB",   "soil_platform"),
    "user":     os.getenv("POSTGRES_USER", "soil_user"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

# ------------------------------------------------------------------
# Dropdown lists
# KEEP IN SYNC with CHECK constraints in database/schema.sql
# ------------------------------------------------------------------

# Soil texture options
SOIL_TEXTURES = ["sableuse", "limoneuse", "argileuse", "équilibrée"]

# Soil water status
WATER_STATUSES = ["sec", "frais", "humide", "engorgé"]

# Apparent salinity
SALINITY_LEVELS = ["absente", "traces", "croûtes de sel visibles"]

# Observed erosion
EROSION_TYPES = ["aucune", "en nappe", "rigoles", "ravines"]

# Irrigation modes (Central Valley context)
IRRIGATION_MODES = ["goutte-à-goutte", "aspersion", "gravitaire", "pluvial"]

# Crops — Central Valley, California
CULTURES = [
    "amande", "noix", "pistache", "tomate",
    "maïs", "blé", "laitue", "oignon",
    "pêche", "raisin", "autre",
]

# Site soil types (from SSURGO vocabulary, simplified)
SOIL_TYPES = ["sableux", "limono-sableux", "limoneux", "argileux", "autre"]

# ------------------------------------------------------------------
# Culture → map marker colour
# ------------------------------------------------------------------
CULTURE_COLOURS = {
    "amande":    "#C4956A",   # warm tan
    "noix":      "#8B5E3C",   # soil brown
    "pistache":  "#6aaa3a",   # green
    "tomate":    "#e63946",   # red
    "maïs":      "#f9c74f",   # yellow
    "blé":       "#f4a62a",   # amber
    "laitue":    "#2ec4b6",   # teal
    "oignon":    "#9b5de5",   # purple
    "pêche":     "#FF8C69",   # salmon
    "raisin":    "#c1121f",   # dark red
    "autre":     "#adb5bd",   # grey
}
DEFAULT_COLOUR = "#adb5bd"
