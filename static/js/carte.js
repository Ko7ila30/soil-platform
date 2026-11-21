/**
 * carte.js — Full interactive map for SoilWatch.
 *
 * Features:
 *   - OSM + CARTO Voyager basemaps (layer control)
 *   - Countries overlay (background, non-interactive)
 *   - Zones layer (SSURGO polygons, hover highlight, click -> panel)
 *   - Sites layer (circle markers, click -> panel with obs history)
 *   - Side panel: attributes, action buttons, observation history
 *   - Add site: click map -> draggable marker -> form -> POST /api/sites
 *   - Draw zone: Leaflet-Geoman polygon -> form -> POST /api/zones
 *   - Edit geometry: Geoman drag mode -> PUT /api/sites/<id>/geometry or /api/zones/<id>/geometry
 *   - Edit attributes: inline form -> PUT /api/sites/<id> or /api/zones/<id>
 *   - Delete: confirm modal -> DELETE /api/sites/<id> or /api/zones/<id>
 *   - Add observation: modal form -> POST /api/sites/<id>/observations
 *   - Search: filters sites + zones by name
 *
 * BBOX_CONFIG, MAP_CENTER, MAP_ZOOM are injected by Flask in carte.html.
 * All user text uses textContent or esc() — never raw innerHTML with user data.
 */
"use strict";

// window.MS is set by the inline <script> in carte.html before this file loads.
// Falls back to English if not set.
var MS = window.MS || {
  hintAddSite:  "Click on the map to place a new site.",
  hintDrawZone: "Draw a polygon on the map, then fill in the form.",
  hintEditGeom: "Drag a site marker or zone vertex to edit geometry.",
  cancel: "Cancel", save: "Save", addObs: "+ Add Observation",
  editAttr: "Edit Attributes", deleteBtn: "Delete",
  obsHistory: "Observation history", noObs: "No observations yet.",
  confirmDel: "Confirm deletion", drawFirst: "Draw a polygon on the map first.",
  clickFirst: "Click the map to place a point first.",
  legendSites: "Sites by crop", legendZones: "Soil units (USDA SSURGO)",
};

/** Escape user text before inserting into HTML. Prevents XSS. */
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}
function $id(id) { return document.getElementById(id); }
function todayISO() {
  var d = new Date();
  return d.getFullYear() + "-"
    + String(d.getMonth()+1).padStart(2,"0") + "-"
    + String(d.getDate()).padStart(2,"0");
}

// ---- Map init --------------------------------------------------------------

var map = L.map("map", {
  preferCanvas: true,   // faster rendering for ~2000 zone polygons
  zoomControl: false
}).fitBounds([BBOX_CONFIG.sw, BBOX_CONFIG.ne]);

L.control.zoom({ position: "bottomright" }).addTo(map);
L.control.scale({ position: "bottomleft", imperial: false }).addTo(map);

// OSM basemap — free, no API key, attribution required, DEFAULT
var osm = L.tileLayer(
  "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  { maxZoom: 19, attribution: "\u00a9 <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors" }
).addTo(map);   // addTo(map) makes this the active/checked basemap

// ESRI World Imagery (satellite) — free, no API key required
var esriSatellite = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    maxZoom: 19,
    attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN"
  }
);

// ---- Colour helpers --------------------------------------------------------

var PALETTE = [
  "#3F8F4E","#2BA3B5","#C98A12","#B4552A","#0E5A6B",
  "#7A6FB0","#8C9A3A","#C46A8A","#4F7F9E","#A0794B"
];
var cultureColors = {};
var zoneColors = {};

function colorFor(key, store) {
  if (!store) { store = cultureColors; }
  key = key || "unknown";
  if (!store[key]) { store[key] = PALETTE[Object.keys(store).length % PALETTE.length]; }
  return store[key];
}

// Badge CSS class based on value
var SAL_CLASS = {
  "absente": "badge-absente",
  "traces":  "badge-traces",
  "cro\u00fbtes de sel visibles": "badge-crouts"
};
var ERO_CLASS = {
  "aucune":   "badge-aucune",
  "en nappe": "badge-en-nappe",
  "rigoles":  "badge-rigoles",
  "ravines":  "badge-ravines"
};

