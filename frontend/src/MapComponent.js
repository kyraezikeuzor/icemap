import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';

// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Import leaflet.heat dynamically
let HeatLayer;
try {
    require('leaflet.heat');
    HeatLayer = L.heatLayer;
} catch (error) {
    console.warn('leaflet.heat not available, falling back to basic implementation');
    // Fallback implementation
    HeatLayer = function (data, options) {
        const layer = L.layerGroup();
        data.forEach(point => {
            const circle = L.circle([point[0], point[1]], {
                radius: options.radius || 20,
                fillColor: '#8B0000', // Dark maroon
                color: '#8B0000',
                weight: 1,
                opacity: 0.8,
                fillOpacity: Math.min(point[2] / 5, 0.9), // More sensitive to fewer arrests
                interactive: false // Ensure circles don't block clicks
            });
            layer.addLayer(circle);
        });
        return layer;
    };
}

// Heat map layer component
function HeatMapLayer({ arrestData, onAreaClick }) {
    const map = useMap();
    const heatLayerRef = useRef(null);
    const clickIndicatorRef = useRef(null);
    const [currentZoom, setCurrentZoom] = useState(map.getZoom());

    // Function to calculate clustering radius based on zoom level
    const getClusterRadius = (zoom) => {
        if (zoom >= 10) return 0.001; // Very close points at high zoom
        if (zoom >= 8) return 0.005;  // Close points at medium-high zoom
        if (zoom >= 6) return 0.02;   // Medium distance at medium zoom
        if (zoom >= 4) return 0.05;   // Further distance at low-medium zoom
        return 0.1;                   // Far distance at low zoom
    };

    // Function to cluster points based on proximity
    const clusterPoints = (points, radius) => {
        const clusters = [];
        const used = new Set();

        points.forEach((point, index) => {
            if (used.has(index)) return;

            const cluster = [point];
            used.add(index);

            // Find nearby points
            points.forEach((otherPoint, otherIndex) => {
                if (used.has(otherIndex)) return;

                const distance = Math.sqrt(
                    Math.pow(point.lat - otherPoint.lat, 2) +
                    Math.pow(point.lng - otherPoint.lng, 2)
                );

                if (distance <= radius) {
                    cluster.push(otherPoint);
                    used.add(otherIndex);
                }
            });

            clusters.push(cluster);
        });

        return clusters;
    };

    // Function to create heat map data from clusters
    const createHeatMapData = (clusters) => {
        return clusters.map(cluster => {
            const centerLat = cluster.reduce((sum, p) => sum + p.lat, 0) / cluster.length;
            const centerLng = cluster.reduce((sum, p) => sum + p.lng, 0) / cluster.length;
            const intensity = cluster.length; // Intensity based on number of points in cluster

            return [centerLat, centerLng, intensity];
        });
    };

    // Function to find incidents within a clicked area
    const findIncidentsInArea = (clickLat, clickLng, radius) => {
        return arrestData.filter(arrest => {
            const lat = parseFloat(arrest.latitude);
            const lng = parseFloat(arrest.longitude);

            if (isNaN(lat) || isNaN(lng)) return false;

            const distance = Math.sqrt(
                Math.pow(lat - clickLat, 2) + Math.pow(lng - clickLng, 2)
            );

            return distance <= radius;
        });
    };

    useEffect(() => {
        if (!arrestData || arrestData.length === 0) return;

        // Convert arrest data to points
        const points = arrestData
            .map(arrest => ({
                lat: parseFloat(arrest.latitude),
                lng: parseFloat(arrest.longitude),
                data: arrest
            }))
            .filter(point => !isNaN(point.lat) && !isNaN(point.lng));

        // Get current zoom and cluster radius
        const radius = getClusterRadius(currentZoom);
        const clusters = clusterPoints(points, radius);
        const heatMapData = createHeatMapData(clusters);

        // Remove existing heat layer
        if (heatLayerRef.current) {
            map.removeLayer(heatLayerRef.current);
        }

        // Create new heat layer with yellow-to-dark-maroon gradient
        heatLayerRef.current = HeatLayer(heatMapData, {
            radius: Math.max(25, 60 - currentZoom * 2), // Slightly larger radius
            blur: 20,
            maxZoom: 10,
            gradient: {
                0.0: '#FFFF00',   // Yellow for low intensity
                0.2: '#FFD700',   // Gold
                0.4: '#FF8C00',   // Dark orange
                0.6: '#DC143C',   // Crimson
                0.8: '#B22222',   // Fire brick
                1.0: '#8B0000'    // Dark maroon for high intensity
            }
        });

        map.addLayer(heatLayerRef.current);

        // Add click handler to the map with improved detection
        const handleMapClick = (e) => {
            console.log('Map clicked at:', e.latlng); // Debug log

            // Add a visual click indicator
            if (clickIndicatorRef.current) {
                map.removeLayer(clickIndicatorRef.current);
            }

            clickIndicatorRef.current = L.circleMarker([e.latlng.lat, e.latlng.lng], {
                radius: 8,
                fillColor: '#FF0000',
                color: '#FF0000',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            }).addTo(map);

            // Remove the indicator after 2 seconds
            setTimeout(() => {
                if (clickIndicatorRef.current) {
                    map.removeLayer(clickIndicatorRef.current);
                    clickIndicatorRef.current = null;
                }
            }, 2000);

            // Use a larger click radius for better detection
            const clickRadius = Math.max(getClusterRadius(currentZoom) * 2, 0.01);
            console.log('Click radius:', clickRadius); // Debug log

            const incidents = findIncidentsInArea(e.latlng.lat, e.latlng.lng, clickRadius);
            console.log('Found incidents:', incidents.length); // Debug log

            if (incidents.length > 0) {
                console.log('Calling onAreaClick with', incidents.length, 'incidents'); // Debug log
                onAreaClick(incidents);
            } else {
                console.log('No incidents found in clicked area'); // Debug log
            }
        };

        // Remove any existing click handlers first
        map.off('click', handleMapClick);
        map.on('click', handleMapClick);

        return () => {
            if (heatLayerRef.current) {
                map.removeLayer(heatLayerRef.current);
            }
            if (clickIndicatorRef.current) {
                map.removeLayer(clickIndicatorRef.current);
            }
            map.off('click', handleMapClick);
        };
    }, [arrestData, currentZoom, map, onAreaClick]);

    // Listen for zoom changes
    useEffect(() => {
        const handleZoomEnd = () => {
            setCurrentZoom(map.getZoom());
        };

        map.on('zoomend', handleZoomEnd);

        return () => {
            map.off('zoomend', handleZoomEnd);
        };
    }, [map]);

    return null;
}

function MapComponent({ arrestData, onAreaClick }) {
    // Calculate center of the map based on data
    const center = arrestData.length > 0
        ? [
            arrestData.reduce((sum, arrest) => sum + parseFloat(arrest.latitude), 0) / arrestData.length,
            arrestData.reduce((sum, arrest) => sum + parseFloat(arrest.longitude), 0) / arrestData.length
        ]
        : [39.8283, -98.5795]; // Default to center of US

    return (
        <div className="map-container">
            <MapContainer
                center={center}
                zoom={4}
                style={{ height: 'calc(100vh - 100px)', width: '100%' }}
                onClick={(e) => {
                    console.log('MapContainer clicked at:', e.latlng); // Additional debug
                }}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <HeatMapLayer arrestData={arrestData} onAreaClick={onAreaClick} />
            </MapContainer>
        </div>
    );
}

export default MapComponent; 