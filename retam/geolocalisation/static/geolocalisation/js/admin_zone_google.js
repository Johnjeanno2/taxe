// admin_zone_google.js
// Fournit un pinceau simple pour afficher et éditer la géométrie d'une zone via Google Maps Drawing

// Helper: execute fn now if DOM already ready, otherwise on DOMContentLoaded
function runWhenReady(fn) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fn);
    } else {
        fn();
    }
}

function initAdminZoneGoogleMap() {
    runWhenReady(function() {
        const container = document.getElementById('google-map-zone');
        if (!container) return;

        const senegal = { lat: 14.4974, lng: -14.4524 };
    const map = new google.maps.Map(container, { center: senegal, zoom: 7 });

        // Charger l'eventuel geom existant et afficher
        const geomField = document.getElementById('id_geom');
        if (geomField && geomField.value) {
            try {
                const pt = parseWKTPoint(geomField.value);
                if (pt) {
                    const mk = new google.maps.Marker({ position: {lat: pt.lat, lng: pt.lng}, map: map });
                    map.setCenter({lat: pt.lat, lng: pt.lng});
                    map.setZoom(12);
                }
            } catch (e) {
                console.warn('Erreur parsing geom existant:', e);
            }
        }

    // DrawingManager pour dessiner des polygones
        const drawingManager = new google.maps.drawing.DrawingManager({
            drawingMode: null,
            drawingControl: true,
            drawingControlOptions: {
                drawingModes: ['polygon']
            },
            polygonOptions: {
                editable: true,
                draggable: false,
                strokeColor: '#0a384f',
                fillColor: '#79aec8',
                fillOpacity: 0.15
            }
        });
        drawingManager.setMap(map);

        let currentPolygon = null;

        google.maps.event.addListener(drawingManager, 'polygoncomplete', function(polygon) {
            if (currentPolygon) currentPolygon.setMap(null);
            currentPolygon = polygon;
            // Convertir en WKT (simple usage: take outer path)
            const path = polygon.getPath();
            const coords = [];
            for (let i = 0; i < path.getLength(); i++) {
                const p = path.getAt(i);
                coords.push(`${p.lng()} ${p.lat()}`);
            }
            // fermer la boucle
            if (coords.length && coords[0] !== coords[coords.length-1]) coords.push(coords[0]);
            const wkt = `POLYGON((${coords.join(', ')}))`;
            if (geomField) geomField.value = wkt;

            // Écouter l'édition pour mettre à jour le champ
            google.maps.event.addListener(polygon.getPath(), 'set_at', function() { updateWKTFromPolygon(polygon); });
            google.maps.event.addListener(polygon.getPath(), 'insert_at', function() { updateWKTFromPolygon(polygon); });
        });

        function updateWKTFromPolygon(polygon) {
            const path = polygon.getPath();
            const coords = [];
            for (let i = 0; i < path.getLength(); i++) {
                const p = path.getAt(i);
                coords.push(`${p.lng()} ${p.lat()}`);
            }
            if (coords.length && coords[0] !== coords[coords.length-1]) coords.push(coords[0]);
            const wkt = `POLYGON((${coords.join(', ')}))`;
            if (geomField) geomField.value = wkt;
        }

        // Si pas de geom existant et pas de polygones, adapter la vue au Sénégal
        try{
            // small heuristic: if zoom is still default low, fit bounds
            if(map.getZoom() <= 7) {
                var senegalBounds = new google.maps.LatLngBounds(
                    new google.maps.LatLng(12.0, -17.6),
                    new google.maps.LatLng(16.8, -11.2)
                );
                map.fitBounds(senegalBounds);
            }
        }catch(e){ }

        function parseWKTPoint(wkt) {
            const m = wkt.match(/POINT\s*\(\s*([0-9eE+\-\.]+)\s+([0-9eE+\-\.]+)\s*\)/);
            if (!m) return null;
            return { lng: parseFloat(m[1]), lat: parseFloat(m[2]) };
        }
    });
}
