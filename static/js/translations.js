/**
 * translations.js -- All user-facing strings in English, French, and Arabic.
 *
 * Usage:
 *   T("addSite")          -- returns the string in the current language
 *   applyLanguage("ar")   -- swaps every labelled element and sets RTL
 *
 * Note on dropdown VALUES:
 *   The database stores controlled-vocabulary values in French
 *   (sableuse, engorgé, goutte-à-goutte, etc.) because the PostGIS CHECK
 *   constraints are defined in French and cannot be changed without a
 *   schema migration. Only the UI LABELS are translated; the stored values
 *   are always French.
 */

"use strict";

// ---------------------------------------------------------------------------
// Translation table
// Each key maps to { en, fr, ar }
// ---------------------------------------------------------------------------
var TRANSLATIONS = {

  // ---- Page / header ----
  pageTitle:        { en: "Soil Observation Platform -- Chott Mariem",
                      fr: "Plateforme d'observation des sols -- Chott Mariem",
                      ar: "منصة مراقبة التربة -- شط مريم" },
  appTitle:         { en: "Soil Observation -- Chott Mariem Perimeter",
                      fr: "Observation des sols -- Périmètre de Chott Mariem",
                      ar: "مراقبة التربة -- محيط شط مريم" },
  addSite:          { en: "+ Add Site",
                      fr: "+ Ajouter un site",
                      ar: "+ إضافة موقع" },

  // ---- Sidebar ----
  searchPlaceholder:{ en: "Search a site...",
                      fr: "Rechercher un site...",
                      ar: "البحث عن موقع..." },
  loading:          { en: "Loading sites...",
                      fr: "Chargement des sites...",
                      ar: "جارٍ تحميل المواقع..." },
  apiError:         { en: "Could not load sites. Make sure Flask and Docker are running.",
                      fr: "Impossible de charger les sites. Vérifiez que Flask et Docker sont démarrés.",
                      ar: "تعذّر تحميل المواقع. تأكد من تشغيل Flask وDocker." },
  noSites:          { en: "No sites found in the database.",
                      fr: "Aucun site trouvé dans la base de données.",
                      ar: "لم يتم العثور على مواقع في قاعدة البيانات." },

  // ---- Legend ----
  legendTitle:      { en: "Crop",
                      fr: "Culture",
                      ar: "المحصول" },

  // ---- Popup ----
  popupId:          { en: "ID",             fr: "Identifiant",    ar: "المعرّف" },
  popupCulture:     { en: "Crop",           fr: "Culture",        ar: "المحصول" },
  popupSoilType:    { en: "Soil type",      fr: "Type de sol",    ar: "نوع التربة" },
  popupObsCount:    { en: "Observations",   fr: "Observations",   ar: "الملاحظات" },
  popupObsUnit:     { en: "recorded",       fr: "enregistrée(s)", ar: "مسجّلة" },
  popupLastObs:     { en: "Last obs.",      fr: "Dernière obs.",  ar: "آخر ملاحظة" },
  popupNone:        { en: "None",           fr: "Aucune",         ar: "لا شيء" },
  popupAddObs:      { en: "+ Add Observation",
                      fr: "+ Ajouter une observation",
                      ar: "+ إضافة ملاحظة" },
  popupHistory:     { en: "Observation history:",
                      fr: "Historique des observations :",
                      ar: "سجل الملاحظات:" },
  popupLoading:     { en: "Loading...",     fr: "Chargement...",  ar: "جارٍ التحميل..." },
  popupError:       { en: "Error loading observations.",
                      fr: "Erreur lors du chargement des observations.",
                      ar: "خطأ في تحميل الملاحظات." },

  // ---- Popup obs card labels ----
  obsTexture:       { en: "Texture",        fr: "Texture",        ar: "القوام" },
  obsWater:         { en: "Water status",   fr: "Hydrique",       ar: "الحالة المائية" },
  obsSalinity:      { en: "Salinity",       fr: "Salinité",       ar: "الملوحة" },
  obsErosion:       { en: "Erosion",        fr: "Erosion",        ar: "التعرية" },
  obsCulture:       { en: "Crop",           fr: "Culture",        ar: "المحصول" },
  obsIrrigation:    { en: "Irrigation",     fr: "Irrigation",     ar: "الري" },

  // ---- Add-site banner ----
  addSiteBanner:    { en: "Click on the map to place a new observation site.",
                      fr: "Cliquez sur la carte pour placer un nouveau site d'observation.",
                      ar: "انقر على الخريطة لوضع موقع مراقبة جديد." },
  cancel:           { en: "Cancel",         fr: "Annuler",        ar: "إلغاء" },

  // ---- Add-site panel ----
  newSiteTitle:     { en: "New observation site",
                      fr: "Nouveau site d'observation",
                      ar: "موقع مراقبة جديد" },
  siteName:         { en: "Site name",      fr: "Nom du site",    ar: "اسم الموقع" },
  culture:          { en: "Crop",           fr: "Culture",        ar: "المحصول" },
  soilType:         { en: "Soil type",      fr: "Type de sol",    ar: "نوع التربة" },
  latitude:         { en: "Latitude",       fr: "Latitude",       ar: "خط العرض" },
  longitude:        { en: "Longitude",      fr: "Longitude",      ar: "خط الطول" },
  save:             { en: "Save",           fr: "Enregistrer",    ar: "حفظ" },

  // ---- Observation modal ----
  obsModalTitle:    { en: "Add an Observation",
                      fr: "Ajouter une observation",
                      ar: "إضافة ملاحظة" },
  site:             { en: "Site",           fr: "Site",           ar: "الموقع" },
  chooseSite:       { en: "-- Choose a site --",
                      fr: "-- Choisir un site --",
                      ar: "-- اختر موقعاً --" },
  contributor:      { en: "Contributor name",
                      fr: "Nom du contributeur",
                      ar: "اسم المساهم" },
  obsDate:          { en: "Observation date",
                      fr: "Date de l'observation",
                      ar: "تاريخ الملاحظة" },
  soilTexture:      { en: "Soil texture",
                      fr: "Texture du sol",
                      ar: "قوام التربة" },
  waterStatus:      { en: "Water status",
                      fr: "État hydrique du sol",
                      ar: "الحالة المائية للتربة" },
  salinity:         { en: "Apparent salinity",
                      fr: "Salinité apparente",
                      ar: "الملوحة الظاهرة" },
  erosion:          { en: "Observed erosion",
                      fr: "Érosion observée",
                      ar: "التعرية الملاحظة" },
  currentCrop:      { en: "Current crop",
                      fr: "Culture en place",
                      ar: "المحصول الحالي" },
  irrigationMode:   { en: "Irrigation mode",
                      fr: "Mode d'irrigation",
                      ar: "طريقة الري" },
  optMeasurements:  { en: "Optional measurements",
                      fr: "Mesures facultatives",
                      ar: "قياسات اختيارية" },
  remark:           { en: "Remark",         fr: "Remarque",       ar: "ملاحظة" },
  choose:           { en: "-- Choose --",   fr: "-- Choisir --",  ar: "-- اختر --" },

  // ---- Validation errors ----
  errChooseSite:    { en: "Please choose a site.",
                      fr: "Veuillez choisir un site.",
                      ar: "يرجى اختيار موقع." },
  errContributorShort: { en: "Contributor name must be at least 2 characters.",
                          fr: "Le nom du contributeur doit contenir au moins 2 caractères.",
                          ar: "يجب أن يحتوي اسم المساهم على حرفين على الأقل." },
  errDateRequired:  { en: "Date is required.",
                      fr: "La date est obligatoire.",
                      ar: "التاريخ مطلوب." },
  errDateFuture:    { en: "Date cannot be in the future.",
                      fr: "La date ne peut pas être dans le futur.",
                      ar: "لا يمكن أن يكون التاريخ في المستقبل." },
  errChoose:        { en: "Please choose",  fr: "Veuillez choisir", ar: "يرجى اختيار" },
  errPh:            { en: "pH must be between 0 and 14.",
                      fr: "Le pH doit être compris entre 0 et 14.",
                      ar: "يجب أن يكون الرقم الهيدروجيني بين 0 و14." },
  errEc:            { en: "EC must be >= 0.",
                      fr: "La CE doit être >= 0.",
                      ar: "يجب أن يكون التوصيل الكهربائي >= 0." },
  errOm:            { en: "Organic matter must be between 0 and 100%.",
                      fr: "La matière organique doit être entre 0 et 100%.",
                      ar: "يجب أن تكون المادة العضوية بين 0 و100%." },

  // ---- Toasts ----
  toastObsSaved:    { en: "Observation saved successfully!",
                      fr: "Observation enregistrée avec succès !",
                      ar: "تم حفظ الملاحظة بنجاح!" },
  toastSiteSaved:   { en: "New site saved!",
                      fr: "Nouveau site enregistré !",
                      ar: "تم حفظ الموقع الجديد!" },
  toastServerError: { en: "Server error.",
                      fr: "Erreur serveur.",
                      ar: "خطأ في الخادم." },
  toastNoServer:    { en: "Cannot reach the server.",
                      fr: "Impossible de joindre le serveur.",
                      ar: "تعذّر الاتصال بالخادم." },
  saving:           { en: "Saving...",      fr: "Enregistrement...", ar: "جارٍ الحفظ..." },

  // ---- Basemap switcher ----
  basemapOSM:       { en: "Street map",     fr: "Carte routière",  ar: "خريطة الشوارع" },
  basemapSat:       { en: "Satellite",      fr: "Satellite",       ar: "صور جوية" },
};

