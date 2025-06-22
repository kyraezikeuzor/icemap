import React from 'react';
import './DonationModal.css';

function DonationModal({ isOpen, onClose }) {
    if (!isOpen) return null;

    const handleDonateClick = () => {
        window.open('https://www.buymeacoffee.com/icemap', '_blank');
        onClose();
    };

    const handleClose = () => {
        onClose();
    };

    return (
        <div className="donation-modal-overlay">
            <div className="donation-modal">
                <div className="donation-modal-content">
                    <div className="donation-header">
                        <h2>Support IceMap</h2>
                        <button className="close-button" onClick={handleClose}>
                            ×
                        </button>
                    </div>

                    <div className="donation-body">
                        <div className="donation-icon">☕</div>
                        <p className="donation-message">
                            Thanks for exploring the map! If you find this tool helpful,
                            please consider supporting its continued development and data maintenance.
                        </p>
                        <p className="donation-subtitle">
                            Your support helps keep the mapping data current and the platform running smoothly so that we can continue to hold ICE accountable for their actions across the country.
                        </p>
                    </div>

                    <div className="donation-actions">
                        <button
                            className="donate-button"
                            onClick={handleDonateClick}
                        >
                            Support with Coffee
                        </button>
                        <button
                            className="skip-button"
                            onClick={handleClose}
                        >
                            Maybe Later
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default DonationModal; 