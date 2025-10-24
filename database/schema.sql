-- California Health Insurance Database Schema
-- schema for ML/AI pipeline

-- ============================================
-- CORE TABLES
-- ============================================

-- Insurance carriers/companies
CREATE TABLE carriers (
    carrier_id SERIAL PRIMARY KEY,
    carrier_name VARCHAR(255) NOT NULL UNIQUE,
    website_url VARCHAR(500),
    customer_service_phone VARCHAR(20),
    rating DECIMAL(3,2), -- e.g., 4.5 out of 5
    total_reviews INTEGER DEFAULT 0,
    am_best_rating VARCHAR(10), -- Financial strength rating
    founded_year INTEGER,
    headquarters_state VARCHAR(2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Main insurance plans table
CREATE TABLE insurance_plans (
    plan_id SERIAL PRIMARY KEY,
    carrier_id INTEGER REFERENCES carriers(carrier_id),
    plan_name VARCHAR(500) NOT NULL,
    plan_type VARCHAR(50) NOT NULL, -- HMO, PPO, EPO, POS
    metal_tier VARCHAR(20), -- Bronze, Silver, Gold, Platinum, Catastrophic
    plan_year INTEGER NOT NULL,
    is_covered_ca BOOLEAN DEFAULT TRUE, -- Available on Covered California marketplace
    hsa_eligible BOOLEAN DEFAULT FALSE, -- Health Savings Account eligible
    network_name VARCHAR(255),
    service_area TEXT, -- Counties covered
    
    -- Core financial details
    monthly_premium_base DECIMAL(10,2), -- Base premium (will vary by age)
    annual_deductible_individual DECIMAL(10,2),
    annual_deductible_family DECIMAL(10,2),
    out_of_pocket_max_individual DECIMAL(10,2),
    out_of_pocket_max_family DECIMAL(10,2),
    
    -- Copays and coinsurance
    primary_care_copay DECIMAL(8,2),
    specialist_copay DECIMAL(8,2),
    emergency_room_copay DECIMAL(8,2),
    urgent_care_copay DECIMAL(8,2),
    inpatient_hospital_copay DECIMAL(8,2),
    generic_drug_copay DECIMAL(8,2),
    coinsurance_percentage INTEGER, -- e.g., 20 for 20%
    
    -- Coverage details
    covers_telehealth BOOLEAN DEFAULT FALSE,
    telehealth_copay DECIMAL(8,2),
    prescription_drug_coverage BOOLEAN DEFAULT TRUE,
    dental_included BOOLEAN DEFAULT FALSE,
    vision_included BOOLEAN DEFAULT FALSE,
    
    -- Network size (for ML features)
    estimated_providers_count INTEGER,
    major_hospitals_in_network TEXT[], -- Array of hospital names
    
    -- Quality metrics
    quality_rating DECIMAL(3,2), -- CMS star rating
    customer_satisfaction_score DECIMAL(3,2),
    
    -- Data freshness tracking
    data_source VARCHAR(255), -- Where we scraped from
    last_verified_at TIMESTAMP,
    last_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_confidence_score DECIMAL(3,2) DEFAULT 1.0, -- Our confidence in data accuracy
    
    -- Metadata
    plan_details_url VARCHAR(1000),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(carrier_id, plan_name, plan_year)
);

-- Age-based premium pricing (premiums vary by age)
CREATE TABLE premium_by_age (
    premium_id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES insurance_plans(plan_id) ON DELETE CASCADE,
    age_start INTEGER NOT NULL,
    age_end INTEGER NOT NULL,
    monthly_premium DECIMAL(10,2) NOT NULL,
    tobacco_user_premium DECIMAL(10,2), -- Higher rate for tobacco users
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plan_id, age_start, age_end)
);

-- Detailed benefits coverage
CREATE TABLE plan_benefits (
    benefit_id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES insurance_plans(plan_id) ON DELETE CASCADE,
    benefit_category VARCHAR(100) NOT NULL, -- e.g., 'Maternity', 'Mental Health', 'Preventive Care'
    benefit_name VARCHAR(255) NOT NULL,
    is_covered BOOLEAN NOT NULL,
    coverage_details TEXT,
    cost_sharing_details TEXT, -- e.g., "20% coinsurance after deductible"
    visit_limit INTEGER, -- Some benefits have visit limits
    annual_maximum DECIMAL(10,2), -- Some benefits have dollar limits
    requires_referral BOOLEAN DEFAULT FALSE,
    requires_prior_auth BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plan_id, benefit_name)
);

