document.addEventListener('DOMContentLoaded', function() {
    // 1. Gestion du champ contribuable
    const contribuableField = document.getElementById('id_contribuable');
    const contribuableLookup = document.querySelector('[href*="/contribuable/"]');
    
    if (contribuableField && contribuableLookup) {
        // Modifie le lien de recherche pour éviter la popup
        contribuableLookup.href = contribuableLookup.href.replace('_popup=1', '_popup=0');
        
        // Met à jour le nom du contribuable après sélection
        contribuableField.addEventListener('change', function() {
            if (this.value) {
                fetch(`/admin/gestion_contribuables/contribuable/${this.value}/change/`)
                    .then(response => response.text())
                    .then(html => {
                        const doc = new DOMParser().parseFromString(html, 'text/html');
                        const nom = doc.getElementById('id_nom').value;
                        if (nom) {
                            const display = document.querySelector('.field-contribuable .readonly');
                            if (display) {
                                display.textContent = nom;
                            }
                        }
                    });
            }
        });
    }

    // 2. Gestion de la soumission du formulaire
    const form = document.getElementById('localisationcontribuable_form');
    if (form) {
        form.addEventListener('submit', function(e) {
            // Ajoute un paramètre pour rester sur la page
            if (!document.querySelector('input[name="_continue"]')) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = '_continue';
                input.value = '1';
                form.appendChild(input);
            }
        });
    }

    // 3. Initialisation avancée de la carte pour les localisations
    if (typeof map !== 'undefined') {
        // Configuration spécifique pour les localisations
        map.setView([14.7167, -16.9667], 12); // Centrer sur Mbour
        
        // Variables pour la gestion des couches
        let zonesLayer = null;
        let currentMarker = null;
        let selectedZone = null;
        
        // Styles pour les zones
        const zonesStyle = {
            color: '#0a384f',
            weight: 3,
            opacity: 0.8,
            fillColor: '#79aec8',
            fillOpacity: 0.15,
            dashArray: '5, 5'
        };
        
        const selectedZoneStyle = {
            color: '#d17e54',
            weight: 4,
            opacity: 1,
            fillColor: '#d17e54',
            fillOpacity: 0.25,
            dashArray: null
        };
        
        const hoverZoneStyle = {
            color: '#f7c948',
            weight: 4,
            opacity: 0.9,
            fillOpacity: 0.3
        };
        
        // Variables pour les marqueurs de zones
        let zoneMarkersLayer = null;
        
        // Fonction pour charger et afficher toutes les zones
        function loadZones() {
            fetch('/geolocalisation/api/zones/all-geojson/')
                .then(response => response.json())
                .then(data => {
                    if (zonesLayer) {
                        map.removeLayer(zonesLayer);
                    }
                    if (zoneMarkersLayer) {
                        map.removeLayer(zoneMarkersLayer);
                    }
                    
                    // Créer les délimitations des zones
                    zonesLayer = L.geoJSON(data, {
                        style: zonesStyle,
                        onEachFeature: function(feature, layer) {
                            const props = feature.properties;
                            
                            // Popup avec informations détaillées
                            const popupContent = `
                                <div class="zone-popup">
                                    <h4 style="margin: 0 0 10px 0; color: #0a384f;">
                                        <i class="fas fa-map-marker-alt"></i> ${props.nom}
                                    </h4>
                                    <div class="zone-info">
                                        <p><strong>Contribuables:</strong> ${props.count_contribuables}</p>
                                        ${props.responsable ? `<p><strong>Responsable:</strong> ${props.responsable}</p>` : ''}
                                        <p><strong>Créée le:</strong> ${new Date(props.date_creation).toLocaleDateString('fr-FR')}</p>
                                    </div>
                                    <div class="zone-actions" style="margin-top: 10px;">
                                        <button onclick="selectZone(${props.id}, '${props.nom}')" 
                                                class="btn btn-sm btn-primary">
                                            <i class="fas fa-check"></i> Sélectionner cette zone
                                        </button>
                                        <button onclick="centerOnZone(${props.id})" 
                                                class="btn btn-sm btn-info" style="margin-left: 5px;">
                                            <i class="fas fa-crosshairs"></i> Centrer
                                        </button>
                                    </div>
                                </div>
                            `;
                            
                            layer.bindPopup(popupContent);
                            
                            // Effets de survol
                            layer.on({
                                mouseover: function(e) {
                                    if (selectedZone !== props.id) {
                                        layer.setStyle(hoverZoneStyle);
                                    }
                                },
                                mouseout: function(e) {
                                    if (selectedZone !== props.id) {
                                        layer.setStyle(zonesStyle);
                                    }
                                },
                                click: function(e) {
                                    // Centrer la carte sur la zone cliquée
                                    map.fitBounds(layer.getBounds(), {padding: [20, 20]});
                                }
                            });
                            
                            // Stocker la référence de la couche pour pouvoir la modifier
                            layer.zoneId = props.id;
                        }
                    }).addTo(map);
                    
                    // Créer les marqueurs centraux pour chaque zone
                    createZoneMarkers(data);
                    
                    console.log(`✅ ${data.total_zones} zones chargées avec délimitations et marqueurs`);
                })
                .catch(error => {
                    console.error('❌ Erreur lors du chargement des zones:', error);
                });
        }
        
        // Fonction pour créer les marqueurs centraux des zones
        function createZoneMarkers(geojsonData) {
            const markers = [];
            
            geojsonData.features.forEach(function(feature) {
                const props = feature.properties;
                const centroid = props.centroid;
                
                if (centroid && centroid.lat && centroid.lng) {
                    // Créer une icône personnalisée pour chaque zone
                    const zoneIcon = L.divIcon({
                        className: 'zone-marker',
                        html: `
                            <div class="zone-marker-content" data-zone-id="${props.id}">
                                <div class="zone-marker-icon">
                                    <i class="fas fa-map-marked-alt"></i>
                                </div>
                                <div class="zone-marker-label">
                                    <span class="zone-name">${props.nom}</span>
                                    <span class="zone-count">${props.count_contribuables} contrib.</span>
                                </div>
                            </div>
                        `,
                        iconSize: [120, 40],
                        iconAnchor: [60, 20]
                    });
                    
                    const marker = L.marker([centroid.lat, centroid.lng], {
                        icon: zoneIcon,
                        zIndex: 1000
                    });
                    
                    // Popup pour le marqueur de zone
                    const markerPopupContent = `
                        <div class="zone-marker-popup">
                            <h4 style="margin: 0 0 10px 0; color: #0a384f;">
                                <i class="fas fa-map-marked-alt"></i> Zone ${props.nom}
                            </h4>
                            <div class="zone-stats">
                                <div class="stat-item">
                                    <i class="fas fa-users"></i>
                                    <span><strong>${props.count_contribuables}</strong> contribuables</span>
                                </div>
                                ${props.responsable ? `
                                <div class="stat-item">
                                    <i class="fas fa-user-tie"></i>
                                    <span><strong>Responsable:</strong> ${props.responsable}</span>
                                </div>
                                ` : ''}
                                <div class="stat-item">
                                    <i class="fas fa-calendar"></i>
                                    <span><strong>Créée:</strong> ${new Date(props.date_creation).toLocaleDateString('fr-FR')}</span>
                                </div>
                            </div>
                            <div class="zone-marker-actions" style="margin-top: 15px;">
                                <button onclick="selectZone(${props.id}, '${props.nom}')" 
                                        class="btn btn-sm btn-primary">
                                    <i class="fas fa-check"></i> Sélectionner
                                </button>
                                <button onclick="showZoneBounds(${props.id})" 
                                        class="btn btn-sm btn-secondary" style="margin-left: 5px;">
                                    <i class="fas fa-expand"></i> Voir délimitations
                                </button>
                            </div>
                        </div>
                    `;
                    
                    marker.bindPopup(markerPopupContent);
                    
                    // Événements pour le marqueur
                    marker.on({
                        mouseover: function(e) {
                            // Mettre en surbrillance la zone correspondante
                            if (zonesLayer) {
                                zonesLayer.eachLayer(function(layer) {
                                    if (layer.zoneId === props.id) {
                                        layer.setStyle(hoverZoneStyle);
                                    }
                                });
                            }
                        },
                        mouseout: function(e) {
                            // Remettre le style normal si la zone n'est pas sélectionnée
                            if (selectedZone !== props.id && zonesLayer) {
                                zonesLayer.eachLayer(function(layer) {
                                    if (layer.zoneId === props.id) {
                                        layer.setStyle(zonesStyle);
                                    }
                                });
                            }
                        },
                        click: function(e) {
                            // Ouvrir le popup et centrer sur la zone
                            marker.openPopup();
                            centerOnZone(props.id);
                        }
                    });
                    
                    markers.push(marker);
                }
            });
            
            // Créer un groupe de marqueurs
            zoneMarkersLayer = L.layerGroup(markers).addTo(map);
        }
        
        // Fonction pour centrer sur une zone spécifique
        window.centerOnZone = function(zoneId) {
            if (zonesLayer) {
                zonesLayer.eachLayer(function(layer) {
                    if (layer.zoneId === zoneId) {
                        map.fitBounds(layer.getBounds(), {padding: [20, 20]});
                        layer.openPopup();
                    }
                });
            }
        };
        
        // Fonction pour afficher les délimitations d'une zone
        window.showZoneBounds = function(zoneId) {
            if (zonesLayer) {
                zonesLayer.eachLayer(function(layer) {
                    if (layer.zoneId === zoneId) {
                        // Mettre en évidence temporairement
                        const originalStyle = layer.options.style || zonesStyle;
                        layer.setStyle({
                            color: '#ff6b6b',
                            weight: 5,
                            opacity: 1,
                            fillColor: '#ff6b6b',
                            fillOpacity: 0.3,
                            dashArray: null
                        });
                        
                        // Centrer sur la zone
                        map.fitBounds(layer.getBounds(), {padding: [20, 20]});
                        
                        // Remettre le style original après 3 secondes
                        setTimeout(() => {
                            if (selectedZone === zoneId) {
                                layer.setStyle(selectedZoneStyle);
                            } else {
                                layer.setStyle(zonesStyle);
                            }
                        }, 3000);
                        
                        showNotification(`Délimitations de la zone "${layer.feature.properties.nom}" mises en évidence`, 'info');
                    }
                });
            }
        };
        
        // Fonction pour sélectionner une zone
        window.selectZone = function(zoneId, zoneName) {
            selectedZone = zoneId;
            
            // Mettre à jour le champ zone dans le formulaire
            const zoneField = document.getElementById('id_zone');
            if (zoneField) {
                zoneField.value = zoneId;
                
                // Déclencher l'événement change pour les éventuels listeners
                const event = new Event('change', { bubbles: true });
                zoneField.dispatchEvent(event);
            }
            
            // Mettre à jour les styles des zones
            if (zonesLayer) {
                zonesLayer.eachLayer(function(layer) {
                    if (layer.zoneId === zoneId) {
                        layer.setStyle(selectedZoneStyle);
                    } else {
                        layer.setStyle(zonesStyle);
                    }
                });
            }
            
            // Afficher un message de confirmation
            showNotification(`Zone "${zoneName}" sélectionnée`, 'success');
        };
        
        // Fonction pour placer un marqueur précis
        function placeMarker(latlng) {
            // Supprimer le marqueur existant
            if (currentMarker) {
                map.removeLayer(currentMarker);
            }
            
            // Créer un nouveau marqueur avec style personnalisé
            const markerIcon = L.divIcon({
                className: 'custom-marker',
                html: '<i class="fas fa-map-pin" style="color: #d17e54; font-size: 24px;"></i>',
                iconSize: [24, 24],
                iconAnchor: [12, 24]
            });
            
            currentMarker = L.marker(latlng, {
                icon: markerIcon,
                draggable: true
            }).addTo(map);
            
            // Popup pour le marqueur
            currentMarker.bindPopup(`
                <div class="marker-popup">
                    <h5><i class="fas fa-map-pin"></i> Position du contribuable</h5>
                    <p><strong>Latitude:</strong> ${latlng.lat.toFixed(6)}</p>
                    <p><strong>Longitude:</strong> ${latlng.lng.toFixed(6)}</p>
                    <small>Vous pouvez déplacer ce marqueur en le faisant glisser</small>
                </div>
            `).openPopup();
            
            // Mettre à jour les champs du formulaire
            updateGeomField(latlng);
            
            // Événement de déplacement du marqueur
            currentMarker.on('dragend', function(e) {
                const newPos = e.target.getLatLng();
                updateGeomField(newPos);
                
                // Mettre à jour le popup
                currentMarker.setPopupContent(`
                    <div class="marker-popup">
                        <h5><i class="fas fa-map-pin"></i> Position du contribuable</h5>
                        <p><strong>Latitude:</strong> ${newPos.lat.toFixed(6)}</p>
                        <p><strong>Longitude:</strong> ${newPos.lng.toFixed(6)}</p>
                        <small>Position mise à jour!</small>
                    </div>
                `);
            });
            
            // Vérifier si le marqueur est dans une zone
            checkMarkerInZone(latlng);
        }
        
        // Fonction pour mettre à jour le champ geom
        function updateGeomField(latlng) {
            const geomField = document.getElementById('id_geom');
            if (geomField) {
                // Format POINT(longitude latitude)
                geomField.value = `POINT(${latlng.lng} ${latlng.lat})`;
            }
        }
        
        // Fonction pour vérifier si le marqueur est dans une zone
        function checkMarkerInZone(latlng) {
            if (!zonesLayer) return;
            
            let foundZone = null;
            zonesLayer.eachLayer(function(layer) {
                // Utiliser la méthode Leaflet pour vérifier si le point est dans le polygone
                if (layer.getBounds().contains(latlng)) {
                    // Vérification plus précise avec les coordonnées du polygone
                    const feature = layer.feature;
                    if (isPointInPolygon(latlng, feature.geometry.coordinates[0])) {
                        foundZone = {
                            id: layer.zoneId,
                            name: feature.properties.nom
                        };
                    }
                }
            });
            
            if (foundZone) {
                selectZone(foundZone.id, foundZone.name);
                showNotification(`Contribuable automatiquement assigné à la zone "${foundZone.name}"`, 'info');
            }
        }
        
        // Fonction pour vérifier si un point est dans un polygone
        function isPointInPolygon(point, polygon) {
            const x = point.lng, y = point.lat;
            let inside = false;
            
            for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
                const xi = polygon[i][0], yi = polygon[i][1];
                const xj = polygon[j][0], yj = polygon[j][1];
                
                if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
                    inside = !inside;
                }
            }
            
            return inside;
        }
        
        // Fonction pour afficher des notifications
        function showNotification(message, type = 'info') {
            // Créer ou réutiliser le conteneur de notifications
            let notificationContainer = document.getElementById('map-notifications');
            if (!notificationContainer) {
                notificationContainer = document.createElement('div');
                notificationContainer.id = 'map-notifications';
                notificationContainer.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 10000;
                    max-width: 300px;
                `;
                document.body.appendChild(notificationContainer);
            }
            
            // Créer la notification
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} alert-dismissible`;
            notification.style.cssText = `
                margin-bottom: 10px;
                padding: 10px 15px;
                border-radius: 5px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: slideInRight 0.3s ease;
            `;
            
            const colors = {
                success: '#d4edda',
                info: '#d1ecf1',
                warning: '#fff3cd',
                error: '#f8d7da'
            };
            
            notification.style.backgroundColor = colors[type] || colors.info;
            notification.innerHTML = `
                <span>${message}</span>
                <button type="button" class="close" onclick="this.parentElement.remove()">
                    <span>&times;</span>
                </button>
            `;
            
            notificationContainer.appendChild(notification);
            
            // Auto-suppression après 5 secondes
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 5000);
        }
        
        // Gestionnaire de clic sur la carte pour placer un marqueur
        map.on('click', function(e) {
            placeMarker(e.latlng);
        });
        
        // Charger les zones au démarrage
        loadZones();
        
        // Ajouter les instructions, la légende et les contrôles
        addMapInstructions();
        addMapLegend();
        addMapControls();
        
        // Fonction pour ajouter les contrôles de la carte
        function addMapControls() {
            const controls = document.createElement('div');
            controls.className = 'map-controls';
            controls.innerHTML = `
                <h6><i class="fas fa-cogs"></i> Contrôles de la carte</h6>
                <div class="control-group">
                    <label class="control-item">
                        <input type="checkbox" id="toggle-zones" checked>
                        <span class="checkmark"></span>
                        Afficher les délimitations des zones
                    </label>
                    <label class="control-item">
                        <input type="checkbox" id="toggle-zone-markers" checked>
                        <span class="checkmark"></span>
                        Afficher les marqueurs de zones
                    </label>
                    <label class="control-item">
                        <input type="checkbox" id="show-zone-labels" checked>
                        <span class="checkmark"></span>
                        Afficher les étiquettes des zones
                    </label>
                </div>
                <div class="control-actions">
                    <button onclick="fitAllZones()" class="btn btn-sm btn-info">
                        <i class="fas fa-expand-arrows-alt"></i> Voir toutes les zones
                    </button>
                    <button onclick="refreshZones()" class="btn btn-sm btn-secondary">
                        <i class="fas fa-sync-alt"></i> Actualiser
                    </button>
                </div>
            `;
            
            // Ajouter au conteneur de la carte
            const mapContainer = document.querySelector('.leaflet-container');
            if (mapContainer && mapContainer.parentElement) {
                mapContainer.parentElement.insertBefore(controls, mapContainer);
            }
            
            // Ajouter les événements pour les contrôles
            setupControlEvents();
        }
        
        // Fonction pour configurer les événements des contrôles
        function setupControlEvents() {
            // Contrôle de visibilité des zones
            const toggleZones = document.getElementById('toggle-zones');
            if (toggleZones) {
                toggleZones.addEventListener('change', function() {
                    if (zonesLayer) {
                        if (this.checked) {
                            map.addLayer(zonesLayer);
                        } else {
                            map.removeLayer(zonesLayer);
                        }
                    }
                });
            }
            
            // Contrôle de visibilité des marqueurs de zones
            const toggleZoneMarkers = document.getElementById('toggle-zone-markers');
            if (toggleZoneMarkers) {
                toggleZoneMarkers.addEventListener('change', function() {
                    if (zoneMarkersLayer) {
                        if (this.checked) {
                            map.addLayer(zoneMarkersLayer);
                        } else {
                            map.removeLayer(zoneMarkersLayer);
                        }
                    }
                });
            }
            
            // Contrôle des étiquettes de zones
            const showZoneLabels = document.getElementById('show-zone-labels');
            if (showZoneLabels) {
                showZoneLabels.addEventListener('change', function() {
                    const markers = document.querySelectorAll('.zone-marker-content');
                    markers.forEach(marker => {
                        const label = marker.querySelector('.zone-marker-label');
                        if (label) {
                            label.style.display = this.checked ? 'flex' : 'none';
                        }
                    });
                });
            }
        }
        
        // Fonction pour ajuster la vue sur toutes les zones
        window.fitAllZones = function() {
            if (zonesLayer) {
                map.fitBounds(zonesLayer.getBounds(), {padding: [20, 20]});
                showNotification('Vue ajustée sur toutes les zones', 'info');
            }
        };
        
        // Fonction pour actualiser les zones
        window.refreshZones = function() {
            showNotification('Actualisation des zones...', 'info');
            loadZones();
        };
        
        // Fonction pour ajouter les instructions
        function addMapInstructions() {
            const instructions = document.createElement('div');
            instructions.className = 'map-instructions';
            instructions.innerHTML = `
                <h5><i class="fas fa-info-circle"></i> Instructions</h5>
                <div class="instructions-content">
                    <div class="instruction-group">
                        <h6><i class="fas fa-mouse-pointer"></i> Navigation</h6>
                        <ul>
                            <li><strong>Cliquez</strong> sur la carte pour placer le marqueur du contribuable</li>
                            <li><strong>Survolez</strong> les zones pour voir leurs informations</li>
                            <li><strong>Cliquez</strong> sur une zone ou son marqueur pour la sélectionner</li>
                        </ul>
                    </div>
                    <div class="instruction-group">
                        <h6><i class="fas fa-edit"></i> Édition</h6>
                        <ul>
                            <li><strong>Déplacez</strong> le marqueur rouge en le faisant glisser</li>
                            <li>La zone sera <strong>automatiquement détectée</strong> selon la position</li>
                            <li>Utilisez les <strong>contrôles</strong> pour personnaliser l'affichage</li>
                        </ul>
                    </div>
                </div>
            `;
            
            // Ajouter au conteneur de la carte
            const mapContainer = document.querySelector('.leaflet-container');
            if (mapContainer && mapContainer.parentElement) {
                mapContainer.parentElement.insertBefore(instructions, mapContainer);
            }
        }
        
        // Fonction pour ajouter la légende
        function addMapLegend() {
            const legend = document.createElement('div');
            legend.className = 'map-legend';
            legend.innerHTML = `
                <h6><i class="fas fa-map"></i> Légende</h6>
                <div class="legend-item">
                    <div class="legend-color zone-default"></div>
                    <span>Zones disponibles</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color zone-hover"></div>
                    <span>Zone survolée</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color zone-selected"></div>
                    <span>Zone sélectionnée</span>
                </div>
                <div class="legend-item">
                    <div class="legend-marker zone-marker-legend">
                        <i class="fas fa-map-marked-alt"></i>
                    </div>
                    <span>Marqueurs de zones</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color marker"></div>
                    <span>Position du contribuable</span>
                </div>
            `;
            
            // Ajouter au conteneur de la carte
            const mapContainer = document.querySelector('.leaflet-container');
            if (mapContainer && mapContainer.parentElement) {
                mapContainer.parentElement.appendChild(legend);
            }
        }
        
        // Ajouter des styles CSS pour les éléments personnalisés
        const style = document.createElement('style');
        style.textContent = `
            .custom-marker {
                background: none;
                border: none;
            }
            
            /* Styles pour les marqueurs de zones */
            .zone-marker {
                background: none;
                border: none;
            }

            /* ... styles omitted for brevity in backup ... */
        `;
        document.head.appendChild(style);
    }
});
