-- BRF Helper Database Schema V2
-- Stores ONLY raw extracted data, not computed analysis results
-- Analysis (scores, red flags) computed on-the-fly from raw data

-- Main BRF table with metadata
CREATE TABLE IF NOT EXISTS brfs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brf_name TEXT UNIQUE NOT NULL,
    display_name TEXT,
    organization_number TEXT,
    
    -- Document metadata
    pdf_path TEXT,
    num_pages INTEGER,
    num_chunks INTEGER,
    
    -- Building information (extracted from report)
    building_year INTEGER,
    num_apartments INTEGER,
    total_area REAL,
    address TEXT,
    
    -- Timestamps
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metrics_extracted_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Status flags
    has_metrics BOOLEAN DEFAULT FALSE,
    extraction_version TEXT DEFAULT '1.0'
);

-- Financial metrics extracted from reports (RAW DATA ONLY)
CREATE TABLE IF NOT EXISTS brf_financial_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brf_id INTEGER UNIQUE NOT NULL,  -- One set of metrics per BRF
    
    -- Income statement metrics
    annual_result REAL,                    -- Årets resultat
    operating_result REAL,                 -- Rörelseresultat
    total_income REAL,                     -- Totala intäkter
    total_expenses REAL,                   -- Totala kostnader
    
    -- Costs breakdown
    interest_costs REAL,                   -- Räntekostnader (often negative)
    maintenance_costs REAL,                -- Underhållskostnader
    operation_costs REAL,                  -- Driftskostnader
    administration_costs REAL,             -- Administrationskostnader
    
    -- Cash flow
    cash_flow REAL,                        -- Kassaflöde
    cash_flow_operations REAL,            -- Kassaflöde från verksamheten
    cash_flow_investments REAL,           -- Kassaflöde från investeringar
    cash_flow_financing REAL,             -- Kassaflöde från finansiering
    
    -- Balance sheet - Assets
    liquid_assets REAL,                    -- Likvida medel (kassa + bank)
    current_assets REAL,                   -- Omsättningstillgångar
    fixed_assets REAL,                     -- Anläggningstillgångar
    total_assets REAL,                     -- Totala tillgångar
    
    -- Balance sheet - Liabilities
    current_liabilities REAL,              -- Kortfristiga skulder
    long_term_debt REAL,                   -- Långfristiga skulder
    total_debt REAL,                       -- Totala skulder
    
    -- Balance sheet - Equity
    equity REAL,                           -- Eget kapital
    equity_start_of_year REAL,            -- Eget kapital vid årets början
    
    -- Calculated ratios (if provided in report, otherwise NULL)
    solvency_ratio REAL,                   -- Soliditet (%)
    
    -- Per-apartment metrics
    monthly_fee_per_sqm REAL,             -- Månadsavgift per kvm
    annual_fee_per_apartment REAL,        -- Årsavgift per lägenhet
    
    -- Reserves and funds
    maintenance_reserves REAL,             -- Underhållsfond
    renovation_fund REAL,                  -- Renoveringsfond
    
    -- Previous year comparison (if available)
    annual_result_previous_year REAL,
    equity_previous_year REAL,
    
    -- Metadata
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extraction_method TEXT DEFAULT 'llm',  -- 'llm', 'ocr', 'manual'
    data_quality_score REAL,               -- 0-1, confidence in extraction
    
    FOREIGN KEY (brf_id) REFERENCES brfs(id) ON DELETE CASCADE
);

-- Additional context extracted from reports (RAW TEXT)
CREATE TABLE IF NOT EXISTS brf_report_extracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brf_id INTEGER NOT NULL,
    
    -- Text extracts from specific sections
    auditor_report TEXT,                   -- Full auditor's report
    board_report TEXT,                     -- Styrelseberättelse
    maintenance_plan TEXT,                 -- Underhållsplan
    income_statement_notes TEXT,           -- Noter till resultaträkning
    balance_sheet_notes TEXT,              -- Noter till balansräkning
    
    -- Extracted facts (not computed)
    has_auditor_remarks BOOLEAN,          -- Har revisorn anmärkningar?
    has_ongoing_disputes BOOLEAN,         -- Pågående tvister?
    has_previous_assessments BOOLEAN,     -- Tidigare uttaxeringar?
    major_renovations_planned TEXT,       -- Planerade större renoveringar
    major_renovations_completed TEXT,     -- Genomförda större renoveringar
    
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (brf_id) REFERENCES brfs(id) ON DELETE CASCADE
);

-- Historical metrics (for trend analysis)
CREATE TABLE IF NOT EXISTS brf_financial_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brf_id INTEGER NOT NULL,
    report_year INTEGER NOT NULL,         -- Which year this data is from
    
    -- Same metrics as brf_financial_metrics
    annual_result REAL,
    operating_result REAL,
    total_debt REAL,
    equity REAL,
    solvency_ratio REAL,
    monthly_fee_per_sqm REAL,
    
    -- When this historical data was extracted
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (brf_id) REFERENCES brfs(id) ON DELETE CASCADE,
    UNIQUE(brf_id, report_year)  -- One entry per BRF per year
);

-- Cache computed analysis (optional, for performance)
-- This is the ONLY table with computed values
CREATE TABLE IF NOT EXISTS brf_analysis_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brf_id INTEGER UNIQUE NOT NULL,
    
    -- Computed scores (from current analysis logic version)
    overall_score INTEGER,
    financial_stability_score INTEGER,
    cost_efficiency_score INTEGER,
    liquidity_score INTEGER,
    debt_management_score INTEGER,
    maintenance_readiness_score INTEGER,
    
    -- Computed risk assessment
    overall_risk_level TEXT,
    total_red_flags INTEGER,
    critical_red_flags INTEGER,
    high_red_flags INTEGER,
    
    -- When this was computed and which version of logic
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_version TEXT NOT NULL,       -- Track which logic version
    
    -- Invalidate cache when metrics change
    metrics_hash TEXT,                     -- Hash of metrics used
    
    FOREIGN KEY (brf_id) REFERENCES brfs(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_brfs_name ON brfs(brf_name);
CREATE INDEX IF NOT EXISTS idx_brfs_has_metrics ON brfs(has_metrics);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_brf ON brf_financial_metrics(brf_id);
CREATE INDEX IF NOT EXISTS idx_report_extracts_brf ON brf_report_extracts(brf_id);
CREATE INDEX IF NOT EXISTS idx_history_brf_year ON brf_financial_metrics_history(brf_id, report_year);
CREATE INDEX IF NOT EXISTS idx_cache_brf ON brf_analysis_cache(brf_id);
CREATE INDEX IF NOT EXISTS idx_cache_version ON brf_analysis_cache(analysis_version);

-- Trigger to update timestamps
CREATE TRIGGER IF NOT EXISTS update_brf_timestamp 
AFTER UPDATE ON brfs
FOR EACH ROW
BEGIN
    UPDATE brfs SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to invalidate cache when metrics change
CREATE TRIGGER IF NOT EXISTS invalidate_cache_on_metrics_update
AFTER UPDATE ON brf_financial_metrics
FOR EACH ROW
BEGIN
    DELETE FROM brf_analysis_cache WHERE brf_id = NEW.brf_id;
END;
