/**
 * map.js -- Leaflet map, markers, popups, legend, site list, basemap switcher,
 *           and add-site mode.
 *
 * Depends on translations.js (loaded first in index.html) for T() and T_key().
 * Reads window.CONFIG (injected by Flask) for all map settings.
 * All user-supplied text uses textContent -- never innerHTML (XSS prevention).
 */

"use strict";

console.log("map.js loaded, CONFIG:", CONFIG ? "present" : "MISSING");

// ---------------------------------------------------------------------------
// 1. Basemap tile layers
// ---------------------------------------------------------------------------

// OpenStreetMap -- default
var osmLayer = L.tileLayer(
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }
);

// Esri World Imagery (satellite) -- free, no API key required
var satelliteLayer = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, and the GIS User Community',
  }
);

// ---------------------------------------------------------------------------
// 2. Map initialisation
// ---------------------------------------------------------------------------

// Restore saved basemap from localStorage (default: OSM)
var savedBasemap = localStorage.getItem("soilBasemap") || "osm";

var map = L.map("map", {
  center: CONFIG.mapCenter,
  zoom:   CONFIG.mapZoom,
  layers: [savedBasemap === "satellite" ? satelliteLayer : osmLayer],
});

// Save basemap choice whenever the user switches
map.on("baselayerchange", function(e) {
  var isSat = map.hasLayer(satelliteLayer) ||
              (e.layer === satelliteLayer);
  localStorage.setItem("soilBasemap", isSat ? "satellite" : "osm");
});

// Scale bar
L.control.scale({ imperial: false, maxWidth: 150 }).addTo(map);

// Leaflet built-in layer control (basemap switcher, top-right)
// Labels are set initially in the current language; updated on language change.
var basemapControl = L.control.layers(
  {
    "Street map":  osmLayer,
    "Satellite":   satelliteLayer,
  },
  {},   // no overlay layers
  { position: "topright", collapsed: false }
).addTo(map);

/**
 * Rebuild the basemap control labels in the current language.
 * Leaflet does not support dynamic label updates natively, so we
 * remove and re-add the control with the new translated names.
 */
function rebuildBasemapControl() {
  basemapControl.remove();

  // Determine which layer is currently active
  var activeLayer = map.hasLayer(satelliteLayer) ? satelliteLayer : osmLayer;
  var newOsmLayer      = map.hasLayer(osmLayer)       ? osmLayer       : osmLayer;
  var newSatLayer      = map.hasLayer(satelliteLayer) ? satelliteLayer : satelliteLayer;

  var basemaps = {};
  basemaps[T("basemapOSM")] = osmLayer;
  basemaps[T("basemapSat")] = satelliteLayer;

  basemapControl = L.control.layers(basemaps, {}, {
    position: "topright",
    collapsed: false,
  }).addTo(map);
}

// ---------------------------------------------------------------------------
// 3. Colour helper
// ---------------------------------------------------------------------------

function colourForCulture(culture) {
  return CONFIG.cultureColours[culture] || CONFIG.defaultColour;
}

// ---------------------------------------------------------------------------
// 4. Shared state
// ---------------------------------------------------------------------------

var markersLayer = L.layerGroup().addTo(map);
var markerById   = {};
var allSites     = [];
var legendControl = null;

// ---------------------------------------------------------------------------
// 5. Date formatter: "YYYY-MM-DD" -> "DD/MM/YYYY"
// ---------------------------------------------------------------------------

function formatDate(isoDate) {
  if (!isoDate) { return ""; }
  var parts = isoDate.split("-");
  if (parts.length !== 3) { return isoDate; }
  return parts[2] + "/" + parts[1] + "/" + parts[0];
}

// ---------------------------------------------------------------------------
// 6. Popup builder (uses T() for labels)
// ---------------------------------------------------------------------------

