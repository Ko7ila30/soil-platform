# Test Plan — Participative Soil Observation Platform

Manual checklist for each phase.
Run these after starting Docker and Flask (see README.md).

Status values: ✅ Pass | ❌ Fail | ⏳ Not yet tested

---

## Phase 1 — Visualisation and query

| ID   | PDF Part | Action | Expected result | Status |
|------|----------|--------|-----------------|--------|
| P1.1a | Part 1 | Run `docker compose up -d` then `docker compose ps` | Service `db` shows status `healthy` | ⏳ |
| P1.1b | Part 1 | Run `docker compose exec db psql -U soil_user -d soil_platform -c "SELECT PostGIS_Version();"` | PostGIS version string is printed | ⏳ |
| P1.1c | Part 1 | Run `docker compose exec db psql -U soil_user -d soil_platform -c "SELECT count(*) FROM sites;"` | Returns 18 | ⏳ |
| P1.1d | Part 1 | Run `docker compose exec db psql -U soil_user -d soil_platform -c "SELECT count(*) FROM observations;"` | Returns 12 | ⏳ |
| P1.2a | Part 1 | Open browser: `http://127.0.0.1:5000/api/sites` | JSON with `"type": "FeatureCollection"` and 18 features | ⏳ |
| P1.2b | Part 1 | In the JSON, check the first feature's properties | Contains `id`, `name`, `culture`, `soil_type`, `observation_count`, `last_observation_date` | ⏳ |
| P1.3a | Part 1 | Open `http://127.0.0.1:5000/` | Page loads without errors; map fills most of the screen | ⏳ |
| P1.3b | Part 1 | Check the basemap | OpenStreetMap tiles visible; OSM attribution shown | ⏳ |
| P1.3c | Part 1 | Check map controls | Zoom buttons and scale bar visible | ⏳ |
| P1.4a | Part 1 | Inspect the markers on the map | Sites appear as coloured circles; different colours for different crops | ⏳ |
| P1.4b | Part 1 | Inspect the legend | Legend panel visible (bottom-right), lists culture names with matching colours | ⏳ |
| P1.5a | Part 1 | Click any site marker | Popup opens showing: identifiant, nom, culture, type de sol, nombre d'observations, dernière observation | ⏳ |
| P1.5b | Part 1 | Click "Parcelle Béjaoui Nord" | Popup shows observation count ≥ 2, dernière observation date shown | ⏳ |
| P1.6a | Part 1 | Type "béjaoui" in the search box | List filters to show only "Parcelle Béjaoui Nord" and "Parcelle Béjaoui Sud" | ⏳ |
| P1.6b | Part 1 | Click a site in the sidebar list | Map zooms to that site and its popup opens | ⏳ |
| P1.6c | Part 1 | Clear the search box | All sites reappear in the list | ⏳ |
| P1.7a | Part 1 | Stop Docker (`docker compose stop`) then refresh the page | French error message appears in the sidebar (no stack trace, no raw SQL) | ⏳ |
| P1.7b | Part 1 | Restart Docker and refresh | Sites load normally again | ⏳ |
| P1.8a | Part 1 | With Docker running, activate venv and run `python scripts/export_geojson.py` | Prints "Exported 18 site(s) to data/sites.geojson" | ⏳ |
| P1.8b | Part 1 | Open `data/sites.geojson` | Valid GeoJSON FeatureCollection; accented characters correct (é, è, â, ç) | ⏳ |

---

## Phase 2 — Observation form

| ID   | PDF Part | Action | Expected result | Status |
|------|----------|--------|-----------------|--------|
| P2.1a | Part 2 | Click any site marker; click "Ajouter une observation" in the popup | Observation form modal opens; site is pre-selected in the dropdown | ⏳ |
| P2.1b | Part 2 | In the form, change the site dropdown | Form is re-bound to the new site | ⏳ |
| P2.2a | Part 2 | Submit the form with all fields empty | Error messages appear next to every required field | ⏳ |
| P2.2b | Part 2 | Fill all required fields correctly and submit | Form submits (201); success toast appears | ⏳ |
| P2.3a | Part 2 | Open the form; inspect the select dropdowns | All dropdowns populated (textures, water, salinity, erosion, culture, irrigation) | ⏳ |
| P2.4a | Part 2 | Enter pH = 15 and submit | Server returns 400; "Le pH doit être compris entre 0 et 14" appears next to pH field | ⏳ |
| P2.4b | Part 2 | Enter a future date and submit | Server returns 400; date error message shown | ⏳ |
| P2.5a | Part 2 | Submit a valid observation; refresh the page | The observation is still visible in the popup history | ⏳ |
| P2.6a | Part 2 | Submit a valid observation | Toast "Observation enregistrée" appears; form resets; popup updates without page reload | ⏳ |
| P2.6b | Part 2 | After submitting, check the popup's observation count | Count has increased by 1 | ⏳ |
| P2.7a | Part 2 | Click a site with 2+ observations | Popup history shows all observations, newest first | ⏳ |
| P2.7b | Part 2 | In the history, find an observation with optional fields | pH / CE / matière organique / remarque all displayed correctly | ⏳ |

---

## Phase 3 — Add a new site

| ID   | PDF Part | Action | Expected result | Status |
|------|----------|--------|-----------------|--------|
| P3.1a | Part 3 | Click "Ajouter un site" button | Cursor changes to crosshair; yellow hint banner appears at top of map | ⏳ |
| P3.1b | Part 3 | In add mode, inspect the map | Dashed orange rectangle showing the allowed bounding box is visible | ⏳ |
| P3.2a | Part 3 | Click anywhere inside the bbox | A draggable marker appears; the add-site form panel opens in the bottom-right | ⏳ |
| P3.2b | Part 3 | Drag the marker to a new position | Latitude and longitude fields in the form update in real time | ⏳ |
| P3.3a | Part 3 | Fill the form and click "Enregistrer" | Site saved; 201 response | ⏳ |
| P3.3b | Part 3 | Click outside the bbox (move marker outside the orange rectangle) and submit | Server returns 400; French error "en dehors du périmètre" shown in form | ⏳ |
| P3.3c | Part 3 | Leave "Nom du site" blank and submit | Error message shown next to the name field | ⏳ |
| P3.4a | Part 3 | After saving a new site, check the map | New coloured marker appears at the clicked location, no page reload | ⏳ |
| P3.4b | Part 3 | Click the new site's marker | Popup opens with correct name, culture, soil type | ⏳ |
| P3.4c | Part 3 | Check the sidebar search | New site appears in the list and is searchable by name | ⏳ |
| P3.4d | Part 3 | Open the observation form | New site appears in the site dropdown | ⏳ |
| P3.4e | Part 3 | Refresh the page | New site is still on the map (persisted in DB) | ⏳ |
| P3.5a | Part 3 | Enter add mode; click "Annuler" | Temporary marker removed; crosshair gone; bbox rectangle removed; add-mode banner gone | ⏳ |
| P3.5b | Part 3 | Enter add mode; save a site | Add mode exits automatically after save | ⏳ |
