import React, { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import './InspectionPins.css';

// Custom pin icon for inspections with yellow-to-scarlet spectrum
const createInspectionIcon = (summaryScore) => {
    const size = 32; // Fixed size for all pins

    // Yellow to scarlet spectrum based on summary score (0-10 scale)
    // Updated to get darker red more quickly
    let color;
    if (summaryScore >= 9) {
        color = '#ffff00'; // Yellow for high scores (9-10)
    } else if (summaryScore >= 8) {
        color = '#ffc107'; // Amber (was light yellow)
    } else if (summaryScore >= 7) {
        color = '#ff9800'; // Orange (was amber)
    } else if (summaryScore >= 6) {
        color = '#ff5722'; // Deep orange (was orange)
    } else if (summaryScore >= 5) {
        color = '#f44336'; // Red (was deep orange)
    } else if (summaryScore >= 4) {
        color = '#d32f2f'; // Dark red (was red)
    } else if (summaryScore >= 3) {
        color = '#b71c1c'; // Very dark red (was dark red)
    } else if (summaryScore >= 2) {
        color = '#8b0000'; // Dark scarlet (was very dark red)
    } else if (summaryScore >= 1) {
        color = '#660000'; // Very dark scarlet (was dark scarlet)
    } else {
        color = '#4a0000'; // Almost black for very low scores (was very dark scarlet)
    }

    // Determine text color based on background brightness
    const brightness = summaryScore >= 7 ? '#333333' : '#ffffff';

    return L.divIcon({
        className: 'inspection-pin',
        html: `
            <div style="
                position: relative;
                width: ${size}px;
                height: ${size * 1.4}px;
                cursor: pointer;
            ">
                <!-- Pin body -->
                <div style="
                    position: absolute;
                    top: 0;
                    left: 50%;
                    transform: translateX(-50%);
                    width: ${size}px;
                    height: ${size}px;
                    background-color: ${color};
                    border: 2px solid ${color};
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: ${brightness};
                    font-weight: bold;
                    font-size: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    z-index: 2;
                ">
                    ${summaryScore}
                </div>
                <!-- Pin shadow -->
                <div style="
                    position: absolute;
                    bottom: 0;
                    left: 50%;
                    transform: translateX(-50%);
                    width: ${size * 0.6}px;
                    height: ${size * 0.4}px;
                    background-color: rgba(0,0,0,0.2);
                    border-radius: 50%;
                    z-index: 1;
                "></div>
            </div>
        `,
        iconSize: [size, size * 1.4],
        iconAnchor: [size / 2, size]
    });
};

function InspectionPins({ inspectionData, onPinClick, enabled = true }) {
    const map = useMap();
    const markersRef = useRef([]);

    useEffect(() => {
        // Create a pane for inspection pins if it doesn't exist yet
        if (!map.getPane('detentionCenterPane')) {
            map.createPane('detentionCenterPane');
            map.getPane('detentionCenterPane').style.zIndex = 650; // Higher than city markers (450) but lower than popups (1000)
        }

        if (!enabled || !inspectionData || inspectionData.length === 0) {
            // Clear existing markers
            markersRef.current.forEach(marker => {
                if (map.hasLayer(marker)) {
                    map.removeLayer(marker);
                }
            });
            markersRef.current = [];
            return;
        }

        // Clear existing markers
        markersRef.current.forEach(marker => {
            if (map.hasLayer(marker)) {
                map.removeLayer(marker);
            }
        });
        markersRef.current = [];

        // Add new markers
        inspectionData
            .filter(inspection =>
                inspection['Detention Center'] !== 'Linn County Jail' &&
                inspection['Detention Center'] !== 'Monroe County Detention Center' &&
                inspection['Detention Center'] !== 'Pottawattamie County Jail'
            )
            .forEach(inspection => {
                const lat = parseFloat(inspection.location_latitude);
                const lng = parseFloat(inspection.location_longitude);

                if (isNaN(lat) || isNaN(lng)) return;

                const summaryScore = parseInt(inspection.summary_score) || 0;
                const icon = createInspectionIcon(summaryScore);

                const marker = L.marker([lat, lng], {
                    icon,
                    pane: 'detentionCenterPane'
                });

                // Create tooltip for hover
                const tooltip = L.tooltip({
                    permanent: false,
                    direction: 'top',
                    offset: [0, -10],
                    className: 'inspection-tooltip',
                    opacity: 0.9
                });

                // Set tooltip content
                tooltip.setContent(`
                    <div style="
                        text-align: center; 
                        min-width: 200px; 
                        max-width: 300px;
                        font-size: 12px;
                        line-height: 1.3;
                        word-wrap: break-word;
                        background-color: white;
                        color: #666666;
                        padding: 8px;
                        border-radius: 4px;
                        border: 1px solid #ccc;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    ">
                        <strong>${inspection['Detention Center']}</strong>
                    </div>
                `);

                marker.bindTooltip(tooltip);

                // Add click handler
                marker.on('click', () => {
                    if (onPinClick) {
                        onPinClick(inspection);
                    }
                });

                marker.addTo(map);
                markersRef.current.push(marker);
            });

        return () => {
            // Cleanup markers on unmount
            markersRef.current.forEach(marker => {
                if (map.hasLayer(marker)) {
                    map.removeLayer(marker);
                }
            });
            markersRef.current = [];
        };
    }, [inspectionData, map, enabled, onPinClick]);

    return null;
}

export default InspectionPins;