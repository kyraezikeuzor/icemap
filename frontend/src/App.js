import React, { useState, useEffect } from 'react';
import MapComponent from './MapComponent';
import InfoModal from './InfoModal';
import UnifiedPanel from './UnifiedPanel';
import BuyMeACoffee from './BuyMeACoffee';
import ContactInfo from './components/ContactInfo';
import './App.css';

// Helper function to detect mobile devices
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
        window.innerWidth <= 768;
}

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

function App() {
    const [arrestData, setArrestData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(true);
    const [cursorPosition, setCursorPosition] = useState(null);
    const [mapClickCount, setMapClickCount] = useState(0);
    const [isMobile, setIsMobile] = useState(false);

    // Detect mobile device on mount and window resize
    useEffect(() => {
        const checkMobile = () => {
            setIsMobile(isMobileDevice());
        };

        // Check on mount
        checkMobile();

        // Listen for window resize
        window.addEventListener('resize', checkMobile);

        return () => {
            window.removeEventListener('resize', checkMobile);
        };
    }, []);

    useEffect(() => {
        const loadArrestData = async () => {
            try {
                const response = await fetch('/arrests_with_titles.csv');
                const csvText = await response.text();

                // Parse CSV with proper handling of quoted fields
                const lines = csvText.split('\n');
                const headers = parseCSVLine(lines[0]);

                const data = lines.slice(1).map(line => {
                    if (!line.trim()) return null; // Skip empty lines
                    const values = parseCSVLine(line);
                    const arrest = {};
                    headers.forEach((header, index) => {
                        arrest[header.trim()] = values[index] ? values[index].trim() : '';
                    });
                    return arrest;
                }).filter(arrest =>
                    arrest &&
                    arrest.latitude &&
                    arrest.longitude &&
                    !isNaN(parseFloat(arrest.latitude)) &&
                    !isNaN(parseFloat(arrest.longitude))
                );

                setArrestData(data);
            } catch (error) {
                console.error('Error loading arrest data:', error);
            } finally {
                setLoading(false);
            }
        };

        loadArrestData();
    }, []);

    const closeModal = () => {
        setShowModal(false);
    };

    const handleCursorMove = (position) => {
        setCursorPosition(position);
    };

    const handleMapClick = () => {
        setMapClickCount(prev => prev + 1);
    };

    if (loading) {
        return (
            <div className="loading">
                <h2>Loading arrest data...</h2>
            </div>
        );
    }

    return (
        <div className="App">
            <InfoModal isOpen={showModal} onClose={closeModal} />
            <ContactInfo />
            <BuyMeACoffee isMobile={isMobile} />
            <UnifiedPanel
                cursorPosition={cursorPosition}
                arrestData={arrestData}
                onMapClick={mapClickCount}
                isMobile={isMobile}
            />
            <MapComponent
                arrestData={arrestData}
                onCursorMove={handleCursorMove}
                onMapClick={handleMapClick}
            />
        </div>
    );
}

export default App; 