function buildPopupHTML(props, obs) {
  var container = document.createElement("div");
  container.style.minWidth = "220px";
  container.style.maxWidth = "340px";

  // Title
  var title = document.createElement("div");
  title.className = "popup-title";
  title.textContent = props.name;
  container.appendChild(title);

  // Attribute rows
  var rows = [
    [T("popupId"),       "#" + props.id],
    [T("popupCulture"),  props.culture],
    [T("popupSoilType"), props.soil_type],
    [T("popupObsCount"), String(props.observation_count) + " " + T("popupObsUnit")],
    [T("popupLastObs"),
      props.last_observation_date
        ? formatDate(props.last_observation_date)
        : T("popupNone")],
  ];

  rows.forEach(function(pair) {
    var row = document.createElement("div");
    row.className = "popup-row";
    var lbl = document.createElement("span");
    lbl.className = "popup-label";
    lbl.textContent = pair[0] + ":";
    var val = document.createElement("span");
    val.textContent = pair[1];
    row.appendChild(lbl);
    row.appendChild(val);
    container.appendChild(row);
  });

  // Add observation button
  var addBtn = document.createElement("button");
  addBtn.className = "btn-add-obs";
  addBtn.textContent = T("popupAddObs");
  addBtn.setAttribute("data-site-id",   String(props.id));
  addBtn.setAttribute("data-site-name", props.name);
  container.appendChild(addBtn);

  // Observation history
  if (obs && obs.length > 0) {
    var histSection = document.createElement("div");
    histSection.className = "popup-obs-history";

    var histTitle = document.createElement("div");
    histTitle.style.fontWeight   = "600";
    histTitle.style.marginBottom = "4px";
    histTitle.style.fontSize     = "0.82rem";
    histTitle.textContent = T("popupHistory");
    histSection.appendChild(histTitle);

    obs.forEach(function(o) {
      var card = document.createElement("div");
      card.className = "obs-card";

      var dateEl = document.createElement("div");
      dateEl.className = "obs-card-date";
      dateEl.textContent = formatDate(o.observation_date) + " -- " + o.contributor_name;
      card.appendChild(dateEl);

      var fields = [
        [T("obsTexture"),    o.soil_texture],
        [T("obsWater"),      o.water_status],
        [T("obsSalinity"),   o.salinity],
        [T("obsErosion"),    o.erosion],
        [T("obsCulture"),    o.culture],
        [T("obsIrrigation"), o.irrigation_mode],
      ];
      if (o.ph                 != null) { fields.push(["pH",   String(o.ph)]); }
      if (o.ec_dsm             != null) { fields.push(["EC",   String(o.ec_dsm) + " dS/m"]); }
      if (o.organic_matter_pct != null) { fields.push(["OM",   String(o.organic_matter_pct) + " %"]); }

      fields.forEach(function(pair) {
        var line = document.createElement("div");
        var s1   = document.createElement("span");
        s1.style.color  = "#6c757d";
        s1.textContent  = pair[0] + ": ";
        var s2 = document.createElement("span");
        s2.textContent  = pair[1];
        line.appendChild(s1);
        line.appendChild(s2);
        card.appendChild(line);
      });

      if (o.remark) {
        var rem = document.createElement("div");
        rem.style.marginTop  = "3px";
        rem.style.fontStyle  = "italic";
        rem.textContent = '"' + o.remark + '"';
        card.appendChild(rem);
      }

      histSection.appendChild(card);
    });

    container.appendChild(histSection);
  }

  return container.outerHTML;
}

// ---------------------------------------------------------------------------
// 7. Add a site to the map, sidebar list
// ---------------------------------------------------------------------------

function addSiteToMap(feature) {
  var props  = feature.properties;
  var coords = feature.geometry.coordinates;  // GeoJSON [lon, lat]
  var lon    = coords[0];
  var lat    = coords[1];
  var colour = colourForCulture(props.culture);

  var marker = L.circleMarker([lat, lon], {
    radius:      8,
    color:       "#fff",
    weight:      1.5,
    fillColor:   colour,
    fillOpacity: 0.85,
  });

  marker.on("click", function() { openSitePopup(feature, marker); });
  marker.addTo(markersLayer);
  markerById[props.id] = marker;
  allSites.push(feature);
  addSiteToList(feature, marker);
}

function openSitePopup(feature, marker) {
  var props = feature.properties;
  marker.bindPopup("<em>" + T("popupLoading") + "</em>", { maxWidth: 360 }).openPopup();

  fetch("/api/sites/" + props.id + "/observations")
    .then(function(r) { return r.json(); })
    .then(function(obs) {
      return fetch("/api/sites/" + props.id)
        .then(function(r) { return r.json(); })
        .then(function(updated) {
          Object.assign(feature.properties, updated.properties);
          marker.setPopupContent(buildPopupHTML(feature.properties, obs));

          var popupEl = marker.getPopup().getElement();
          if (popupEl) {
            var btn = popupEl.querySelector(".btn-add-obs");
            if (btn) {
              btn.addEventListener("click", function(e) {
                var sid   = parseInt(e.currentTarget.getAttribute("data-site-id"), 10);
                var sname = e.currentTarget.getAttribute("data-site-name");
                if (typeof window.openObsFormForSite === "function") {
                  window.openObsFormForSite(sid, sname);
                }
              });
            }
          }
        });
    })
    .catch(function() {
      marker.setPopupContent(
        "<span style='color:#842029'>" + T("popupError") + "</span>"
      );
    });
}