function mkBadge(text, cls) {
  if (!text) { return ""; }
  return "<span class=\"badge " + (cls || "badge-water") + "\">" + esc(text) + "</span>";
}

// ---- State -----------------------------------------------------------------

var currentMode = null;   // "add-site" | "draw-zone" | "edit-geom" | null
var currentFeature = null; // {type:"site"|"zone", id, layer, props}
var tempMarker = null;
var drawnPolygon = null;
var allSiteLayers = {};   // id -> Leaflet layer
var allZoneLayers = {};
var sitesGeoLayer, zonesGeoLayer;
var optionsCache = null;  // from /api/options
var searchItems = [];

// ---- Side panel ------------------------------------------------------------

var panel      = $id("side-panel");
var panelTitle = $id("panel-title");
var panelSub   = $id("panel-sub");
var panelAttrs = $id("panel-attrs");
var panelActs  = $id("panel-actions");
var obsSection = $id("obs-section");
var editForm   = $id("edit-form");

$id("panel-close").onclick = function() { closePanel(); };

function closePanel() {
  panel.classList.remove("open");
  currentFeature = null;
  editForm.classList.remove("visible");
}

function openPanel(title, sub) {
  panelTitle.textContent = title;
  panelSub.textContent   = sub || "";
  editForm.classList.remove("visible");
  panel.classList.add("open");
}

/** Render an attribute grid from an array of [label, value] pairs. */
function renderAttrs(pairs) {
  var html = "<dl class=\"attr-grid\">";
  pairs.forEach(function(p) {
    html += "<div class=\"attr-item\"><dt>" + esc(p[0])
          + "</dt><dd>" + esc(p[1] != null ? p[1] : "\u2014") + "</dd></div>";
  });
  html += "</dl>";
  panelAttrs.innerHTML = html;
}

// ---- Observation card builder ---------------------------------------------

function buildObsCard(o) {
  var meta = [];
  if (o.ph != null)                 { meta.push("pH " + o.ph); }
  if (o.ec_dsm != null)             { meta.push("EC " + o.ec_dsm + " dS/m"); }
  if (o.organic_matter_pct != null) { meta.push("OM " + o.organic_matter_pct + "%"); }

  return "<div class=\"obs-card\">"
    + "<div class=\"obs-card-header\"><strong>" + esc(o.observation_date) + "</strong>"
    + "<span>" + esc(o.contributor_name) + "</span></div>"
    + "<div class=\"obs-badges\">"
    + mkBadge("Salinity: " + o.salinity,       SAL_CLASS[o.salinity])
    + mkBadge("Erosion: "  + o.erosion,         ERO_CLASS[o.erosion])
    + mkBadge(o.water_status,                   "badge-water")
    + mkBadge(o.irrigation_mode,                "badge-irrigation")
    + "</div>"
    + "<div class=\"obs-meta\">" + esc(o.soil_texture) + " \u00b7 " + esc(o.culture) + "</div>"
    + (meta.length ? "<div class=\"obs-meta\">" + meta.map(esc).join(" \u00b7 ") + "</div>" : "")
    + (o.remark ? "<div class=\"obs-meta\" style=\"font-style:italic;\">\u201c" + esc(o.remark) + "\u201d</div>" : "")
    + "</div>";
}

// ---- Show site in panel ----------------------------------------------------

