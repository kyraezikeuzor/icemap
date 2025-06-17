-- Enhanced ICE Data Aggregation Database Schema
-- For the icemap.dev transparency initiative

-- Geographic hierarchy table for case count data
CREATE TABLE geographic_case_counts (
    id SERIAL PRIMARY KEY,
    category VARCHAR(20) NOT NULL, -- 'state', 'county', 'subcounty'
    case_count INTEGER NOT NULL,
    subcounty_name VARCHAR(255),
    county_name VARCHAR(255),
    state_name VARCHAR(100) NOT NULL,
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_category CHECK (category IN ('state', 'county', 'subcounty'))
);

-- Enhanced articles table for news/press releases
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    summary TEXT,
    content TEXT, -- Full article content extraction
    date_published DATE,
    date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL, -- 'ice_newsroom', 'dhs_press', 'foia_library'
    news_type VARCHAR(100),
    category VARCHAR(100),
    hash_content VARCHAR(64), -- SHA256 hash for duplicate detection
    sentiment_score DECIMAL(3,2), -- Sentiment analysis (-1.0 to 1.0)
    key_entities JSON, -- AI-extracted entities (people, places, operations)
    geographic_mentions JSON, -- Mentioned states, counties, cities
    enforcement_keywords JSON, -- ICE operation types detected
    status VARCHAR(20) DEFAULT 'active' -- active, archived, duplicate
);

-- FOIA documents table
CREATE TABLE foia_documents (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    date_published DATE,
    date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(100),
    document_type VARCHAR(50), -- memo, report, policy, statistics
    content_summary TEXT,
    file_size BIGINT,
    file_type VARCHAR(20),
    hash_content VARCHAR(64),
    key_topics JSON, -- AI-extracted topics and themes
    redaction_level VARCHAR(20), -- heavy, moderate, light, none
    legal_significance_score INTEGER, -- 1-10 scale
    status VARCHAR(20) DEFAULT 'active'
);

-- Enhanced ICE facilities table
CREATE TABLE facilities (
    id SERIAL PRIMARY KEY,
    facility_name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(50),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    facility_type VARCHAR(100),
    aor VARCHAR(100), -- Area of Responsibility
    capacity INTEGER,
    current_population INTEGER,
    contractor_name VARCHAR(255),
    contract_value DECIMAL(15, 2),
    date_opened DATE,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operational_status VARCHAR(20) DEFAULT 'active', -- active, closed, pending
    source_verified BOOLEAN DEFAULT FALSE,
    inspection_scores JSON, -- Government inspection data
    violation_history JSON, -- Documented violations
    additional_info JSON -- Flexible metadata
);

-- Enforcement operations tracking
CREATE TABLE enforcement_operations (
    id SERIAL PRIMARY KEY,
    operation_name VARCHAR(255),
    operation_date DATE,
    location_state VARCHAR(50),
    location_county VARCHAR(100),
    location_city VARCHAR(100),
    arrests_count INTEGER,
    deportations_count INTEGER,
    target_demographics JSON, -- Age groups, nationalities, etc.
    operation_type VARCHAR(50), -- raid, checkpoint, workplace, targeted
    ice_field_office VARCHAR(100),
    article_id INTEGER REFERENCES articles(id),
    source_link TEXT,
    date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified BOOLEAN DEFAULT FALSE,
    community_impact_score INTEGER, -- 1-10 scale
    status VARCHAR(20) DEFAULT 'active'
);

-- Federal contracts related to ICE
CREATE TABLE federal_contracts (
    id SERIAL PRIMARY KEY,
    contract_number VARCHAR(100) UNIQUE,
    vendor_name VARCHAR(255) NOT NULL,
    contract_description TEXT,
    total_value DECIMAL(15, 2),
    date_awarded DATE,
    date_start DATE,
    date_end DATE,
    contracting_agency VARCHAR(100), -- ICE, CBP, etc.
    contract_type VARCHAR(50), -- facility_operations, transportation, etc.
    facility_id INTEGER REFERENCES facilities(id),
    performance_metrics JSON,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_link TEXT,
    status VARCHAR(20) DEFAULT 'active'
);

