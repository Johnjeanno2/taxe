// static/geolocalisation/js/google_maps_integration.js
// Wrapper Google Maps pour initialiser la carte et ajouter GeoJSON (remplace Leaflet)
function GoogleMapsIntegration(mapId){
  this.mapId = mapId;
  this.map = null;
  this.zonesData = null;
  this.localisationsData = null;
  this.markers = [];
  this.infoWindow = null;
}

GoogleMapsIntegration.prototype.init = function(){
  if(this.map) return;
  // centre par défaut : région de Kaffrine
  var centerSenegal = { lat: 13.8975, lng: -14.4490 };
  // Bounding box approximative du Sénégal (SW, NE)
  var senegalBounds = {
    north: 16.8,
    south: 12.0,
    west: -17.6,
    east: -11.2
  };
  this.map = new google.maps.Map(document.getElementById(this.mapId), {
  center: centerSenegal,
  zoom: 11,
  mapTypeId: 'roadmap',
  // UI optimizations
  streetViewControl: false,
  mapTypeControl: false,
  fullscreenControl: true,
  zoomControl: true,
  scaleControl: true
  });
  // restreindre la navigation à l'intérieur du Sénégal
  try{
    // use strictBounds to prevent the user moving outside the Senegal bbox
    this.map.setOptions({ restriction: { latLngBounds: new google.maps.LatLngBounds(
      new google.maps.LatLng(senegalBounds.south, senegalBounds.west),
      new google.maps.LatLng(senegalBounds.north, senegalBounds.east)
    ), strictBounds: true } });
  }catch(e){ console.warn('set restriction failed', e); }
  this.infoWindow = new google.maps.InfoWindow();
  // stockage des polygons affichés (pour containment tests)
  this.polygons = [];
  this.userMarker = null;
  this.searchMarker = null;
  this.zonesVisible = true;
  this.searchMarkerIcon = null; // allow customizing icon for search marker
  // ajouter la barre d'outils (réinitialiser)
  try { this.addToolbar(); } catch(e) { console.warn('addToolbar failed', e); }
  try { this.addSearchControl(); } catch(e) { console.warn('addSearchControl failed', e); }
  // clic sur la carte: si la carte contient des zones, autoriser placement du marqueur seulement à l'intérieur d'une zone
  var self = this;
  this.map.addListener('click', function(ev){
    try{
      if(!self.polygons || !self.polygons.length){
        // pas de zones chargées: autoriser placement libre
        self.placeMarker(ev.latLng);
        return;
      }
      var insideAny = self.polygons.some(function(p){
        return google.maps.geometry && google.maps.geometry.poly && google.maps.geometry.poly.containsLocation(ev.latLng, p);
      });
      if(insideAny){
        self.placeMarker(ev.latLng);
      } else {
        alert('Veuillez placer le marqueur à l\'intérieur d\'une zone.');
      }
    }catch(e){ console.warn('map click handler error', e); }
  });
};

// add a search input atop the map (uses Places Autocomplete when available)
GoogleMapsIntegration.prototype.addSearchControl = function(){
  if(!this.map) return;
  var map = this.map;
  var container = document.createElement('div');
  container.style.position = 'relative';
  container.style.padding = '8px';

  var input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'Rechercher une adresse ou lieu...';
  input.style.width = '260px';
  input.style.padding = '8px';
  input.style.border = '1px solid rgba(0,0,0,0.2)';
  input.style.borderRadius = '4px';
  input.style.boxShadow = '0 1px 4px rgba(0,0,0,0.2)';
  input.style.background = '#fff';

  container.appendChild(input);
  this.map.controls[google.maps.ControlPosition.TOP_LEFT].push(container);

  var self = this;
  // Prefer Google Places Autocomplete if available
  if(window.google && google.maps && google.maps.places && google.maps.places.Autocomplete){
    var autocomplete = new google.maps.places.Autocomplete(input, { fields: ['geometry','name','formatted_address'] });
    autocomplete.bindTo('bounds', this.map);
    autocomplete.addListener('place_changed', function(){
      var place = autocomplete.getPlace();
      if(!place.geometry) return;
      var loc = place.geometry.location;
  // place search marker and update the id_geom field so backend forms receive the point
  self.placeSearchMarker(loc, place.name || place.formatted_address);
  self.updateGeomField(loc);
      self.map.panTo(loc);
      self.map.setZoom(15);
    });
  } else {
    // fallback: simple text search via backend endpoint if exists
    input.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); self.performSearch(input.value); } });
  }
};