function showSite(props, layer) {
  currentFeature = { type: "site", id: props.id, layer: layer, props: props };
  openPanel(props.name, "Observation site #" + props.id);

  renderAttrs([
    ["Crop",       props.culture],
    ["Soil type",  props.soil_type],
    ["Source",     props.source || "\u2014"],
    ["mukey",      props.mukey  || "\u2014"],
    ["Observations", props.observation_count || 0],
    ["Last obs.",  props.last_observation_date || "\u2014"],
  ]);

  // Action buttons
  panelActs.innerHTML =
    "<button class=\"btn btn-sm btn-primary\" id=\"pa-add-obs\">" + MS.addObs + "</button>"
  + "<button class=\"btn btn-sm btn-secondary\" id=\"pa-edit-attr\">" + MS.editAttr + "</button>"
  + "<button class=\"btn btn-sm btn-danger\" id=\"pa-delete\">" + MS.deleteBtn + "</button>";

  $id("pa-add-obs").onclick   = function() { openObsModal(props.id); };
  $id("pa-edit-attr").onclick = function() { openEditForm("site", props); };
  $id("pa-delete").onclick    = function() { confirmDelete("site", props.id, props.name, false); };

  // Load observation history
  obsSection.innerHTML = "<h4>" + MS.obsHistory + "</h4><p style=\"color:var(--muted);font-size:.82rem;\">Loading...</p>";
  fetch("/api/sites/" + props.id + "/observations")
    .then(function(r) { return r.json(); })
    .then(function(list) {
      list = Array.isArray(list) ? list : [];
      obsSection.innerHTML = "<h4>" + MS.obsHistory + "</h4>"
        + (list.length ? list.map(buildObsCard).join("") : "<p style=\"color:var(--muted);font-size:.82rem;\">" + MS.noObs + "</p>");
    })
    .catch(function() {
      obsSection.innerHTML = "<h4>" + MS.obsHistory + "</h4><p style=\"color:var(--danger);font-size:.82rem;\">Failed to load.</p>";
    });
}

// ---- Show zone in panel ----------------------------------------------------

function showZone(props, layer) {
  currentFeature = { type: "zone", id: props.id, layer: layer, props: props };
  openPanel(props.name, "Soil unit #" + props.id);

  renderAttrs([
    ["Type",        props.zone_type],
    ["Symbol",      props.musym  || "\u2014"],
    ["mukey",       props.mukey  || "\u2014"],
    ["Source",      props.source || "\u2014"],
    ["Description", props.description || "\u2014"],
  ]);

  panelActs.innerHTML =
    "<button class=\"btn btn-sm btn-secondary\" id=\"pa-edit-attr\">" + MS.editAttr + "</button>"
  + "<button class=\"btn btn-sm btn-danger\" id=\"pa-delete\">" + MS.deleteBtn + "</button>";

  $id("pa-edit-attr").onclick = function() { openEditForm("zone", props); };
  $id("pa-delete").onclick    = function() { confirmDelete("zone", props.id, props.name, false); };

  obsSection.innerHTML = "";
}

// ---- Edit attributes form --------------------------------------------------

function openEditForm(type, props) {
  var fields = [];
  if (type === "site") {
    fields = [
      { name: "name",      label: "Site name",  type: "text",   val: props.name },
      { name: "culture",   label: "Crop",       type: "select", val: props.culture,
        opts: (optionsCache || {}).cultures || [] },
      { name: "soil_type", label: "Soil type",  type: "select", val: props.soil_type,
        opts: (optionsCache || {}).soilTypes || [] },
    ];
  } else {
    fields = [
      { name: "name",        label: "Zone name",  type: "text",     val: props.name },
      { name: "zone_type",   label: "Zone type",  type: "text",     val: props.zone_type },
      { name: "description", label: "Description",type: "textarea", val: props.description || "" },
    ];
  }

  var html = "";
  fields.forEach(function(f) {
    html += "<div class=\"form-group\">"
          + "<label style=\"font-size:.82rem;\">" + esc(f.label) + "</label>";
    if (f.type === "select") {
      html += "<select class=\"form-control\" name=\"" + f.name + "\">";
      (f.opts || []).forEach(function(o) {
        html += "<option value=\"" + esc(o) + "\"" + (o === f.val ? " selected" : "") + ">"
              + esc(o) + "</option>";
      });
      html += "</select>";
    } else if (f.type === "textarea") {
      html += "<textarea class=\"form-control\" name=\"" + f.name + "\" rows=\"2\">"
            + esc(f.val) + "</textarea>";
    } else {
      html += "<input class=\"form-control\" type=\"text\" name=\"" + f.name + "\" value=\""
            + esc(f.val) + "\"/>";
    }
    html += "<span class=\"field-error\" id=\"edit-err-" + f.name + "\"></span></div>";
  });

  $id("edit-fields").innerHTML = html;
  $id("edit-errors").innerHTML = "";
  editForm.classList.add("visible");
  editForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

$id("btn-cancel-edit").onclick = function() { editForm.classList.remove("visible"); };

$id("btn-save-edit").onclick = function() {
  if (!currentFeature) { return; }

  // Collect field values from the edit form
  var data = {};
  editForm.querySelectorAll("[name]").forEach(function(el) {
    data[el.name] = el.value.trim();
  });

  var url = currentFeature.type === "site"
    ? "/api/sites/" + currentFeature.id
    : "/api/zones/" + currentFeature.id;

  fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  })
  .then(function(r) { return r.json().then(function(d) { return { s: r.status, d: d }; }); })
  .then(function(res) {
    if (res.s === 200) {
      showToast("Saved successfully.", "success");
      editForm.classList.remove("visible");
      // Update in-memory props and re-render panel
      Object.assign(currentFeature.props, res.d);
      if (currentFeature.type === "site") {
        showSite(currentFeature.props, currentFeature.layer);
      } else {
        showZone(currentFeature.props, currentFeature.layer);
      }
    } else if (res.s === 400 && res.d.errors) {
      Object.keys(res.d.errors).forEach(function(k) {
        var el = $id("edit-err-" + k);
        if (el) { el.textContent = res.d.errors[k]; }
      });
    } else {
      showToast(res.d.error || "Save failed.", "error");
    }
  })
  .catch(function() { showToast("Server unreachable.", "error"); });
};

