import React from 'react';
import './InfoModal.css';

function InfoModal({ isOpen, onClose }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal">
                <button className="modal-close" onClick={onClose}>×</button>
                <div className="modal-content">
                    <h1>icemap</h1>
                    <p>
                        We strongly believe that the American people should have full insight into the actions of its democratically-elected government.
                    </p>
                    <p>
                        icemap.dev aims to provide a comprehensive view of the activities and the injustices of America's Immigration Customs Agency (ICE),
                        with specific focus on its Enforcement and Removal Operations department (ERO).
                    </p>
                    <p>
                        icemap aggregates both unstructured and structured data from a multitude of public online sources, then distills these data into useful sources and figures.
                    </p>
                    <p>
                        icemap does not aim to hinder operations nor spark fear, but instead provide a lens with which the American people can
                        observe.
                    </p>
                    <button className="continue-button" onClick={onClose}>
                        Continue
                    </button>
                </div>
            </div>
        </div>
    );
}

export default InfoModal; 