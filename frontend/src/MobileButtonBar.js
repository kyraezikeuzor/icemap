import React, { useState } from 'react';
import './MobileButtonBar.css';

const contactEmail = 'contact@icemap.dev';

function MobileButtonBar({ isMobile, showDetentionPins, onToggleDetentionPins, isPanelMinimized }) {
    const [showEmail, setShowEmail] = useState(false);

    const handleContactClick = () => {
        if (!showEmail) {
            setShowEmail(true);
        } else {
            window.location.href = `mailto:${contactEmail}`;
            setShowEmail(false);
        }
    };

    const handleSupportClick = () => {
        window.open('https://www.buymeacoffee.com/icemap', '_blank');
    };

    if (!isMobile) {
        return null; // Only show on mobile
    }

    return (
        <div className={`mobile-button-bar ${isPanelMinimized ? 'panel-minimized' : ''}`}>
            {/* Detention Center Pins Toggle */}
            <button
                className={`mobile-bar-button detention-toggle ${showDetentionPins ? 'active' : ''}`}
                onClick={onToggleDetentionPins}
                title="Toggle detention center pins"
            >
                <span className="button-icon">📍</span>
                <span className="button-text">Detention Center Pins</span>
            </button>

            {/* Contact Button */}
            <button
                className="mobile-bar-button contact-button"
                onClick={handleContactClick}
                title="Contact"
            >
                <span className="button-icon">📧</span>
                <span className="button-text">
                    {showEmail ? contactEmail : 'Contact'}
                </span>
            </button>

            {/* Support Button */}
            <button
                className="mobile-bar-button support-button"
                onClick={handleSupportClick}
                title="Support icemap"
            >
                <span className="button-icon">☕</span>
                <span className="button-text">Support</span>
            </button>
        </div>
    );
}

export default MobileButtonBar; 