import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from brf_helper.llm.rag_interface import BRFQueryInterface

logger = logging.getLogger(__name__)


@dataclass
class BRFMetrics:
    """Core financial metrics for a BRF"""
    brf_name: str
    annual_result: Optional[float] = None  # Årets resultat
    operating_result: Optional[float] = None  # Rörelseresultat
    interest_costs: Optional[float] = None  # Räntekostnader
    cash_flow: Optional[float] = None  # Kassaflöde
    liquid_assets: Optional[float] = None  # Likvida medel
    monthly_fee_per_sqm: Optional[float] = None  # Årsavgift per kvm/månad
    total_debt: Optional[float] = None  # Skulder
    equity: Optional[float] = None  # Eget kapital
    solvency_ratio: Optional[float] = None  # Soliditet
    maintenance_reserves: Optional[float] = None  # Underhållsfond
    
    # Additional context
    num_apartments: Optional[int] = None
    building_year: Optional[int] = None
    total_area: Optional[float] = None


@dataclass 
class BRFHealthScore:
    """Comprehensive health assessment for a BRF"""
    overall_score: int  # 0-100
    financial_stability_score: int  # 0-100
    cost_efficiency_score: int  # 0-100
    liquidity_score: int  # 0-100
    debt_management_score: int  # 0-100
    maintenance_readiness_score: int  # 0-100
    
    # Explanations
    overall_explanation: str
    strengths: List[str]
    concerns: List[str]
    red_flags: List[str]
    recommendations: List[str]


