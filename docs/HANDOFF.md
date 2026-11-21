# SoilWatch — Complete Project Handoff Document
# Generated: Phase 0b complete, Phase 1 ready to start
# ============================================================

## 1. What this project is

A participatory web-mapping platform (VGI) where farmers, irrigation-association
members and technicians observe and record soil conditions (salinity, moisture,
erosion) in the Turlock irrigated perimeter, Central Valley, California.

Built with:
  - Backend:  Python 3.15.2 64-bit, Flask, psycopg2-binary, python-dotenv
  - Database: PostgreSQL 16 + PostGIS 3.4 running in Docker
  - Frontend: Leaflet 1.9.4, vanilla JavaScript, Jinja2 templates, no build step
  - Design:   Direction A "Soil Strata" — DM Serif Display + Inter, earth tones

The PDF assignment (Parts 1-3) is fully complete and still accessible at
http://localhost:5000/legacy. The new multi-page platform is built on top of it.


## 2. Environment

  Python interpreter : C:\Users\adame\AppData\Local\Programs\Python\Python315\python.exe
  Virtual environment: soil-platform\.venv
  Activate (PowerShell):
      Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
      .\.venv\Scripts\Activate.ps1

  Docker image (database): postgis/postgis:16-3.4
  Docker image (web app):  built from Dockerfile in soil-platform\
  Host ports:  Flask �� 5000,  PostgreSQL → 5433 (host) / 5432 (container)

  .env variables (never commit this file):
      POSTGRES_HOST     = localhost   (db when inside Docker)
      POSTGRES_PORT     = 5433        (5432 inside Docker)
      POSTGRES_DB       = soil_platform
      POSTGRES_USER     = soil_user
      POSTGRES_PASSWORD = soil_pass_2026


## 3. Daily workflow

  # Start everything (Docker Desktop must be running first)
  cd C:\Users\adame\Desktop\Soil_Platform\soil-platform
  docker compose up -d

  # Open the app
  http://localhost:5000

  # Run Flask locally (faster for development — no rebuild needed)
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  python app.py
  # then open http://127.0.0.1:5000

  # Run tests
  python -m pytest tests/ -v

  # Rebuild Docker image after code changes
  docker compose up -d --build


## 4. Complete file tree (every file explained)

