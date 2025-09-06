document.addEventListener('DOMContentLoaded', function() {
    const mapSearchForm = document.getElementById('map-search-form');
    if (mapSearchForm) {
        mapSearchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            // traitement spécifique du formulaire de recherche de la carte
        });
    }

    // Vérifie que la carte Leaflet est chargée
    if (typeof map !== 'undefined') {
        // Ajoute le contrôle de recherche
        L.Control.geocoder({
            defaultMarkGeocode: false,
            position: 'topright'
        }).on('markgeocode', function(e) {
            const {center, name} = e.geocode;
            map.setView(center, 16);
            L.marker(center).addTo(map)
                .bindPopup(name)
                .openPopup();
        }).addTo(map);

        // Gestion du clic sur la carte
        map.on('click', function(e) {
            // Met à jour les coordonnées dans le formulaire
            document.getElementById('id_geom_0').value = e.latlng.lat;
            document.getElementById('id_geom_1').value = e.latlng.lng;
            
            // Ajoute un marqueur temporaire
            if (window.currentMarker) {
                map.removeLayer(window.currentMarker);
            }
            window.currentMarker = L.marker(e.latlng).addTo(map)
                .bindPopup("Nouvelle localisation").openPopup();
        });
    }

    // ne pas lier d'événements globaux sur "form" ni sur "document" susceptibles d'empêcher
    // le submit du formulaire d'actions de l'admin.
});