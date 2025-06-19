import React, { useEffect, useState, useRef } from 'react';
import { GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import * as d3Scale from 'd3-scale';
import * as d3Interpolate from 'd3-scale-chromatic';
import { interpolateRgb } from 'd3-interpolate';
import './CountyCaseHeatMap.css';

// County Case Heat Map component
function CountyCaseHeatMap({ enabled = true }) {
    const map = useMap();
    const [countyData, setCountyData] = useState(null);
    const [caseData, setCaseData] = useState({});
    const geojsonLayerRef = useRef(null);

    useEffect(() => {
        // Load the US counties GeoJSON
        const loadCountyData = async () => {
            try {
                // Using a public counties GeoJSON source
                const response = await fetch('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json');
                const data = await response.json();
                setCountyData(data);
            } catch (error) {
                console.error('Error loading county data:', error);
            }
        };

        // Load case count data from casesbycounty.csv
        const loadCaseData = async () => {
            try {
                const response = await fetch('/casesbycounty.csv');
                const csvText = await response.text();

                const parsedData = {};

                // Parse the CSV
                const lines = csvText.split('\n');
                const headers = lines[0].split(',');

                // Process each line of the CSV
                lines.slice(1).forEach(line => {
                    if (!line.trim()) return;

                    // Handle quoted values that may contain commas
                    let values = [];
                    let inQuotes = false;
                    let currentValue = '';

                    for (let i = 0; i < line.length; i++) {
                        if (line[i] === '"') {
                            inQuotes = !inQuotes;
                        } else if (line[i] === ',' && !inQuotes) {
                            values.push(currentValue);
                            currentValue = '';
                        } else {
                            currentValue += line[i];
                        }
                    }

                    // Add the last value
                    values.push(currentValue);

                    // Extract the county ID and case count
                    const countyId = values[0]?.trim();
                    let caseCount = values[1]?.trim();

                    // Remove commas and convert to number
                    if (caseCount) {
                        caseCount = parseInt(caseCount.replace(/,/g, ''), 10);
                    }

                    if (countyId && !isNaN(caseCount)) {
                        parsedData[countyId] = caseCount;
                    }
                });

                setCaseData(parsedData);
            } catch (error) {
                console.error('Error loading case count data:', error);
            }
        };

        loadCountyData();
        loadCaseData();

        return () => {
            if (geojsonLayerRef.current) {
                map.removeLayer(geojsonLayerRef.current);
            }
        };
    }, [map]);

    useEffect(() => {
        if (!countyData || !Object.keys(caseData).length || !enabled) {
            return;
        }

        // Remove existing layer
        if (geojsonLayerRef.current) {
            map.removeLayer(geojsonLayerRef.current);
        }

        // Find min and max case counts for color scale
        const caseCounts = Object.values(caseData).filter(count => count > 0);
        const minCount = Math.min(...caseCounts) || 0;
        const maxCount = Math.max(...caseCounts) || 1;

        // Create a custom color scale that is overall redder and starts at a darker baseline
        const customInterpolator = t => {
            // t is normalized [0,1] value
            // For the lowest 40%, blend from #fc9272 (light red) to #de2d26 (dark red)
            if (t < 0.4) {
                return interpolateRgb("#fc9272", "#de2d26")(t / 0.4);
            }
            // For the rest, blend from #de2d26 (dark red) to #800026 (very dark red)
            return interpolateRgb("#de2d26", "#800026")((t - 0.4) / 0.6);
        };
        const colorScale = d3Scale.scaleSequential()
            .domain([minCount, maxCount])
            .interpolator(customInterpolator);

        // Style function for the GeoJSON
        const style = (feature) => {
            // Extract the county FIPS code from the GeoJSON
            const countyId = feature.id;

            // Get the case count using the county FIPS code
            const caseCount = caseData[countyId] || 0;

            // Get the color and opacity based on case count
            let fillColor = '#ffffff'; // Default to white
            let fillOpacity = 0.2;     // Slightly higher minimum opacity for better visibility

            if (caseCount > 0) {
                // Use min-max scaling for better color distribution
                fillColor = colorScale(caseCount);

                // High contrast opacity scale
                const opacityScale = d3Scale.scaleLinear()
                    .domain([minCount, maxCount])
                    .range([0.5, 0.95]);  // Higher minimum opacity for better visibility

                fillOpacity = opacityScale(caseCount);
            }

            return {
                fillColor: fillColor,
                weight: 0.8,                // Slightly thicker borders for better definition
                opacity: 0.7,               // More visible borders
                color: '#e34a33',           // Softer red for borders
                fillOpacity: fillOpacity,
                className: 'county-polygon',
                zIndex: 100
            };
        };

        // Create GeoJSON layer
        geojsonLayerRef.current = L.geoJSON(countyData, {
            style: style,
            onEachFeature: (feature, layer) => {
                // Extract county name from properties
                const countyName = feature.properties.NAME;
                const countyId = feature.id;
                const caseCount = caseData[countyId] || 0;

                // Format case count with commas
                const formattedCount = caseCount.toLocaleString();

                // Create tooltip with only county info and case count
                layer.bindTooltip(`
                    <div style="font-weight:600; margin-bottom:4px;">${countyName}</div>
                    <div style="display:flex; align-items:center;">
                        <span style="color:#3182bd; font-weight:bold; margin-right:5px;">${formattedCount}</span>
                        <span style="color:#800000;">open cases</span>
                    </div>
                `, {
                    sticky: true,
                    offset: [0, -5],
                    direction: 'top',
                    className: 'county-tooltip'
                });

                // Add event listeners for hover highlighting (no click)
                layer.on({
                    mouseover: function (e) {
                        const l = e.target;
                        l.setStyle({
                            weight: 2.5,
                            color: '#1a4a8a',
                            fillOpacity: 0.95,
                            dashArray: ''
                        });

                        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                            l.bringToFront();
                        }

                        // Open the tooltip on hover
                        layer.openTooltip();
                    },
                    mouseout: function (e) {
                        geojsonLayerRef.current.resetStyle(e.target);

                        // Close the tooltip on mouseout
                        setTimeout(() => layer.closeTooltip(), 300);
                    }
                    // No click event
                });
            }
        });

        // Add the layer to the map
        if (enabled) {
            // Create a custom pane for the choropleth layer to control z-index
            if (!map.getPane('countyPane')) {
                map.createPane('countyPane');
                map.getPane('countyPane').style.zIndex = 200; // Lower value to ensure it's below the heat map layer
            }

            geojsonLayerRef.current.options.pane = 'countyPane';
            geojsonLayerRef.current.addTo(map);
        } else {
            // Remove the layer if not enabled
            if (geojsonLayerRef.current) {
                map.removeLayer(geojsonLayerRef.current);
            }
        }

        return () => {
            if (geojsonLayerRef.current) {
                map.removeLayer(geojsonLayerRef.current);
            }
        };

    }, [map, countyData, caseData, enabled]);

    return null;
}

export default CountyCaseHeatMap;