soil-platform\
│
├── app.py                      FLASK APPLICATION — all routes
│                               Routes currently defined:
│                                 GET  /           → redirects to /home
│                                 GET  /legacy     → original PDF map (index.html)
│                                 GET  /home       → new home page (home.html)
│                                 GET  /map        → map stub (map_page.html)
│                                 GET  /tables     → tables stub (tables_page.html)
│                                 GET  /api/sites                 → GeoJSON FeatureCollection
│                                 GET  /api/sites/<id>            → one GeoJSON Feature
│                                 GET  /api/options               → all dropdown lists
│                                 GET  /api/sites/<id>/observations
│                                 POST /api/sites/<id>/observations
│                                 POST /api/sites
│                               Helpers inside app.py:
│                                 _serial(obj)         converts date/Decimal to JSON-safe
│                                 _safe_json(value)    applies _serial to one value
│                                 _row_to_dict(cur,row) zips column names + row
│                                 _build_config_json() builds CONFIG for index.html
│                                 _get_lang()          reads lang cookie (en/fr/ar)
│                                 _get_stats()         queries DB for home page counts
│
├── config.py                   SINGLE SOURCE OF TRUTH for all constants
│                               Contains:
│                                 PERIMETER_NAME = "Turlock, Californie"
│                                 MAP_CENTER_LAT = 37.46
│                                 MAP_CENTER_LON = -120.875
│                                 MAP_ZOOM       = 11
│                                 BBOX           = {lon_min:-121.05, lon_max:-120.70,
│                                                   lat_min:37.32,  lat_max:37.60}
│                                 DB_SETTINGS    = dict read from .env (for scripts)
│                                 SOIL_TEXTURES, WATER_STATUSES, SALINITY_LEVELS,
│                                 EROSION_TYPES, IRRIGATION_MODES (French values,
│                                   must match CHECK constraints in schema.sql)
│                                 CULTURES       = Central Valley crops
│                                 SOIL_TYPES     = SSURGO-inspired types
│                                 CULTURE_COLOURS = crop → hex colour dict
│                                 DEFAULT_COLOUR = "#adb5bd"
│
├── db.py                       DATABASE CONNECTION HELPER
│                               get_connection()  → opens one psycopg2 conn per request
│                               close_connection(conn) → explicit close (not GC)
│                               Reads credentials from .env via python-dotenv
│                               Raises RuntimeError (not a stack trace) if unreachable
│
├── validators.py               PURE SERVER-SIDE VALIDATION (no Flask/DB imports)
│                               validate_observation(data) → (cleaned_dict, errors_dict)
│                               validate_new_site(data, bbox) → (cleaned_dict, errors_dict)
│                               All error messages are in French
│                               Returns per-field errors dict for the API to return
│
├── Dockerfile                  Flask app container definition
│                               Base image: python:3.15-slim
│                               Copies requirements.txt, runs pip install, copies code
│                               Binds on 0.0.0.0:5000 inside the container
│                               Uses FLASK_HOST / FLASK_PORT / FLASK_ENV env vars
│
├── docker-compose.yml          Two services:
│                                 db  — postgis/postgis:16-3.4
│                                       port 5433→5432, named volume soil_db_data
│                                       mounts schema.sql + seed.sql as init scripts
│                                       healthcheck: pg_isready
│                                 web — built from Dockerfile
│                                       port 5000→5000
│                                       depends_on db (service_healthy)
│                                       env: POSTGRES_HOST=db, POSTGRES_PORT=5432
│
├── requirements.txt            Pinned Python dependencies:
│                                 Flask==3.1.0
│                                 psycopg2-binary==2.9.13
│                                 python-dotenv==1.0.1
│                                 pytest==8.3.4
│
├── .env                        Real credentials — GIT IGNORED, never commit
├── .env.example                Template with placeholder values
├── .gitignore                  Excludes .env, .venv/, __pycache__/, data/sites.geojson
├── .dockerignore               Excludes .env, .venv/, __pycache__/ from Docker image
│
├── database\
│   ├── schema.sql              Applied on first Docker start (01_schema.sql)
│   │                           Creates tables: sites, observations
│   │                           Indexes: idx_sites_geom (GIST), idx_observations_site
│   │                           CHECK constraints on observations match config.py lists
│   │
│   └── seed.sql                Applied on first Docker start (02_seed.sql)
│                               Currently inserts 18 Chott Mariem sites + 12 observations
│                               WILL BE REPLACED in Phase 1 — seed will clear this
│                               and import data from scripts instead
│
├── data\                       GeoJSON data files (DO NOT read in Flask — too large)
│   ├── soil_units.geojson      ~2000 real USDA SSURGO soil polygons
│   │                           Properties: mupolygonkey, mukey, musym, muname, data_source
│   │
│   ├── points.geojson          60 observation sites (real locations, some simulated attrs)
│   │                           Properties: name, soil_type (real SSURGO), culture, mukey,
│   │                                       data_source
│   │
│   ├── countries.geojson       Natural Earth country polygons (property: name)
│   │                           Used as a background layer on the map
│   │
│   └── wells.geojson           DO NOT USE — excluded from the project
│
├── scripts\
│   ├── export_geojson.py       Exports sites from DB to data/sites.geojson
│   │                           Uses only json + psycopg2, no pandas
│   │                           Run: python scripts/export_geojson.py
│   │
│   ├── import_geojson.py       TO CREATE IN PHASE 1
│   │                           Clears sites/zones/observations, imports soil_units.geojson
│   │                           and points.geojson into the DB
│   │                           Uses config.DB_SETTINGS for connection
│   │                           Expected output: ~2000 zones, 60 sites
│   │
│   └── seed_observations.py    TO CREATE IN PHASE 1
│                               Creates 1-3 simulated observations for ~45 random sites
│                               contributor_name='Démo', dates last 6 months
│                               pH 5.5-8.5, CE 0.3-6, MO 0.5-4%, remark="Donnée simulée"
│
├── templates\
│   ├── base.html               BASE TEMPLATE — all pages extend this
│   │                           Contains:
│   │                             - Google Fonts: DM Serif Display + Inter
│   │                             - Navbar: SVG logo mark (stacked soil strata layers),
│   │                               links: Accueil/Carte/Tables, language switcher,
│   │                               Login button (or user email + Logout when Phase 3 done)
│   │                             - Footer: copyright, data source note, OSM credit
│   │                             - Toast container (#toast-container)
│   │                             - setLang(code) JS function: sets cookie, reloads page
│   │                             - showToast(msg, type, duration) shared helper
│   │                           Jinja variables expected:
│   │                             lang         — 'en', 'fr', or 'ar' (from cookie)
│   │                             current_user — None or {id, email, role} (Phase 3)
│   │                           Blocks: title, head, content, scripts
│   │
│   ├── home.html               HOME PAGE (extends base.html)
│   │                           Hero layout:
│   │                             Left col: non-interactive Leaflet map preview
│   │                                       (CARTO Voyager tiles, Turlock centre)
│   │                             Right col: title, subtitle, 2×2 stat grid, CTA buttons
│   │                           Stats grid uses {{ stats.zones/sites/observations/contributors }}
│   │                           passed from _get_stats() in app.py
│   │                           Below hero: 3-step explainer with circular numbered steps
│   │                           Translated via PAGE_STRINGS object in inline <script>
│   │                           All text uses data-i18n attributes
│   │
│   ├── map_page.html           MAP PAGE STUB (extends base.html)
│   │                           Just shows "Coming in Phase 2"
│   │                           Will be fully replaced in Phase 2
│   │
│   ├── tables_page.html        TABLES PAGE STUB (extends base.html)
│   │                           Just shows "Coming in Phase 5"
│   │
│   ├── index.html              ORIGINAL PDF MAP PAGE (Phase 1-3 PDF project)
│   │                           Still works at /legacy
│   │                           Uses window.CONFIG injected by Flask
│   │                           Loads translations.js, map.js, forms.js
│   │
│   └── [login.html]            TO CREATE IN PHASE 3
│       [register.html]         TO CREATE IN PHASE 3
│
├── static\
│   ├── css\
│   │   ├── theme.css           DESIGN SYSTEM (Direction A — Soil Strata)
│   │   │                       CSS custom properties (tokens):
│   │   │                         --soil-dark #2C1A0E  deep topsoil, navbar bg
│   │   │                         --soil-mid  #8B5E3C  subsoil, accents
│   │   │                         --clay      #C4956A  warm mid-tone
│   │   │                         --silt      #E8D5B0  card backgrounds
│   │   │                         --water     #3A7CA5  primary CTA, links
│   │   │                         --surface   #F5F0E8  page background
│   │   │                       Components: navbar, footer, buttons (.btn-primary /
│   │   │                         -secondary / -danger / -ghost / -sm / -lg),
│   │   │                         form controls (.form-control, .field-error),
│   │   │                         cards (.card, .stat-card), badges, tables,
│   │   │                         toasts (.toast, .toast-success, .toast-error),
│   │   │                         modal (.modal-overlay, .modal-box),
│   │   │                         alerts (.alert-error / -success / -info)
│   │   │                       Badge semantics:
│   │   │                         .badge-absente / .badge-aucune  → green
│   │   │                         .badge-traces / .badge-en-nappe → amber
│   │   │                         .badge-crouts / .badge-rigoles /
│   │   │                           .badge-ravines                → red
│   │   │                         .badge-water / .badge-irrigation → blue
│   │   │                       RTL support for Arabic (dir="rtl")
│   │   │                       Google Fonts imported at top of file
│   │   │
│   │   └── style.css           ORIGINAL CSS for the PDF map page (index.html / /legacy)
│   │                           Still used by index.html. Do not delete.
│   │
│   ├── js\
│   │   ├── translations.js     CLIENT-SIDE i18n for the original map page (/legacy)
│   │   │                       T(key) function returns string in currentLang
│   │   │                       applyLanguage(code) swaps data-i18n elements + RTL
│   │   │                       Saves language to localStorage
│   │   │                       NOTE: the new multi-page app uses server-side language
│   │   │                       (cookie + Jinja), not this file
│   │   │
│   │   ├── map.js              Leaflet map logic for /legacy
│   │   │                       Initialises map from window.CONFIG
│   │   │                       OSM + Esri Satellite basemaps with layer control
│   │   │                       Saves selected basemap to localStorage
│   │   │                       Circle markers coloured by culture
│   │   │                       Popup with observation history
│   │   │                       Sidebar site list with search
│   │   │                       Add-site mode (crosshair, draggable marker, bbox rect)
│   │   │                       Exposes: window.refreshSitePopup, window.onNewSiteSaved,
│   │   │                                window.addSiteToObsDropdown, window.onLanguageChange
│   │   │
│   │   ├── forms.js            Form logic for /legacy
│   │   │                       Loads /api/options on page load
│   │   │                       Observation form modal: open, validate, POST, toast
│   │   │                       Add-site form: POST /api/sites
│   │   │                       Uses T() from translations.js for error messages
│   │   │
│   │   └── carte.js            (Extra file found — may be an experiment, review before Phase 2)
│   │
│   └── data\
│       └── countries.geojson   Static copy of countries data served directly by Flask
│                               (also exists in data\ — keep both for now)
│
├── tests\
│   ├── __init__.py             Makes tests\ a Python package
│   ├── test_validators.py      81 unit tests for validators.py (no DB needed)
│   │                           All passed: boundary values, NaN, future dates, etc.
│   └── test_api.py             29 integration tests (needs Docker DB running)
│                               All passed: including coordinate-order test,
│                               accent round-trip, cleanup fixtures with TEST_ prefix
│
├── docs\
│   ├── REPORT_NOTES.md         Architecture decisions, data flows, defence Q&A
│   ├── TEST_PLAN.md            Manual checklist for all 3 PDF phases (P1.1-P3.5)
│   └── HANDOFF.md              THIS FILE
│
├── make_sites.py               (Extra file — appears to be a data preparation script,
│                                review before Phase 1)
└── prepare_data.py             (Extra file — appears to be a data preparation script,
                                 review before Phase 1)


## 5. Database schema (current state)

Tables that exist NOW (from schema.sql + seed.sql):

  sites
    id           SERIAL PK
    name         TEXT NOT NULL
    culture      TEXT NOT NULL
    soil_type    TEXT NOT NULL
    geom         geometry(Point, 4326) NOT NULL
    created_at   TIMESTAMP DEFAULT now()
    status       TEXT DEFAULT 'approved' CHECK (status IN ('pending','approved'))

  observations
    id                 SERIAL PK
    site_id            INTEGER FK → sites(id) ON DELETE CASCADE
    contributor_name   TEXT NOT NULL
    observation_date   DATE NOT NULL
    soil_texture       TEXT NOT NULL  CHECK (matches SOIL_TEXTURES in config.py)
    water_status       TEXT NOT NULL  CHECK (matches WATER_STATUSES)
    salinity           TEXT NOT NULL  CHECK (matches SALINITY_LEVELS)
    erosion            TEXT NOT NULL  CHECK (matches EROSION_TYPES)
    culture            TEXT NOT NULL
    irrigation_mode    TEXT NOT NULL  CHECK (matches IRRIGATION_MODES)
    ph                 NUMERIC(4,2)   CHECK (0 ≤ ph ≤ 14) — optional
    ec_dsm             NUMERIC(6,2)   CHECK (ec_dsm ≥ 0) — optional
    organic_matter_pct NUMERIC(5,2)   CHECK (0 ≤ pct ≤ 100) — optional
    remark             TEXT — optional
    created_at         TIMESTAMP DEFAULT now()

Tables TO ADD in Phase 1 migration (database/02_migration.sql):

  users
    id            SERIAL PK
    email         TEXT NOT NULL UNIQUE
    password_hash TEXT NOT NULL
    role          TEXT DEFAULT 'user' CHECK (role IN ('user','admin'))
    created_at    TIMESTAMP DEFAULT now()

  zones
    id          SERIAL PK
    name        TEXT NOT NULL
    zone_type   TEXT DEFAULT 'unité de sol'
    description TEXT
    mukey       TEXT
    musym       TEXT
    source      TEXT
    geom        geometry(MultiPolygon, 4326) NOT NULL
    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL
    created_at  TIMESTAMP DEFAULT now()
    CONSTRAINT zones_valid CHECK (ST_IsValid(geom))
    INDEX: zones_geom_idx USING GIST (geom)

  ALTER sites ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id)
  ALTER sites ADD COLUMN IF NOT EXISTS mukey TEXT
  ALTER sites ADD COLUMN IF NOT EXISTS source TEXT
  ALTER observations ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id)


