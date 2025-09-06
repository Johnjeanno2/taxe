// Shim for osm_map_integration.js removed during migration to Google Maps
console.warn('osm_map_integration.js has been replaced by google_maps_integration.js. This shim avoids errors.');
if (window.GoogleMapsIntegration && typeof window.GoogleMapsIntegration === 'function') {
  // no-op: functionality moved to google_maps_integration.js
}
// static/geolocalisation/js/osm_map_integration.js
// simple wrapper Leaflet pour initialiser la map et ajouter GeoJSON
function OSMMapIntegration(mapId){
  this.mapId = mapId;
  this.map = null;
  this._layers = [];
  this.searchMarker = null;
  this.zonesData = null;
  this.localisationsData = null;
}

// Contrôle de recherche personnalisé pour Leaflet
L.Control.SearchBox = L.Control.extend({
  onAdd: function(map) {
    var container = L.DomUtil.create('div', 'leaflet-search-container');
    container.innerHTML = `
      <div class="leaflet-search-box">
        <input type="text" class="leaflet-search-input" placeholder="Rechercher zones, sites, lieux, restaurants..." autocomplete="off">
        <button class="leaflet-search-btn" type="button">
          <i class="fas fa-search"></i>
        </button>
        <div class="leaflet-search-loading" style="display: none;">
          <i class="fas fa-spinner fa-spin"></i>
        </div>
        <div class="leaflet-search-results"></div>
      </div>
      <div class="leaflet-search-actions">
        <button class="leaflet-action-btn" id="leaflet-locate-btn" title="Ma position">
          <i class="fas fa-location-arrow"></i>
        </button>
        <button class="leaflet-action-btn" id="leaflet-reset-btn" title="Vue d'ensemble">
          <i class="fas fa-expand-arrows-alt"></i>
        </button>
      </div>
    `;

    // Empêcher la propagation des événements de la carte
    L.DomEvent.disableClickPropagation(container);
    L.DomEvent.disableScrollPropagation(container);

    return container;
  },

  onRemove: function(map) {
    // Nettoyage si nécessaire
  }
});

L.control.searchBox = function(opts) {
  return new L.Control.SearchBox(opts);
};
OSMMapIntegration.prototype.init = function(){
  if(this.map) return;
  this.map = L.map(this.mapId, { preferCanvas: true }).setView([14.5, -14.5], 7);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(this.map);

  // Ajouter le contrôle de recherche
  var searchControl = L.control.searchBox({ position: 'topleft' }).addTo(this.map);
  this.initSearchFunctionality();

  // éviter carte noire si conteneur était caché
  var self = this;
  setTimeout(function(){ try{ self.map.invalidateSize(); }catch(e){} }, 200);
};

// Initialiser les fonctionnalités de recherche
OSMMapIntegration.prototype.initSearchFunctionality = function() {
  var self = this;
  var searchInput = document.querySelector('.leaflet-search-input');
  var searchBtn = document.querySelector('.leaflet-search-btn');
  var searchResults = document.querySelector('.leaflet-search-results');
  var searchLoading = document.querySelector('.leaflet-search-loading');
  var locateBtn = document.getElementById('leaflet-locate-btn');
  var resetBtn = document.getElementById('leaflet-reset-btn');
  var searchTimeout;

  if (!searchInput) return;

  // Recherche en temps réel
  searchInput.addEventListener('input', function() {
    var query = this.value.trim();
    clearTimeout(searchTimeout);

    if (query.length < 2) {
      self.hideSearchResults();
      return;
    }

    searchTimeout = setTimeout(function() {
      self.performSearch(query);
    }, 300);
  });

  // Bouton de recherche
  searchBtn.addEventListener('click', function() {
    var query = searchInput.value.trim();
    if (query) {
      self.performSearch(query);
    }
  });

  // Entrée pour rechercher
  searchInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      var query = this.value.trim();
      if (query) {
        self.performSearch(query);
      }
    }
  });

  // Géolocalisation
  if (locateBtn) {
    locateBtn.addEventListener('click', function() {
      self.locateUser();
    });
  }

  // Reset vue
  if (resetBtn) {
    resetBtn.addEventListener('click', function() {
      self.resetView();
    });
  }

  // Focus/blur pour les résultats
  searchInput.addEventListener('focus', function() {
    if (searchResults.children.length > 0) {
      self.showSearchResults();
    }
  });

  searchInput.addEventListener('blur', function() {
    setTimeout(function() {
      self.hideSearchResults();
    }, 200);
  });
};
// Méthodes de recherche
OSMMapIntegration.prototype.performSearch = function(query) {
  var self = this;
  this.showLoading();

  // Recherche locale d'abord
  var localResults = this.searchLocalData(query);

  // Recherche géocodage
  var geocodeUrl = 'https://nominatim.openstreetmap.org/search?format=json&limit=5&q=' + encodeURIComponent(query);

  fetch(geocodeUrl)
    .then(function(response) { return response.json(); })
    .then(function(data) {
      self.hideLoading();
      var results = localResults.slice(); // copie

      data.forEach(function(item) {
        results.push({
          type: 'geocode',
          title: item.display_name.split(',')[0],
          subtitle: item.display_name,
          lat: parseFloat(item.lat),
          lon: parseFloat(item.lon),
          icon: self.getLocationIcon(item.type)
        });
      });

      self.displaySearchResults(results);
    })
    .catch(function(error) {
      self.hideLoading();
      console.error('Erreur de recherche:', error);
      self.displaySearchResults(localResults);
    });
};

