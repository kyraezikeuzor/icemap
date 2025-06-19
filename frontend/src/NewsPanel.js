import React, { useState, useEffect, useRef } from 'react';
import './NewsPanel.css';

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

function NewsPanel({ isMobile, onCollapseChange }) {
    const [articles, setArticles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isCollapsed, setIsCollapsed] = useState(isMobile);
    const [allArticles, setAllArticles] = useState([]);
    const [displayedCount, setDisplayedCount] = useState(20);
    const [loadingMore, setLoadingMore] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date());
    const articlesListRef = useRef(null);

    // Clock effect
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date());
        }, 1000);

        return () => clearInterval(timer);
    }, []);

    // Notify parent of collapse state changes
    useEffect(() => {
        if (onCollapseChange) {
            onCollapseChange(isCollapsed);
        }
    }, [isCollapsed, onCollapseChange]);

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
                setLoading(false);
            } catch (error) {
                console.error('Error loading articles:', error);
                setLoading(false);
            }
        };

        loadArticles();
    }, []);

    const loadMoreArticles = async () => {
        if (loadingMore || displayedCount >= allArticles.length) return;

        setLoadingMore(true);

        // Simulate a small delay to show loading state
        await new Promise(resolve => setTimeout(resolve, 300));

        const nextBatch = allArticles.slice(displayedCount, displayedCount + 20);
        setArticles(prev => [...prev, ...nextBatch]);
        setDisplayedCount(prev => prev + 20);
        setLoadingMore(false);
    };

    const handleScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        const scrollableHeight = scrollHeight - clientHeight;
        const threshold = scrollableHeight * 0.1; // Load when within 10% of bottom

        // Calculate scroll percentage
        const scrollPercentage = Math.round((scrollTop / scrollableHeight) * 100);

        if (scrollHeight - scrollTop <= clientHeight + threshold) {
            loadMoreArticles();
        }
    };

    const toggleCollapse = () => {
        setIsCollapsed(!isCollapsed);
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

    if (loading) {
        return (
            <div className={`news-panel ${isCollapsed ? 'collapsed' : ''} ${isMobile ? 'mobile' : ''}`}>
                <div className="news-collapse-handle" onClick={toggleCollapse}>
                    <span className="collapse-icon">{isCollapsed ? '▶' : '◀'}</span>
                </div>
                <div className="news-panel-header">
                    <div className={`header-content ${isMobile ? 'mobile' : ''}`}>
                        <h3>Live News Feed</h3>
                        <span className="live-clock">{formatMilitaryTime(currentTime)}</span>
                    </div>
                </div>
                {!isCollapsed && (
                    <div className="news-panel-content">
                        <div className="loading">Loading news...</div>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className={`news-panel ${isCollapsed ? 'collapsed' : ''} ${isMobile ? 'mobile' : ''}`}>
            <div className="news-collapse-handle" onClick={toggleCollapse}>
                <span className="collapse-icon">{isCollapsed ? '◀' : '▶'}</span>
            </div>
            <div className="news-panel-header">
                <h3>Live News Feed</h3>
                <span className="live-clock">{formatMilitaryTime(currentTime)}</span>
            </div>
            {!isCollapsed && (
                <div className="news-panel-content" onScroll={handleScroll}>
                    <div
                        className="articles-list"
                        ref={articlesListRef}
                        onScroll={handleScroll}
                    >
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
                        {loadingMore && (
                            <div className="loading-more">Loading more articles...</div>
                        )}
                        {displayedCount >= allArticles.length && allArticles.length > 0 && (
                            <div className="no-more-articles">No more articles to load</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

export default NewsPanel; 