GoogleMapsIntegration.prototype.placeSearchMarker = function(latLng, title){
  try{
    if(this.searchMarker) this.searchMarker.setMap(null);
  var opts = { position: latLng, map: this.map, title: title || '', draggable: true };
  if(this.searchMarkerIcon) opts.icon = this.searchMarkerIcon;
  this.searchMarker = new google.maps.Marker(opts);
    var self = this;
  this.searchMarker.addListener('dragend', function(e){ self.updateGeomField(e.latLng); });
    this.infoWindow.setContent(title || '');
    this.infoWindow.open(this.map, this.searchMarker);
  }catch(e){ console.warn('placeSearchMarker', e); }
};

GoogleMapsIntegration.prototype.resetView = function(){
  if(this.zonesData && this.zonesData.features && this.zonesData.features.length){
    var bounds = new google.maps.LatLngBounds();
    this.zonesData.features.forEach(function(f){
      if(f.properties && f.properties.centroid){
        bounds.extend(new google.maps.LatLng(f.properties.centroid.lat, f.properties.centroid.lng));
      }
    });
    if(!bounds.isEmpty()) this.map.fitBounds(bounds);
    else this.map.setCenter({lat:14.4974, lng:-14.4524});
  } else {
    // Aucun zoneData : centrer et zoomer pour montrer tout le Sénégal
    // Bounding box approximative du Sénégal
    var senegalBounds = new google.maps.LatLngBounds(
      new google.maps.LatLng(12.0, -17.6), // south-west (lat, lng)
      new google.maps.LatLng(16.8, -11.2)  // north-east (lat, lng)
    );
    try {
      this.map.fitBounds(senegalBounds);
    } catch(e) {
      // fallback
      this.map.setCenter({lat:14.4974, lng:-14.4524});
      this.map.setZoom(7);
    }
  }
};

// ajoute une petite barre d'outils en haut à droite (reset)
GoogleMapsIntegration.prototype.addToolbar = function(){
  if(!this.map) return;
  var controlDiv = document.createElement('div');
  controlDiv.style.display = 'flex';
  controlDiv.style.flexDirection = 'column';
  controlDiv.style.gap = '6px';

  var btnReset = document.createElement('button');
  btnReset.type = 'button';
  btnReset.textContent = 'Réinitialiser';
  btnReset.title = 'Réinitialiser la vue';
  btnReset.style.padding = '6px 8px';
  btnReset.style.background = '#fff';
  btnReset.style.border = '1px solid #ccc';
  btnReset.style.borderRadius = '4px';
  btnReset.style.cursor = 'pointer';
  var self = this;
  btnReset.addEventListener('click', function(){ self.resetView(); });

  var btnToggleZones = document.createElement('button');
  btnToggleZones.type = 'button';
  btnToggleZones.textContent = 'Masquer zones';
  btnToggleZones.title = 'Afficher / Masquer les zones';
  btnToggleZones.style.padding = '6px 8px';
  btnToggleZones.style.background = '#fff';
  btnToggleZones.style.border = '1px solid #ccc';
  btnToggleZones.style.borderRadius = '4px';
  btnToggleZones.style.cursor = 'pointer';
  btnToggleZones.addEventListener('click', function(){
    self.zonesVisible = !self.zonesVisible;
    if(self.zonesVisible) {
      btnToggleZones.textContent = 'Masquer zones';
      // réafficher
      if(self.polygons){ self.polygons.forEach(function(p){ p.setMap(self.map); }); }
      if(self.markers){ self.markers.forEach(function(m){ m.setMap(self.map); }); }
    } else {
      btnToggleZones.textContent = 'Afficher zones';
      if(self.polygons){ self.polygons.forEach(function(p){ p.setMap(null); }); }
      if(self.markers){ self.markers.forEach(function(m){ m.setMap(null); }); }
    }
  });

  controlDiv.appendChild(btnToggleZones);

  controlDiv.appendChild(btnReset);
  this.map.controls[google.maps.ControlPosition.TOP_RIGHT].push(controlDiv);
};

// place un marqueur utilisateur (unique) et met à jour le champ id_geom si présent
GoogleMapsIntegration.prototype.placeMarker = function(latLng){
  try{
    if(this.userMarker) this.userMarker.setMap(null);
    this.userMarker = new google.maps.Marker({ position: latLng, map: this.map, draggable: true });
    var self = this;
    this.userMarker.addListener('dragend', function(e){ self.updateGeomField(e.latLng); });
    this.updateGeomField(latLng);
    this.map.panTo(latLng);
  }catch(e){ console.warn('placeMarker error', e); }
};

