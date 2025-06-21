import React from 'react';
import './InspectionModal.css';

function InspectionModal({ isOpen, onClose, inspectionData }) {
    if (!isOpen || !inspectionData) return null;

    // Get the most recent inspection for detailed findings
    const mostRecentInspection = inspectionData.Inspections && inspectionData.Inspections.length > 0
        ? inspectionData.Inspections[0]
        : null;

    // Get deficiency descriptions from the most recent inspection
    const deficiencyDescriptions = mostRecentInspection ? [
        { key: 'SAFETY', label: 'Safety Issues' },
        { key: 'SECURITY', label: 'Security Issues' },
        { key: 'CARE', label: 'Care Issues' },
        { key: 'ACTIVITIES', label: 'Activities Issues' },
        { key: 'JUSTICE', label: 'Justice Issues' }
    ].filter(desc => mostRecentInspection[desc.key] && mostRecentInspection[desc.key] !== 'N/A') : [];

    // Helper function to format inspection date with proper spacing
    const formatInspectionDate = (dateString) => {
        if (!dateString || dateString === 'N/A') return dateString;

        // Check if there's a pattern like "MonthDay-Day" (no space after month)
        // Common patterns: "January30-February1", "March21-23", etc.
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];

        let formattedDate = dateString;

        // Look for patterns where a month name is followed immediately by a number
        monthNames.forEach(month => {
            const regex = new RegExp(`(${month})(\\d)`, 'g');
            formattedDate = formattedDate.replace(regex, `$1 $2`);
        });

        return formattedDate;
    };

    const getYearFromDate = (dateString = '') => {
        if (!dateString) return 'N/A';
        const match = dateString.match(/\b\d{4}\b/);
        return match ? match[0] : 'N/A';
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal inspection-modal" onClick={(e) => e.stopPropagation()}>
                <button className="modal-close" onClick={onClose}>×</button>
                <div
                    style={{
                        position: 'absolute',
                        top: '15px',
                        left: '15px',
                        backgroundColor: '#ff6b35',
                        color: 'white',
                        padding: '6px 12px',
                        borderRadius: '20px',
                        fontSize: '0.8rem',
                        fontWeight: '600',
                        zIndex: 10,
                        letterSpacing: '0.5px'
                    }}
                >
                    icemap.dev
                </div>
                <div className="modal-content">
                    <h1>{inspectionData['Detention Center']}</h1>

                    {inspectionData.generated_summary && (
                        <div className="summary-section">
                            <h2>Summary</h2>
                            <p>{inspectionData.generated_summary}</p>
                        </div>
                    )}

                    {mostRecentInspection && (
                        <div className="inspection-details">
                            <p>Most Recent Inspection: {formatInspectionDate(mostRecentInspection['Inspection Date'])}</p>
                            <p>Inspection Type: {mostRecentInspection['Inspection Type']}</p>

                            {mostRecentInspection.CONCLUSION && mostRecentInspection.CONCLUSION !== 'N/A' && (
                                <div className="conclusion-section">
                                    <h2>Inspection Conclusion</h2>
                                    <p>{mostRecentInspection.CONCLUSION}</p>
                                </div>
                            )}

                            {deficiencyDescriptions.length > 0 && (
                                <div className="deficiency-descriptions">
                                    <h2>Detailed Findings</h2>
                                    {deficiencyDescriptions.map((desc, index) => (
                                        <div key={index} className="deficiency-description">
                                            <h3>{desc.label}</h3>
                                            <p>{mostRecentInspection[desc.key]}</p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="inspection-reports-container">
                                <h3 className="inspection-reports-label">Inspection Reports</h3>
                                <table className="inspection-reports-table">
                                    <thead>
                                        <tr>
                                            <th>Type</th>
                                            <th>Date</th>
                                            <th>Report</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {inspectionData.Inspections &&
                                            inspectionData.Inspections.map((inspection, index) =>
                                                inspection.URL ? (
                                                    <tr key={index}>
                                                        <td>{inspection['Inspection Type'] || 'N/A'}</td>
                                                        <td>{formatInspectionDate(inspection['Inspection Date'])}</td>
                                                        <td>
                                                            <a href={inspection.URL} target="_blank" rel="noopener noreferrer">
                                                                View
                                                            </a>
                                                        </td>
                                                    </tr>
                                                ) : null
                                            )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                    <div className="inspection-footer">
                        <p className="quality-score">Quality Score: {inspectionData.summary_score || 'N/A'}/10</p>
                        <div style={{ height: '20px' }}></div>
                        <small className="disclaimer" style={{ color: '#666' }}>
                            The summaries provided may contain inaccuracies. For the most accurate information, please refer to the original inspection reports.
                        </small>
                    </div>

                </div>
            </div>
        </div>
    );
}

export default InspectionModal; 