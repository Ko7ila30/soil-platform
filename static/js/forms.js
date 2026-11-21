/**
 * forms.js -- Observation form and add-site form.
 *
 * Depends on translations.js for T().
 * All DOM text uses textContent -- no innerHTML, no XSS risk.
 */

"use strict";

console.log("forms.js loaded");

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function showToast(message, duration) {
  if (!duration) { duration = 3000; }
  var toast = document.getElementById("toast");
  toast.textContent = message;
  toast.hidden = false;
  toast.classList.remove("fade-out");
  setTimeout(function() {
    toast.classList.add("fade-out");
    setTimeout(function() { toast.hidden = true; }, 300);
  }, duration);
}

function setFieldError(fieldName, message) {
  var errorEl = document.getElementById("err-" + fieldName);
  var inputEl = document.querySelector("#obs-form [name='" + fieldName + "']");
  if (!inputEl) { inputEl = document.getElementById("obs-" + fieldName); }
  if (errorEl)  { errorEl.textContent = message || ""; }
  if (inputEl)  {
    if (message) { inputEl.classList.add("invalid"); }
    else         { inputEl.classList.remove("invalid"); }
  }
}

function clearObsErrors() {
  ["site_id","contributor_name","observation_date","soil_texture","water_status",
   "salinity","erosion","culture","irrigation_mode","ph","ec_dsm",
   "organic_matter_pct","remark"]
    .forEach(function(f) { setFieldError(f, null); });
}

function populateSelect(selectEl, values) {
  while (selectEl.options.length > 1) { selectEl.remove(1); }
  values.forEach(function(v) {
    var opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    selectEl.appendChild(opt);
  });
}

// ---------------------------------------------------------------------------
// 1. Load options
// ---------------------------------------------------------------------------

var obsForm       = document.getElementById("obs-form");
var obsSiteSelect = document.getElementById("obs-site-id");

fetch("/api/options")
  .then(function(r) {
    if (!r.ok) { throw new Error("HTTP " + r.status); }
    return r.json();
  })
  .then(function(opts) {
    opts.sites.forEach(function(s) {
      var opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name;
      obsSiteSelect.appendChild(opt);
    });
    populateSelect(document.getElementById("obs-texture"),    opts.soilTextures);
    populateSelect(document.getElementById("obs-water"),      opts.waterStatuses);
    populateSelect(document.getElementById("obs-salinity"),   opts.salinityLevels);
    populateSelect(document.getElementById("obs-erosion"),    opts.erosionTypes);
    populateSelect(document.getElementById("obs-culture"),    opts.cultures);
    populateSelect(document.getElementById("obs-irrigation"), opts.irrigationModes);
    console.log("Options loaded:", opts.sites.length, "sites");
  })
  .catch(function(err) { console.error("Failed to load options:", err); });

// ---------------------------------------------------------------------------
// 2. Open / close modal
// ---------------------------------------------------------------------------

var obsModal = document.getElementById("obs-modal");

function openObsFormForSite(siteId, siteName) {
  clearObsErrors();
  obsForm.reset();

  var today = new Date();
  var yyyy  = today.getFullYear();
  var mm    = String(today.getMonth() + 1).padStart(2, "0");
  var dd    = String(today.getDate()).padStart(2, "0");
  document.getElementById("obs-date").value = yyyy + "-" + mm + "-" + dd;

  obsSiteSelect.value = String(siteId);
  obsModal.hidden = false;
  document.getElementById("obs-contributor").focus();
}

window.openObsFormForSite = openObsFormForSite;

document.getElementById("btn-close-obs-modal").addEventListener("click", function() {
  obsModal.hidden = true;
});
document.getElementById("btn-cancel-obs").addEventListener("click", function() {
  obsModal.hidden = true;
});
obsModal.addEventListener("click", function(e) {
  if (e.target === obsModal) { obsModal.hidden = true; }
});