-- Court cases and legal proceedings
CREATE TABLE court_cases (
    id SERIAL PRIMARY KEY,
    case_number VARCHAR(100),
    court_name VARCHAR(255),
    case_type VARCHAR(50), -- immigration, civil_rights, criminal
    filing_date DATE,
    case_status VARCHAR(50), -- pending, closed, appealed
    plaintiff VARCHAR(255),
    defendant VARCHAR(255),
    case_summary TEXT,
    outcome TEXT,
    significance_level INTEGER, -- 1-10 scale
    geographic_impact JSON, -- States/regions affected
    facility_id INTEGER REFERENCES facilities(id),
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_link TEXT,
    pdf_link TEXT
);

-- Social media and community reports
CREATE TABLE community_reports (
    id SERIAL PRIMARY KEY,
    report_date TIMESTAMP,
    report_type VARCHAR(50), -- sighting, raid, checkpoint, family_separation
    location_description TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    reporter_type VARCHAR(50), -- community_member, legal_aid, media
    description TEXT,
    verification_status VARCHAR(20), -- unverified, verified, false
    related_article_id INTEGER REFERENCES articles(id),
    related_operation_id INTEGER REFERENCES enforcement_operations(id),
    sensitivity_level INTEGER, -- 1-5 (5 = high sensitivity)
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_platform VARCHAR(50) -- twitter, facebook, direct_report
);

-- Data processing and quality logs
CREATE TABLE processing_logs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    scrape_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    items_processed INTEGER DEFAULT 0,
    items_new INTEGER DEFAULT 0,
    items_duplicate INTEGER DEFAULT 0,
    items_error INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    lambda_function VARCHAR(100),
    data_quality_score DECIMAL(3, 2), -- 0-1 scale
    status VARCHAR(20) DEFAULT 'success', -- success, partial, failed
    error_message TEXT,
    performance_metrics JSON
);

-- Search and indexing for fast queries
CREATE INDEX idx_articles_date ON articles(date_published DESC);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_articles_hash ON articles(hash_content);
CREATE INDEX idx_geographic_state ON geographic_case_counts(state_name);
CREATE INDEX idx_geographic_category ON geographic_case_counts(category);
CREATE INDEX idx_facilities_location ON facilities(state, city);
CREATE INDEX idx_facilities_status ON facilities(operational_status);
CREATE INDEX idx_operations_date ON enforcement_operations(operation_date DESC);
CREATE INDEX idx_operations_location ON enforcement_operations(location_state, location_county);
CREATE INDEX idx_contracts_vendor ON federal_contracts(vendor_name);
CREATE INDEX idx_contracts_value ON federal_contracts(total_value DESC);
CREATE INDEX idx_court_cases_date ON court_cases(filing_date DESC);
CREATE INDEX idx_community_reports_date ON community_reports(report_date DESC);
CREATE INDEX idx_community_reports_location ON community_reports(latitude, longitude);
CREATE INDEX idx_logs_source_date ON processing_logs(source, scrape_date DESC);

-- Full text search capabilities
CREATE INDEX idx_articles_search ON articles USING gin(to_tsvector('english', title || ' ' || COALESCE(summary, '') || ' ' || COALESCE(content, '')));
CREATE INDEX idx_foia_search ON foia_documents USING gin(to_tsvector('english', title || ' ' || COALESCE(content_summary, '')));
CREATE INDEX idx_operations_search ON enforcement_operations USING gin(to_tsvector('english', operation_name || ' ' || COALESCE(location_city, '') || ' ' || COALESCE(location_county, '')));

-- Views for common queries
CREATE VIEW v_facility_summary AS
SELECT 
    state,
    COUNT(*) as facility_count,
    SUM(capacity) as total_capacity,
    AVG(capacity) as avg_capacity,
    COUNT(CASE WHEN operational_status = 'active' THEN 1 END) as active_facilities
FROM facilities 
WHERE facility_type IS NOT NULL
GROUP BY state
ORDER BY total_capacity DESC;

CREATE VIEW v_enforcement_summary AS
SELECT 
    DATE_TRUNC('month', operation_date) as month,
    location_state,
    COUNT(*) as operation_count,
    SUM(arrests_count) as total_arrests,
    AVG(arrests_count) as avg_arrests_per_operation
FROM enforcement_operations 
WHERE operation_date IS NOT NULL
GROUP BY DATE_TRUNC('month', operation_date), location_state
ORDER BY month DESC, total_arrests DESC;

CREATE VIEW v_geographic_hierarchy AS
SELECT 
    state_name,
    county_name,
    subcounty_name,
    SUM(case_count) as total_cases,
    COUNT(*) as record_count
FROM geographic_case_counts
GROUP BY state_name, county_name, subcounty_name
ORDER BY total_cases DESC;