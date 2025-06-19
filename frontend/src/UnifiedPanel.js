import React, { useState, useEffect, useRef } from 'react';
import './UnifiedPanel.css';

// Helper function to properly parse CSV lines with quoted fields
function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                // Escaped quote
                current += '"';
                i++; // Skip next quote
            } else {
                // Toggle quote state
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            // End of field
            result.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }

    // Add the last field
    result.push(current.trim());

    return result;
}

function UnifiedPanel({ cursorPosition, arrestData, onMapClick, isMobile }) {
    const [activeTab, setActiveTab] = useState('incidents'); // 'incidents' or 'news'

    // Incidents state
    const [nearbyIncidents, setNearbyIncidents] = useState([]);
    const [displayedIncidentCount, setDisplayedIncidentCount] = useState(20);
    const [loadingMoreIncidents, setLoadingMoreIncidents] = useState(false);
    const [persistentIncidents, setPersistentIncidents] = useState([]);
    const [isPersistent, setIsPersistent] = useState(false);
    const [lastClickCount, setLastClickCount] = useState(0);

    // News state
    const [articles, setArticles] = useState([]);
    const [loadingNews, setLoadingNews] = useState(true);
    const [allArticles, setAllArticles] = useState([]);
    const [displayedArticleCount, setDisplayedArticleCount] = useState(20);
    const [loadingMoreArticles, setLoadingMoreArticles] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date());

    const incidentsListRef = useRef(null);
    const articlesListRef = useRef(null);
    const incidentsContentRef = useRef(null);
    const newsContentRef = useRef(null);

    // Clock effect for news
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date());
        }, 1000);

        return () => clearInterval(timer);
    }, []);

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

    // Function to get cluster radius based on zoom level
    const getClusterRadius = (zoom) => {
        if (zoom >= 10) return 0.001; // Very close points at high zoom
        if (zoom >= 8) return 0.005;  // Close points at medium-high zoom
        if (zoom >= 6) return 0.02;   // Medium distance at medium zoom
        if (zoom >= 4) return 0.05;   // Further distance at low-medium zoom
        return 0.1;                   // Far distance at low zoom
    };

    // Effect to handle incidents based on cursor position
    useEffect(() => {
        if (!cursorPosition || !arrestData || arrestData.length === 0) {
            if (!isPersistent) {
                setNearbyIncidents([]);
                setDisplayedIncidentCount(20);
            }
            return;
        }

        // If we have persistent incidents, don't update based on cursor movement
        if (isPersistent) {
            return;
        }

        const { lat, lng, zoom } = cursorPosition;

        // Convert arrest data to points with proper filtering
        const points = arrestData
            .map(arrest => ({
                lat: parseFloat(arrest.latitude),
                lng: parseFloat(arrest.longitude),
                data: arrest
            }))
            .filter(point => !isNaN(point.lat) && !isNaN(point.lng));

        // Use zoom-aware search radius that decreases significantly as user zooms in
        // This provides more precise results at higher zoom levels
        let searchRadius;
        if (zoom >= 12) {
            searchRadius = 0.05; // Very precise at highest zoom
        } else if (zoom >= 10) {
            searchRadius = 0.1; // Precise at high zoom
        } else if (zoom >= 8) {
            searchRadius = 0.25; // Medium precision
        } else if (zoom >= 6) {
            searchRadius = 0.5; // Less precise at medium zoom
        } else if (zoom >= 4) {
            searchRadius = 1.0; // Generous at low-medium zoom
        } else {
            searchRadius = 2.0; // Very generous at low zoom
        }

        const nearby = points.filter(point => {
            const distance = Math.sqrt(
                Math.pow(lat - point.lat, 2) +
                Math.pow(lng - point.lng, 2)
            );
            return distance <= searchRadius;
        }).map(point => ({
            ...point.data,
            distance: calculateDistance(lat, lng, point.lat, point.lng)
        }));

        // Remove duplicates based on URL
        const uniqueIncidents = nearby.filter((incident, index, self) =>
            index === self.findIndex(i => i.url === incident.url)
        );

        // Sort by distance and limit to 100 closest incidents
        const sortedIncidents = uniqueIncidents
            .sort((a, b) => a.distance - b.distance)
            .slice(0, 100);

        setNearbyIncidents(sortedIncidents);
        setDisplayedIncidentCount(20);
    }, [cursorPosition, arrestData, isPersistent]);

    // Effect to handle map clicks - toggle persistent mode
    useEffect(() => {
        if (onMapClick > lastClickCount) {
            if (nearbyIncidents.length > 0) {
                if (!isPersistent) {
                    // First click - pause the current incidents and switch to incidents tab
                    setPersistentIncidents([...nearbyIncidents]);
                    setIsPersistent(true);
                    setActiveTab('incidents');
                    // Reset scroll position when switching via map click
                    setTimeout(() => {
                        if (incidentsContentRef.current) {
                            incidentsContentRef.current.scrollTop = 0;
                        }
                    }, 0);
                } else {
                    // Second click - unpause and clear
                    setPersistentIncidents([]);
                    setIsPersistent(false);
                }
            }
        }
        setLastClickCount(onMapClick);
    }, [onMapClick, nearbyIncidents, isPersistent, lastClickCount]);

    // Load news articles
    useEffect(() => {
        const loadArticles = async () => {
            try {
                // Load both CSV files
                const [mediacloudResponse, newsroomResponse] = await Promise.all([
                    fetch('/mediacloud_articles.csv'),
                    fetch('/newsroom_reports.csv')
                ]);

                const mediacloudText = await mediacloudResponse.text();
                const newsroomText = await newsroomResponse.text();

                // Parse mediacloud articles
                const mediacloudLines = mediacloudText.split('\n');
                const mediacloudHeaders = parseCSVLine(mediacloudLines[0]);

                const mediacloudArticles = mediacloudLines.slice(1).map(line => {
                    if (!line.trim()) return null; // Skip empty lines
                    const values = parseCSVLine(line);
                    const article = {};
                    mediacloudHeaders.forEach((header, index) => {
                        article[header.trim()] = values[index] ? values[index].trim() : '';
                    });
                    return {
                        ...article,
                        source: 'MediaCloud',
                        url: article.url,
                        title: article.title,
                        date: article.date
                    };
                }).filter(article => article && article.title && article.url);

                // Parse newsroom articles
                const newsroomLines = newsroomText.split('\n');
                const newsroomHeaders = parseCSVLine(newsroomLines[0]);

                const newsroomArticles = newsroomLines.slice(1).map(line => {
                    if (!line.trim()) return null; // Skip empty lines
                    const values = parseCSVLine(line);
                    const article = {};
                    newsroomHeaders.forEach((header, index) => {
                        article[header.trim()] = values[index] ? values[index].trim() : '';
                    });
                    return {
                        ...article,
                        source: 'Newsroom',
                        url: article.link,
                        title: article.title,
                        date: article.date
                    };
                }).filter(article => article && article.title && article.url);

                // Combine and sort by date (newest first)
                const combinedArticles = [...mediacloudArticles, ...newsroomArticles]
                    .sort((a, b) => {
                        const dateA = new Date(a.date);
                        const dateB = new Date(b.date);
                        return dateB - dateA;
                    });

                setAllArticles(combinedArticles);
                setArticles(combinedArticles.slice(0, 20));
                setLoadingNews(false);
            } catch (error) {
                console.error('Error loading articles:', error);
                setLoadingNews(false);
            }
        };

        loadArticles();
    }, []);

    // Use persistent incidents if available, otherwise use nearby incidents
    const currentIncidents = isPersistent ? persistentIncidents : nearbyIncidents;
    const displayedIncidents = currentIncidents.slice(0, displayedIncidentCount);

    const clearPersistentIncidents = () => {
        setPersistentIncidents([]);
        setIsPersistent(false);
        setNearbyIncidents([]);
        setDisplayedIncidentCount(20);
    };

    const loadMoreIncidents = async () => {
        if (loadingMoreIncidents || displayedIncidentCount >= currentIncidents.length) return;

        setLoadingMoreIncidents(true);
        await new Promise(resolve => setTimeout(resolve, 300));

        const nextBatch = currentIncidents.slice(displayedIncidentCount, displayedIncidentCount + 20);
        setDisplayedIncidentCount(prev => prev + 20);
        setLoadingMoreIncidents(false);
    };

    const loadMoreArticles = async () => {
        if (loadingMoreArticles || displayedArticleCount >= allArticles.length) return;

        setLoadingMoreArticles(true);
        await new Promise(resolve => setTimeout(resolve, 300));

        const nextBatch = allArticles.slice(displayedArticleCount, displayedArticleCount + 20);
        setArticles(prev => [...prev, ...nextBatch]);
        setDisplayedArticleCount(prev => prev + 20);
        setLoadingMoreArticles(false);
    };

    const handleIncidentsScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        const scrollableHeight = scrollHeight - clientHeight;
        const threshold = scrollableHeight * 0.1;

        if (scrollHeight - scrollTop <= clientHeight + threshold) {
            loadMoreIncidents();
        }
    };

    const handleArticlesScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        const scrollableHeight = scrollHeight - clientHeight;
        const threshold = scrollableHeight * 0.1;

        if (scrollHeight - scrollTop <= clientHeight + threshold) {
            loadMoreArticles();
        }
    };

    const handleTabSwitch = (newTab) => {
        if (newTab === 'news' && isPersistent) {
            // When switching to news tab, automatically unpause
            setPersistentIncidents([]);
            setIsPersistent(false);
        }

        setActiveTab(newTab);
    };

    // Effect to reset scroll position when tab changes
    useEffect(() => {
        // Use setTimeout to ensure DOM has been updated
        const timer = setTimeout(() => {
            if (activeTab === 'incidents' && incidentsContentRef.current) {
                incidentsContentRef.current.scrollTop = 0;
            } else if (activeTab === 'news' && newsContentRef.current) {
                newsContentRef.current.scrollTop = 0;
            }
        }, 0);

        return () => clearTimeout(timer);
    }, [activeTab]);

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

    const formatMilitaryTime = (date) => {
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    return (
        <div className={`unified-panel ${isMobile ? 'mobile' : ''}`}>
            <div className="unified-panel-header">

                {!isMobile && (
                    <div className="paused-indicator">
                        {activeTab === 'incidents'
                            ? (isPersistent ? 'Click to Unpause' : 'Click to Pause')
                            : 'News Feed'
                        }
                    </div>
                )}
                <div className="live-clock-container">
                    <span className="live-clock">{formatMilitaryTime(currentTime)}</span>
                </div>
                <div className="header-top">
                    <div className="tab-toggle">
                        <button
                            className={`tab-button ${activeTab === 'incidents' ? 'active' : ''}`}
                            onClick={() => handleTabSwitch('incidents')}
                        >
                            Incidents
                        </button>
                        <button
                            className={`tab-button ${activeTab === 'news' ? 'active' : ''}`}
                            onClick={() => handleTabSwitch('news')}
                        >
                            {isMobile ? 'Feed' : 'Live News Feed'}
                        </button>
                    </div>
                </div>
            </div>

            <div className="unified-panel-content">
                {activeTab === 'incidents' ? (
                    <div className="incidents-content" ref={incidentsContentRef} onScroll={handleIncidentsScroll}>
                        {currentIncidents.length === 0 ? (
                            <div className="incidents-placeholder">
                                <h4>No Nearby Incidents</h4>
                                <p className="placeholder-text">
                                    {isMobile ? 'Tap to see nearby incidents' : 'Move your cursor over the map to see nearby incidents.'}
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
                                {loadingMoreIncidents && (
                                    <div className="loading-more">Loading more incidents...</div>
                                )}
                                {displayedIncidentCount >= currentIncidents.length && currentIncidents.length > 0 && (
                                    <div className="no-more-incidents">No more incidents to load</div>
                                )}
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="news-content" ref={newsContentRef} onScroll={handleArticlesScroll}>
                        {loadingNews ? (
                            <div className="loading">Loading news...</div>
                        ) : (
                            <div className="articles-list" ref={articlesListRef}>
                                {articles.map((article, index) => (
                                    <div key={index} className="article-item">
                                        <div className="article-header">
                                            {formatDate(article.date) && (
                                                <span className="article-date">{formatDate(article.date)}</span>
                                            )}
                                        </div>
                                        <a
                                            href={article.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="article-title"
                                        >
                                            {article.title}
                                        </a>
                                    </div>
                                ))}
                                {loadingMoreArticles && (
                                    <div className="loading-more">Loading more articles...</div>
                                )}
                                {displayedArticleCount >= allArticles.length && allArticles.length > 0 && (
                                    <div className="no-more-articles">No more articles to load</div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

export default UnifiedPanel; 