# Copilot instructions for this repository

Purpose
- Help AI agents become productive quickly in this Django + GeoDjango project (RETAM / geolocalisation app).
- Be concrete: reference files, workflows, data shapes and common pitfall points discovered in the codebase.

Big picture
- This is a Django project (`retam/`) with a geospatial app `geolocalisation/` using GeoDjango + PostGIS.
- Major components:
  - `retam/` — Django project settings and URL wiring (see `retam/settings.py`, `retam/urls.py`).
  - `geolocalisation/` — primary app that stores `Zone` (PolygonField) and `LocalisationContribuable` (PointField). Key files: `models.py`, `forms.py`, `admin.py`, `views.py`, `templates/`, `static/`.
  - `gestion_contribuables/` — contribuables app (contains `Contribuable` model referenced by localisation).
  - `api/` — lightweight API endpoints used to serve GeoJSON (used by frontend maps).

Key patterns and conventions
- Geometry flow
  - Frontend admin JS (Google Maps) writes WKT strings directly to the hidden form field `id_geom`:
    - Zone polygons: `POLYGON((lon lat, ...))`
    - Localisation: `POINT(lon lat)`
  - `geolocalisation/forms.py` contains parsers that accept WKT or GeoJSON and convert to `GEOSGeometry` (SRID 4326). If you change the admin JS, keep the WKT contract or update forms accordingly.
  - `models.py` uses GeoDjango fields: `Zone.geom = PolygonField`, `LocalisationContribuable.geom = PointField`. `save()` on `LocalisationContribuable` auto-assigns a zone when possible.

- Admin integration
  - Custom admin change_form templates were added in `geolocalisation/templates/admin/geolocalisation/` to inject Google Maps scripts and a `#google-map` container.
  - `geolocalisation/admin.py` now uses `ModelAdmin` with Media to include `geolocalisation/js/admin_zone_google.js` and `admin_localisation_google.js`.
  - Initialization timing is fragile: callbacks must exist before the Google Maps script loads. The codebase uses helpers `runWhenReady` in admin JS to avoid DOM/callback race conditions — keep that in mind when editing.

- Frontend mapping
  - Public pages use `google_maps_integration.js` which exposes `GoogleMapsIntegration` and helper methods `addZonesFromGeoJSON()` and `addLocalisationsFromGeoJSON()`.
  - There are legacy Leaflet files present as backups. Avoid removing them until you validate the Google Maps integration end-to-end.

Integration points / endpoints
- GeoJSON endpoints used by frontends and admin:
  - `geolocalisation:all_zones_geojson` — all zones
  - `geolocalisation:zones_geojson` — zones for certain pages
  - `geolocalisation:localisations_geojson` — localisations
  Check `geolocalisation/views.py` to see their exact URL names and JSON shapes.

Developer workflows & quick commands
- Run dev server
  - python manage.py runserver
- DB / migrations
  - python manage.py makemigrations
  - python manage.py migrate
  - Ensure PostGIS is available; `retam/settings.py` expects `django.contrib.gis.db.backends.postgis`.
- Tests
  - There are app-level tests (e.g. `geolocalisation/tests.py`). Run `python manage.py test` to run the suite.
- Static files
  - Static files are under `static/` and `geolocalisation/static/geolocalisation/`. `STATICFILES_DIRS` is set in `retam/settings.py`.

Common pitfalls found during development
- Google Maps API errors are often caused by wrong key, missing enabled APIs, billing disabled or HTTP referrer restrictions. Check console message: Google gives explicit error codes (e.g. `RefererNotAllowedMapError`).
- Template errors: custom admin templates must include `{% load static %}` when they use `{% static %}`. Watch for missing `load static` in change_form templates.
- Script ordering: callback functions (init...) must exist on the page before the script tag that loads the Google Maps API with `&callback=`. Use the `runWhenReady` helper where necessary.
- ID expectations: JS expects DOM field id `id_geom`; forms/widgets must preserve that id or JS will fail.

How to modify maps safely
- Edit admin JS (`geolocalisation/static/geolocalisation/js/admin_*.js`) and templates in `geolocalisation/templates/admin/geolocalisation/`. Keep the following contract:
  - Admin JS updates `id_geom` with WKT.
  - Forms parse WKT into GEOSGeometry.
- Validate: draw polygon in admin, save, re-open and verify the geometry is present.

What an AI agent should do first on a change request
1. Search for `geom` usage (grep) to find all places that assume `id_geom`.
2. Inspect admin templates for `{% load static %}` and proper callback ordering.
3. Check `forms.py` to ensure parsing matches the frontend output.
4. Run quick smoke test locally (runserver) and reproduce the add/edit workflow in admin.

Files to check when debugging mapping issues
- `geolocalisation/static/geolocalisation/js/google_maps_integration.js`
- `geolocalisation/static/geolocalisation/js/admin_zone_google.js`
- `geolocalisation/static/geolocalisation/js/admin_localisation_google.js`
- `geolocalisation/forms.py`
- `geolocalisation/admin.py`
- `geolocalisation/templates/admin/geolocalisation/*.html`
- `retam/settings.py` (Google key, STATICFILES_DIRS, DB backend)

When uncertain, ask for
- The exact browser console error (copy the full "Google Maps JavaScript API error: <CODE>" message and network request URL),
- The rendered HTML around map script tags (to verify callback and script order),
- Whether the environment uses a restricted API key (referrers/billing).

If you change the map provider or the WKT contract
- Update both admin JS and `forms.py` together; run the admin add/edit save cycle to confirm round-trip.

---
If you want, I can merge this content into an existing `.github/copilot-instructions.md` (none found) or expand sections (e.g. add example snippets for typical fixes). Please review and tell me which sections you want expanded or adjusted.
