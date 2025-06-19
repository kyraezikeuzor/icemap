import React, { useEffect, useState, useRef } from 'react';
import { GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import * as d3Scale from 'd3-scale';
import * as d3Interpolate from 'd3-scale-chromatic';
import './CountyCaseHeatMap.css';

// Helper function to create a legend
const createLegend = (minCount, maxCount) => {
    const legend = L.control({ position: 'bottomright' });
    
    legend.onAdd = (map) => {
        const div = L.DomUtil.create('div', 'info legend');
        
        // Define legend breakpoints
        const breaks = [0, 10, 50, 100, 500, 1000, Math.round(maxCount)];
        
        div.innerHTML = '<div class="legend-title">Case Counts</div>';
        
        // Loop through the intervals and generate a label with colored square for each interval
        for (let i = 0; i < breaks.length - 1; i++) {
            const from = breaks[i];
            const to = breaks[i + 1];
            
            // Create color scale for legend, matching the map
            const colorScale = d3Scale.scaleSequential()
                .domain([0, breaks.length - 1])
                .interpolator(t => {
                    // Create a lighter blue palette similar to the example image
                    if (t < 0.2) return 'rgb(235, 245, 255)';      // Very light blue
                    if (t < 0.4) return 'rgb(198, 219, 239)';      // Light blue
                    if (t < 0.6) return 'rgb(158, 202, 225)';      // Medium light blue
                    if (t < 0.8) return 'rgb(107, 174, 214)';      // Medium blue
                    return 'rgb(66, 146, 198)';                    // Darker blue (not too dark)
                });
                
            div.innerHTML +=
                '<div class="legend-item">' +
                `<i style="background:${colorScale(i / (breaks.length - 2))}"></i> ` +
                `${from.toLocaleString()}${i === breaks.length - 2 ? '+' : '–' + to.toLocaleString()}` +
                '</div>';
        }
        
        return div;
    };
    
    return legend;
};

// County Case Heat Map component
function CountyCaseHeatMap({ enabled = true }) {
    const map = useMap();
    const [countyData, setCountyData] = useState(null);
    const [caseData, setCaseData] = useState({});
    const geojsonLayerRef = useRef(null);
    const legendRef = useRef(null);

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

        // Create a custom color scale with lighter blues like in the example
        const colorScale = d3Scale.scaleSequential()
            .domain([0, maxCount])
            .interpolator(t => {
                // Create a lighter blue palette similar to the example image
                if (t < 0.2) return 'rgb(235, 245, 255)';      // Very light blue
                if (t < 0.4) return 'rgb(198, 219, 239)';      // Light blue
                if (t < 0.6) return 'rgb(158, 202, 225)';      // Medium light blue
                if (t < 0.8) return 'rgb(107, 174, 214)';      // Medium blue
                return 'rgb(66, 146, 198)';                    // Darker blue (not too dark)
            });

        // Style function for the GeoJSON
        const style = (feature) => {
            // Extract the county FIPS code from the GeoJSON
            const countyId = feature.id;
            
            // Get the case count using the county FIPS code
            const caseCount = caseData[countyId] || 0;
            
            // Get the color and opacity based on case count
            let fillColor = '#ffffff'; // Default to white
            let fillOpacity = 0.05;    // Default low opacity for counties with no data
            
            if (caseCount > 0) {
                // Get color from our custom scale for counties with cases
                fillColor = colorScale(caseCount);
                
                // Create a scale that shows distinctions better even with large ranges
                const powerScale = d3Scale.scalePow()
                    .exponent(0.3)  // Lower exponent gives more visual distinction to lower values
                    .domain([1, Math.max(maxCount, 10)])
                    .range([0.4, 0.95]);  // Slightly reduced opacity range for better visibility
                    
                fillOpacity = powerScale(Math.max(1, caseCount));
            }
            
            return {
                fillColor: fillColor,       // Use the color we calculated above
                weight: 0.5,                // Thinner borders like in the example
                opacity: 0.5,               // Semi-transparent borders
                color: '#a9c6e5',           // Lighter blue for borders like in example
                fillOpacity: fillOpacity,
                className: 'county-polygon',
                zIndex: 100                 // Ensure county polygons are below the heat map
            };
        };

        // Create GeoJSON layer
        geojsonLayerRef.current = L.geoJSON(countyData, {
            style: style,
            onEachFeature: (feature, layer) => {
                // Extract county name and state from properties
                const countyName = feature.properties.NAME;
                const stateName = feature.properties.STATE_NAME;
                const countyId = feature.id;
                const caseCount = caseData[countyId] || 0;
                
                // Format case count with commas
                const formattedCount = caseCount.toLocaleString();
                
                // Create tooltip with county info and case count
                layer.bindTooltip(`
                    <div style="font-weight:600; margin-bottom:4px;">${countyName}, ${stateName}</div>
                    <div style="display:flex; align-items:center;">
                        <span style="color:#3182bd; font-weight:bold; margin-right:5px;">${formattedCount}</span>
                        <span>open cases</span>
                    </div>
                `, { 
                    sticky: true,
                    offset: [0, -5],
                    direction: 'top',
                    className: 'county-tooltip'
                });
                
                // Add event listeners for hover highlighting and click
                layer.on({
                    mouseover: function(e) {
                        const l = e.target;
                        l.setStyle({
                            weight: 2,
                            color: '#4a89dc',
                            fillOpacity: 0.85,
                            dashArray: ''
                        });
                        
                        if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                            l.bringToFront();
                        }
                        
                        // Open the tooltip on hover
                        layer.openTooltip();
                    },
                    mouseout: function(e) {
                        geojsonLayerRef.current.resetStyle(e.target);
                        
                        // Close the tooltip on mouseout
                        setTimeout(() => layer.closeTooltip(), 300);
                    },
                    click: function(e) {
                        // Zoom to the county on click
                        map.fitBounds(e.target.getBounds(), {
                            padding: [50, 50],
                            maxZoom: 10
                        });
                    }
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
            
            // Add legend to the map if it doesn't exist yet
            if (!legendRef.current) {
                legendRef.current = createLegend(minCount, maxCount);
                legendRef.current.addTo(map);
            }
        } else {
            // Remove the layer if not enabled
            if (geojsonLayerRef.current) {
                map.removeLayer(geojsonLayerRef.current);
            }
            
            // Remove legend if disabled
            if (legendRef.current) {
                legendRef.current.remove();
                legendRef.current = null;
            }
        }
        
        return () => {
            if (geojsonLayerRef.current) {
                map.removeLayer(geojsonLayerRef.current);
            }
            
            if (legendRef.current) {
                legendRef.current.remove();
                legendRef.current = null;
            }
        };

        // Add the legend control to the map
        const legend = createLegend(minCount, maxCount);
        legend.addTo(map);

    }, [map, countyData, caseData, enabled]);

    return null;
}

export default CountyCaseHeatMap;