OSMMapIntegration.prototype.searchLocalData = function(query) {
  var results = [];
  query = query.toLowerCase();

  // Rechercher dans les zones
  if (this.zonesData && this.zonesData.features) {
    this.zonesData.features.forEach(function(feature) {
      var props = feature.properties;
      var name = (props.nom || props.name || '').toLowerCase();

      if (name.includes(query)) {
        var centroid = props.centroid;
        if (centroid) {
          results.push({
            type: 'zone',
            title: props.nom || props.name,
            subtitle: 'Zone - ' + (props.count_contribuables || 0) + ' contribuables',
            lat: centroid.lat,
            lon: centroid.lng,
            icon: 'fa-map-marked-alt',
            data: feature
          });
        }
      }
    });
  }

  // Rechercher dans les localisations
  if (this.localisationsData && this.localisationsData.features) {
    this.localisationsData.features.forEach(function(feature) {
      var props = feature.properties;
      var name = (props.contribuable__nom || props.name || '').toLowerCase();
      var zone = (props.zone__nom || '').toLowerCase();

      if (name.includes(query) || zone.includes(query)) {
        var coords = feature.geometry.coordinates;
        results.push({
          type: 'localisation',
          title: props.contribuable__nom || props.name,
          subtitle: 'Contribuable - Zone: ' + (props.zone__nom || 'N/A'),
          lat: coords[1],
          lon: coords[0],
          icon: 'fa-user',
          data: feature
        });
      }
    });
  }

  return results;
};

OSMMapIntegration.prototype.getLocationIcon = function(type) {
  var iconMap = {
    'city': 'fa-city',
    'town': 'fa-building',
    'village': 'fa-home',
    'restaurant': 'fa-utensils',
    'hotel': 'fa-bed',
    'shop': 'fa-shopping-cart',
    'hospital': 'fa-hospital',
    'school': 'fa-school',
    'university': 'fa-university',
    'bank': 'fa-university',
    'fuel': 'fa-gas-pump'
  };
  return iconMap[type] || 'fa-map-marker-alt';
};

OSMMapIntegration.prototype.displaySearchResults = function(results) {
  var self = this;
  var searchResults = document.querySelector('.leaflet-search-results');

  if (!searchResults) return;

  if (results.length === 0) {
    searchResults.innerHTML = '<div class="leaflet-search-result-item"><div class="leaflet-search-result-text">Aucun résultat trouvé</div></div>';
  } else {
    searchResults.innerHTML = results.map(function(result, index) {
      return '<div class="leaflet-search-result-item" data-index="' + index + '">' +
        '<div class="leaflet-search-result-icon"><i class="fas ' + result.icon + '"></i></div>' +
        '<div class="leaflet-search-result-text">' +
        '<div class="leaflet-search-result-title">' + result.title + '</div>' +
        '<div class="leaflet-search-result-subtitle">' + result.subtitle + '</div>' +
        '</div></div>';
    }).join('');

    // Ajouter les événements de clic
    searchResults.querySelectorAll('.leaflet-search-result-item').forEach(function(item) {
      item.addEventListener('click', function() {
        var index = parseInt(this.dataset.index);
        var result = results[index];
        if (result) {
          self.goToLocation(result.lat, result.lon, result);
          self.hideSearchResults();
          document.querySelector('.leaflet-search-input').value = result.title;
        }
      });
    });
  }

  this.showSearchResults();
};

