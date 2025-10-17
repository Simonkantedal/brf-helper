from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BRF:
    """Main BRF metadata"""
    id: Optional[int]
    brf_name: str
    display_name: Optional[str] = None
    organization_number: Optional[str] = None
    pdf_path: Optional[str] = None
    num_pages: Optional[int] = None
    num_chunks: Optional[int] = None
    building_year: Optional[int] = None
    num_apartments: Optional[int] = None
    total_area: Optional[float] = None
    address: Optional[str] = None
    ingested_at: Optional[datetime] = None
    metrics_extracted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    has_metrics: bool = False
    extraction_version: str = "1.0"


@dataclass
class BRFFinancialMetrics:
    """Raw financial metrics extracted from reports - NO COMPUTED VALUES"""
    id: Optional[int]
    brf_id: int
    
    # Income statement
    annual_result: Optional[float] = None
    operating_result: Optional[float] = None
    total_income: Optional[float] = None
    total_expenses: Optional[float] = None
    
    # Costs breakdown
    interest_costs: Optional[float] = None
    maintenance_costs: Optional[float] = None
    operation_costs: Optional[float] = None
    administration_costs: Optional[float] = None
    
    # Cash flow
    cash_flow: Optional[float] = None
    cash_flow_operations: Optional[float] = None
    cash_flow_investments: Optional[float] = None
    cash_flow_financing: Optional[float] = None
    
    # Balance sheet - Assets
    liquid_assets: Optional[float] = None
    current_assets: Optional[float] = None
    fixed_assets: Optional[float] = None
    total_assets: Optional[float] = None
    
    # Balance sheet - Liabilities
    current_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    total_debt: Optional[float] = None
    
    # Balance sheet - Equity
    equity: Optional[float] = None
    equity_start_of_year: Optional[float] = None
    
    # Ratios (if provided in report)
    solvency_ratio: Optional[float] = None
    
    # Per-apartment metrics
    annual_fee_per_sqm: Optional[float] = None
    annual_fee_per_apartment: Optional[float] = None
    
    # Reserves
    maintenance_reserves: Optional[float] = None
    renovation_fund: Optional[float] = None
    
    # Previous year (for comparison)
    annual_result_previous_year: Optional[float] = None
    equity_previous_year: Optional[float] = None
    
    # Metadata
    extracted_at: Optional[datetime] = None
    extraction_method: str = "llm"
    data_quality_score: Optional[float] = None


@dataclass
class BRFReportExtracts:
    """Text extracts and boolean flags from reports"""
    id: Optional[int]
    brf_id: int
    
    # Text sections
    auditor_report: Optional[str] = None
    board_report: Optional[str] = None
    maintenance_plan: Optional[str] = None
    income_statement_notes: Optional[str] = None
    balance_sheet_notes: Optional[str] = None
    
    # Boolean facts
    has_auditor_remarks: Optional[bool] = None
    has_ongoing_disputes: Optional[bool] = None
    has_previous_assessments: Optional[bool] = None
    major_renovations_planned: Optional[str] = None
    major_renovations_completed: Optional[str] = None
    
    extracted_at: Optional[datetime] = None


@dataclass
class BRFFinancialMetricsHistory:
    """Historical metrics for trend analysis"""
    id: Optional[int]
    brf_id: int
    report_year: int
    
    annual_result: Optional[float] = None
    operating_result: Optional[float] = None
    total_debt: Optional[float] = None
    equity: Optional[float] = None
    solvency_ratio: Optional[float] = None
    monthly_fee_per_sqm: Optional[float] = None
    
    extracted_at: Optional[datetime] = None


@dataclass
class BRFAnalysisCache:
    """OPTIONAL cache of computed analysis results"""
    id: Optional[int]
    brf_id: int
    
    # Computed scores
    overall_score: Optional[int] = None
    financial_stability_score: Optional[int] = None
    cost_efficiency_score: Optional[int] = None
    liquidity_score: Optional[int] = None
    debt_management_score: Optional[int] = None
    maintenance_readiness_score: Optional[int] = None
    
    # Computed risk
    overall_risk_level: Optional[str] = None
    total_red_flags: Optional[int] = None
    critical_red_flags: Optional[int] = None
    high_red_flags: Optional[int] = None
    
    # Cache metadata
    computed_at: Optional[datetime] = None
    analysis_version: str = "1.0"
    metrics_hash: Optional[str] = None


@dataclass
class BRFWithMetrics:
    """Combined BRF data with raw metrics"""
    brf: BRF
    metrics: Optional[BRFFinancialMetrics] = None
    extracts: Optional[BRFReportExtracts] = None
    history: list = None
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
