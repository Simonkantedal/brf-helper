from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
from brf_helper.analysis.brf_analyzer import BRFAnalyzer, BRFMetrics, BRFHealthScore

logger = logging.getLogger(__name__)


@dataclass
class ComparisonMetric:
    """A single metric comparison across multiple BRFs"""
    metric_name: str
    display_name: str
    values: Dict[str, Optional[float]]  # brf_name -> value
    unit: str
    higher_is_better: bool
    interpretation: str
    winner: Optional[str] = None  # BRF name with best value


@dataclass
class BRFComparisonResult:
    """Complete comparison result for multiple BRFs"""
    brf_names: List[str]
    overall_winner: str
    overall_scores: Dict[str, int]  # brf_name -> overall_score
    
    # Detailed comparisons
    metric_comparisons: List[ComparisonMetric]
    score_comparisons: Dict[str, Dict[str, int]]  # category -> brf_name -> score
    
    # Insights
    summary: str
    recommendations: Dict[str, List[str]]  # brf_name -> recommendations
    key_differences: List[str]
    
    # Individual analyses
    detailed_analyses: Dict[str, Tuple[BRFMetrics, BRFHealthScore]]


class BRFComparator:
    """Tool for comparing multiple BRFs side-by-side"""
    
    def __init__(self, analyzer: BRFAnalyzer):
        self.analyzer = analyzer
        
        # Define metrics for comparison
        self.comparison_metrics = [
            {
                "metric_name": "annual_result",
                "display_name": "Årets resultat",
                "unit": "kr",
                "higher_is_better": True,
                "interpretation": "Positivt resultat visar lönsamhet, negativt kan vara normalt p.g.a. avskrivningar"
            },
            {
                "metric_name": "operating_result", 
                "display_name": "Rörelseresultat",
                "unit": "kr",
                "higher_is_better": True,
                "interpretation": "Visar om intäkterna täcker driftskostnaderna - mycket viktigt att detta är positivt"
            },
            {
                "metric_name": "monthly_fee_per_sqm",
                "display_name": "Månadsavgift per kvm", 
                "unit": "kr/kvm",
                "higher_is_better": False,
                "interpretation": "Lägre avgift är generellt bättre, men kan indikera underskott på underhåll"
            },
            {
                "metric_name": "interest_costs",
                "display_name": "Räntekostnader",
                "unit": "kr",
                "higher_is_better": False,
                "interpretation": "Lägre räntekostnader indikerar lägre skuldsättning och mindre ränterisk"
            },
            {
                "metric_name": "cash_flow",
                "display_name": "Kassaflöde",
                "unit": "kr", 
                "higher_is_better": True,
                "interpretation": "Positivt kassaflöde visar att kassan växer, viktigt för framtida betalningsförmåga"
            },
            {
                "metric_name": "liquid_assets",
                "display_name": "Likvida medel",
                "unit": "kr",
                "higher_is_better": True, 
                "interpretation": "Högre kassa ger trygghet för oförutsedda kostnader"
            },
            {
                "metric_name": "solvency_ratio",
                "display_name": "Soliditet",
                "unit": "%",
                "higher_is_better": True,
                "interpretation": "Över 20% är bra, under 10% kan vara riskabelt - visar finansiell styrka"
            },
            {
                "metric_name": "maintenance_reserves",
                "display_name": "Underhållsreserver",
                "unit": "kr",
                "higher_is_better": True,
                "interpretation": "Högre reserver ger bättre förmåga att hantera framtida underhåll"
            }
        ]
    
    def compare_brfs(self, brf_names: List[str]) -> BRFComparisonResult:
        """Compare multiple BRFs and return comprehensive analysis"""
        logger.info(f"Starting comparison of BRFs: {brf_names}")
        
        if len(brf_names) < 2:
            raise ValueError("Need at least 2 BRFs to compare")
        
        # Analyze each BRF
        detailed_analyses = {}
        for brf_name in brf_names:
            logger.info(f"Analyzing {brf_name}")
            metrics, health_score = self.analyzer.analyze_brf(brf_name)
            detailed_analyses[brf_name] = (metrics, health_score)
        
        # Create metric comparisons
        metric_comparisons = self._create_metric_comparisons(detailed_analyses)
        
        # Create score comparisons
        score_comparisons = self._create_score_comparisons(detailed_analyses)
        
        # Determine overall winner
        overall_scores = {name: health_score.overall_score 
                         for name, (_, health_score) in detailed_analyses.items()}
        overall_winner = max(overall_scores.items(), key=lambda x: x[1])[0]
        
        # Generate insights
        summary = self._generate_comparison_summary(detailed_analyses, overall_winner)
        recommendations = self._generate_recommendations(detailed_analyses)
        key_differences = self._identify_key_differences(detailed_analyses)
        
        result = BRFComparisonResult(
            brf_names=brf_names,
            overall_winner=overall_winner,
            overall_scores=overall_scores,
            metric_comparisons=metric_comparisons,
            score_comparisons=score_comparisons,
            summary=summary,
            recommendations=recommendations,
            key_differences=key_differences,
            detailed_analyses=detailed_analyses
        )
        
        logger.info(f"Comparison complete. Winner: {overall_winner}")
        return result
    
    def _create_metric_comparisons(self, analyses: Dict[str, Tuple[BRFMetrics, BRFHealthScore]]) -> List[ComparisonMetric]:
        """Create detailed metric comparisons"""
        comparisons = []
        
        for metric_def in self.comparison_metrics:
            metric_name = metric_def["metric_name"]
            
            # Extract values for this metric
            values = {}
            for brf_name, (metrics, _) in analyses.items():
                # Handle special case for interest costs (convert to positive for comparison)
                value = getattr(metrics, metric_name)
                if metric_name == "interest_costs" and value is not None:
                    value = abs(value)  # Make positive for easier comparison
                values[brf_name] = value
            
            # Determine winner
            winner = None
            if any(v is not None for v in values.values()):
                valid_values = {k: v for k, v in values.items() if v is not None}
                if valid_values:
                    if metric_def["higher_is_better"]:
                        winner = max(valid_values.items(), key=lambda x: x[1])[0]
                    else:
                        winner = min(valid_values.items(), key=lambda x: x[1])[0]
            
            comparison = ComparisonMetric(
                metric_name=metric_name,
                display_name=metric_def["display_name"],
                values=values,
                unit=metric_def["unit"],
                higher_is_better=metric_def["higher_is_better"],
                interpretation=metric_def["interpretation"],
                winner=winner
            )
            
            comparisons.append(comparison)
        
        return comparisons
    
    def _create_score_comparisons(self, analyses: Dict[str, Tuple[BRFMetrics, BRFHealthScore]]) -> Dict[str, Dict[str, int]]:
        """Create score comparisons across categories"""
        categories = [
            "financial_stability_score",
            "cost_efficiency_score", 
            "liquidity_score",
            "debt_management_score",
            "maintenance_readiness_score"
        ]
        
        comparisons = {}
        for category in categories:
            comparisons[category] = {}
            for brf_name, (_, health_score) in analyses.items():
                comparisons[category][brf_name] = getattr(health_score, category)
        
        return comparisons
    
    def _generate_comparison_summary(
        self, 
        analyses: Dict[str, Tuple[BRFMetrics, BRFHealthScore]], 
        winner: str
    ) -> str:
        """Generate a summary of the comparison"""
        
        brf_names = list(analyses.keys())
        winner_score = analyses[winner][1].overall_score
        
        # Find second place
        scores = [(name, health_score.overall_score) 
                 for name, (_, health_score) in analyses.items()]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        summary_parts = []
        
        # Overall winner
        summary_parts.append(f"**Övergripande vinnare: {winner}** ({winner_score}/100 poäng)")
        
        # Rankings
        summary_parts.append("\n**Ranking:**")
        for i, (name, score) in enumerate(scores, 1):
            summary_parts.append(f"{i}. {name}: {score}/100 poäng")
        
        # Score difference analysis
        if len(scores) >= 2:
            first_score = scores[0][1]
            second_score = scores[1][1]
            diff = first_score - second_score
            
            if diff <= 5:
                summary_parts.append(f"\n⚖️ **Mycket jämn tävling** - endast {diff} poängs skillnad mellan topp 2")
            elif diff <= 15:
                summary_parts.append(f"\n📊 **Tydlig ledare** - {scores[0][0]} leder med {diff} poäng")
            else:
                summary_parts.append(f"\n🏆 **Klar vinnare** - {scores[0][0]} leder med {diff} poäng")
        
        return "\n".join(summary_parts)
    
    def _generate_recommendations(self, analyses: Dict[str, Tuple[BRFMetrics, BRFHealthScore]]) -> Dict[str, List[str]]:
        """Generate specific recommendations for each BRF"""
        recommendations = {}
        
        for brf_name, (metrics, health_score) in analyses.items():
            brf_recommendations = []
            
            # Overall score based recommendations
            if health_score.overall_score >= 80:
                brf_recommendations.append("✅ Utmärkt val med stark ekonomisk profil")
            elif health_score.overall_score >= 65:
                brf_recommendations.append("👍 Bra alternativ som kan rekommenderas")
            elif health_score.overall_score >= 50:
                brf_recommendations.append("⚠️ Kräver noggrann granskning innan beslut")
            else:
                brf_recommendations.append("❌ Hög risk - rekommenderas ej utan djupare analys")
            
            # Specific weaknesses
            if health_score.financial_stability_score < 50:
                brf_recommendations.append("🔍 Granska den finansiella stabiliteten noga")
            if health_score.cost_efficiency_score < 50:
                brf_recommendations.append("💰 Höga kostnader - kontrollera avgiftsutvecklingen")
            if health_score.liquidity_score < 50:
                brf_recommendations.append("💧 Liquiditetsproblem - kontrollera kassaflödet")
            if health_score.debt_management_score < 50:
                brf_recommendations.append("📊 Hög skuldsättning - kontrollera ränterisk")
            if health_score.maintenance_readiness_score < 50:
                brf_recommendations.append("🔧 Underhållsrisk - kontrollera framtida renoveringskostnader")
            
            # Add general recommendations
            brf_recommendations.extend(health_score.recommendations)
            
            recommendations[brf_name] = brf_recommendations
        
        return recommendations
    
    def _identify_key_differences(self, analyses: Dict[str, Tuple[BRFMetrics, BRFHealthScore]]) -> List[str]:
        """Identify the most significant differences between BRFs"""
        differences = []
        
        brf_names = list(analyses.keys())
        if len(brf_names) < 2:
            return differences
        
        # Compare scores across categories
        categories = [
            ("financial_stability_score", "Finansiell stabilitet"),
            ("cost_efficiency_score", "Kostnadseffektivitet"),
            ("liquidity_score", "Likviditet"),
            ("debt_management_score", "Skuldsättning"),
            ("maintenance_readiness_score", "Underhållsberedskap")
        ]
        
        for score_attr, display_name in categories:
            scores = {name: getattr(health_score, score_attr) 
                     for name, (_, health_score) in analyses.items()}
            
            max_score = max(scores.values())
            min_score = min(scores.values()) 
            diff = max_score - min_score
            
            if diff >= 30:  # Significant difference
                best_brf = max(scores.items(), key=lambda x: x[1])[0]
                worst_brf = min(scores.items(), key=lambda x: x[1])[0]
                differences.append(
                    f"**{display_name}**: Stor skillnad - {best_brf} ({max_score}) vs {worst_brf} ({min_score})"
                )
        
        # Compare key metrics
        for brf1 in brf_names:
            for brf2 in brf_names:
                if brf1 >= brf2:  # Avoid duplicates
                    continue
                    
                metrics1, _ = analyses[brf1]
                metrics2, _ = analyses[brf2]
                
                # Monthly fee comparison
                if (metrics1.monthly_fee_per_sqm and metrics2.monthly_fee_per_sqm):
                    fee_diff = abs(metrics1.monthly_fee_per_sqm - metrics2.monthly_fee_per_sqm)
                    if fee_diff > 10:  # More than 10 kr/sqm difference
                        cheaper = brf1 if metrics1.monthly_fee_per_sqm < metrics2.monthly_fee_per_sqm else brf2
                        expensive = brf2 if cheaper == brf1 else brf1
                        cheaper_fee = metrics1.monthly_fee_per_sqm if cheaper == brf1 else metrics2.monthly_fee_per_sqm
                        expensive_fee = metrics2.monthly_fee_per_sqm if expensive == brf2 else metrics1.monthly_fee_per_sqm
                        differences.append(
                            f"**Månadsavgift**: {cheaper} ({cheaper_fee:.0f} kr/kvm) vs {expensive} ({expensive_fee:.0f} kr/kvm) - {fee_diff:.0f} kr skillnad/kvm"
                        )
        
        return differences[:5]  # Limit to top 5 differences