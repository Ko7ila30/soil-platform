# SoilWatch — Participative Soil Observation Platform

A web-mapping application for collaborative soil monitoring in irrigated agricultural perimeters.
Built as an academic project for a Web GIS course (Mini-Project, 2026).

---

## What it does

SoilWatch lets farmers, irrigation-association members (GDA) and field technicians
collectively observe and record soil conditions across an irrigated perimeter.
Anyone can browse the map, click on a site or soil unit to read its history,
and submit a new observation from the field.
Technicians and administrators can add new sites, draw soil zones, edit attributes,
and delete records directly from the interface.

The platform follows the **VGI principle** (Volunteered Geographic Information):
the data grows through contributions from non-specialist users, building a shared
picture of soil health over time.

---

## Study area

**Turlock Irrigated Perimeter, Central Valley, California**

- Bounding box: lon −121.05 → −120.70 / lat 37.32 → 37.60
- Map centre: 37.46 N, −120.875 W, zoom 11
- ~2 000 real soil polygons from **USDA SSURGO** (National Cooperative Soil Survey)
- 60 observation sites with real soil types and simulated crop assignments
- ~100 simulated observations for demonstration purposes

> All observation data and crop assignments are **simulated**.
> Soil polygon geometry and soil type names are **real** (USDA SSURGO).

---

## Features

### Part 1 — Visualisation and query
- Interactive Leaflet map with OpenStreetMap and ESRI Satellite basemaps
- ~2 000 USDA SSURGO soil unit polygons as a semi-transparent overlay
- 60 observation site markers coloured by crop type with a legend
- Side panel showing full site attributes and complete observation history
- Sidebar search: filter sites and zones by name, zoom to result
- Country border overlay (Natural Earth)

### Part 2 — Observation form
- Click any site → "Add Observation" button opens a modal form
- Required fields: contributor name, date, soil texture, water status,
  salinity, erosion, crop, irrigation mode
- Optional measurements: pH (0–14), electrical conductivity (dS/m), organic matter (%)
- Client-side and server-side validation with per-field error messages
- Observation saved to PostgreSQL, popup refreshes instantly without page reload

### Part 3 — Add a new site
- "Add Site" toolbar button activates crosshair mode
- Click anywhere inside the allowed bounding box to place a draggable marker
- Fill in name, crop and soil type; coordinates update live as the marker is dragged
- New site appears on the map and in the search immediately after saving

### Extended features
- **Draw zone**: digitise a new soil polygon directly on the map using Leaflet-Geoman
- **Edit geometry**: drag site markers or zone vertices to update stored coordinates
- **Edit attributes**: inline editing of site and zone attributes from the side panel
- **Delete**: remove sites (with all linked observations) or zones after confirmation
- **Tables page**: paginated, searchable tables for Sites, Zones and Observations
  with inline editing, delete, "View on map" and CSV export
- **Home page**: live statistics panel (zone count, site count, observations, contributors),
  OSM map preview, 3-step explainer
- **Three languages**: English, French, Arabic (including RTL layout for Arabic),
  language stored in a browser cookie and applied server-side

---

## Architecture

```
Browser  (Leaflet 1.9.4 · Leaflet-Geoman 2.17.0 · vanilla JS · HTML/CSS)
    │
    │  HTTP  JSON / GeoJSON  (localhost:5000)
    ▼
Flask 3.1  (Python 3.15, host or Docker container)
  app.py        — all routes and JSON serialisation
  zones_api.py  — zones blueprint (GET/POST /api/zones, GET /carte)
  config.py     — single source of truth for all constants
  db.py         — psycopg2 connection helper
  validators.py — pure server-side validation (no Flask/DB imports)
    │
    │  psycopg2  TCP  (localhost:5433)
    ▼
PostgreSQL 16 + PostGIS 3.4  (Docker container)
  table: sites        — point geometry + attributes
  table: observations — field records linked to sites
  table: zones        — SSURGO MultiPolygon geometry + attributes
  table: users        — prepared for authentication (Phase 3)
  Named Docker volume — data persists across restarts
```

---

## Technology stack

| Layer | Technology |
|---|---|
| Map library | Leaflet 1.9.4 (served locally) |
| Drawing / editing | Leaflet-Geoman 2.17.0 (served locally) |
| Frontend | Vanilla JavaScript, Jinja2 templates, custom CSS |
| Backend | Python 3.15.2, Flask 3.1.0 |
| Database driver | psycopg2-binary 2.9.13 |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| Container | Docker + Docker Compose |
| Basemaps | OpenStreetMap (default), ESRI World Imagery (satellite) |
| Fonts | DM Serif Display + Inter (Google Fonts) |

---

## Project structure