## 6. API endpoints (current state)

  GET  /api/sites
       Returns all approved sites as GeoJSON FeatureCollection
       Properties: id, name, culture, soil_type, observation_count,
                   last_observation_date (YYYY-MM-DD or null)

  GET  /api/sites/<id>
       Returns one site as GeoJSON Feature, or 404

  GET  /api/options
       Returns all dropdown lists + sites list for forms
       Keys: sites, cultures, soilTypes, soilTextures, waterStatuses,
             salinityLevels, erosionTypes, irrigationModes

  GET  /api/sites/<id>/observations
       Returns observations newest first, or 404

  POST /api/sites/<id>/observations
       Body: JSON with observation fields (see validators.py)
       Returns 201 + new record, or 400 + per-field French errors

  POST /api/sites
       Body: {name, culture, soil_type, longitude, latitude}
       Returns 201 + GeoJSON Feature, or 400

  Error shape always: {"error": "...", "errors": {"field": "message"}}


## 7. Phase 1 — what you need to build

STEP 1: Create database/02_migration.sql
  Copy the SQL from section 5 above (users, zones, ALTER sites/observations).
  Run it against the running container:
    docker compose exec db psql -U soil_user -d soil_platform \
      -f /path/inside/container
  Or copy the file into the container first, or use:
    docker compose exec -T db psql -U soil_user -d soil_platform \
      < database/02_migration.sql