OSMMapIntegration.prototype.goToLocation = function(lat, lon, result) {
  // Supprimer le marqueur précédent
  if (this.searchMarker) {
    this.map.removeLayer(this.searchMarker);
  }

  // Centrer la carte
  this.map.setView([lat, lon], 15);

  // Ajouter un marqueur
  var icon = L.divIcon({
    className: 'leaflet-search-marker',
    html: '<div class="leaflet-search-marker-content"><i class="fas ' + result.icon + '"></i></div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });

  this.searchMarker = L.marker([lat, lon], { icon: icon }).addTo(this.map);

  // Popup avec informations
  var popupContent = '<div class="leaflet-search-popup">' +
    '<h4><i class="fas ' + result.icon + '"></i> ' + result.title + '</h4>' +
    '<p>' + result.subtitle + '</p>' +
    '</div>';

  this.searchMarker.bindPopup(popupContent).openPopup();
};

OSMMapIntegration.prototype.locateUser = function() {
  var self = this;
  var locateBtn = document.getElementById('leaflet-locate-btn');

  if (navigator.geolocation) {
    if (locateBtn) locateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

    navigator.geolocation.getCurrentPosition(function(position) {
      var lat = position.coords.latitude;
      var lon = position.coords.longitude;

      self.map.setView([lat, lon], 16);

      if (self.searchMarker) {
        self.map.removeLayer(self.searchMarker);
      }

      var icon = L.divIcon({
        className: 'leaflet-location-marker',
        html: '<div class="leaflet-location-marker-content"><i class="fas fa-location-arrow"></i></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });

      self.searchMarker = L.marker([lat, lon], { icon: icon }).addTo(self.map);
      self.searchMarker.bindPopup('<div class="leaflet-location-popup"><h4><i class="fas fa-location-arrow"></i> Ma position</h4><p>Vous êtes ici</p></div>').openPopup();

      if (locateBtn) locateBtn.innerHTML = '<i class="fas fa-location-arrow"></i>';
    }, function(error) {
      console.error('Erreur de géolocalisation:', error);
      if (locateBtn) locateBtn.innerHTML = '<i class="fas fa-location-arrow"></i>';
      alert('Impossible d\'obtenir votre position');
    });
  } else {
    alert('La géolocalisation n\'est pas supportée par votre navigateur');
  }
};

OSMMapIntegration.prototype.resetView = function() {
  if (this.searchMarker) {
    this.map.removeLayer(this.searchMarker);
    this.searchMarker = null;
  }

  // Retourner à la vue d'ensemble des zones
  if (this.zonesData && this.zonesData.features && this.zonesData.features.length > 0) {
    var group = new L.featureGroup();
    this.zonesData.features.forEach(function(feature) {
      if (feature.geometry) {
        L.geoJSON(feature).addTo(group);
      }
    });
    this.map.fitBounds(group.getBounds(), { padding: [20, 20] });
  } else {
    this.map.setView([14.5, -14.5], 7);
  }

  var searchInput = document.querySelector('.leaflet-search-input');
  if (searchInput) searchInput.value = '';
  this.hideSearchResults();
};

// Utilitaires pour l'interface
OSMMapIntegration.prototype.showLoading = function() {
  var searchBtn = document.querySelector('.leaflet-search-btn');
  var searchLoading = document.querySelector('.leaflet-search-loading');
  if (searchBtn) searchBtn.style.display = 'none';
  if (searchLoading) searchLoading.style.display = 'block';
};

OSMMapIntegration.prototype.hideLoading = function() {
  var searchBtn = document.querySelector('.leaflet-search-btn');
  var searchLoading = document.querySelector('.leaflet-search-loading');
  if (searchBtn) searchBtn.style.display = 'block';
  if (searchLoading) searchLoading.style.display = 'none';
};

OSMMapIntegration.prototype.showSearchResults = function() {
  var searchResults = document.querySelector('.leaflet-search-results');
  if (searchResults) searchResults.style.display = 'block';
};

OSMMapIntegration.prototype.hideSearchResults = function() {
  var searchResults = document.querySelector('.leaflet-search-results');
  if (searchResults) searchResults.style.display = 'none';
};

OSMMapIntegration.prototype.addZonesFromGeoJSON = function(geojson, style){
  try{
    this.zonesData = geojson; // Stocker les données pour la recherche
    style = style || function(){ return { color:'#0a384f', weight:3, fillOpacity:0.15, fillColor:'#79aec8' }; };
    var layer = L.geoJSON(geojson, { 
      style: style, 
      onEachFeature: function(f, l){
        if(f && f.properties) {
          var props = f.properties;
          var popupContent = '<div class="zone-info-popup">' +
            '<h4><i class="fas fa-map-marker-alt"></i> ' + (props.nom || props.name || 'Zone') + '</h4>';
          
          if(props.count_contribuables !== undefined) {
            popupContent += '<p><strong>Contribuables:</strong> ' + props.count_contribuables + '</p>';
          }
          if(props.responsable) {
            popupContent += '<p><strong>Responsable:</strong> ' + props.responsable + '</p>';
          }
          if(props.date_creation) {
            popupContent += '<p><strong>Créée le:</strong> ' + new Date(props.date_creation).toLocaleDateString('fr-FR') + '</p>';
          }
          
          popupContent += '</div>';
          l.bindPopup(popupContent);
        }
      }
    }).addTo(this.map);
    this._layers.push(layer);
    
    // Ajouter les marqueurs de zones si les données le permettent
    this.addZoneMarkers(geojson);
    
    this.map.fitBounds(layer.getBounds(), { padding:[20,20] });
  }catch(e){ console.warn('addZonesFromGeoJSON', e); }
};

OSMMapIntegration.prototype.addZoneMarkers = function(geojson){
  try{
    var self = this;
    if(geojson && geojson.features) {
      geojson.features.forEach(function(feature) {
        var props = feature.properties;
        var centroid = props.centroid;
        
        // Calculer le centroïde si pas fourni
        if(!centroid && feature.geometry && feature.geometry.type === 'Polygon') {
          var coords = feature.geometry.coordinates[0];
          var lat = 0, lng = 0;
          for(var i = 0; i < coords.length; i++) {
            lat += coords[i][1];
            lng += coords[i][0];
          }
          centroid = {
            lat: lat / coords.length,
            lng: lng / coords.length
          };
        }
        
        if(centroid && centroid.lat && centroid.lng) {
          var zoneIcon = L.divIcon({
            className: 'zone-marker-osm',
            html: '<div class="zone-marker-content-osm">' +
                  '<div class="zone-marker-icon-osm"><i class="fas fa-map-marked-alt"></i></div>' +
                  '<div class="zone-marker-label-osm">' +
                  '<span class="zone-name-osm">' + (props.nom || props.name || 'Zone') + '</span>' +
                  (props.count_contribuables !== undefined ? 
                    '<span class="zone-count-osm">' + props.count_contribuables + ' contrib.</span>' : '') +
                  '</div></div>',
            iconSize: [100, 35],
            iconAnchor: [50, 17]
          });
          
          var marker = L.marker([centroid.lat, centroid.lng], {
            icon: zoneIcon,
            zIndex: 1000
          });
          
          // Popup pour le marqueur
          var markerPopupContent = '<div class="zone-marker-popup-osm">' +
            '<h4><i class="fas fa-map-marked-alt"></i> ' + (props.nom || props.name || 'Zone') + '</h4>';
          
          if(props.count_contribuables !== undefined) {
            markerPopupContent += '<p><i class="fas fa-users"></i> <strong>' + props.count_contribuables + '</strong> contribuables</p>';
          }
          if(props.responsable) {
            markerPopupContent += '<p><i class="fas fa-user-tie"></i> <strong>Responsable:</strong> ' + props.responsable + '</p>';
          }
          if(props.date_creation) {
            markerPopupContent += '<p><i class="fas fa-calendar"></i> <strong>Créée:</strong> ' + new Date(props.date_creation).toLocaleDateString('fr-FR') + '</p>';
          }
          
          markerPopupContent += '</div>';
          marker.bindPopup(markerPopupContent);
          
          marker.addTo(self.map);
          self._layers.push(marker);
        }
      });
    }
  }catch(e){ console.warn('addZoneMarkers', e); }
};
OSMMapIntegration.prototype.addLocalisationsFromGeoJSON = function(geojson){
  try{
    this.localisationsData = geojson; // Stocker les données pour la recherche
    var self = this;
    var markers = L.geoJSON(geojson, {
      pointToLayer: function(geo, latlng){
        return L.circleMarker(latlng, {
          radius: 8,
          color: '#1a9850',
          fillColor: '#4CAF50',
          fillOpacity: 0.8,
          weight: 2,
          opacity: 1
        });
      },
      onEachFeature: function(feature, layer){
        if(feature && feature.properties) {
          var props = feature.properties;
          var popupContent = '<div class="contribuable-popup">' +
            '<h4><i class="fas fa-user"></i> ' + (props.contribuable__nom || props.name || 'Contribuable') + '</h4>';

          if(props.zone__nom) {
            popupContent += '<p><i class="fas fa-map-marker-alt"></i> <strong>Zone:</strong> ' + props.zone__nom + '</p>';
          }
          if(props.date_maj) {
            popupContent += '<p><i class="fas fa-calendar"></i> <strong>Mis à jour:</strong> ' + new Date(props.date_maj).toLocaleDateString('fr-FR') + '</p>';
          }

          popupContent += '</div>';
          layer.bindPopup(popupContent);

          // Effet hover
          layer.on('mouseover', function(e) {
            this.setStyle({
              radius: 10,
              fillOpacity: 1
            });
          });

          layer.on('mouseout', function(e) {
            this.setStyle({
              radius: 8,
              fillOpacity: 0.8
            });
          });
        }
      }
    }).addTo(this.map);
    this._layers.push(markers);
    console.log('✅ Marqueurs de contribuables ajoutés');
  }catch(e){ console.warn('addLocalisationsFromGeoJSON', e); }
};

// Ajouter les styles CSS pour les contrôles de recherche Leaflet et les marqueurs OSM
function addOSMMapStyles() {
    if(document.getElementById('osm-map-styles')) return; // Éviter les doublons
    
    var style = document.createElement('style');
    style.id = 'osm-map-styles';
    style.textContent = `
        /* Styles pour le contrôle de recherche Leaflet */
        .leaflet-search-container {
            display: flex;
            gap: 10px;
            max-width: 500px;
            margin: 5px;
        }

        .leaflet-search-box {
            flex: 1;
            position: relative;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
            backdrop-filter: blur(10px);
            border: 2px solid rgba(15, 111, 182, 0.3);
            transition: all 0.3s ease;
            min-height: 50px;
        }

        .leaflet-search-box:hover {
            box-shadow: 0 6px 25px rgba(0, 0, 0, 0.3);
            border-color: rgba(15, 111, 182, 0.5);
        }

        .leaflet-search-input {
            width: 100%;
            padding: 15px 50px 15px 20px;
            border: none;
            background: transparent;
            font-size: 16px;
            color: #333;
            outline: none;
            border-radius: 12px;
            box-sizing: border-box;
        }

        .leaflet-search-input::placeholder {
            color: #888;
            font-style: italic;
        }

        .leaflet-search-btn,
        .leaflet-search-loading {
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: #0f6fb6;
            font-size: 18px;
            cursor: pointer;
            transition: color 0.3s ease;
        }

        .leaflet-search-btn:hover {
            color: #2db45a;
        }

        .leaflet-search-actions {
            display: flex;
            gap: 8px;
        }

        .leaflet-action-btn {
            width: 50px;
            height: 50px;
            border: none;
            border-radius: 12px;
            background: linear-gradient(135deg, #0f6fb6, #2db45a);
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(15, 111, 182, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .leaflet-action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(15, 111, 182, 0.5);
        }

        .leaflet-search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(255, 255, 255, 0.98);
            border-radius: 0 0 12px 12px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            backdrop-filter: blur(10px);
            max-height: 300px;
            overflow-y: auto;
            display: none;
            z-index: 1000;
        }

        .leaflet-search-result-item {
            padding: 12px 20px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            cursor: pointer;
            transition: background-color 0.2s ease;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .leaflet-search-result-item:hover {
            background: rgba(15, 111, 182, 0.1);
        }

        .leaflet-search-result-item:last-child {
            border-bottom: none;
        }

        .leaflet-search-result-icon {
            color: #0f6fb6;
            font-size: 14px;
            width: 20px;
            text-align: center;
        }

        .leaflet-search-result-text {
            flex: 1;
        }

        .leaflet-search-result-title {
            font-weight: 600;
            color: #333;
            font-size: 14px;
        }

        .leaflet-search-result-subtitle {
            color: #666;
            font-size: 12px;
            margin-top: 2px;
        }

        /* Marqueurs de recherche et géolocalisation */
        .leaflet-search-marker,
        .leaflet-location-marker {
            background: none;
            border: none;
        }

        .leaflet-search-marker-content,
        .leaflet-location-marker-content {
            width: 30px;
            height: 30px;
            background: linear-gradient(135deg, #0f6fb6, #2db45a);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 14px;
            box-shadow: 0 3px 10px rgba(15, 111, 182, 0.4);
            border: 2px solid white;
            animation: markerPulse 2s infinite;
        }

        .leaflet-location-marker-content {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            animation: locationPulse 1.5s infinite;
        }

        @keyframes markerPulse {
            0% { transform: scale(1); box-shadow: 0 3px 10px rgba(15, 111, 182, 0.4); }
            50% { transform: scale(1.1); box-shadow: 0 5px 15px rgba(15, 111, 182, 0.6); }
            100% { transform: scale(1); box-shadow: 0 3px 10px rgba(15, 111, 182, 0.4); }
        }

        @keyframes locationPulse {
            0% { transform: scale(1); box-shadow: 0 3px 10px rgba(255, 107, 107, 0.4); }
            50% { transform: scale(1.15); box-shadow: 0 5px 15px rgba(255, 107, 107, 0.6); }
            100% { transform: scale(1); box-shadow: 0 3px 10px rgba(255, 107, 107, 0.4); }
        }

        /* Popups personnalisés */
        .leaflet-search-popup,
        .leaflet-location-popup {
            min-width: 200px;
        }

        .leaflet-search-popup h4,
        .leaflet-location-popup h4 {
            margin: 0 0 8px 0;
            color: #0f6fb6;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .leaflet-search-popup p,
        .leaflet-location-popup p {
            margin: 0;
            color: #666;
            font-size: 12px;
        }

        .leaflet-location-popup h4 {
            color: #ff6b6b;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .leaflet-search-container {
                max-width: none;
                margin: 3px;
            }

            .leaflet-search-input {
                padding: 12px 45px 12px 15px;
                font-size: 14px;
            }

            .leaflet-action-btn {
                width: 45px;
                height: 45px;
                font-size: 14px;
            }

            .leaflet-search-marker-content,
            .leaflet-location-marker-content {
                width: 25px;
                height: 25px;
                font-size: 12px;
            }
        }

        /* Styles pour les marqueurs de zones OSM */
        .zone-marker-osm {
            background: none;
            border: none;
        }
        
        .zone-marker-content-osm {
            display: flex;
            align-items: center;
            background: linear-gradient(135deg, #0a384f, #79aec8);
            color: white;
            padding: 6px 10px;
            border-radius: 18px;
            box-shadow: 0 3px 10px rgba(10, 56, 79, 0.3);
            border: 2px solid rgba(255, 255, 255, 0.9);
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 90px;
        }
        
        .zone-marker-content-osm:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(10, 56, 79, 0.4);
            background: linear-gradient(135deg, #79aec8, #0a384f);
        }
        
        .zone-marker-icon-osm {
            margin-right: 6px;
            font-size: 14px;
            color: #f7c948;
        }
        
        .zone-marker-label-osm {
            display: flex;
            flex-direction: column;
            line-height: 1.1;
        }
        
        .zone-name-osm {
            font-weight: 700;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        
        .zone-count-osm {
            font-size: 9px;
            opacity: 0.9;
            font-weight: 400;
        }
        
        /* Styles pour les popups */
        .zone-info-popup,
        .zone-marker-popup-osm,
        .contribuable-popup {
            min-width: 200px;
        }
        
        .zone-info-popup h4,
        .zone-marker-popup-osm h4,
        .contribuable-popup h4 {
            margin: 0 0 10px 0;
            color: #0a384f;
            font-size: 14px;
        }
        
        .zone-info-popup p,
        .zone-marker-popup-osm p,
        .contribuable-popup p {
            margin: 5px 0;
            font-size: 12px;
            display: flex;
            align-items: center;
        }
        
        .zone-marker-popup-osm p i,
        .contribuable-popup p i {
            margin-right: 8px;
            width: 14px;
            color: #0a384f;
        }
        
        .contribuable-popup {
            border-left: 4px solid #4CAF50;
            padding-left: 10px;
        }

        .contribuable-popup h4 {
            color: #1a9850;
        }

        /* Animation pour les marqueurs */
        @keyframes zoneMarkerPulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .zone-marker-content-osm:active {
            animation: zoneMarkerPulse 0.2s ease;
        }
        
        /* Responsive pour les marqueurs OSM */
        @media (max-width: 768px) {
            .zone-marker-content-osm {
                min-width: 80px;
                padding: 5px 8px;
            }
            
            .zone-name-osm {
                font-size: 9px;
            }
            
            .zone-count-osm {
                font-size: 8px;
            }
            
            .zone-marker-icon-osm {
                font-size: 12px;
            }
        }
    `;
    document.head.appendChild(style);
}

// Fonction d'initialisation des styles (appelée par le template)
function initMapStyles() {
    addOSMMapStyles();
}