class BRFAnalyzer:
    """Advanced analyzer for BRF financial health assessment"""
    
    def __init__(self, query_interface: BRFQueryInterface):
        self.query_interface = query_interface
        
        # Metric extraction queries in Swedish
        self.metric_queries = {
            "annual_result": "Vad är årets resultat? Ange siffran i kronor.",
            "operating_result": "Vad är rörelseresultatet? Ange beloppet i kronor.",
            "interest_costs": "Hur mycket betalar föreningen i räntekostnader per år? Ange beloppet i kronor.",
            "cash_flow": "Vad är föreningens kassaflöde för året? Ange beloppet i kronor.",
            "liquid_assets": "Hur mycket likvida medel har föreningen? Ange beloppet i kronor.",
            "monthly_fee": "Vad är den genomsnittliga månadsavgiften per kvadratmeter? Ange i kronor per kvm och månad.",
            "total_debt": "Vad är föreningens totala skulder? Ange beloppet i kronor.",
            "equity": "Vad är föreningens egna kapital? Ange beloppet i kronor.",
            "solvency_ratio": "Vad är föreningens soliditet? Ange i procent.",
            "maintenance_reserves": "Hur mycket har föreningen avsatt för underhåll och renoveringar? Ange beloppet i kronor.",
            "building_info": "Vilket år byggdes fastigheten och hur många lägenheter finns det? Vad är den totala arean?",
        }
    
    def extract_metrics(self, brf_name: str) -> BRFMetrics:
        """Extract key financial metrics for a specific BRF"""
        logger.info(f"Extracting metrics for BRF: {brf_name}")
        
        metrics = BRFMetrics(brf_name=brf_name)
        
        # Extract each metric using targeted queries
        for metric_key, query in self.metric_queries.items():
            try:
                logger.debug(f"Extracting {metric_key} for {brf_name}")
                
                result = self.query_interface.query(
                    question=query,
                    brf_name=brf_name,
                    include_sources=False
                )
                
                answer = result.get("answer", "")
                
                # Parse numeric values from the response
                if metric_key == "building_info":
                    self._parse_building_info(answer, metrics)
                else:
                    value = self._extract_numeric_value(answer)
                    setattr(metrics, metric_key, value)
                    
            except Exception as e:
                logger.warning(f"Failed to extract {metric_key} for {brf_name}: {e}")
                
        return metrics
    
    def calculate_health_score(self, metrics: BRFMetrics) -> BRFHealthScore:
        """Calculate comprehensive health score based on extracted metrics"""
        logger.info(f"Calculating health score for {metrics.brf_name}")
        
        # Individual component scores
        financial_stability = self._score_financial_stability(metrics)
        cost_efficiency = self._score_cost_efficiency(metrics)
        liquidity = self._score_liquidity(metrics)
        debt_management = self._score_debt_management(metrics)
        maintenance_readiness = self._score_maintenance_readiness(metrics)
        
        # Weighted overall score
        weights = {
            "financial_stability": 0.25,
            "cost_efficiency": 0.20,
            "liquidity": 0.20,
            "debt_management": 0.20,
            "maintenance_readiness": 0.15,
        }
        
        overall = int(
            financial_stability * weights["financial_stability"] +
            cost_efficiency * weights["cost_efficiency"] +
            liquidity * weights["liquidity"] +
            debt_management * weights["debt_management"] +
            maintenance_readiness * weights["maintenance_readiness"]
        )
        
        # Generate explanations and insights
        explanations = self._generate_explanations(
            metrics, overall, financial_stability, cost_efficiency,
            liquidity, debt_management, maintenance_readiness
        )
        
        return BRFHealthScore(
            overall_score=overall,
            financial_stability_score=financial_stability,
            cost_efficiency_score=cost_efficiency,
            liquidity_score=liquidity,
            debt_management_score=debt_management,
            maintenance_readiness_score=maintenance_readiness,
            **explanations
        )
    
    def analyze_brf(self, brf_name: str) -> Tuple[BRFMetrics, BRFHealthScore]:
        """Complete analysis of a BRF - extract metrics and calculate health score"""
        logger.info(f"Starting complete analysis of BRF: {brf_name}")
        
        # Extract metrics
        metrics = self.extract_metrics(brf_name)
        
        # Calculate health score
        health_score = self.calculate_health_score(metrics)
        
        logger.info(f"Analysis complete for {brf_name}. Overall score: {health_score.overall_score}/100")
        
        return metrics, health_score
    
    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text response"""
        if not text:
            return None
            
        # Remove common Swedish currency and formatting
        text = text.replace(" kr", "").replace(" kronor", "").replace(" SEK", "")
        text = text.replace(" ", "").replace(",", ".")
        
        # Look for numbers (including negative)
        patterns = [
            r'-?\d+\.?\d*',  # General number pattern
            r'-?\d{1,3}(?:\.\d{3})*(?:,\d{2})?',  # Swedish number format
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # Take the first reasonable number found
                    value = float(matches[0].replace(",", "."))
                    return value
                except ValueError:
                    continue
        
        return None
    
    def _parse_building_info(self, text: str, metrics: BRFMetrics):
        """Parse building information from text response"""
        if not text:
            return
            
        # Extract building year
        year_match = re.search(r'19\d{2}|20\d{2}', text)
        if year_match:
            metrics.building_year = int(year_match.group())
        
        # Extract number of apartments
        apt_patterns = [
            r'(\d+)\s*(?:lägenheter|lägenhet)',
            r'(\d+)\s*(?:apartements|apt)',
        ]
        for pattern in apt_patterns:
            match = re.search(pattern, text.lower())
            if match:
                metrics.num_apartments = int(match.group(1))
                break
        
        # Extract total area
        area_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:kvm|m2|kvadratmeter)',
            r'(\d+(?:[.,]\d+)?)\s*(?:sqm|square)',
        ]
        for pattern in area_patterns:
            match = re.search(pattern, text.lower().replace(" ", ""))
            if match:
                metrics.total_area = float(match.group(1).replace(",", "."))
                break
    
    def _score_financial_stability(self, metrics: BRFMetrics) -> int:
        """Score financial stability (0-100)"""
        score = 50  # Start with neutral
        
        # Annual result impact
        if metrics.annual_result is not None:
            if metrics.annual_result >= 0:
                score += 20  # Positive result is good
            elif metrics.annual_result > -100000:  # Small loss acceptable
                score += 10
            elif metrics.annual_result > -500000:  # Moderate loss concerning
                score -= 10
            else:  # Large loss is bad
                score -= 30
        
        # Operating result impact
        if metrics.operating_result is not None:
            if metrics.operating_result > 0:
                score += 15  # Positive operating result is crucial
            else:
                score -= 25  # Negative operating result is very concerning
        
        # Solvency ratio impact
        if metrics.solvency_ratio is not None:
            if metrics.solvency_ratio > 20:
                score += 15  # Good solvency
            elif metrics.solvency_ratio > 10:
                score += 5   # Acceptable solvency
            else:
                score -= 20  # Poor solvency
        
        return max(0, min(100, score))
    
    def _score_cost_efficiency(self, metrics: BRFMetrics) -> int:
        """Score cost efficiency based on monthly fees (0-100)"""
        score = 50  # Start with neutral
        
        if metrics.monthly_fee_per_sqm is not None:
            # Benchmark monthly fees (kr/sqm/month)
            if metrics.monthly_fee_per_sqm < 40:
                score += 30  # Very good
            elif metrics.monthly_fee_per_sqm < 50:
                score += 15  # Good
            elif metrics.monthly_fee_per_sqm < 60:
                score += 0   # Average
            elif metrics.monthly_fee_per_sqm < 70:
                score -= 15  # High
            else:
                score -= 30  # Very high
        
        return max(0, min(100, score))
    
    def _score_liquidity(self, metrics: BRFMetrics) -> int:
        """Score liquidity based on cash flow and liquid assets (0-100)"""
        score = 50  # Start with neutral
        
        # Cash flow impact
        if metrics.cash_flow is not None:
            if metrics.cash_flow > 0:
                score += 25  # Positive cash flow is excellent
            elif metrics.cash_flow > -50000:  # Small negative acceptable
                score += 5
            else:
                score -= 20  # Large negative cash flow concerning
        
        # Liquid assets impact (rough estimate based on building size)
        if metrics.liquid_assets is not None and metrics.num_apartments:
            assets_per_apt = metrics.liquid_assets / metrics.num_apartments
            if assets_per_apt > 50000:
                score += 15  # Good reserves per apartment
            elif assets_per_apt > 20000:
                score += 5   # Acceptable reserves
            else:
                score -= 15  # Low reserves
        
        return max(0, min(100, score))
    
    def _score_debt_management(self, metrics: BRFMetrics) -> int:
        """Score debt management based on interest costs and debt levels (0-100)"""
        score = 50  # Start with neutral
        
        # Interest cost impact (as indicator of debt burden)
        if metrics.interest_costs is not None and metrics.num_apartments:
            interest_per_apt = abs(metrics.interest_costs) / metrics.num_apartments
            if interest_per_apt < 5000:
                score += 25  # Low debt burden
            elif interest_per_apt < 15000:
                score += 10  # Moderate debt burden
            elif interest_per_apt < 25000:
                score -= 5   # High debt burden
            else:
                score -= 25  # Very high debt burden
        
        # Debt to equity ratio if available
        if metrics.total_debt and metrics.equity:
            debt_to_equity = metrics.total_debt / metrics.equity
            if debt_to_equity < 0.5:
                score += 15  # Conservative debt level
            elif debt_to_equity < 1.0:
                score += 5   # Reasonable debt level
            elif debt_to_equity < 2.0:
                score -= 10  # High debt level
            else:
                score -= 25  # Excessive debt level
        
        return max(0, min(100, score))
    
    def _score_maintenance_readiness(self, metrics: BRFMetrics) -> int:
        """Score maintenance readiness based on reserves and building age (0-100)"""
        score = 50  # Start with neutral
        
        # Maintenance reserves impact
        if metrics.maintenance_reserves is not None and metrics.num_apartments:
            reserves_per_apt = metrics.maintenance_reserves / metrics.num_apartments
            if reserves_per_apt > 100000:
                score += 20  # Excellent reserves
            elif reserves_per_apt > 50000:
                score += 10  # Good reserves
            elif reserves_per_apt > 20000:
                score += 0   # Adequate reserves
            else:
                score -= 20  # Insufficient reserves
        
        # Building age impact (older buildings need more maintenance)
        if metrics.building_year:
            building_age = 2024 - metrics.building_year
            if building_age < 20:
                score += 10  # New building
            elif building_age < 40:
                score += 0   # Middle-aged building
            elif building_age < 60:
                score -= 10  # Older building
            else:
                score -= 20  # Very old building
        
        return max(0, min(100, score))
    
    def _generate_explanations(
        self, 
        metrics: BRFMetrics,
        overall: int,
        financial_stability: int,
        cost_efficiency: int,
        liquidity: int,
        debt_management: int,
        maintenance_readiness: int
    ) -> Dict[str, Any]:
        """Generate human-readable explanations for the scores"""
        
        # Overall explanation
        if overall >= 80:
            overall_explanation = f"{metrics.brf_name} visar utmärkt finansiell hälsa med stabila nyckeltal och låg risk."
        elif overall >= 65:
            overall_explanation = f"{metrics.brf_name} har god ekonomisk status med några områden som kan förbättras."
        elif overall >= 50:
            overall_explanation = f"{metrics.brf_name} har genomsnittlig ekonomisk status med vissa utmaningar att beakta."
        elif overall >= 35:
            overall_explanation = f"{metrics.brf_name} har svag ekonomisk status som kräver noggrann granskning."
        else:
            overall_explanation = f"{metrics.brf_name} visar betydande ekonomiska utmaningar och höga risker."
        
        # Identify strengths
        strengths = []
        if financial_stability >= 70:
            strengths.append("Stabil ekonomisk grund med hållbart resultat")
        if cost_efficiency >= 70:
            strengths.append("Konkurrenskraftiga månadsavgifter")
        if liquidity >= 70:
            strengths.append("God likviditet och kassaflöde")
        if debt_management >= 70:
            strengths.append("Välskött skuldsättning med låg räntebelastning")
        if maintenance_readiness >= 70:
            strengths.append("Goda resurser för framtida underhåll")
        
        # Identify concerns
        concerns = []
        if financial_stability < 50:
            concerns.append("Instabila finansiella resultat som behöver granskas")
        if cost_efficiency < 50:
            concerns.append("Höga månadsavgifter jämfört med marknaden")
        if liquidity < 50:
            concerns.append("Begränsad likviditet eller negativt kassaflöde")
        if debt_management < 50:
            concerns.append("Hög skuldsättning med betydande räntebelastning")
        if maintenance_readiness < 50:
            concerns.append("Otillräckliga resurser för framtida underhåll")
        
        # Identify red flags
        red_flags = []
        if metrics.operating_result is not None and metrics.operating_result < -100000:
            red_flags.append("Mycket negativt rörelseresultat - intäkterna täcker inte driftskostnaderna")
        if metrics.cash_flow is not None and metrics.cash_flow < -200000:
            red_flags.append("Kraftigt negativt kassaflöde som hotar föreningens likviditet")
        if financial_stability < 30:
            red_flags.append("Kritisk finansiell instabilitet")
        if debt_management < 30:
            red_flags.append("Ohållbart hög skuldsättning")
        
        # Generate recommendations
        recommendations = []
        if overall < 65:
            recommendations.append("Begär in flera års årsredovisningar för att se trender")
        if debt_management < 60:
            recommendations.append("Granska föreningens skuldsättning och amorteringsplan")
        if maintenance_readiness < 60:
            recommendations.append("Kontrollera planerat underhåll och kommande renoveringsprojekt")
        if cost_efficiency < 60:
            recommendations.append("Jämför månadsavgifterna med liknande föreningar i området")
        if liquidity < 60:
            recommendations.append("Undersök föreningens kassaflöde och likviditetssituation")
        
        return {
            "overall_explanation": overall_explanation,
            "strengths": strengths,
            "concerns": concerns,
            "red_flags": red_flags,
            "recommendations": recommendations,
        }