window.refreshSitePopup = function(siteId) {
  var marker  = markerById[siteId];
  var feature = null;
  for (var i = 0; i < allSites.length; i++) {
    if (allSites[i].properties.id === siteId) { feature = allSites[i]; break; }
  }
  if (marker && feature && marker.isPopupOpen()) {
    openSitePopup(feature, marker);
  }
};

// ---------------------------------------------------------------------------
// 8. Sidebar list
// ---------------------------------------------------------------------------

var siteListEl    = document.getElementById("site-list");
var searchInputEl = document.getElementById("site-search");

function addSiteToList(feature, marker) {
  var props  = feature.properties;
  var colour = colourForCulture(props.culture);
  var lon    = feature.geometry.coordinates[0];
  var lat    = feature.geometry.coordinates[1];

  var li = document.createElement("li");
  li.setAttribute("data-id",   String(props.id));
  li.setAttribute("data-name", props.name.toLowerCase());

  var dot = document.createElement("span");
  dot.className        = "site-culture-badge";
  dot.style.background = colour;

  var nameEl = document.createElement("div");
  nameEl.className   = "site-name";
  nameEl.textContent = props.name;

  var metaEl = document.createElement("div");
  metaEl.className   = "site-meta";
  metaEl.textContent = props.culture + " - " + props.soil_type;

  var topRow = document.createElement("div");
  topRow.style.display    = "flex";
  topRow.style.alignItems = "center";
  topRow.appendChild(dot);
  topRow.appendChild(nameEl);

  li.appendChild(topRow);
  li.appendChild(metaEl);

  li.addEventListener("click", function() {
    map.setView([lat, lon], 15);
    openSitePopup(feature, marker);
  });

  siteListEl.appendChild(li);
}

searchInputEl.addEventListener("input", function() {
  var query = searchInputEl.value.toLowerCase().trim();
  siteListEl.querySelectorAll("li").forEach(function(li) {
    var name = li.getAttribute("data-name") || "";
    li.hidden = (query.length > 0 && name.indexOf(query) === -1);
  });
});

// ---------------------------------------------------------------------------
// 9. Legend
// ---------------------------------------------------------------------------

function buildLegend(cultures) {
  if (legendControl) { legendControl.remove(); }

  legendControl = L.control({ position: "bottomright" });
  legendControl.onAdd = function() {
    var div = L.DomUtil.create("div", "legend");

    var titleEl = document.createElement("div");
    titleEl.className   = "legend-title";
    titleEl.textContent = T("legendTitle");
    div.appendChild(titleEl);

    var seen   = {};
    var unique = [];
    cultures.forEach(function(c) {
      if (!seen[c]) { seen[c] = true; unique.push(c); }
    });

    unique.forEach(function(culture) {
      var item  = document.createElement("div");
      item.className = "legend-item";

      var dot = document.createElement("span");
      dot.className        = "legend-dot";
      dot.style.background = colourForCulture(culture);

      var label = document.createElement("span");
      label.textContent = culture;

      item.appendChild(dot);
      item.appendChild(label);
      div.appendChild(item);
    });

    return div;
  };

  legendControl.addTo(map);
}

// ---------------------------------------------------------------------------
// 10. Load all sites on page load
// ---------------------------------------------------------------------------

var loadingEl  = document.getElementById("loading-indicator");
var apiErrorEl = document.getElementById("api-error");