// ---------------------------------------------------------------------------
// 3. Add site to obs dropdown after new site saved
// ---------------------------------------------------------------------------

window.addSiteToObsDropdown = function(siteProps) {
  var opt = document.createElement("option");
  opt.value = siteProps.id;
  opt.textContent = siteProps.name;
  obsSiteSelect.appendChild(opt);
};

// ---------------------------------------------------------------------------
// 4. Client-side validation (uses T() for messages)
// ---------------------------------------------------------------------------

function validateObsForm() {
  clearObsErrors();
  var valid = true;

  function val(name) {
    var el = obsForm.elements[name];
    if (!el) { return ""; }
    return el.value ? el.value.trim() : "";
  }

  if (!val("site_id")) {
    setFieldError("site_id", T("errChooseSite"));
    valid = false;
  }

  if (val("contributor_name").length < 2) {
    setFieldError("contributor_name", T("errContributorShort"));
    valid = false;
  }

  var dateVal = val("observation_date");
  if (!dateVal) {
    setFieldError("observation_date", T("errDateRequired"));
    valid = false;
  } else {
    var now    = new Date();
    var todayStr = now.getFullYear() + "-" +
      String(now.getMonth() + 1).padStart(2, "0") + "-" +
      String(now.getDate()).padStart(2, "0");
    if (dateVal > todayStr) {
      setFieldError("observation_date", T("errDateFuture"));
      valid = false;
    }
  }

  var selects = [
    ["soil_texture",   T("soilTexture")],
    ["water_status",   T("waterStatus")],
    ["salinity",       T("salinity")],
    ["erosion",        T("erosion")],
    ["culture",        T("currentCrop")],
    ["irrigation_mode",T("irrigationMode")],
  ];
  selects.forEach(function(pair) {
    if (!val(pair[0])) {
      setFieldError(pair[0], T("errChoose") + " " + pair[1] + ".");
      valid = false;
    }
  });

  var phEl = obsForm.elements["ph"];
  if (phEl && phEl.value !== "") {
    var n = parseFloat(phEl.value);
    if (isNaN(n) || n < 0 || n > 14) { setFieldError("ph", T("errPh")); valid = false; }
  }

  var ecEl = obsForm.elements["ec_dsm"];
  if (ecEl && ecEl.value !== "") {
    var n2 = parseFloat(ecEl.value);
    if (isNaN(n2) || n2 < 0) { setFieldError("ec_dsm", T("errEc")); valid = false; }
  }

  var omEl = obsForm.elements["organic_matter_pct"];
  if (omEl && omEl.value !== "") {
    var n3 = parseFloat(omEl.value);
    if (isNaN(n3) || n3 < 0 || n3 > 100) {
      setFieldError("organic_matter_pct", T("errOm"));
      valid = false;
    }
  }

  return valid;
}

// ---------------------------------------------------------------------------
// 5. Observation form submit
// ---------------------------------------------------------------------------