// ---- Delete ----------------------------------------------------------------

var deleteTarget = null;

function confirmDelete(type, id, name, hasObs) {
  deleteTarget = { type: type, id: id };
  var msg = "Delete " + type + ' "' + name + '"?';
  if (hasObs || type === "site") {
    msg += " All linked observations will also be deleted.";
  }
  $id("delete-modal-msg").textContent = msg;
  $id("delete-modal").hidden = false;
}

$id("btn-close-delete-modal").onclick = function() { $id("delete-modal").hidden = true; };
$id("btn-cancel-delete").onclick      = function() { $id("delete-modal").hidden = true; };

$id("btn-confirm-delete").onclick = function() {
  if (!deleteTarget) { return; }
  var url = deleteTarget.type === "site"
    ? "/api/sites/" + deleteTarget.id
    : "/api/zones/" + deleteTarget.id;

  fetch(url, { method: "DELETE" })
  .then(function(r) { return r.json().then(function(d) { return { s: r.status, d: d }; }); })
  .then(function(res) {
    $id("delete-modal").hidden = true;
    if (res.s === 200) {
      showToast("Deleted.", "success");
      closePanel();
      if (deleteTarget.type === "site" && allSiteLayers[deleteTarget.id]) {
        sitesGeoLayer.removeLayer(allSiteLayers[deleteTarget.id]);
        delete allSiteLayers[deleteTarget.id];
        searchItems = searchItems.filter(function(i) {
          return !(i.kind === "Site" && i.props.id === deleteTarget.id);
        });
      } else if (deleteTarget.type === "zone" && allZoneLayers[deleteTarget.id]) {
        zonesGeoLayer.removeLayer(allZoneLayers[deleteTarget.id]);
        delete allZoneLayers[deleteTarget.id];
        searchItems = searchItems.filter(function(i) {
          return !(i.kind === "Zone" && i.props.id === deleteTarget.id);
        });
      }
    } else {
      showToast(res.d.error || "Delete failed.", "error");
    }
  })
  .catch(function() { showToast("Server unreachable.", "error"); });
};

// ---- Toolbar mode management -----------------------------------------------

var hintBanner = $id("hint-banner");
var hintText   = $id("hint-text");

function setMode(mode) {
  currentMode = mode;
  // Reset all toolbar button active states
  ["btn-add-site","btn-draw-zone","btn-edit-geom","btn-delete"].forEach(function(id) {
    $id(id).classList.remove("active");
  });

  if (mode === "add-site") {
    $id("btn-add-site").classList.add("active");
    hintText.textContent = MS.hintAddSite;
    hintBanner.classList.add("visible");
    map.getContainer().style.cursor = "crosshair";
  } else if (mode === "draw-zone") {
    $id("btn-draw-zone").classList.add("active");
    hintText.textContent = MS.hintDrawZone;
    hintBanner.classList.add("visible");
    map.pm.enableDraw("Polygon", { snappable: false });
  } else if (mode === "edit-geom") {
    $id("btn-edit-geom").classList.add("active");
    hintText.textContent = MS.hintEditGeom;
    hintBanner.classList.add("visible");
    map.pm.enableGlobalEditMode();
  } else {
    hintBanner.classList.remove("visible");
    map.getContainer().style.cursor = "";
    map.pm.disableDraw();
    map.pm.disableGlobalEditMode();
    // Hide floating forms
    $id("add-site-form-wrap").classList.remove("visible");
    $id("draw-zone-form-wrap").classList.remove("visible");
    if (tempMarker) { map.removeLayer(tempMarker); tempMarker = null; }
    drawnPolygon = null;
  }
}