fetch("/api/sites")
  .then(function(response) {
    if (!response.ok) { throw new Error("HTTP " + response.status); }
    return response.json();
  })
  .then(function(geojson) {
    loadingEl.hidden = true;

    if (!geojson.features || geojson.features.length === 0) {
      loadingEl.hidden      = false;
      loadingEl.textContent = T("noSites");
      return;
    }

    geojson.features.forEach(function(feature) {
      try { addSiteToMap(feature); }
      catch (err) { console.error("Error adding site:", feature, err); }
    });

    var cultures = geojson.features.map(function(f) { return f.properties.culture; });
    buildLegend(cultures);

    window.sitesLoaded = allSites;
    console.log("Sites loaded:", allSites.length);
  })
  .catch(function(err) {
    loadingEl.hidden  = true;
    apiErrorEl.hidden = false;
    console.error("Failed to load sites:", err);
  });

// ---------------------------------------------------------------------------
// 11. Add-site mode
// ---------------------------------------------------------------------------

var mapEl         = document.getElementById("map");
var addSiteBanner = document.getElementById("add-site-banner");
var btnAddSite    = document.getElementById("btn-add-site");
var btnCancelAdd  = document.getElementById("btn-cancel-add");
var addSitePanel  = document.getElementById("add-site-panel");

var addModeActive = false;
var tempMarker    = null;
var bboxRect      = null;

function enterAddMode() {
  addModeActive = true;
  mapEl.classList.add("add-mode");
  addSiteBanner.hidden = false;

  var bb = CONFIG.bbox;
  bboxRect = L.rectangle(
    [[bb.lat_min, bb.lon_min], [bb.lat_max, bb.lon_max]],
    { color: "#e67e22", weight: 2, dashArray: "6 4", fill: false }
  ).addTo(map);
}

function exitAddMode() {
  addModeActive = false;
  mapEl.classList.remove("add-mode");
  addSiteBanner.hidden = true;
  addSitePanel.hidden  = true;

  if (tempMarker) { map.removeLayer(tempMarker); tempMarker = null; }
  if (bboxRect)   { map.removeLayer(bboxRect);   bboxRect   = null; }

  document.getElementById("add-site-form").reset();
  clearAddSiteErrors();
}

function updateCoordFields(latlng) {
  document.getElementById("site-lat").value = latlng.lat.toFixed(6);
  document.getElementById("site-lon").value = latlng.lng.toFixed(6);
}

function clearAddSiteErrors() {
  ["err-site-name", "err-site-culture", "err-site-soil_type", "err-site-coords"]
    .forEach(function(id) {
      var el = document.getElementById(id);
      if (el) { el.textContent = ""; }
    });
}

btnAddSite.addEventListener("click",   enterAddMode);
btnCancelAdd.addEventListener("click", exitAddMode);
document.getElementById("btn-cancel-site").addEventListener("click", exitAddMode);

map.on("click", function(e) {
  if (!addModeActive) { return; }

  if (tempMarker) {
    tempMarker.setLatLng(e.latlng);
  } else {
    tempMarker = L.marker(e.latlng, { draggable: true }).addTo(map);
    tempMarker.on("drag",    function(ev) { updateCoordFields(ev.target.getLatLng()); });
    tempMarker.on("dragend", function(ev) { updateCoordFields(ev.target.getLatLng()); });
    addSitePanel.hidden = false;

    var cultureSelect  = document.getElementById("site-culture");
    var soilTypeSelect = document.getElementById("site-soil-type");

    if (cultureSelect.options.length <= 1) {
      CONFIG.cultures.forEach(function(c) {
        var opt = document.createElement("option");
        opt.value = c; opt.textContent = c;
        cultureSelect.appendChild(opt);
      });
    }
    if (soilTypeSelect.options.length <= 1) {
      CONFIG.soilTypes.forEach(function(t) {
        var opt = document.createElement("option");
        opt.value = t; opt.textContent = t;
        soilTypeSelect.appendChild(opt);
      });
    }
  }

  updateCoordFields(e.latlng);
});

// ---------------------------------------------------------------------------
// 12. Language change hook -- rebuild legend + basemap labels
// ---------------------------------------------------------------------------

window.onLanguageChange = function(lang) {
  // Rebuild legend with new title
  var cultures = allSites.map(function(f) { return f.properties.culture; });
  if (cultures.length > 0) { buildLegend(cultures); }

  // Rebuild basemap switcher labels
  rebuildBasemapControl();
};

// ---------------------------------------------------------------------------
// 13. Expose for forms.js
// ---------------------------------------------------------------------------

window.onNewSiteSaved = function(feature) {
  addSiteToMap(feature);
  if (typeof window.addSiteToObsDropdown === "function") {
    window.addSiteToObsDropdown(feature.properties);
  }
  exitAddMode();
};
