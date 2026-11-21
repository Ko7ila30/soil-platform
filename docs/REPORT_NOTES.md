# Report Notes — Participative Soil Observation Platform

This document is the written companion for the oral defence. It explains every
architecture decision, data flow, and file so you can answer questions confidently.
All data in this project is simulated.

---

## 1. Architecture choices

### Why Flask instead of GeoServer / WFS-T?
The PDF allows either a small server (Flask, Node.js, PHP) or WFS-T. Flask was
chosen because:
- It requires very few lines of code for our endpoints.
- It is easy to debug (readable Python, `flask --debug`).
- It has no complex configuration (no XML, no layer publishing, no CORS setup).
- Students can read and explain every line.

GeoServer/WFS-T has no server-side code, but its configuration is "often
tricky" (the PDF's own words): write permissions, security, CORS headers.

### Why PostgreSQL + PostGIS instead of a GeoJSON file only?
- PostGIS stores geometry in a spatially indexed column; spatial queries
  (bounding box, nearest neighbour) are fast even with thousands of records.
- The relational model lets us link observations to sites with a foreign key,
  enforcing integrity (no orphan observations).
- SQL queries with `ST_AsGeoJSON` produce valid GeoJSON directly.
- The PDF explicitly asks for a spatial database.

### Why Docker for PostgreSQL?
- Avoids installing PostgreSQL on the host machine.
- Everyone gets the exact same PostGIS version (`postgis/postgis:16-3.4`).
- The database is isolated; stopping the container leaves the host clean.
- A named volume keeps data between restarts.

### Why Leaflet 1.9.4 and not OpenLayers?
The PDF suggests Leaflet as the simpler option. Leaflet's API is small and
readable; the student can explain every call. OpenLayers is more powerful but
much larger and more complex.

### Why EPSG:4326 (WGS84)?
- GPS receivers output WGS84 coordinates.
- Leaflet works in WGS84 by default.
- OpenStreetMap tiles use Web Mercator (3857) for display, but Leaflet
  reprojects internally — we never need to touch EPSG:3857.
- The PDF specifies WGS84.

### Why longitude before latitude in ST_MakePoint?
PostGIS follows the mathematical convention: X (east-west = longitude) before
Y (north-south = latitude). Leaflet does the opposite: `L.latLng(lat, lon)`.
This is a common source of bugs. Comments in `app.py` and `validators.py`
flag every place this order matters.

---

## 2. Data model

```
sites
  id          SERIAL PK
  name        TEXT NOT NULL
  culture     TEXT NOT NULL
  soil_type   TEXT NOT NULL
  geom        geometry(Point, 4326)  — WGS84 point
  created_at  TIMESTAMP DEFAULT now()
  status      TEXT DEFAULT 'approved'  — 'pending' reserved for bonus 3

observations
  id                 SERIAL PK
  site_id            INTEGER FK → sites(id) ON DELETE CASCADE
  contributor_name   TEXT NOT NULL
  observation_date   DATE NOT NULL
  soil_texture       TEXT (CHECK constraint)
  water_status       TEXT (CHECK constraint)
  salinity           TEXT (CHECK constraint)
  erosion            TEXT (CHECK constraint)
  culture            TEXT NOT NULL
  irrigation_mode    TEXT (CHECK constraint)
  ph                 NUMERIC(4,2) optional
  ec_dsm             NUMERIC(6,2) optional
  organic_matter_pct NUMERIC(5,2) optional
  remark             TEXT optional
  created_at         TIMESTAMP DEFAULT now()
```

The `ON DELETE CASCADE` means: if a site is deleted, all its observations are
automatically deleted too. This keeps the database consistent.

The `CHECK` constraints on `observations` enforce the same values as
`config.py`. Both files carry a "KEEP IN SYNC" comment.

---

## 3. Data flows

### 3.1 Load the map (Phase 1)

```
Browser                    Flask                       PostGIS
  │                          │                            │
  ├─ GET / ────────────────▶ │                            │
  │                          │  render index.html         │
  │                          │  inject CONFIG JSON        │
  │◀──────────────────────── │                            │
  │  (page loads, Leaflet    │                            │
  │   initialises the map)   │                            │
  │                          │                            │
  ├─ GET /api/sites ────────▶│                            │
  │                          ├─ SELECT … ST_AsGeoJSON … ▶│
  │                          │◀──────────────────────────┤
  │                          │  assemble FeatureCollection│
  │◀──────────────────────── │                            │
  │  GeoJSON → circleMarkers │                            │
  │  + legend + site list    │                            │
```

### 3.2 Submit an observation (Phase 2)

```
Browser                    Flask (validators.py + app.py)   PostGIS
  │                               │                            │
  │  User fills form              │                            │
  │  JS validates client-side     │                            │
  │                               │                            │
  ├─ POST /api/sites/3/obs ──────▶│                            │
  │  JSON body                    │  validate_observation()    │
  │                               │  (pure Python, no DB)      │
  │                               │                            │
  │                        errors?│                            │
  │◀─── 400 + errors dict ────────│                            │
  │  display next to fields       │                            │
  │                               │                            │
  │                        valid? │                            │
  │                               ├─ INSERT INTO observations ▶│
  │                               │◀──────────────────────────┤
  │◀─── 201 + new record ─────────│                            │
  │  toast + reset form           │                            │
  │  refresh popup (GET site +    │                            │
  │  GET observations)            │                            │
```