obsForm.addEventListener("submit", function(e) {
  e.preventDefault();
  if (!validateObsForm()) { return; }

  var siteId = parseInt(obsForm.elements["site_id"].value, 10);

  var payload = {
    contributor_name: obsForm.elements["contributor_name"].value.trim(),
    observation_date: obsForm.elements["observation_date"].value,
    soil_texture:     obsForm.elements["soil_texture"].value,
    water_status:     obsForm.elements["water_status"].value,
    salinity:         obsForm.elements["salinity"].value,
    erosion:          obsForm.elements["erosion"].value,
    culture:          obsForm.elements["culture"].value,
    irrigation_mode:  obsForm.elements["irrigation_mode"].value,
  };

  var phVal  = obsForm.elements["ph"].value;
  var ecVal  = obsForm.elements["ec_dsm"].value;
  var omVal  = obsForm.elements["organic_matter_pct"].value;
  var remVal = obsForm.elements["remark"].value.trim();

  if (phVal  !== "") { payload.ph                 = parseFloat(phVal); }
  if (ecVal  !== "") { payload.ec_dsm             = parseFloat(ecVal); }
  if (omVal  !== "") { payload.organic_matter_pct = parseFloat(omVal); }
  if (remVal !== "") { payload.remark             = remVal; }

  var submitBtn = obsForm.querySelector('[type="submit"]');
  submitBtn.disabled    = true;
  submitBtn.textContent = T("saving");

  fetch("/api/sites/" + siteId + "/observations", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  })
  .then(function(response) {
    return response.json().then(function(data) {
      return { status: response.status, data: data };
    });
  })
  .then(function(result) {
    if (result.status === 201) {
      obsModal.hidden = true;
      obsForm.reset();
      showToast(T("toastObsSaved"));
      if (typeof window.refreshSitePopup === "function") {
        window.refreshSitePopup(siteId);
      }
    } else if (result.status === 400 && result.data.errors) {
      Object.keys(result.data.errors).forEach(function(field) {
        setFieldError(field, result.data.errors[field]);
      });
    } else {
      showToast(result.data.error || T("toastServerError"), 5000);
    }
  })
  .catch(function(err) {
    console.error("Observation submit error:", err);
    showToast(T("toastNoServer"), 5000);
  })
  .finally(function() {
    submitBtn.disabled    = false;
    submitBtn.textContent = T("save");
  });
});

// ---------------------------------------------------------------------------
// 6. Add-site form submit
// ---------------------------------------------------------------------------

var addSiteForm = document.getElementById("add-site-form");

addSiteForm.addEventListener("submit", function(e) {
  e.preventDefault();

  ["err-site-name","err-site-culture","err-site-soil_type","err-site-coords"]
    .forEach(function(id) {
      var el = document.getElementById(id);
      if (el) { el.textContent = ""; }
    });

  var payload = {
    name:      document.getElementById("site-name").value.trim(),
    culture:   document.getElementById("site-culture").value,
    soil_type: document.getElementById("site-soil-type").value,
    longitude: parseFloat(document.getElementById("site-lon").value),
    latitude:  parseFloat(document.getElementById("site-lat").value),
  };

  var submitBtn = addSiteForm.querySelector('[type="submit"]');
  submitBtn.disabled    = true;
  submitBtn.textContent = T("saving");

  fetch("/api/sites", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  })
  .then(function(response) {
    return response.json().then(function(data) {
      return { status: response.status, data: data };
    });
  })
  .then(function(result) {
    if (result.status === 201) {
      showToast(T("toastSiteSaved"));
      if (typeof window.onNewSiteSaved === "function") {
        window.onNewSiteSaved(result.data);
      }
    } else if (result.status === 400 && result.data.errors) {
      var errorMap = {
        name:      "err-site-name",
        culture:   "err-site-culture",
        soil_type: "err-site-soil_type",
        longitude: "err-site-coords",
        latitude:  "err-site-coords",
      };
      Object.keys(result.data.errors).forEach(function(field) {
        var el = document.getElementById(errorMap[field] || "err-site-coords");
        if (el) { el.textContent = result.data.errors[field]; }
      });
    } else {
      showToast(result.data.error || T("toastServerError"), 5000);
    }
  })
  .catch(function(err) {
    console.error("Add site error:", err);
    showToast(T("toastNoServer"), 5000);
  })
  .finally(function() {
    submitBtn.disabled    = false;
    submitBtn.textContent = T("save");
  });
});

// ---------------------------------------------------------------------------
// 7. Language change hook -- re-apply translations to open modal/panel
// ---------------------------------------------------------------------------

window.onLanguageChange = (function(existingHook) {
  return function(lang) {
    // Chain with map.js hook if it was set first
    if (existingHook) { existingHook(lang); }
    // Nothing extra needed in forms.js:
    // static labels use data-i18n (handled by applyLanguage in translations.js)
    // dynamic validation messages call T() at the moment of validation
  };
})(window.onLanguageChange);