STEP 2: Update database/schema.sql
  Add all new tables/columns so a fresh install creates everything at once.
  Keep the existing sites/observations definitions, add users, zones, ALTERs.

STEP 3: Update database/seed.sql
  Remove the 18 Chott Mariem site inserts and 12 observation inserts.
  Seed should now only create the PostGIS extension and nothing else
  (data comes from the import scripts).

STEP 4: Create scripts/import_geojson.py
  Exact reference code is in the Phase 1 section of the original prompt:

    import json, psycopg2
    from config import DB_SETTINGS

    def load(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["features"]

    conn = psycopg2.connect(**DB_SETTINGS)
    cur = conn.cursor()
    cur.execute("TRUNCATE observations, sites, zones RESTART IDENTITY CASCADE")

    for f in load("data/soil_units.geojson"):
        p = f["properties"]
        cur.execute("""
            INSERT INTO zones (name, zone_type, description, mukey, musym, source, geom)
            VALUES (%s, 'unité de sol', %s, %s, %s, %s,
                    ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))))
        """, (
            p.get("muname") or "non renseigné",
            "Symbole : " + str(p.get("musym")),
            p.get("mukey"), p.get("musym"), p.get("data_source"),
            json.dumps(f["geometry"])
        ))

    for f in load("data/points.geojson"):
        p = f["properties"]
        cur.execute("""
            INSERT INTO sites (name, culture, soil_type, mukey, source, geom)
            VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
        """, (
            p["name"],
            p.get("culture") or "non renseigné",
            p.get("soil_type") or "non renseigné",
            p.get("mukey"), p.get("data_source"),
            json.dumps(f["geometry"])
        ))

    conn.commit()
    # Print counts
    cur.execute("SELECT count(*) FROM zones"); print("Zones:", cur.fetchone()[0])
    cur.execute("SELECT count(*) FROM sites"); print("Sites:", cur.fetchone()[0])
    conn.close()

STEP 5: Create scripts/seed_observations.py
  For ~45 random sites create 1-3 observations each:
    - contributor_name = 'Démo'
    - observation_date = random date in the last 6 months
    - soil_texture, water_status, salinity, erosion, culture, irrigation_mode:
        pick randomly from the lists in config.py
    - ph between 5.5 and 8.5
    - ec_dsm between 0.3 and 6.0
    - organic_matter_pct between 0.5 and 4.0
    - Some rows should have ph/ec_dsm/organic_matter_pct = None
    - remark = "Donnée simulée"
    - created_by = None (reference data)

STEP 6: Reset and import commands
  docker compose down -v                              # destroys ALL data
  docker compose up -d                               # recreates with new schema+seed
  python scripts/import_geojson.py                  # loads ~2000 zones + 60 sites
  python scripts/seed_observations.py               # adds ~45-135 simulated obs

STEP 7: Update /api/sites response
  Add created_by and mukey to the properties returned by get_sites() and get_site()

STEP 8: Update /api/options
  Add a zones list [{id, name}] for future use in forms

STEP 9: Verify
  docker compose exec db psql -U soil_user -d soil_platform \
    -c "SELECT count(*) FROM zones;"              -- expect ~2000
  docker compose exec db psql -U soil_user -d soil_platform \
    -c "SELECT count(*) FROM sites;"              -- expect 60
  docker compose exec db psql -U soil_user -d soil_platform \
    -c "SELECT count(*) FROM observations;"       -- expect 45-135


## 8. Phase roadmap

  Phase 0b (DONE):  Design system (theme.css, base.html, home.html, stubs)
  Phase 1:          Database migration + real SSURGO data import (see section 7)
  Phase 2:          /api/zones endpoint + full map page (Leaflet, zones layer,
                    side panel, search, CARTO basemap)
  Phase 3:          Authentication (users table, login/register/logout,
                    session cookie, login_required decorator, auth.py helper)
  Phase 4:          Digitize/edit/delete (Leaflet-Geoman, PUT/DELETE endpoints,
                    permissions via can_modify())
  Phase 5:          Tables page (tabs Sites/Zones/Observations, server-side
                    pagination, inline edit, CSV export)
  Final:            Updated README + REPORT_NOTES + focused tests


## 9. Key rules (never break these)

  - All SQL uses %s parameterized queries. Never f-strings or concatenation in SQL.
  - Geometry inserts: ST_MakePoint(longitude, latitude) — longitude FIRST (X=lon, Y=lat).
  - Zones: ST_Multi(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))
  - Open one DB connection per request, close it in a finally block.
  - Never send stack traces, SQL text, or credentials to the browser.
  - All user text into the DOM via textContent, never innerHTML.
  - config.py is the single source of truth — never duplicate lists or bbox in JS.
  - Language is set server-side via cookie (new pages) or client-side localStorage
    (legacy map page only).
  - pandas / GeoPandas are NOT imported in app.py or any server route.
    They may only be used in standalone scripts with a separate requirements file.
  - .env is git-ignored. Credentials never in source code.
  - New pages must extend base.html and use theme.css components only.
  - Badge classes follow the semantic naming in section 4 (theme.css).


## 10. Important file notes

  make_sites.py and prepare_data.py
    These were found in the project root. They appear to be one-off data
    preparation scripts. Review their content before Phase 1 — if they
    duplicate what import_geojson.py will do, delete them. If they contain
    useful transformation logic, copy what you need into import_geojson.py.

  static/js/carte.js and templates/carte.html
    Also found in the project. These appear to be an earlier experiment.
    Review before Phase 2 — if the map logic is useful, incorporate it.
    Otherwise delete both to avoid confusion.

  static/data/countries.geojson
    A second copy of countries.geojson is in static/data/.
    Flask serves static files directly. For Phase 2, serve this as a
    static file: fetch("/static/data/countries.geojson") in the map JS.


## 11. Test status (last run)

  tests/test_validators.py  81 tests  ALL PASSED  (no DB needed)
  tests/test_api.py         29 tests  ALL PASSED  (needs Docker DB)

  After Phase 1 (data reset), re-run test_api.py.
  The test for >= 18 sites will need updating to >= 60.
  The coordinate-order and accent round-trip tests are still valid.
