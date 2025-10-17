from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from brf_helper.analysis.brf_analyzer import BRFMetrics, BRFHealthScore
from brf_helper.llm.rag_interface import BRFQueryInterface

logger = logging.getLogger(__name__)


class RedFlagSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RedFlagCategory(Enum):
    FINANCIAL_STABILITY = "financial_stability"
    DEBT_RISK = "debt_risk"
    LIQUIDITY = "liquidity"
    MAINTENANCE = "maintenance"
    GOVERNANCE = "governance"
    LEGAL = "legal"
    OPERATIONAL = "operational"


@dataclass
class RedFlag:
    title: str
    category: RedFlagCategory
    severity: RedFlagSeverity
    description: str
    impact: str
    recommendation: str
    evidence: Optional[str] = None
    metric_value: Optional[float] = None


@dataclass
class RedFlagReport:
    brf_name: str
    total_red_flags: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    red_flags: List[RedFlag]
    overall_risk_level: str
    summary: str
    immediate_actions: List[str]


class RedFlagDetector:
    
    def __init__(self, query_interface: Optional[BRFQueryInterface] = None):
        self.query_interface = query_interface
        
        self.severity_thresholds = {
            "negative_operating_result_critical": -500000,
            "negative_operating_result_high": -100000,
            "negative_cash_flow_critical": -500000,
            "negative_cash_flow_high": -200000,
            "solvency_critical": 5,
            "solvency_high": 10,
            "solvency_medium": 15,
            "interest_per_apt_critical": 40000,
            "interest_per_apt_high": 25000,
            "interest_per_apt_medium": 15000,
            "monthly_fee_high": 70,
            "monthly_fee_medium": 60,
            "reserves_per_apt_low": 20000,
            "reserves_per_apt_critical": 10000,
            "building_age_old": 60,
            "building_age_very_old": 80,
            "debt_to_equity_critical": 3.0,
            "debt_to_equity_high": 2.0,
            "debt_to_equity_medium": 1.5,
        }
    
    def detect_red_flags(
        self,
        metrics: BRFMetrics,
        health_score: Optional[BRFHealthScore] = None
    ) -> RedFlagReport:
        logger.info(f"Detecting red flags for {metrics.brf_name}")
        
        red_flags = []
        
        red_flags.extend(self._check_financial_stability(metrics))
        red_flags.extend(self._check_debt_risk(metrics))
        red_flags.extend(self._check_liquidity(metrics))
        red_flags.extend(self._check_maintenance(metrics))
        red_flags.extend(self._check_operational_issues(metrics))
        
        if self.query_interface:
            red_flags.extend(self._check_governance_issues(metrics.brf_name))
            red_flags.extend(self._check_legal_issues(metrics.brf_name))
        
        severity_counts = {
            "critical": sum(1 for rf in red_flags if rf.severity == RedFlagSeverity.CRITICAL),
            "high": sum(1 for rf in red_flags if rf.severity == RedFlagSeverity.HIGH),
            "medium": sum(1 for rf in red_flags if rf.severity == RedFlagSeverity.MEDIUM),
            "low": sum(1 for rf in red_flags if rf.severity == RedFlagSeverity.LOW),
        }
        
        overall_risk = self._calculate_overall_risk(severity_counts)
        summary = self._generate_summary(metrics.brf_name, severity_counts, overall_risk)
        immediate_actions = self._generate_immediate_actions(red_flags)
        
        report = RedFlagReport(
            brf_name=metrics.brf_name,
            total_red_flags=len(red_flags),
            critical_count=severity_counts["critical"],
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
            red_flags=sorted(red_flags, key=lambda x: self._severity_sort_key(x.severity)),
            overall_risk_level=overall_risk,
            summary=summary,
            immediate_actions=immediate_actions
        )
        
        logger.info(f"Found {len(red_flags)} red flags for {metrics.brf_name}")
        return report
    
    def _check_financial_stability(self, metrics: BRFMetrics) -> List[RedFlag]:
        flags = []
        
        if metrics.operating_result is not None:
            if metrics.operating_result < self.severity_thresholds["negative_operating_result_critical"]:
                flags.append(RedFlag(
                    title="Kritiskt negativt rörelseresultat",
                    category=RedFlagCategory.FINANCIAL_STABILITY,
                    severity=RedFlagSeverity.CRITICAL,
                    description=f"Föreningens rörelseresultat är {metrics.operating_result:,.0f} kr, vilket innebär att intäkterna inte täcker de löpande driftskostnaderna.",
                    impact="Föreningen går med förlust i den dagliga driften och kan behöva höja avgifterna kraftigt eller ta ut extra uttaxering från medlemmarna.",
                    recommendation="Kräv detaljerad ekonomisk plan från styrelsen. Undersök orsaken till underskottet och om avgiftshöjningar planeras.",
                    evidence=f"Rörelseresultat: {metrics.operating_result:,.0f} kr",
                    metric_value=metrics.operating_result
                ))
            elif metrics.operating_result < self.severity_thresholds["negative_operating_result_high"]:
                flags.append(RedFlag(
                    title="Negativt rörelseresultat",
                    category=RedFlagCategory.FINANCIAL_STABILITY,
                    severity=RedFlagSeverity.HIGH,
                    description=f"Rörelseresultatet är negativt ({metrics.operating_result:,.0f} kr). Intäkterna täcker inte fullt ut de löpande kostnaderna.",
                    impact="Indikerar att föreningen kan ha för låga avgifter eller för höga driftskostnader.",
                    recommendation="Granska kostnadsutvecklingen och fråga om planerade avgiftshöjningar.",
                    evidence=f"Rörelseresultat: {metrics.operating_result:,.0f} kr",
                    metric_value=metrics.operating_result
                ))
        
        if metrics.annual_result is not None and metrics.annual_result < -1000000:
            flags.append(RedFlag(
                title="Stort negativt årsresultat",
                category=RedFlagCategory.FINANCIAL_STABILITY,
                severity=RedFlagSeverity.HIGH,
                description=f"Årets resultat är kraftigt negativt ({metrics.annual_result:,.0f} kr).",
                impact="Även om avskrivningar kan förklara negativt resultat, är detta belopp oroväckande stort.",
                recommendation="Begär förklaring från styrelsen. Kontrollera om det beror på extraordinära kostnader eller strukturella problem.",
                evidence=f"Årets resultat: {metrics.annual_result:,.0f} kr",
                metric_value=metrics.annual_result
            ))
        
        if metrics.solvency_ratio is not None:
            if metrics.solvency_ratio < self.severity_thresholds["solvency_critical"]:
                flags.append(RedFlag(
                    title="Kritiskt låg soliditet",
                    category=RedFlagCategory.FINANCIAL_STABILITY,
                    severity=RedFlagSeverity.CRITICAL,
                    description=f"Soliditeten är endast {metrics.solvency_ratio:.1f}%, vilket är mycket lågt.",
                    impact="Extremt hög skuldsättning innebär stor sårbarhet för ränteförändringar och begränsad ekonomisk buffert.",
                    recommendation="UNDVIK - Mycket hög ekonomisk risk. Föreningen kan ha svårt att hantera oförutsedda kostnader.",
                    evidence=f"Soliditet: {metrics.solvency_ratio:.1f}%",
                    metric_value=metrics.solvency_ratio
                ))
            elif metrics.solvency_ratio < self.severity_thresholds["solvency_high"]:
                flags.append(RedFlag(
                    title="Låg soliditet",
                    category=RedFlagCategory.FINANCIAL_STABILITY,
                    severity=RedFlagSeverity.HIGH,
                    description=f"Soliditeten är {metrics.solvency_ratio:.1f}%, vilket är under rekommenderad nivå (>20%).",
                    impact="Hög skuldsättning gör föreningen känslig för räntehöjningar och ekonomiska chocker.",
                    recommendation="Granska skuldsättningen noggrant. Kontrollera räntebindning och amorteringsplan.",
                    evidence=f"Soliditet: {metrics.solvency_ratio:.1f}%",
                    metric_value=metrics.solvency_ratio
                ))
            elif metrics.solvency_ratio < self.severity_thresholds["solvency_medium"]:
                flags.append(RedFlag(
                    title="Måttlig soliditet",
                    category=RedFlagCategory.FINANCIAL_STABILITY,
                    severity=RedFlagSeverity.MEDIUM,
                    description=f"Soliditeten är {metrics.solvency_ratio:.1f}%, vilket är något lågt.",
                    impact="Begränsad ekonomisk buffert mot oförutsedda kostnader.",
                    recommendation="Kontrollera trend över tid - förbättras eller försämras soliditeten?",
                    evidence=f"Soliditet: {metrics.solvency_ratio:.1f}%",
                    metric_value=metrics.solvency_ratio
                ))
        
        return flags
    
    def _check_debt_risk(self, metrics: BRFMetrics) -> List[RedFlag]:
        flags = []
        
        if metrics.interest_costs is not None and metrics.num_apartments:
            interest_per_apt = abs(metrics.interest_costs) / metrics.num_apartments
            
            if interest_per_apt > self.severity_thresholds["interest_per_apt_critical"]:
                flags.append(RedFlag(
                    title="Mycket hög räntebelastning",
                    category=RedFlagCategory.DEBT_RISK,
                    severity=RedFlagSeverity.CRITICAL,
                    description=f"Räntekostnaderna är {interest_per_apt:,.0f} kr per lägenhet och år ({abs(metrics.interest_costs):,.0f} kr totalt).",
                    impact="Extremt hög skuldsättning. Kraftiga avgiftshöjningar vid ränteuppgångar.",
                    recommendation="VARNING - Hög ränterisk. Kontrollera räntebindning och om föreningen kan hantera högre räntor.",
                    evidence=f"Räntekostnad per lägenhet: {interest_per_apt:,.0f} kr/år",
                    metric_value=interest_per_apt
                ))
            elif interest_per_apt > self.severity_thresholds["interest_per_apt_high"]:
                flags.append(RedFlag(
                    title="Hög räntebelastning",
                    category=RedFlagCategory.DEBT_RISK,
                    severity=RedFlagSeverity.HIGH,
                    description=f"Räntekostnaderna är {interest_per_apt:,.0f} kr per lägenhet och år.",
                    impact="Betydande skuldsättning som påverkar månadsavgiftens utveckling.",
                    recommendation="Granska föreningens skulder, räntebindning och känslighetsanalys för ränteförändringar.",
                    evidence=f"Räntekostnad per lägenhet: {interest_per_apt:,.0f} kr/år",
                    metric_value=interest_per_apt
                ))
            elif interest_per_apt > self.severity_thresholds["interest_per_apt_medium"]:
                flags.append(RedFlag(
                    title="Måttlig räntebelastning",
                    category=RedFlagCategory.DEBT_RISK,
                    severity=RedFlagSeverity.MEDIUM,
                    description=f"Räntekostnaderna är {interest_per_apt:,.0f} kr per lägenhet och år.",
                    impact="Viss räntekänslighet som kan påverka avgifterna vid ränteuppgång.",
                    recommendation="Kontrollera räntebindningstid och framtida ränterisk.",
                    evidence=f"Räntekostnad per lägenhet: {interest_per_apt:,.0f} kr/år",
                    metric_value=interest_per_apt
                ))
        
        if metrics.total_debt and metrics.equity and metrics.equity > 0:
            debt_to_equity = metrics.total_debt / metrics.equity
            
            if debt_to_equity > self.severity_thresholds["debt_to_equity_critical"]:
                flags.append(RedFlag(
                    title="Kritisk skuldsättningsgrad",
                    category=RedFlagCategory.DEBT_RISK,
                    severity=RedFlagSeverity.CRITICAL,
                    description=f"Skuldsättningsgraden är {debt_to_equity:.1f}x (skulder/eget kapital).",
                    impact="Extremt hög belåning innebär mycket begränsad ekonomisk flexibilitet.",
                    recommendation="UNDVIK - Ohållbart hög skuldsättning med stor ekonomisk risk.",
                    evidence=f"Skulder/Eget kapital: {debt_to_equity:.1f}x",
                    metric_value=debt_to_equity
                ))
            elif debt_to_equity > self.severity_thresholds["debt_to_equity_high"]:
                flags.append(RedFlag(
                    title="Hög skuldsättningsgrad",
                    category=RedFlagCategory.DEBT_RISK,
                    severity=RedFlagSeverity.HIGH,
                    description=f"Skuldsättningsgraden är {debt_to_equity:.1f}x.",
                    impact="Hög belåning begränsar föreningens ekonomiska handlingsutrymme.",
                    recommendation="Granska amorteringsplan och föreningens långsiktiga skuldstrategi.",
                    evidence=f"Skulder/Eget kapital: {debt_to_equity:.1f}x",
                    metric_value=debt_to_equity
                ))
        
        return flags
    
    def _check_liquidity(self, metrics: BRFMetrics) -> List[RedFlag]:
        flags = []
        
        if metrics.cash_flow is not None:
            if metrics.cash_flow < self.severity_thresholds["negative_cash_flow_critical"]:
                flags.append(RedFlag(
                    title="Kritiskt negativt kassaflöde",
                    category=RedFlagCategory.LIQUIDITY,
                    severity=RedFlagSeverity.CRITICAL,
                    description=f"Kassaflödet är {metrics.cash_flow:,.0f} kr, vilket betyder att kassan minskar kraftigt.",
                    impact="Föreningen förbrukar sina likvida medel snabbt och riskerar betalningssvårigheter.",
                    recommendation="VARNING - Kräv akut förklaring. Risk för extra uttaxering eller lånebehov.",
                    evidence=f"Kassaflöde: {metrics.cash_flow:,.0f} kr",
                    metric_value=metrics.cash_flow
                ))
            elif metrics.cash_flow < self.severity_thresholds["negative_cash_flow_high"]:
                flags.append(RedFlag(
                    title="Negativt kassaflöde",
                    category=RedFlagCategory.LIQUIDITY,
                    severity=RedFlagSeverity.HIGH,
                    description=f"Kassaflödet är negativt ({metrics.cash_flow:,.0f} kr).",
                    impact="Kassan minskar vilket kan leda till likviditetsproblem på sikt.",
                    recommendation="Granska orsaken till det negativa kassaflödet och föreningens likviditetsplan.",
                    evidence=f"Kassaflöde: {metrics.cash_flow:,.0f} kr",
                    metric_value=metrics.cash_flow
                ))
        
        if metrics.liquid_assets is not None and metrics.num_apartments:
            assets_per_apt = metrics.liquid_assets / metrics.num_apartments
            
            if assets_per_apt < self.severity_thresholds["reserves_per_apt_critical"]:
                flags.append(RedFlag(
                    title="Mycket låga likvida medel",
                    category=RedFlagCategory.LIQUIDITY,
                    severity=RedFlagSeverity.HIGH,
                    description=f"Föreningen har endast {assets_per_apt:,.0f} kr i likvida medel per lägenhet.",
                    impact="Mycket begränsad buffert för oförutsedda kostnader.",
                    recommendation="Risk för extra uttaxering vid akuta reparationer. Kontrollera föreningens beredskapsplan.",
                    evidence=f"Likvida medel per lägenhet: {assets_per_apt:,.0f} kr",
                    metric_value=assets_per_apt
                ))
            elif assets_per_apt < self.severity_thresholds["reserves_per_apt_low"]:
                flags.append(RedFlag(
                    title="Låga likvida medel",
                    category=RedFlagCategory.LIQUIDITY,
                    severity=RedFlagSeverity.MEDIUM,
                    description=f"Likvida medel är {assets_per_apt:,.0f} kr per lägenhet.",
                    impact="Begränsad buffert för oväntade utgifter.",
                    recommendation="Kontrollera om föreningen har kreditmöjligheter eller planerar att bygga upp kassan.",
                    evidence=f"Likvida medel per lägenhet: {assets_per_apt:,.0f} kr",
                    metric_value=assets_per_apt
                ))
        
        return flags
    
    def _check_maintenance(self, metrics: BRFMetrics) -> List[RedFlag]:
        flags = []
        
        if metrics.building_year:
            building_age = 2024 - metrics.building_year
            
            if building_age > self.severity_thresholds["building_age_very_old"]:
                flags.append(RedFlag(
                    title="Mycket gammal fastighet",
                    category=RedFlagCategory.MAINTENANCE,
                    severity=RedFlagSeverity.HIGH,
                    description=f"Fastigheten är byggd {metrics.building_year} ({building_age} år gammal).",
                    impact="Äldre fastigheter kräver omfattande underhåll. Risk för stora renoveringskostnader.",
                    recommendation="Granska underhållsplan och genomförda renoveringar. Kontrollera skick på tak, fasad, stammar och el.",
                    evidence=f"Byggår: {metrics.building_year} ({building_age} år)",
                    metric_value=building_age
                ))
            elif building_age > self.severity_thresholds["building_age_old"]:
                flags.append(RedFlag(
                    title="Äldre fastighet med underhållsbehov",
                    category=RedFlagCategory.MAINTENANCE,
                    severity=RedFlagSeverity.MEDIUM,
                    description=f"Fastigheten är från {metrics.building_year} ({building_age} år).",
                    impact="Ålder innebär ökande underhållsbehov och potentiella renoveringskostnader.",
                    recommendation="Kontrollera genomförda renoveringar och planerat underhåll de närmaste åren.",
                    evidence=f"Byggår: {metrics.building_year} ({building_age} år)",
                    metric_value=building_age
                ))
            
            if building_age > self.severity_thresholds["building_age_old"]:
                if metrics.maintenance_reserves is not None and metrics.num_apartments:
                    reserves_per_apt = metrics.maintenance_reserves / metrics.num_apartments
                    
                    if reserves_per_apt < 50000:
                        flags.append(RedFlag(
                            title="Otillräckliga underhållsreserver för gammal fastighet",
                            category=RedFlagCategory.MAINTENANCE,
                            severity=RedFlagSeverity.HIGH,
                            description=f"Fastigheten är {building_age} år gammal men har endast {reserves_per_apt:,.0f} kr i underhållsreserver per lägenhet.",
                            impact="Risk för att föreningen inte kan finansiera nödvändiga renoveringar utan extra uttaxering.",
                            recommendation="VARNING - Kombination av hög ålder och låga reserver är mycket riskabelt. Kräv detaljerad underhållsplan.",
                            evidence=f"Underhållsreserver: {reserves_per_apt:,.0f} kr/lägenhet, Ålder: {building_age} år",
                            metric_value=reserves_per_apt
                        ))
        
        if metrics.maintenance_reserves is not None and metrics.num_apartments:
            reserves_per_apt = metrics.maintenance_reserves / metrics.num_apartments
            
            if reserves_per_apt < 20000:
                flags.append(RedFlag(
                    title="Låga underhållsreserver",
                    category=RedFlagCategory.MAINTENANCE,
                    severity=RedFlagSeverity.MEDIUM,
                    description=f"Underhållsreserverna är {reserves_per_apt:,.0f} kr per lägenhet.",
                    impact="Begränsad förmåga att finansiera framtida underhåll och renoveringar.",
                    recommendation="Kontrollera om föreningen planerar att bygga upp reserverna eller om stora projekt nyligen genomförts.",
                    evidence=f"Underhållsreserver: {reserves_per_apt:,.0f} kr/lägenhet",
                    metric_value=reserves_per_apt
                ))
        
        return flags
    
    def _check_operational_issues(self, metrics: BRFMetrics) -> List[RedFlag]:
        flags = []
        
        if metrics.annual_fee_per_sqm is not None:
            # Convert annual to monthly for comparison
            monthly_equivalent = metrics.annual_fee_per_sqm / 12
            if monthly_equivalent > self.severity_thresholds["monthly_fee_high"]:
                flags.append(RedFlag(
                    title="Mycket hög månadsavgift",
                    category=RedFlagCategory.OPERATIONAL,
                    severity=RedFlagSeverity.MEDIUM,
                    description=f"Månadsavgiften är {monthly_equivalent:.0f} kr/kvm (årsavgift: {metrics.annual_fee_per_sqm:.0f} kr/kvm), vilket är högt jämfört med marknaden.",
                    impact="Höga löpande kostnader påverkar din ekonomi och kan göra lägenheten svårsåld.",
                    recommendation="Jämför med liknande föreningar. Kontrollera vad som ingår i avgiften och varför den är hög.",
                    evidence=f"Årsavgift: {metrics.annual_fee_per_sqm:.0f} kr/kvm ({monthly_equivalent:.0f} kr/kvm/månad)",
                    metric_value=metrics.annual_fee_per_sqm
                ))
            elif monthly_equivalent > self.severity_thresholds["monthly_fee_medium"]:
                flags.append(RedFlag(
                    title="Hög månadsavgift",
                    category=RedFlagCategory.OPERATIONAL,
                    severity=RedFlagSeverity.LOW,
                    description=f"Månadsavgiften är {monthly_equivalent:.0f} kr/kvm (årsavgift: {metrics.annual_fee_per_sqm:.0f} kr/kvm).",
                    impact="Något högre än genomsnittet.",
                    recommendation="Kontrollera vad som ingår och jämför med alternativ.",
                    evidence=f"Årsavgift: {metrics.annual_fee_per_sqm:.0f} kr/kvm ({monthly_equivalent:.0f} kr/kvm/månad)",
                    metric_value=metrics.annual_fee_per_sqm
                ))
        
        return flags
    
    def _check_governance_issues(self, brf_name: str) -> List[RedFlag]:
        flags = []
        
        if not self.query_interface:
            return flags
        
        try:
            result = self.query_interface.query(
                question="Finns det några anmärkningar från revisorn eller avvikelser i revisionsberättelsen?",
                brf_name=brf_name,
                include_sources=False
            )
            
            answer = result.get("answer", "").lower()
            if any(word in answer for word in ["ja", "anmärkning", "avvikelse", "kritik", "problem"]):
                flags.append(RedFlag(
                    title="Revisoranmärkningar",
                    category=RedFlagCategory.GOVERNANCE,
                    severity=RedFlagSeverity.HIGH,
                    description="Revisorn har gjort anmärkningar i revisionsberättelsen.",
                    impact="Kan indikera brister i förvaltningen eller ekonomiska problem.",
                    recommendation="Läs revisionsberättelsen noggrant och kräv förklaring från styrelsen.",
                    evidence=result.get("answer", "")
                ))
        except Exception as e:
            logger.warning(f"Failed to check governance issues: {e}")
        
        return flags
    
    def _check_legal_issues(self, brf_name: str) -> List[RedFlag]:
        flags = []
        
        if not self.query_interface:
            return flags
        
        try:
            result = self.query_interface.query(
                question="Finns det några pågående tvister, rättsliga processer, försäkringsärenden eller myndighetskrav?",
                brf_name=brf_name,
                include_sources=False
            )
            
            answer = result.get("answer", "").lower()
            if any(word in answer for word in ["ja", "tvist", "rättegång", "process", "krav", "försäkring"]):
                flags.append(RedFlag(
                    title="Pågående juridiska ärenden",
                    category=RedFlagCategory.LEGAL,
                    severity=RedFlagSeverity.HIGH,
                    description="Det finns pågående tvister eller juridiska processer.",
                    impact="Kan leda till oförutsedda kostnader och komplicera föreningens förvaltning.",
                    recommendation="Begär detaljerad information om ärendets art, status och potentiella kostnader.",
                    evidence=result.get("answer", "")
                ))
        except Exception as e:
            logger.warning(f"Failed to check legal issues: {e}")
        
        try:
            result = self.query_interface.query(
                question="Har föreningen tidigare behövt ta ut extra avgifter eller uttaxering från medlemmarna?",
                brf_name=brf_name,
                include_sources=False
            )
            
            answer = result.get("answer", "").lower()
            if any(word in answer for word in ["ja", "uttaxering", "extra avgift", "medlemslån"]):
                flags.append(RedFlag(
                    title="Tidigare uttaxeringar",
                    category=RedFlagCategory.GOVERNANCE,
                    severity=RedFlagSeverity.MEDIUM,
                    description="Föreningen har tidigare tagit ut extra avgifter från medlemmarna.",
                    impact="Indikerar bristfällig ekonomisk planering eller oförutsedda problem.",
                    recommendation="Granska orsakerna och om liknande situation kan uppstå igen.",
                    evidence=result.get("answer", "")
                ))
        except Exception as e:
            logger.warning(f"Failed to check previous special assessments: {e}")
        
        return flags
    
    def _calculate_overall_risk(self, severity_counts: Dict[str, int]) -> str:
        critical = severity_counts["critical"]
        high = severity_counts["high"]
        medium = severity_counts["medium"]
        
        if critical >= 2:
            return "KRITISK"
        elif critical >= 1 or high >= 3:
            return "HÖG"
        elif high >= 1 or medium >= 3:
            return "MÅTTLIG"
        elif medium >= 1:
            return "LÅG"
        else:
            return "MINIMAL"
    
    def _generate_summary(self, brf_name: str, severity_counts: Dict[str, int], risk_level: str) -> str:
        total = sum(severity_counts.values())
        
        if total == 0:
            return f"✅ **Inga allvarliga varningssignaler hittades för {brf_name}**. Grundläggande ekonomiska nyckeltal ser bra ut."
        
        parts = [f"⚠️ **{total} varningssignal{'er' if total > 1 else ''} identifierad{'e' if total > 1 else ''} för {brf_name}**"]
        parts.append(f"**Övergripande risknivå: {risk_level}**")
        
        details = []
        if severity_counts["critical"] > 0:
            details.append(f"🔴 {severity_counts['critical']} kritisk{'a' if severity_counts['critical'] > 1 else ''}")
        if severity_counts["high"] > 0:
            details.append(f"🟠 {severity_counts['high']} hög")
        if severity_counts["medium"] > 0:
            details.append(f"🟡 {severity_counts['medium']} måttlig")
        if severity_counts["low"] > 0:
            details.append(f"🟢 {severity_counts['low']} låg")
        
        if details:
            parts.append(", ".join(details))
        
        return "\n".join(parts)
    
    def _generate_immediate_actions(self, red_flags: List[RedFlag]) -> List[str]:
        actions = []
        
        critical_flags = [rf for rf in red_flags if rf.severity == RedFlagSeverity.CRITICAL]
        high_flags = [rf for rf in red_flags if rf.severity == RedFlagSeverity.HIGH]
        
        if critical_flags:
            actions.append("🚨 KRITISKT: Undvik detta köp utan djupgående ekonomisk analys från expert")
        
        if any(rf.category == RedFlagCategory.FINANCIAL_STABILITY for rf in critical_flags + high_flags):
            actions.append("📊 Begär in årsredovisningar för minst 5 år bakåt för att se trender")
        
        if any(rf.category == RedFlagCategory.DEBT_RISK for rf in critical_flags + high_flags):
            actions.append("💰 Begär information om räntebindning, amorteringsplan och känslighetsanalys")
        
        if any(rf.category == RedFlagCategory.LIQUIDITY for rf in critical_flags + high_flags):
            actions.append("💧 Kontrollera föreningens likviditetsplan och beredskap för oförutsedda kostnader")
        
        if any(rf.category == RedFlagCategory.MAINTENANCE for rf in critical_flags + high_flags):
            actions.append("🔧 Begär underhållsplan och teknisk besiktningsrapport")
        
        if any(rf.category == RedFlagCategory.GOVERNANCE for rf in red_flags):
            actions.append("📋 Läs senaste årsstämmoprotokoll och revisionsberättelse noggrant")
        
        if any(rf.category == RedFlagCategory.LEGAL for rf in red_flags):
            actions.append("⚖️ Begär fullständig information om pågående tvister och juridiska ärenden")
        
        if not actions:
            actions.append("✅ Fortsätt med normal due diligence process")
        
        return actions
    
    def _severity_sort_key(self, severity: RedFlagSeverity) -> int:
        order = {
            RedFlagSeverity.CRITICAL: 0,
            RedFlagSeverity.HIGH: 1,
            RedFlagSeverity.MEDIUM: 2,
            RedFlagSeverity.LOW: 3,
        }
        return order.get(severity, 999)
