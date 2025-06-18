import React, { useState, useEffect } from 'react';
import MapComponent from './MapComponent';
import Sidebar from './Sidebar';
import './App.css';

function App() {
    const [arrestData, setArrestData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [selectedIncidents, setSelectedIncidents] = useState([]);

    useEffect(() => {
        const loadArrestData = async () => {
            try {
                const response = await fetch('/arrests.csv');
                const csvText = await response.text();

                // Simple CSV parsing (assuming no commas in quoted fields)
                const lines = csvText.split('\n');
                const headers = lines[0].split(',');

                const data = lines.slice(1).map(line => {
                    const values = line.split(',');
                    const arrest = {};
                    headers.forEach((header, index) => {
                        arrest[header.trim()] = values[index] ? values[index].trim() : '';
                    });
                    return arrest;
                }).filter(arrest =>
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

    const handleAreaClick = (incidents) => {
        console.log('handleAreaClick called with', incidents.length, 'incidents');
        console.log('Current sidebar state:', sidebarOpen);
        setSelectedIncidents(incidents);
        setSidebarOpen(true);
        console.log('Sidebar should now be open');
    };

    const handleCloseSidebar = () => {
        setSidebarOpen(false);
        setSelectedIncidents([]);
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
            <header className="header">
                <h1>ICE Arrest Heat Map</h1>
                <p>{arrestData.length} arrests mapped • Click on heat areas to view incidents</p>
                {/* Debug info */}
                <p style={{ fontSize: '0.8rem', opacity: 0.7 }}>
                    Debug: Sidebar open: {sidebarOpen ? 'Yes' : 'No'} |
                    Selected incidents: {selectedIncidents.length}
                </p>
                {/* Test button */}
                <button
                    onClick={() => {
                        console.log('Test button clicked');
                        setSelectedIncidents(arrestData.slice(0, 3)); // Test with first 3 incidents
                        setSidebarOpen(true);
                    }}
                    style={{
                        background: '#FFD700',
                        color: '#333',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        marginTop: '8px'
                    }}
                >
                    Test Sidebar
                </button>
            </header>
            <MapComponent arrestData={arrestData} onAreaClick={handleAreaClick} />
            <Sidebar
                isOpen={sidebarOpen}
                incidents={selectedIncidents}
                onClose={handleCloseSidebar}
            />
        </div>
    );
}

export default App; 