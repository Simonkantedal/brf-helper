import sqlite3
import logging
import hashlib
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from brf_helper.database.models import (
    BRF, BRFFinancialMetrics, BRFReportExtracts,
    BRFFinancialMetricsHistory, BRFAnalysisCache, BRFWithMetrics
)

logger = logging.getLogger(__name__)


class BRFDatabase:
    """
    Database for storing RAW BRF metrics only.
    Analysis (scores, red flags) are computed on-the-fly from raw data.
    """
    
    def __init__(self, db_path: str = "./data/brf_analysis.db"):
        self.db_path = db_path
        self._ensure_directory()
        self.conn = None
        self._initialize_db()
    
    def _ensure_directory(self):
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def _initialize_db(self):
        schema_path = Path(__file__).parent / "schema.sql"
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        conn = self._get_connection()
        conn.executescript(schema_sql)
        conn.commit()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    # ==================== BRF Operations ====================
    
    def create_or_update_brf(self, brf_name: str, **kwargs) -> int:
        """Create or update BRF metadata"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM brfs WHERE brf_name = ?", (brf_name,))
        existing = cursor.fetchone()
        
        if existing:
            brf_id = existing['id']
            
            set_clauses = []
            values = []
            for key, value in kwargs.items():
                if key != 'brf_name':
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if set_clauses:
                values.append(brf_id)
                sql = f"UPDATE brfs SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(sql, values)
            
            logger.info(f"Updated BRF: {brf_name} (ID: {brf_id})")
        else:
            columns = ['brf_name'] + list(kwargs.keys())
            placeholders = ','.join(['?'] * len(columns))
            values = [brf_name] + list(kwargs.values())
            
            sql = f"INSERT INTO brfs ({','.join(columns)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            brf_id = cursor.lastrowid
            
            logger.info(f"Created BRF: {brf_name} (ID: {brf_id})")
        
        conn.commit()
        return brf_id
    
    def get_brf_by_name(self, brf_name: str) -> Optional[BRF]:
        """Get BRF by name"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM brfs WHERE brf_name = ?", (brf_name,))
        row = cursor.fetchone()
        
        if row:
            return BRF(**dict(row))
        return None
    
    def get_brf_by_id(self, brf_id: int) -> Optional[BRF]:
        """Get BRF by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM brfs WHERE id = ?", (brf_id,))
        row = cursor.fetchone()
        
        if row:
            return BRF(**dict(row))
        return None
    
    def list_all_brfs(self, with_metrics_only: bool = False) -> List[BRF]:
        """List all BRFs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if with_metrics_only:
            cursor.execute("SELECT * FROM brfs WHERE has_metrics = 1 ORDER BY brf_name")
        else:
            cursor.execute("SELECT * FROM brfs ORDER BY brf_name")
        
        return [BRF(**dict(row)) for row in cursor.fetchall()]
    
    # ==================== Financial Metrics Operations ====================
    
    def save_financial_metrics(self, brf_id: int, metrics: Dict[str, Any]) -> int:
        """Save or update financial metrics for a BRF"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if metrics already exist
        cursor.execute("SELECT id FROM brf_financial_metrics WHERE brf_id = ?", (brf_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            set_clauses = []
            values = []
            for key, value in metrics.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if set_clauses:
                values.append(brf_id)
                sql = f"UPDATE brf_financial_metrics SET {', '.join(set_clauses)} WHERE brf_id = ?"
                cursor.execute(sql, values)
            
            metrics_id = existing['id']
        else:
            # Insert new
            columns = ['brf_id'] + list(metrics.keys())
            placeholders = ','.join(['?'] * len(columns))
            values = [brf_id] + list(metrics.values())
            
            sql = f"INSERT INTO brf_financial_metrics ({','.join(columns)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            metrics_id = cursor.lastrowid
        
        # Mark BRF as having metrics
        cursor.execute(
            "UPDATE brfs SET has_metrics = 1, metrics_extracted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (brf_id,)
        )
        
        conn.commit()
        logger.info(f"Saved financial metrics for BRF ID {brf_id}")
        return metrics_id
    
    def get_financial_metrics(self, brf_id: int) -> Optional[BRFFinancialMetrics]:
        """Get financial metrics for a BRF"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM brf_financial_metrics WHERE brf_id = ?", (brf_id,))
        row = cursor.fetchone()
        
        if row:
            return BRFFinancialMetrics(**dict(row))
        return None
    
    # ==================== Report Extracts Operations ====================
    
    def save_report_extracts(self, brf_id: int, extracts: Dict[str, Any]) -> int:
        """Save text extracts and boolean flags"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if extracts already exist
        cursor.execute("SELECT id FROM brf_report_extracts WHERE brf_id = ?", (brf_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update
            set_clauses = []
            values = []
            for key, value in extracts.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
            
            if set_clauses:
                values.append(brf_id)
                sql = f"UPDATE brf_report_extracts SET {', '.join(set_clauses)} WHERE brf_id = ?"
                cursor.execute(sql, values)
            
            extract_id = existing['id']
        else:
            # Insert
            columns = ['brf_id'] + list(extracts.keys())
            placeholders = ','.join(['?'] * len(columns))
            values = [brf_id] + list(extracts.values())
            
            sql = f"INSERT INTO brf_report_extracts ({','.join(columns)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            extract_id = cursor.lastrowid
        
        conn.commit()
        return extract_id
    
    def get_report_extracts(self, brf_id: int) -> Optional[BRFReportExtracts]:
        """Get report extracts for a BRF"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM brf_report_extracts WHERE brf_id = ?", (brf_id,))
        row = cursor.fetchone()
        
        if row:
            return BRFReportExtracts(**dict(row))
        return None
    
    # ==================== Analysis Cache Operations (Optional) ====================
    
    def save_analysis_cache(
        self, 
        brf_id: int, 
        analysis: Dict[str, Any],
        analysis_version: str = "1.0"
    ) -> int:
        """Save computed analysis results to cache"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Calculate metrics hash for cache invalidation
        metrics = self.get_financial_metrics(brf_id)
        metrics_hash = self._calculate_metrics_hash(metrics) if metrics else None
        
        # Delete existing cache
        cursor.execute("DELETE FROM brf_analysis_cache WHERE brf_id = ?", (brf_id,))
        
        # Insert new cache
        analysis['brf_id'] = brf_id
        analysis['analysis_version'] = analysis_version
        analysis['metrics_hash'] = metrics_hash
        
        columns = list(analysis.keys())
        placeholders = ','.join(['?'] * len(columns))
        values = list(analysis.values())
        
        sql = f"INSERT INTO brf_analysis_cache ({','.join(columns)}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        
        conn.commit()
        return cursor.lastrowid
    
    def get_analysis_cache(
        self, 
        brf_id: int,
        analysis_version: str = "1.0"
    ) -> Optional[BRFAnalysisCache]:
        """Get cached analysis if valid"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM brf_analysis_cache WHERE brf_id = ? AND analysis_version = ?",
            (brf_id, analysis_version)
        )
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Verify cache is still valid (metrics haven't changed)
        cached = BRFAnalysisCache(**dict(row))
        metrics = self.get_financial_metrics(brf_id)
        current_hash = self._calculate_metrics_hash(metrics) if metrics else None
        
        if cached.metrics_hash != current_hash:
            logger.info(f"Analysis cache invalid for BRF ID {brf_id} (metrics changed)")
            # Delete invalid cache
            cursor.execute("DELETE FROM brf_analysis_cache WHERE brf_id = ?", (brf_id,))
            conn.commit()
            return None
        
        return cached
    
    def _calculate_metrics_hash(self, metrics: BRFFinancialMetrics) -> str:
        """Calculate hash of metrics for cache invalidation"""
        # Serialize relevant metric fields
        data = {
            'annual_result': metrics.annual_result,
            'operating_result': metrics.operating_result,
            'total_debt': metrics.total_debt,
            'equity': metrics.equity,
            'solvency_ratio': metrics.solvency_ratio,
            'liquid_assets': metrics.liquid_assets,
            'cash_flow': metrics.cash_flow,
            'interest_costs': metrics.interest_costs,
            'monthly_fee_per_sqm': metrics.monthly_fee_per_sqm,
            'maintenance_reserves': metrics.maintenance_reserves,
        }
        
        # Create hash
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    # ==================== Combined Operations ====================
    
    def get_brf_with_metrics(self, brf_name: str) -> Optional[BRFWithMetrics]:
        """Get BRF with all raw metrics"""
        brf = self.get_brf_by_name(brf_name)
        if not brf:
            return None
        
        return BRFWithMetrics(
            brf=brf,
            metrics=self.get_financial_metrics(brf.id),
            extracts=self.get_report_extracts(brf.id),
            history=[]  # TODO: implement history retrieval if needed
        )