GoogleMapsIntegration.prototype.updateGeomField = function(latLng){
  try{
    var geomField = document.getElementById('id_geom');
    if(geomField) geomField.value = 'POINT(' + latLng.lng() + ' ' + latLng.lat() + ')';
  }catch(e){ console.warn('updateGeomField error', e); }
};

GoogleMapsIntegration.prototype.performSearch = function(query){
  // Appel au backend existant (search_location) pour trouver zone/localisation
  var self = this;
  fetch('/geolocalisation/search/?q=' + encodeURIComponent(query))
    .then(r=>r.json())
    .then(data=>{
      if(data.lat && data.lng){
        var pos = { lat: parseFloat(data.lat), lng: parseFloat(data.lng) };
        self.map.setCenter(pos);
        self.map.setZoom(14);
        self.infoWindow.setContent('<div><strong>'+ (data.label||'') +'</strong><div style="font-size:0.85em;color:#666">Type: '+(data.type||'')+'</div></div>');
        self.infoWindow.setPosition(pos);
        self.infoWindow.open(self.map);
      }
    }).catch(e=>{ console.warn('search error', e); });
};

GoogleMapsIntegration.prototype.addZonesFromGeoJSON = function(geojson){
  try{
    this.zonesData = geojson;
    var map = this.map;
    var self = this;
    // Dessiner polygones
    geojson.features.forEach(function(feature){
      if(!feature.geometry) return;
      if(feature.geometry.type === 'Polygon' || feature.geometry.type === 'MultiPolygon'){
        var paths = [];
        if(feature.geometry.type === 'Polygon'){
          paths = feature.geometry.coordinates[0].map(function(c){ return {lat: c[1], lng: c[0]}; });
        } else {
          // prendre le premier anneau du premier poly
          paths = feature.geometry.coordinates[0][0].map(function(c){ return {lat: c[1], lng: c[0]}; });
        }
  var polygon = new google.maps.Polygon({
          paths: paths,
          strokeColor: '#0a384f',
          strokeOpacity: 0.8,
          strokeWeight: 2,
          fillColor: '#79aec8',
          fillOpacity: 0.15
        });
        polygon.setMap(map);
  // conserver la référence pour tests de containment
  if(self && self.polygons) self.polygons.push(polygon);
        polygon.addListener('click', function(ev){
          var props = feature.properties || {};
          var html = '<div><strong>' + (props.nom||props.name||'Zone') + '</strong>' + (props.count_contribuables ? '<div>'+props.count_contribuables+' contribuables</div>' : '') + '</div>';
          self.infoWindow.setContent(html);
          self.infoWindow.setPosition(ev.latLng);
          self.infoWindow.open(map);
        });
      }
      // Ajouter marqueur de zone si centroid fourni
      if(feature.properties && feature.properties.centroid){
        var c = feature.properties.centroid;
        var marker = new google.maps.Marker({
          position: {lat: c.lat, lng: c.lng},
          map: map,
          title: feature.properties.nom || feature.properties.name || 'Zone'
        });
        marker.addListener('click', function(){
          var props = feature.properties || {};
          var html = '<div><strong>' + (props.nom||props.name||'Zone') + '</strong>' + (props.count_contribuables ? '<div>'+props.count_contribuables+' contribuables</div>' : '') + '</div>';
          self.infoWindow.setContent(html);
          self.infoWindow.open(map, marker);
        });
        self.markers.push(marker);
      }
    });
    this.resetView();
  }catch(e){ console.warn('addZonesFromGeoJSON', e); }
};

GoogleMapsIntegration.prototype.addLocalisationsFromGeoJSON = function(geojson){
  try{
    this.localisationsData = geojson;
    var map = this.map;
    var self = this;
    geojson.features.forEach(function(feature){
      if(!feature.geometry) return;
      var coords = feature.geometry.coordinates;
      var lat = coords[1], lng = coords[0];
      var title = (feature.properties && (feature.properties.contribuable__nom || feature.properties.name)) || 'Contribuable';
      var marker = new google.maps.Marker({
        position: {lat: lat, lng: lng},
        map: map,
        title: title
      });
      marker.addListener('mouseover', function(){
        // simple infowindow
        var props = feature.properties || {};
        var html = '<div><strong>' + (props.contribuable__nom || props.name || '') + '</strong>' + (props.zone__nom ? '<div>Zone: '+props.zone__nom+'</div>' : '') + '</div>';
        self.infoWindow.setContent(html);
        self.infoWindow.open(map, marker);
      });
      marker.addListener('mouseout', function(){ self.infoWindow.close(); });
      self.markers.push(marker);
    });
  }catch(e){ console.warn('addLocalisationsFromGeoJSON', e); }
};

