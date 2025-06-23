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
                        icemap.dev aims to provide a comprehensive view of the activities of America's Immigration Customs Agency (ICE),
                        with specific focus on its Enforcement and Removal Operations department (ERO).
                    </p>
                    <p>
                        icemap aggregates both unstructured and structured data from a multitude of public online sources, then distills these data into useful news streams and figures.
                        Currently, this vizualization pulls statistics and articles from ICE newsroom reports, TRAC immigration data, as well as a myriad of local and national news sources.
                    </p>
                    <p>
                        These sources originate from both left and right-leaning news sources, and we do not see it our aim to ideologically favor certain sources over others. We recommend that the user
                        perform their own due diligence to formulate an informed opinion on the events provided.
                    </p>
                    <p>
                        icemap does not aim to hinder operations nor spark fear, but instead provide a lens with which the American people can
                        observe.
                    </p>
                    <p>
                        We collect zero individual user data, nor do we involve any user interaction to source the data for our analysis.
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