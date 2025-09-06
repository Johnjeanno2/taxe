document.addEventListener('DOMContentLoaded', function() {
    // Attendre que la carte Leaflet soit chargée
    var map = window.map; // ou trouve la variable map selon ton widget
    if (!map) return;

    // Créer le formulaire
    var form = document.createElement('form');
    form.innerHTML = `
        <input type="text" id="searchInput" placeholder="Rechercher une zone ou une adresse..." style="width:180px;padding:4px 8px;border-radius:6px;border:1px solid #79aec8;">
        <button type="submit" style="background:#3db2ff;color:#fff;border:none;border-radius:6px;padding:4px 12px;margin-left:6px;cursor:pointer;">Rechercher</button>
    `;
    form.style.position = 'absolute';
    form.style.top = '20px';
    form.style.left = '20px';
    form.style.zIndex = 1000;
    form.style.background = '#fff';
    form.style.padding = '8px 12px';
    form.style.borderRadius = '8px';
    form.style.boxShadow = '0 2px 8px rgba(30,58,92,0.10)';

    // Ajouter le formulaire à la carte
    var mapContainer = document.querySelector('.leaflet-container');
    if (mapContainer) mapContainer.appendChild(form);

    // Gérer la recherche
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        var query = document.getElementById('searchInput').value.trim();
        if (!query) return;
        // Ici, tu peux faire un fetch vers une API Django qui retourne les coordonnées
        fetch(`/geolocalisation/api/search/?q=${encodeURIComponent(query)}`)
          .then(r => r.json())
          .then(data => {
              if (data.lat && data.lng) {
                  map.setView([data.lat, data.lng], 15);
                  L.marker([data.lat, data.lng]).addTo(map)
                    .bindPopup(data.label || query).openPopup();
              } else {
                  alert("Aucun résultat trouvé.");
              }
          });
    });
});