// ---------------------------------------------------------------------------
// Current language -- read from localStorage, default English
// ---------------------------------------------------------------------------
var currentLang = localStorage.getItem("soilLang") || "en";

/**
 * Return the translated string for a key in the current language.
 * Falls back to English if the key or language is missing.
 *
 * @param {string} key
 * @returns {string}
 */
function T(key) {
  var entry = TRANSLATIONS[key];
  if (!entry) { return key; }
  return entry[currentLang] || entry["en"] || key;
}

/**
 * Switch the active language, persist to localStorage, and re-render
 * every element that carries a data-i18n attribute.
 *
 * Also sets dir="rtl" on <html> for Arabic and updates the lang attribute.
 *
 * @param {string} lang -- "en", "fr", or "ar"
 */
function applyLanguage(lang) {
  if (!["en", "fr", "ar"].includes(lang)) { return; }
  currentLang = lang;
  localStorage.setItem("soilLang", lang);

  // RTL / LTR
  document.documentElement.lang = lang;
  document.documentElement.dir  = (lang === "ar") ? "rtl" : "ltr";

  // Swap every element that has data-i18n="key" (textContent)
  document.querySelectorAll("[data-i18n]").forEach(function(el) {
    el.textContent = T(el.getAttribute("data-i18n"));
  });

  // Swap every element that has data-i18n-placeholder="key" (placeholder)
  document.querySelectorAll("[data-i18n-placeholder]").forEach(function(el) {
    el.placeholder = T(el.getAttribute("data-i18n-placeholder"));
  });

  // Swap every element that has data-i18n-title="key" (title tooltip)
  document.querySelectorAll("[data-i18n-title]").forEach(function(el) {
    el.title = T(el.getAttribute("data-i18n-title"));
  });

  // Page <title>
  document.title = T("pageTitle");

  // Highlight the active language button
  ["btn-lang-en", "btn-lang-fr", "btn-lang-ar"].forEach(function(id) {
    var btn = document.getElementById(id);
    if (btn) { btn.classList.remove("lang-active"); }
  });
  var active = document.getElementById("btn-lang-" + lang);
  if (active) { active.classList.add("lang-active"); }

  // Notify map.js and forms.js so they can re-render live elements
  // (popups are rebuilt on next open; dropdowns keep French values)
  if (typeof window.onLanguageChange === "function") {
    window.onLanguageChange(lang);
  }
}

// Apply saved language on load
applyLanguage(currentLang);