$id("btn-add-site").onclick  = function() { setMode(currentMode === "add-site"  ? null : "add-site"); };
$id("btn-draw-zone").onclick = function() { setMode(currentMode === "draw-zone" ? null : "draw-zone"); };
$id("btn-edit-geom").onclick = function() { setMode(currentMode === "edit-geom" ? null : "edit-geom"); };
$id("btn-delete").onclick    = function() {
  if (currentFeature) {
    confirmDelete(currentFeature.type, currentFeature.id, currentFeature.props.name, true);
  } else {
    showToast("Select a site or zone first.", "");
  }
};
$id("btn-cancel-mode").onclick = function() { setMode(null); };

// ---- Add site mode: map click -> marker -> form ----------------------------

map.on("click", function(e) {
  if (currentMode !== "add-site") { return; }

  if (tempMarker) {
    tempMarker.setLatLng(e.latlng);
  } else {
    tempMarker = L.marker(e.latlng, { draggable: true }).addTo(map);
    tempMarker.on("drag dragend", function() { updateAddCoords(tempMarker.getLatLng()); });
    $id("add-site-form-wrap").classList.add("visible");
  }
  updateAddCoords(e.latlng);
});

function updateAddCoords(ll) {
  $id("add-lat").value = ll.lat.toFixed(6);
  $id("add-lon").value = ll.lng.toFixed(6);
}

$id("btn-cancel-add-site").onclick = function() { setMode(null); };

$id("add-site-form").onsubmit = function(e) {
  e.preventDefault();
  // Clear errors
  ["name","culture","soil_type","coords"].forEach(function(f) {
    $id("err-add-" + f).textContent = "";
  });

  var lat = parseFloat($id("add-lat").value);
  var lon = parseFloat($id("add-lon").value);
  if (isNaN(lat) || isNaN(lon)) {
    $id("err-add-coords").textContent = MS.clickFirst;
    return;
  }

  var payload = {
    name:      this.elements["name"].value.trim(),
    culture:   this.elements["culture"].value,
    soil_type: this.elements["soil_type"].value,
    latitude:  lat,
    longitude: lon
  };

  fetch("/api/sites", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(function(r) { return r.json().then(function(d) { return { s: r.status, d: d }; }); })
  .then(function(res) {
    if (res.s === 201) {
      showToast("Site saved!", "success");
      setMode(null);
      addSiteFeatureToMap(res.d);
    } else if (res.s === 400 && res.d.errors) {
      var em = { name:"err-add-name", culture:"err-add-culture",
                 soil_type:"err-add-soil_type", longitude:"err-add-coords", latitude:"err-add-coords" };
      Object.keys(res.d.errors).forEach(function(k) {
        if (em[k]) { $id(em[k]).textContent = res.d.errors[k]; }
      });
    } else {
      showToast(res.d.error || "Save failed.", "error");
    }
  })
  .catch(function() { showToast("Server unreachable.", "error"); });
};

// ---- Draw zone mode: Geoman -> polygon -> form ----------------------------

map.on("pm:create", function(e) {
  if (currentMode !== "draw-zone") { return; }
  drawnPolygon = e.layer;
  $id("draw-zone-form-wrap").classList.add("visible");
  map.pm.disableDraw();
});

$id("btn-cancel-draw-zone").onclick = function() {
  if (drawnPolygon) { map.removeLayer(drawnPolygon); drawnPolygon = null; }
  setMode(null);
};

$id("draw-zone-form").onsubmit = function(e) {
  e.preventDefault();
  $id("err-zone-name").textContent = "";
  $id("err-zone-geom").textContent = "";

  if (!drawnPolygon) {
    $id("err-zone-geom").textContent = MS.drawFirst;
    return;
  }

  var geojson = drawnPolygon.toGeoJSON().geometry;

  var payload = {
    name:        this.elements["name"].value.trim(),
    zone_type:   this.elements["zone_type"].value.trim() || "unité de sol",
    description: this.elements["description"].value.trim(),
    geojson:     geojson
  };

  fetch("/api/zones", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(function(r) { return r.json().then(function(d) { return { s: r.status, d: d }; }); })
  .then(function(res) {
    if (res.s === 201) {
      showToast("Zone saved!", "success");
      if (drawnPolygon) { map.removeLayer(drawnPolygon); drawnPolygon = null; }
      setMode(null);
      addZoneFeatureToMap(res.d);
    } else if (res.s === 400 && res.d.errors) {
      if (res.d.errors.name) { $id("err-zone-name").textContent = res.d.errors.name; }
      if (res.d.errors.geojson) { $id("err-zone-geom").textContent = res.d.errors.geojson; }
    } else {
      showToast(res.d.error || "Save failed.", "error");
    }
  })
  .catch(function() { showToast("Server unreachable.", "error"); });
};

// ---- Edit geometry: Geoman pm:edit -> PUT ----------------------------------

map.on("pm:edit", function(e) {
  if (currentMode !== "edit-geom" || !currentFeature) { return; }

  if (currentFeature.type === "site") {
    var ll  = e.layer.getLatLng();
    fetch("/api/sites/" + currentFeature.id + "/geometry", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ longitude: ll.lng, latitude: ll.lat })
    })
    .then(function(r) { return r.json().then(function(d) { return { s: r.status, d: d }; }); })
    .then(function(res) {
      if (res.s === 200) { showToast("Geometry updated.", "success"); }
      else { showToast(res.d.error || "Update failed.", "error"); }
    });
  } else if (currentFeature.type === "zone") {
    var geojson = e.layer.toGeoJSON().geometry;
    fetch("/api/zones/" + currentFeature.id + "/geometry", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ geojson: geojson })
    })
    .then(function(r) { return r.json().then(function(d) { return { s: r.status, d: d }; }); })
    .then(function(res) {
      if (res.s === 200) { showToast("Geometry updated.", "success"); }
      else { showToast(res.d.error || "Update failed.", "error"); }
    });
  }
});

