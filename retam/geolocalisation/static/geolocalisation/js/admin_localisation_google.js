// admin_localisation_google.js
// Remplace les interactions Leaflet par Google Maps dans l'admin pour LocalisationContribuable

// Helper: execute fn now if DOM already ready, otherwise on DOMContentLoaded
function runWhenReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

function initAdminGoogleMap() {
    runWhenReady(function() {
        const googleMapContainer = document.getElementById('google-map');
        if (!googleMapContainer) return;

        // centre par défaut : région de Kaffrine
        const kaffrine = { lat: 13.8975, lng: -14.4490 };
        const map = new google.maps.Map(googleMapContainer, {
            center: kaffrine,
            zoom: 11,
            mapTypeId: 'roadmap'
        });

        console.debug('[admin_localisation] initAdminGoogleMap starting, fetching zones');
        // mode admin : autoriser placement libre si activé
        var adminAllowFreePlacement = true; // default true to allow quick admin placement

        // Ajouter un contrôle UI simple pour activer/désactiver le mode ajout
        try{
            var controlDiv = document.createElement('div');
            controlDiv.style.padding = '6px';
            controlDiv.style.background = 'white';
            controlDiv.style.border = '1px solid #ccc';
            controlDiv.style.borderRadius = '4px';
            controlDiv.style.boxShadow = '0 1px 4px rgba(0,0,0,0.3)';
            controlDiv.style.cursor = 'pointer';
            controlDiv.title = 'Activer / désactiver le mode ajout de marqueur (admin)';
            controlDiv.textContent = adminAllowFreePlacement ? 'Ajout: ON' : 'Ajout: OFF';
            controlDiv.addEventListener('click', function(){
                adminAllowFreePlacement = !adminAllowFreePlacement;
                controlDiv.textContent = adminAllowFreePlacement ? 'Ajout: ON' : 'Ajout: OFF';
            });
            map.controls[google.maps.ControlPosition.TOP_RIGHT].push(controlDiv);
        } catch(e){ console.warn('failed to add admin control', e); }
        // Charger les zones via l'endpoint admin existant (envoyer cookies/session)
        fetch('/geolocalisation/api/zones/all-geojson/', { credentials: 'same-origin' })
            .then(function(r){
                if(!r.ok){
                    return r.text().then(function(text){ throw new Error('HTTP '+r.status+': '+text); });
                }
                return r.json();
            })
            .then(data => {
                console.debug('[admin_localisation] zones fetched', data && data.features ? data.features.length : 0);
                const polygons = [];
                data.features.forEach(function(feature) {
                    if (!feature.geometry) return;
                    if (feature.geometry.type === 'Polygon' || feature.geometry.type === 'MultiPolygon') {
                        const paths = [];
                        if (feature.geometry.type === 'Polygon') {
                            feature.geometry.coordinates.forEach(function(ring) {
                                const ringPath = ring.map(function(coord) { return {lng: coord[0], lat: coord[1]}; });
                                paths.push(ringPath);
                            });
                        } else {
                            feature.geometry.coordinates.forEach(function(poly) {
                                poly.forEach(function(ring) {
                                    const ringPath = ring.map(function(coord) { return {lng: coord[0], lat: coord[1]}; });
                                    paths.push(ringPath);
                                });
                            });
                        }

                        const polygon = new google.maps.Polygon({
                            paths: paths,
                            strokeColor: '#0a384f',
                            strokeOpacity: 0.8,
                            strokeWeight: 2,
                            fillColor: '#79aec8',
                            fillOpacity: 0.15,
                            map: map
                        });
                        polygons.push(polygon);
                    }
                });

                console.debug('[admin_localisation] polygons created:', polygons.length);
                // Si la page contient déjà une valeur geom, afficher le marqueur
                const geomField = document.getElementById('id_geom');
                console.debug('[admin_localisation] geomField element:', !!geomField, geomField && geomField.value);
                if (geomField && geomField.value) {
                    const m = parseWKTPoint(geomField.value);
                    if (m) {
                        const mk = new google.maps.Marker({ position: {lat: m.lat, lng: m.lng}, map: map, draggable: true });
                        map.setCenter({lat: m.lat, lng: m.lng});
                        map.setZoom(12);
                        mk.addListener('dragend', function(e){ updateGeomField(e.latLng); });
                    }
                }

                // Si pas de polygons chargés, centrer sur tout le Sénégal
                if (!polygons.length) {
                    var senegalBounds = new google.maps.LatLngBounds(
                        new google.maps.LatLng(12.0, -17.6),
                        new google.maps.LatLng(16.8, -11.2)
                    );
                    map.fitBounds(senegalBounds);
                }

                // Search control (Places Autocomplete) pour l'admin
                try{
                    var inputDiv = document.createElement('div');
                    inputDiv.style.padding = '8px';
                    inputDiv.style.background = '#fff';
                    inputDiv.style.borderRadius = '4px';
                    inputDiv.style.boxShadow = '0 1px 4px rgba(0,0,0,0.2)';
                    var input = document.createElement('input');
                    input.type = 'text';
                    input.placeholder = 'Rechercher une adresse ou contribuable...';
                    input.style.width = '300px';
                    input.style.padding = '6px 8px';
                    inputDiv.appendChild(input);
                    map.controls[google.maps.ControlPosition.TOP_LEFT].push(inputDiv);

                    if(window.google && google.maps && google.maps.places && google.maps.places.Autocomplete){
                        var ac = new google.maps.places.Autocomplete(input, { fields: ['geometry','name','formatted_address'] });
                        ac.bindTo('bounds', map);
                        ac.addListener('place_changed', function(){
                            var place = ac.getPlace();
                            if(!place.geometry) return;
                            var loc = place.geometry.location;
                            placeAdminMarker(loc, map);
                        });
                    } else {
                        // fallback: search via backend endpoint
                        input.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); fetch('/geolocalisation/search/?q='+encodeURIComponent(input.value)).then(r=>r.json()).then(function(data){ if(data.lat && data.lng) placeAdminMarker(new google.maps.LatLng(data.lat, data.lng), map); }).catch(console.error); } });
                    }
                }catch(se){ console.warn('admin search init failed', se); }

                // Clic pour placer un marqueur si à l'intérieur d'une zone
                // Si aucune zone chargée, autoriser placement (fallback admin)
                map.addListener('click', function(e) {
                    console.debug('[admin_localisation] map clicked at', e.latLng, 'polygons:', polygons.length);
                    try{
                        var inside = false;
                        if(polygons.length){
                            inside = polygons.some(function(p){
                                var ok = google.maps.geometry && google.maps.geometry.poly && google.maps.geometry.poly.containsLocation(e.latLng, p);
                                console.debug('[admin_localisation] containsLocation result for polygon', ok);
                                return ok;
                            });
                        } else {
                            console.debug('[admin_localisation] no polygons loaded');
                        }

                        if (inside || (!polygons.length && adminAllowFreePlacement) || adminAllowFreePlacement) {
                            placeAdminMarker(e.latLng, map);
                        } else {
                            alert("Veuillez placer le marqueur à l'intérieur d'une zone.");
                        }
                    }catch(err){ console.error('[admin_localisation] click handler error', err); }
                });

                function placeAdminMarker(latLng, map) {
                    // supprimer le marqueur existant
                    if (window.__admin_marker) {
                        window.__admin_marker.setMap(null);
                    }
                    window.__admin_marker = new google.maps.Marker({ position: latLng, map: map, draggable: true });
                    updateGeomField(latLng);
                    window.__admin_marker.addListener('dragend', function(e) { updateGeomField(e.latLng); });
                    map.panTo(latLng);
                }

                function updateGeomField(latLng) {
                    const geomField = document.getElementById('id_geom');
                    if (geomField) geomField.value = `POINT(${latLng.lng()} ${latLng.lat()})`;
                }

                function parseWKTPoint(wkt) {
                    // simple parse 'POINT(lon lat)'
                    const m = wkt.match(/POINT\s*\(\s*([0-9eE+\-\.]+)\s+([0-9eE+\-\.]+)\s*\)/);
                    if (!m) return null;
                    return { lng: parseFloat(m[1]), lat: parseFloat(m[2]) };
                }
            })
            .catch(err => console.error('Erreur chargement zones admin:', err));

        // create search UI (re-use integration helper if present)
        if (window.GoogleMapsIntegration && typeof window.GoogleMapsIntegration.createSearchControl === 'function') {
          const searchOptions = { placeholder: 'Rechercher un lieu ou contribuable...', btnText: 'OK', searchZoom: 16 };
          window.GoogleMapsIntegration.createSearchControl(map, searchOptions);
        } else {
          // fallback: simple input + button injected into DOM (minimal)
          const ctrl = document.createElement('div');
          ctrl.style.padding = '6px';
          const input = document.createElement('input');
          input.type = 'search';
          input.placeholder = 'Rechercher...';
          input.id = 'admin-search-input';
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.textContent = 'OK';
          ctrl.appendChild(input);
          ctrl.appendChild(btn);
          map.controls[google.maps.ControlPosition.TOP_LEFT].push(ctrl);

          async function fallbackSearch(q) {
            if (!q) return;
            try {
              const res = await fetch(`/geolocalisation/search_location/?q=${encodeURIComponent(q)}`);
              if (!res.ok) throw new Error('Recherche serveur échouée');
              const data = await res.json();
              if (data && data.lat && data.lng) {
                const latlng = new google.maps.LatLng(data.lat, data.lng);
                // place marker and update id_geom (use global helper if exists)
                if (window.GoogleMapsIntegration && window.GoogleMapsIntegration.placeSearchMarker) {
                  window.GoogleMapsIntegration.placeSearchMarker(map, latlng, data.label || q);
                } else {
                  // minimal marker
                  const m = new google.maps.Marker({ map: map, position: latlng, draggable: true });
                  m.addListener('dragend', function(){ 
                    const p = m.getPosition();
                    const wkt = `POINT(${p.lng()} ${p.lat()})`;
                    const el = document.getElementById('id_geom'); if (el) { el.value = wkt; el.dispatchEvent(new Event('change')); }
                  });
                  const el = document.getElementById('id_geom'); if (el) { el.value = `POINT(${latlng.lng()} ${latlng.lat()})`; el.dispatchEvent(new Event('change')); }
                }
                map.panTo(latlng);
                map.setZoom(16);
              } else {
                alert('Aucun résultat trouvé.');
              }
            } catch (err) {
              console.error('fallbackSearch error', err);
              alert('Erreur lors de la recherche (voir console)');
            }
          }

          btn.addEventListener('click', function(){ fallbackSearch(input.value); });
          input.addEventListener('keydown', function(e){ if (e.key === 'Enter') { e.preventDefault(); btn.click(); }});
        }
    });
}
