import React, { useState, useEffect, useRef } from 'react';
import './IncidentsPanel.css';

function IncidentsPanel({ cursorPosition, arrestData, onMapClick }) {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [nearbyIncidents, setNearbyIncidents] = useState([]);
    const [displayedCount, setDisplayedCount] = useState(20);
    const [loadingMore, setLoadingMore] = useState(false);
    const [persistentIncidents, setPersistentIncidents] = useState([]);
    const [isPersistent, setIsPersistent] = useState(false);
    const [lastClickCount, setLastClickCount] = useState(0);
    const incidentsListRef = useRef(null);

    // Function to calculate distance between two points
    const calculateDistance = (lat1, lng1, lat2, lng2) => {
        const R = 6371; // Earth's radius in kilometers
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    };

    // Function to get cluster radius based on zoom level (similar to MapComponent)
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

    // Effect to find nearby incidents based on cursor position
    useEffect(() => {
        if (!cursorPosition || !arrestData || arrestData.length === 0) {
            if (!isPersistent) {
                setNearbyIncidents([]);
                setDisplayedCount(20);
            }
            return;
        }

        // If we have persistent incidents, don't update based on cursor movement
        if (isPersistent) {
            return;
        }

        // Convert arrest data to points
        const points = arrestData
            .map(arrest => ({
                lat: parseFloat(arrest.latitude),
                lng: parseFloat(arrest.longitude),
                data: arrest
            }))
            .filter(point => !isNaN(point.lat) && !isNaN(point.lng));

        // Find incidents within a reasonable radius of the cursor
        // Using a very generous radius to capture incidents matching visual clusters
        const searchRadius = 2.5; // About 250km radius for very generous coverage

        const nearbyIncidents = points.filter(point => {
            const distance = Math.sqrt(
                Math.pow(cursorPosition.lat - point.lat, 2) +
                Math.pow(cursorPosition.lng - point.lng, 2)
            );
            return distance <= searchRadius;
        }).map(point => point.data);

        // Remove duplicates based on URL
        const uniqueIncidents = nearbyIncidents.filter((incident, index, self) =>
            index === self.findIndex(i => i.url === incident.url)
        );

        setNearbyIncidents(uniqueIncidents);
        setDisplayedCount(20);
    }, [cursorPosition, arrestData, isPersistent]);

    // Effect to handle map clicks - toggle persistent mode
    useEffect(() => {
        if (onMapClick > lastClickCount) {
            if (nearbyIncidents.length > 0) {
                if (!isPersistent) {
                    // First click - pause the current incidents
                    setPersistentIncidents([...nearbyIncidents]);
                    setIsPersistent(true);
                } else {
                    // Second click - unpause and clear
                    setPersistentIncidents([]);
                    setIsPersistent(false);
                }
            }
        }
        setLastClickCount(onMapClick);
    }, [onMapClick, nearbyIncidents, isPersistent, lastClickCount]);

    const clearPersistentIncidents = () => {
        setPersistentIncidents([]);
        setIsPersistent(false);
        setNearbyIncidents([]);
        setDisplayedCount(20);
    };

    const loadMoreIncidents = async () => {
        if (loadingMore || displayedCount >= nearbyIncidents.length) return;

        setLoadingMore(true);

        // Simulate a small delay to show loading state
        await new Promise(resolve => setTimeout(resolve, 300));

        const nextBatch = nearbyIncidents.slice(displayedCount, displayedCount + 20);
        setDisplayedCount(prev => prev + 20);
        setLoadingMore(false);
    };

    const handleScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        const scrollableHeight = scrollHeight - clientHeight;
        const threshold = scrollableHeight * 0.1; // Load when within 10% of bottom

        if (scrollHeight - scrollTop <= clientHeight + threshold) {
            loadMoreIncidents();
        }
    };

    const toggleCollapse = () => {
        setIsCollapsed(!isCollapsed);
    };

    const formatCoordinates = (lat, lng) => {
        if (lat === null || lng === null || lat === undefined || lng === undefined || isNaN(lat) || isNaN(lng)) {
            return 'No cursor data';
        }
        return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
    };

    const formatDate = (dateString) => {
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) {
                return null;
            }
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } catch (error) {
            return null;
        }
    };

    // Use persistent incidents if available, otherwise use nearby incidents
    const currentIncidents = isPersistent ? persistentIncidents : nearbyIncidents;
    const displayedIncidents = currentIncidents.slice(0, displayedCount);

    return (
        <div className={`incidents-panel ${isCollapsed ? 'collapsed' : ''}`}>
            <div className="incidents-collapse-handle" onClick={toggleCollapse}>
                <span className="collapse-icon">{isCollapsed ? '▶' : '◀'}</span>
            </div>
            <div className="incidents-panel-header">
                <h3>Nearby Incidents</h3>
                {isPersistent && (
                    <div className="paused-indicator" title="Click map again to unpause">
                        ⏸
                    </div>
                )}
            </div>
            {!isCollapsed && (
                <div className="incidents-panel-content" onScroll={handleScroll}>
                    {currentIncidents.length === 0 ? (
                        <div className="incidents-placeholder">
                            <h4>No Nearby Incidents</h4>
                            <p className="placeholder-text">
                                Move your cursor over the map to see nearby incidents.
                            </p>
                        </div>
                    ) : (
                        <div className="incidents-list" ref={incidentsListRef}>
                            <div className="incidents-header">
                                <h4>
                                    {isPersistent ? 'Incidents ' : 'Incidents in Range '}
                                    ({currentIncidents.length})
                                </h4>
                            </div>
                            {displayedIncidents.map((incident, index) => (
                                <div key={index} className="incident-item">
                                    <div className="incident-header">
                                        {formatDate(incident.date) && (
                                            <span className="incident-date">{formatDate(incident.date)}</span>
                                        )}
                                    </div>
                                    <a
                                        href={incident.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="incident-title"
                                    >
                                        {incident.title || 'No title available'}
                                    </a>
                                </div>
                            ))}
                            {loadingMore && (
                                <div className="loading-more">Loading more incidents...</div>
                            )}
                            {displayedCount >= currentIncidents.length && currentIncidents.length > 0 && (
                                <div className="no-more-incidents">No more incidents to load</div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default IncidentsPanel; 