### 3.3 Add a new site (Phase 3)

```
Browser                    Flask (validators.py + app.py)   PostGIS
  │                               │                            │
  │  Click "Ajouter un site"      │                            │
  │  add-mode: crosshair cursor   │                            │
  │  bbox rectangle on map        │                            │
  │                               │                            │
  │  Click on map                 │                            │
  │  → draggable marker appears   │                            │
  │  → short form opens           │                            │
  │                               │                            │
  │  Fill form, click Enregistrer │                            │
  ├─ POST /api/sites ────────────▶│                            │
  │  {name, culture, soil_type,   │  validate_new_site()       │
  │   longitude, latitude}        │  bbox check                │
  │                               │                            │
  │                        valid? │                            │
  │                               ├─ INSERT INTO sites         │
  │                               │  ST_SetSRID(               │
  │                               │   ST_MakePoint(lon, lat),  │
  │                               │   4326)                   ▶│
  │                               │◀──────────────────────────┤
  │◀─── 201 + GeoJSON Feature ────│                            │
  │  new circleMarker on map      │                            │
  │  added to list + dropdown     │                            │
  │  add-mode exits               │                            │
```

---

## 4. File-by-file guide

| File | What it does | Key things to know |
|---|---|---|
| `app.py` | Flask routes + JSON helpers | One connection per request; explicit close; no stack traces to browser |
| `config.py` | All constants | Single source of truth for lists, colours, bbox, centre |
| `db.py` | DB connection | Reads `.env`; raises `RuntimeError` on failure; explicit `close_connection` |
| `validators.py` | Pure validation | No Flask/DB imports; returns `(cleaned, errors)`; French error messages |
| `docker-compose.yml` | PostGIS container | Port 5433; named volume; init scripts mounted |
| `database/schema.sql` | Tables + indexes | CHECK constraints must match config.py lists |
| `database/seed.sql` | 18 sites + 12 obs | All simulated; sites by name in obs inserts |
| `templates/index.html` | Single page | CONFIG injected by Flask; no hard-coded values |
| `static/css/style.css` | Layout + components | Header + sidebar + map; modal; toast; legend |
| `static/js/map.js` | Leaflet map | Markers by culture colour; popup with history; site list; add-mode |
| `static/js/forms.js` | Forms logic | Loads options from API; validates; POSTs; shows errors + toast |
| `scripts/export_geojson.py` | Export tool | Pure Python; writes data/sites.geojson; run on demand |
| `tests/test_validators.py` | Unit tests | No DB needed; boundary values for every rule |
| `tests/test_api.py` | API tests | Needs Docker DB; TEST_ prefix + cleanup fixture |

---

## 5. Screenshots to take (for the report)

1. Map with all 18 seed sites, legend visible, sidebar showing the site list.
2. A site popup with attributes and at least one observation in the history.
3. The observation form open and filled in.
4. The observation form showing a validation error (e.g. pH > 14).
5. The success toast after submitting an observation.
6. Add-site mode: crosshair cursor, bbox rectangle, short form with coords.
7. The new site on the map after saving.

---

## 6. Likely defence questions and short answers

**Q: What is VGI (information géographique volontaire)?**
A: Volunteered Geographic Information — spatial data contributed by ordinary
people (not professional surveyors). Farmers, GDA members or technicians
submit observations through the web interface. The platform aggregates them
into a shared dataset.

**Q: Why validate data on the server if you already validate in the browser?**
A: Browser validation can be bypassed (curl, Postman, modified JavaScript).
Server-side validation in `validators.py` is the authoritative check; it
protects the database regardless of how the request was made.

**Q: What is a GeoJSON FeatureCollection?**
A: A JSON object with `"type": "FeatureCollection"` and a `"features"` array.
Each feature has a `"geometry"` (coordinates) and `"properties"` (attributes).
Leaflet can display a FeatureCollection directly.

**Q: Why SRID 4326?**
A: SRID 4326 is the EPSG code for WGS84 — the coordinate system used by GPS
and OpenStreetMap. Storing geometry in 4326 means coordinates are plain
longitude/latitude degrees, easy to understand and exchange.

**Q: Why is longitude before latitude in ST_MakePoint?**
A: PostGIS follows the mathematical convention (X before Y). X is the
horizontal axis = longitude. Y is the vertical axis = latitude. Leaflet does
the opposite (`L.latLng(lat, lon)`). We always pass longitude first to
`ST_MakePoint` and add a comment explaining why.

**Q: What would you change for a production deployment?**
A: (1) Add user authentication. (2) Use a connection pool instead of
per-request connections. (3) Serve through NGINX with HTTPS. (4) Restrict
CORS. (5) Store credentials in a secrets manager. (6) Add rate limiting.

**Q: What are the limits of simulated data?**
A: The coordinates are plausible but not field-verified. The measurement values
(pH, CE, organic matter) are invented. A real project would require GPS-measured
sites and actual lab analyses.

**Q: What does the bbox check do and why is it important?**
A: It rejects new sites with coordinates outside the configured bounding box
(lon 10.50–10.62, lat 35.88–35.96). This prevents users from adding sites
in another country or in the sea, keeping the dataset geographically coherent.