// Styles init (reprise du CSS du fichier OSM pour cohérence)
function initMapStyles() {
  // Reuse existing CSS by leaving the OSM styles injection intact; this function kept for compatibility
}

// export pour compatibilité avec le template
window.GoogleMapsIntegration = GoogleMapsIntegration;
(function(global){
  // création UI recherche (input + bouton)
  function createSearchControl(map, options) {
    options = options || {};
    const container = document.createElement('div');
    container.className = 'gmi-search-control';

    const input = document.createElement('input');
    input.type = 'search';
    input.placeholder = options.placeholder || 'Rechercher une adresse ou lieu...';
    input.id = options.inputId || 'gmi-search-input';
    input.className = 'gmi-search-input';

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'gmi-search-btn';
    btn.textContent = options.btnText || 'Rechercher';

    container.appendChild(input);
    container.appendChild(btn);

    // attach to map controls (top-left)
    map.controls[google.maps.ControlPosition.TOP_LEFT].push(container);

    // helper: perform search (fallback to backend)
    async function performSearch(q) {
      if (!q) return;
      // try backend search endpoint - adjust URL if different
      try {
        const res = await fetch(`/geolocalisation/search_location/?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error('Recherche serveur échouée');
        const data = await res.json();
        if (data && data.lat && data.lng) {
          const latlng = new google.maps.LatLng(data.lat, data.lng);
          placeSearchMarker(map, latlng, data.label || q);
          map.setCenter(latlng);
          map.setZoom(options.searchZoom || 15);
        } else {
          console.warn('Aucun résultat de recherche', data);
          alert('Aucun résultat trouvé');
        }
      } catch (err) {
        console.error('performSearch error', err);
        alert('Erreur lors de la recherche (voir console)');
      }
    }

    // if Places Autocomplete available, wire it (preferred)
    let autocomplete;
    if (window.google && google.maps && google.maps.places) {
      autocomplete = new google.maps.places.Autocomplete(input);
      autocomplete.bindTo('bounds', map);
      autocomplete.addListener('place_changed', function(){
        const place = autocomplete.getPlace();
        if (!place.geometry) {
          // fallback to backend
          performSearch(input.value);
          return;
        }
        const loc = place.geometry.location;
        placeSearchMarker(map, loc, place.formatted_address || place.name || input.value);
        map.panTo(loc);
        map.setZoom(options.searchZoom || 15);
      });
    }

    // handle button click and Enter key
    btn.addEventListener('click', function(){ 
      if (autocomplete) {
        // if autocomplete present, selecting via input is preferred
        // but trigger fallback if no selection
        const place = autocomplete.getPlace && autocomplete.getPlace();
        if (!place || !place.geometry) {
          performSearch(input.value);
        }
      } else {
        performSearch(input.value);
      }
    });

    input.addEventListener('keydown', function(e){
      if (e.key === 'Enter') {
        e.preventDefault();
        btn.click();
      }
    });

    return { container, input, btn, autocomplete };
  }

  // helper to place a search marker and update id_geom
  function placeSearchMarker(map, latlng, title) {
    if (!window.googleMapsSearchMarker) {
      window.googleMapsSearchMarker = new google.maps.Marker({
        map: map,
        position: latlng,
        draggable: true,
        title: title || 'Recherche',
        icon: window.googleMapsApp && window.googleMapsApp.searchMarkerIcon || null
      });
      window.googleMapsSearchMarker.addListener('dragend', function(){
        updateGeomFieldFromLatLng(window.googleMapsSearchMarker.getPosition());
      });
    } else {
      window.googleMapsSearchMarker.setPosition(latlng);
      window.googleMapsSearchMarker.setTitle(title || '');
      window.googleMapsSearchMarker.setMap(map);
    }
    updateGeomFieldFromLatLng(latlng);
  }

  function updateGeomFieldFromLatLng(latlng) {
    if (!latlng) return;
    // WKT POINT(lon lat)
    const wkt = `POINT(${latlng.lng()} ${latlng.lat()})`;
    const el = document.getElementById('id_geom');
    if (el) {
      el.value = wkt;
      const evt = new Event('change', { bubbles: true });
      el.dispatchEvent(evt);
    } else {
      console.warn('updateGeomField: id_geom introuvable');
    }
  }

  // expose helpers on global integration object if needed
  global.GoogleMapsIntegration = global.GoogleMapsIntegration || {};
  global.GoogleMapsIntegration.createSearchControl = createSearchControl;
  global.GoogleMapsIntegration.placeSearchMarker = placeSearchMarker;
  global.GoogleMapsIntegration.updateGeomFieldFromLatLng = updateGeomFieldFromLatLng;

})(window);