-- Plan exclusions and limitations
CREATE TABLE plan_exclusions (
    exclusion_id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES insurance_plans(plan_id) ON DELETE CASCADE,
    exclusion_category VARCHAR(100),
    exclusion_description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Provider networks (doctors, hospitals)
CREATE TABLE provider_network (
    provider_id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES insurance_plans(plan_id) ON DELETE CASCADE,
    provider_name VARCHAR(500) NOT NULL,
    provider_type VARCHAR(100), -- Hospital, Primary Care, Specialist, etc.
    specialty VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(2) DEFAULT 'CA',
    zip_code VARCHAR(10),
    phone VARCHAR(20),
    accepting_new_patients BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User reviews and ratings (for ML features + user trust)
CREATE TABLE plan_reviews (
    review_id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES insurance_plans(plan_id) ON DELETE CASCADE,
    reviewer_source VARCHAR(100), -- e.g., 'BBB', 'ConsumerAffairs', 'Our Platform'
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    review_date DATE,
    helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ML/AI SPECIFIC TABLES
-- ============================================

-- For vector embeddings (RAG system)
CREATE TABLE plan_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    plan_id INTEGER REFERENCES insurance_plans(plan_id) ON DELETE CASCADE,
    embedding_text TEXT NOT NULL, -- The text that was embedded
    embedding_vector FLOAT8[], -- Store embedding vector (or use pgvector extension)
    embedding_model VARCHAR(100), -- e.g., 'text-embedding-ada-002'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(plan_id, embedding_model)
);

-- Track model predictions for monitoring
CREATE TABLE model_predictions (
    prediction_id SERIAL PRIMARY KEY,
    user_session_id VARCHAR(255),
    plan_id INTEGER REFERENCES insurance_plans(plan_id),
    prediction_score DECIMAL(5,4), -- Match score from ML model
    model_version VARCHAR(50),
    user_features JSONB, -- Store user input as JSON
    prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_feedback INTEGER, -- Did user click/select this plan?
    feedback_timestamp TIMESTAMP
);

-- A/B testing experiments
CREATE TABLE ab_experiments (
    experiment_id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(255) NOT NULL,
    variant_name VARCHAR(100) NOT NULL, -- 'control', 'variant_a', etc.
    user_session_id VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    converted BOOLEAN DEFAULT FALSE, -- Did user complete desired action?
    conversion_timestamp TIMESTAMP,
    UNIQUE(experiment_name, user_session_id)
);

-- ============================================
-- DATA QUALITY & MONITORING TABLES
-- ============================================

-- Track scraping jobs
CREATE TABLE scraping_jobs (
    job_id SERIAL PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    source_url VARCHAR(1000),
    status VARCHAR(50), -- 'running', 'completed', 'failed'
    plans_scraped INTEGER DEFAULT 0,
    plans_updated INTEGER DEFAULT 0,
    plans_failed INTEGER DEFAULT 0,
    error_log TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Data quality checks
CREATE TABLE data_quality_checks (
    check_id SERIAL PRIMARY KEY,
    check_name VARCHAR(255) NOT NULL,
    table_name VARCHAR(100),
    check_type VARCHAR(100), -- 'null_check', 'range_check', 'freshness_check'
    check_passed BOOLEAN,
    failure_details TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Query optimization indexes
CREATE INDEX idx_plans_carrier ON insurance_plans(carrier_id);
CREATE INDEX idx_plans_metal_tier ON insurance_plans(metal_tier);
CREATE INDEX idx_plans_type ON insurance_plans(plan_type);
CREATE INDEX idx_plans_active ON insurance_plans(is_active);
CREATE INDEX idx_plans_year ON insurance_plans(plan_year);
CREATE INDEX idx_premium_age_plan ON premium_by_age(plan_id, age_start, age_end);
CREATE INDEX idx_benefits_plan ON plan_benefits(plan_id);
CREATE INDEX idx_providers_plan ON provider_network(plan_id);
CREATE INDEX idx_reviews_plan ON plan_reviews(plan_id);
CREATE INDEX idx_predictions_session ON model_predictions(user_session_id);

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Complete plan view with carrier info
CREATE VIEW vw_plans_complete AS
SELECT 
    p.*,
    c.carrier_name,
    c.rating as carrier_rating,
    c.customer_service_phone,
    AVG(pr.rating) as avg_user_rating,
    COUNT(pr.review_id) as review_count
FROM insurance_plans p
JOIN carriers c ON p.carrier_id = c.carrier_id
LEFT JOIN plan_reviews pr ON p.plan_id = pr.plan_id
WHERE p.is_active = TRUE
GROUP BY p.plan_id, c.carrier_id;

-- Plan comparison view (optimized for comparison feature)
CREATE VIEW vw_plan_comparison AS
SELECT 
    p.plan_id,
    p.plan_name,
    c.carrier_name,
    p.metal_tier,
    p.plan_type,
    p.monthly_premium_base,
    p.annual_deductible_individual,
    p.out_of_pocket_max_individual,
    p.primary_care_copay,
    p.specialist_copay,
    p.quality_rating,
    p.covers_telehealth,
    p.hsa_eligible
FROM insurance_plans p
JOIN carriers c ON p.carrier_id = c.carrier_id
WHERE p.is_active = TRUE;