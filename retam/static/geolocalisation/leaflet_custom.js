(function() {
    // Attendre que la carte Leaflet soit prête
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(function() {
            // La carte Leaflet de django-leaflet est accessible via window.LEAFLET_MAPS
            var map = null;
            if (window.LEAFLET_MAPS && Object.values(window.LEAFLET_MAPS).length > 0) {
                map = Object.values(window.LEAFLET_MAPS)[0];
            }
            if (map && L.Control.geocoder) {
                L.Control.geocoder().addTo(map);
                var satellite = L.tileLayer(
                    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    { attribution: '© Esri' }
                );
                var osm = null;
                map.eachLayer(function(layer) {
                    if (layer instanceof L.TileLayer && !osm) { osm = layer; }
                });
                var baseMaps = { "Plan": osm, "Satellite": satellite };
                L.control.layers(baseMaps).addTo(map);
            }
        }, 1000);
    });
})();