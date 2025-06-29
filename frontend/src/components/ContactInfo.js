import React, { useState } from 'react';
import '../BuyMeACoffee.css';

const contactEmail = 'contact@icemap.dev';

export default function ContactInfo({ isMobile }) {
    const [showEmail, setShowEmail] = useState(false);

    const handleClick = () => {
        if (!showEmail) {
            setShowEmail(true);
        } else {
            window.location.href = `mailto:${contactEmail}`;
            setShowEmail(false);
        }
    };

    // Hide on mobile since it's now in the mobile button bar
    if (isMobile) {
        return null;
    }

    return (
        <div className="buy-me-coffee" style={{ bottom: 80, right: 20 }}>
            <button
                className="coffee-button"
                style={{ minWidth: 200 }}
                aria-label={showEmail ? 'Show contact label' : 'Show contact email'}
                onClick={handleClick}
            >
                <span
                    className="coffee-text"
                    style={{
                        opacity: showEmail ? 0 : 1,
                        position: 'absolute',
                        left: 0,
                        right: 0,
                        top: 0,
                        bottom: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'opacity 0.35s, transform 0.35s',
                        transform: showEmail ? 'translateY(-10px)' : 'translateY(0)',
                        pointerEvents: showEmail ? 'none' : 'auto',
                    }}
                >
                    Contact
                </span>
                <span
                    className="coffee-text"
                    style={{
                        opacity: showEmail ? 1 : 0,
                        position: 'absolute',
                        left: 0,
                        right: 0,
                        top: 0,
                        bottom: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'opacity 0.35s, transform 0.35s',
                        transform: showEmail ? 'translateY(0)' : 'translateY(10px)',
                        pointerEvents: showEmail ? 'auto' : 'none',
                        color: '#ccc',
                    }}
                >
                    {contactEmail}
                </span>
            </button>
        </div>
    );
} 