```
soil-platform/
├── app.py                  Flask routes (all APIs + page routes)
├── zones_api.py            Blueprint: /api/zones, /carte
├── config.py               All constants (bbox, lists, colours)
├── db.py                   Database connection helper
├── validators.py           Pure validation functions
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── database/
│   ├── schema.sql          Table definitions (applied on first Docker start)
│   └── seed.sql            Minimal seed (extension only; data via scripts)
├── data/
│   ├── soil_units.geojson  ~2000 USDA SSURGO polygons (real)
│   ├── points.geojson      60 observation sites
│   └── countries.geojson   Natural Earth background layer
├── scripts/
│   ├── import_geojson.py   Loads soil_units + points into the DB
│   ├── seed_observations.py Generates simulated observations
│   └── export_geojson.py   Exports sites to data/sites.geojson
├── static/
│   ├── css/
│   │   ├── theme.css       Design system (Direction A — Soil Strata)
│   │   └── style.css       Original PDF map page CSS
│   ├── js/
│   │   ├── carte.js        Full map logic (markers, panel, toolbar, forms)
│   │   ├── map.js          Legacy map JS (for /legacy)
│   │   ├── forms.js        Legacy forms JS (for /legacy)
│   │   └── translations.js Legacy i18n (for /legacy)
│   ├── vendor/             Leaflet + Geoman served locally (no CDN)
│   └── data/
│       └── countries.geojson
├── templates/
│   ├── base.html           Shared navbar + footer (home/tables pages)
│   ├── home.html           Home page (stats, OSM preview, how it works)
│   ├── carte.html          Full standalone map page
│   ├── tables_page.html    Data tables (sites, zones, observations)
│   ├── index.html          Original PDF map page (available at /legacy)
│   ├── map_page.html       Redirects to /carte
│   └── tables_page.html    Tables page
├── tests/
│   ├── test_validators.py  81 unit tests (no DB required)
│   └── test_api.py         29 integration tests (requires Docker DB)
└── docs/
    ├── HANDOFF.md          Full technical handoff document
    ├── REPORT_NOTES.md     Architecture decisions, defence Q&A
    └── TEST_PLAN.md        Manual test checklist (P1.1–P3.5)
```

---

## Setup and run

### Prerequisites
- Docker Desktop (running)
- Python 3.15 64-bit
- Internet connection (for OSM tiles and Google Fonts)

### First-time setup

```powershell
cd soil-platform

# 1. Start the database (creates schema automatically)
docker compose up -d
docker compose ps   # wait until db shows "healthy"

# 2. Import real SSURGO data
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python scripts/import_geojson.py
python scripts/seed_observations.py

# 3. Build and start the full stack
docker compose up -d --build
```

Open **http://localhost:5000**

### Daily use
Open Docker Desktop → click ▶ on the soil-platform stack → open the browser.

### Reset the database (destroys all data)
```powershell
docker compose down -v
docker compose up -d
python scripts/import_geojson.py
python scripts/seed_observations.py
```

---

## API reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Redirects to `/home` |
| GET | `/home` | Home page |
| GET | `/carte` | Interactive map page |
| GET | `/tables` | Data tables page |
| GET | `/legacy` | Original PDF assignment map |
| GET | `/api/sites` | All approved sites (GeoJSON FeatureCollection) |
| GET | `/api/sites/<id>` | One site (GeoJSON Feature) |
| POST | `/api/sites` | Create a site |
| PUT | `/api/sites/<id>` | Update site attributes |
| PUT | `/api/sites/<id>/geometry` | Update site point geometry |
| DELETE | `/api/sites/<id>` | Delete site and its observations |
| GET | `/api/sites/<id>/observations` | Observations for a site |
| POST | `/api/sites/<id>/observations` | Add an observation |
| DELETE | `/api/observations/<id>` | Delete one observation |
| GET | `/api/zones` | All zones (simplified GeoJSON) |
| GET | `/api/zones/<id>` | One zone (full precision) |
| POST | `/api/zones` | Create a zone |
| PUT | `/api/zones/<id>` | Update zone attributes |
| PUT | `/api/zones/<id>/geometry` | Update zone polygon geometry |
| DELETE | `/api/zones/<id>` | Delete a zone |
| GET | `/api/options` | All dropdown lists + site list |
| GET | `/api/table/sites` | Paginated sites for tables page |
| GET | `/api/table/zones` | Paginated zones for tables page |
| GET | `/api/table/observations` | Paginated observations for tables page |

---

## Data sources

| Data | Source | Status |
|---|---|---|
| Soil unit polygons | USDA SSURGO (National Cooperative Soil Survey) | Real |
| Soil type names | USDA SSURGO `muname` field | Real |
| Site locations | Generated programmatically (one per SSURGO polygon) | Simulated |
| Crop assignments | Random selection from Central Valley crops | Simulated |
| Observations | Random generation with valid parameter ranges | Simulated |
| Basemap tiles | OpenStreetMap contributors | Real (live) |
| Satellite imagery | ESRI World Imagery (Maxar, USGS, USDA) | Real (live) |
| Country borders | Natural Earth 1:110m | Real |

---

## Tests

```powershell
# Unit tests — no database required (81 tests)
python -m pytest tests/test_validators.py -v

# API integration tests — Docker must be running (29 tests)
python -m pytest tests/test_api.py -v
```

All 110 tests pass on Python 3.15.2 with psycopg2-binary 2.9.13.

---

## Academic context

This project fulfils all three parts of the PDF assignment
*"Plateforme participative d'observation des sols"*:

| Part | Points | Requirement | Status |
|---|---|---|---|
| Part 1 | 10 pts | Map with ≥15 sites, OSM basemap, attribute popup | ✅ 60 sites, full popup |
| Part 2 | 6 pts | Observation form with validation, stored in DB | ✅ Full validation, history |
| Part 3 | 4 pts | Add new site by clicking map, appears immediately | ✅ With draggable marker |

The original assignment implementation remains accessible at **/legacy**.
The extended platform (home page, tables, zone digitisation, multilingual interface)
was built on top of the assignment as additional work.