// ---- Observation modal -----------------------------------------------------

var obsModal = $id("obs-modal");

function openObsModal(siteId) {
  $id("obs-site-id-hidden").value = siteId;
  // Set today's date
  obsModal.querySelector("[name=observation_date]").value = todayISO();
  // Clear errors
  obsModal.querySelectorAll(".field-error").forEach(function(el) { el.textContent = ""; });
  obsModal.querySelector("form").reset();
  obsModal.querySelector("[name=observation_date]").value = todayISO();
  obsModal.hidden = false;
}

$id("btn-close-obs-modal").onclick  = function() { obsModal.hidden = true; };
$id("btn-cancel-obs-modal").onclick = function() { obsModal.hidden = true; };
obsModal.addEventListener("click", function(e) { if (e.target === obsModal) { obsModal.hidden = true; } });

$id("obs-modal-form").onsubmit = function(e) {
  e.preventDefault();
  var siteId = parseInt($id("obs-site-id-hidden").value, 10);
  var form   = this;

  // Clear previous errors
  form.querySelectorAll(".field-error").forEach(function(el) { el.textContent = ""; });

  var payload = {
    contributor_name: form.elements["contributor_name"].value.trim(),
    observation_date: form.elements["observation_date"].value,
    soil_texture:     form.elements["soil_texture"].value,
    water_status:     form.elements["water_status"].value,
    salinity:         form.elements["salinity"].value,
    erosion:          form.elements["erosion"].value,
    culture:          form.elements["culture"].value,
    irrigation_mode:  form.elements["irrigation_mode"].value,
  };

  var ph  = form.elements["ph"].value;
  var ec  = form.elements["ec_dsm"].value;
  var om  = form.elements["organic_matter_pct"].value;
  var rem = form.elements["remark"].value.trim();
  if (ph)  { payload.ph                 = parseFloat(ph); }
  if (ec)  { payload.ec_dsm             = parseFloat(ec); }
  if (om)  { payload.organic_matter_pct = parseFloat(om); }
  if (rem) { payload.remark             = rem; }

  fetch("/api/sites/" + siteId + "/observations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(function(r) { return r.json().then(function(d) { return { s: r.status, d: d }; }); })
  .then(function(res) {
    if (res.s === 201) {
      obsModal.hidden = true;
      showToast("Observation saved!", "success");
      // Refresh the panel if this site is open
      if (currentFeature && currentFeature.type === "site" && currentFeature.id === siteId) {
        showSite(currentFeature.props, currentFeature.layer);
      }
    } else if (res.s === 400 && res.d.errors) {
      Object.keys(res.d.errors).forEach(function(k) {
        var el = $id("err-obs-" + k);
        if (el) { el.textContent = res.d.errors[k]; }
      });
    } else {
      showToast(res.d.error || "Save failed.", "error");
    }
  })
  .catch(function() { showToast("Server unreachable.", "error"); });
};

// ---- Helper: add a new site layer after save -------------------------------

function addSiteFeatureToMap(feature) {
  var props  = feature.properties;
  var coords = feature.geometry.coordinates;  // [lon, lat]
  var ll     = L.latLng(coords[1], coords[0]);

  var marker = L.circleMarker(ll, {
    radius: 8, color: "#fff", weight: 2.5,
    fillColor: colorFor(props.culture, cultureColors), fillOpacity: 1
  });
  marker.on("click", function() { showSite(props, marker); });
  sitesGeoLayer.addLayer(marker);
  allSiteLayers[props.id] = marker;
  searchItems.push({ label: props.name, kind: "Site", layer: marker, props: props });
}

// ---- Helper: add a new zone layer after save --------------------------------

function addZoneFeatureToMap(feature) {
  var props = feature.properties;
  var layer = L.geoJSON(feature, {
    style: { color: colorFor(props.musym, zoneColors), weight: 1, fillOpacity: 0.25 }
  });
  layer.on("click", function() { showZone(props, layer); });
  layer.on("mouseover", function() { layer.setStyle({ fillOpacity: 0.5, weight: 2 }); });
  layer.on("mouseout",  function() { layer.setStyle({ fillOpacity: 0.25, weight: 1 }); });
  zonesGeoLayer.addLayer(layer);
  allZoneLayers[props.id] = layer;
  searchItems.push({ label: props.name, kind: "Zone", layer: layer, props: props });
}

// ---- Search ----------------------------------------------------------------

$id("q").addEventListener("input", function(e) {
  var t   = e.target.value.trim().toLowerCase();
  var box = $id("search-results");
  box.innerHTML = "";
  if (t.length < 2) { return; }

  searchItems
    .filter(function(i) { return (i.label||"").toLowerCase().indexOf(t) !== -1; })
    .slice(0, 10)
    .forEach(function(i) {
      var d = document.createElement("div");
      var nameEl  = document.createElement("span");
      nameEl.textContent = i.label;
      var kindEl  = document.createElement("small");
      kindEl.textContent = i.kind;
      d.appendChild(nameEl);
      d.appendChild(kindEl);
      d.onclick = function() {
        box.innerHTML = "";
        e.target.value = "";
        if (i.kind === "Site") {
          map.setView(i.layer.getLatLng(), 15);
          showSite(i.props, i.layer);
        } else {
          map.fitBounds(i.layer.getBounds());
          showZone(i.props, i.layer);
        }
      };
      box.appendChild(d);
    });
});

// ---- Load all data ---------------------------------------------------------

function populateSelect(selId, values) {
  var sel = $id(selId);
  if (!sel) { return; }
  values.forEach(function(v) {
    var opt = document.createElement("option");
    opt.value = v; opt.textContent = v;
    sel.appendChild(opt);
  });
}

// ---- Initial load ----------------------------------------------------------
// Load options first, then map data
fetch("/api/options")
  .then(function(r) { return r.json(); })
  .then(function(opts) {
    optionsCache = opts;
    populateSelect("add-culture-sel",  opts.cultures  || []);
    populateSelect("add-soiltype-sel", opts.soilTypes || []);
    populateSelect("obs-texture-sel",  opts.soilTextures   || []);
    populateSelect("obs-water-sel",    opts.waterStatuses  || []);
    populateSelect("obs-salinity-sel", opts.salinityLevels || []);
    populateSelect("obs-erosion-sel",  opts.erosionTypes   || []);
    populateSelect("obs-culture-sel",  opts.cultures       || []);
    populateSelect("obs-irrigation-sel", opts.irrigationModes || []);
  })
  .catch(function(err) { console.error("Options load error:", err); });

// fixMapHeight() was removed — #map uses position:fixed with top:56px/bottom:0
// so Leaflet always gets the correct pixel dimensions at construction time.

// Belt-and-suspenders: set explicit pixel height on #map so Leaflet always
// has a real number regardless of CSS cascade issues.
// window.load: invalidate once after all resources finish loading
window.addEventListener('load', function() { map.invalidateSize(); });
window.addEventListener('resize', function() { map.invalidateSize(); });

Promise.all([
  fetch("/api/sites").then(function(r) { return r.json(); }),
  fetch("/api/zones").then(function(r) { return r.json(); }),
  fetch("/static/data/countries.geojson").then(function(r) { return r.json(); }).catch(function() { return null; }),
]).then(function(results) {
  var sites     = results[0];
  var zones     = results[1];
  var countries = results[2];

  // Countries: dark outline only, non-interactive background layer
  if (countries) {
    L.geoJSON(countries, {
      interactive: false,
      style: { color: "#2C1A0E", weight: 1.5, fill: false, opacity: 0.6 }
    }).addTo(map);
  }

  // Zones layer
  zonesGeoLayer = L.layerGroup().addTo(map);
  (zones.features || []).forEach(function(f) {
    var props = f.properties;
    var layer = L.geoJSON(f, {
      style: { color: colorFor(props.musym, zoneColors), weight: 1, fillOpacity: 0.25 }
    });
    layer.on("click",     function() { showZone(props, layer); });
    layer.on("mouseover", function() { layer.setStyle({ fillOpacity: 0.5, weight: 2 }); });
    layer.on("mouseout",  function() { layer.setStyle({ fillOpacity: 0.25, weight: 1 }); });
    zonesGeoLayer.addLayer(layer);
    allZoneLayers[props.id] = layer;
    searchItems.push({ label: props.name, kind: "Zone", layer: layer, props: props });
  });

  // Sites layer
  sitesGeoLayer = L.layerGroup().addTo(map);
  (sites.features || []).forEach(function(f) {
    var props  = f.properties;
    var coords = f.geometry.coordinates;  // [lon, lat]
    var ll     = L.latLng(coords[1], coords[0]);
    var marker = L.circleMarker(ll, {
      radius: 8, color: "#fff", weight: 2.5,
      fillColor: colorFor(props.culture, cultureColors), fillOpacity: 1,
      bubblingMouseEvents: false
    });
    marker.on("click", function() { showSite(props, marker); });
    sitesGeoLayer.addLayer(marker);
    allSiteLayers[props.id] = marker;
    searchItems.push({ label: props.name, kind: "Site", layer: marker, props: props });
  });

  // Basemap / overlay layer control
  L.control.layers(
    { "OpenStreetMap": osm, "Satellite (ESRI)": esriSatellite },
    { "Soil zones": zonesGeoLayer, "Sites": sitesGeoLayer },
    { position: "topright", collapsed: true }
  ).addTo(map);

  // Legend
  var html = "<b style=\"font-size:.8rem;\">" + MS.legendSites + "</b>";
  Object.keys(cultureColors).sort().forEach(function(c) {
    html += "<div class=\"legend-item\"><span class=\"legend-dot\" style=\"background:"
          + cultureColors[c] + "\"></span><span>" + esc(c) + "</span></div>";
  });
  html += "<div class=\"legend-item\" style=\"margin-top:6px;\">"
        + "<span class=\"legend-swatch\" style=\"background:#3F8F4E;\"></span>"
        + "<span>" + MS.legendZones + "</span></div>";
  $id("legend-content").innerHTML = html;

}).catch(function(err) {
  console.error("Data load error:", err);
  showToast("Failed to load map data. Check that Flask and Docker are running.", "error", 8000);
});

// Final invalidateSize after all data is rendered
// (zone polygons can cause a reflow that confuses Leaflet's size detection)
window.addEventListener("load", function() { map.invalidateSize(); });
