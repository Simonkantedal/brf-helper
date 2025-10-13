from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class QuestionCategory(Enum):
    FINANCIAL_STABILITY = "financial_stability"
    COST_ANALYSIS = "cost_analysis" 
    RISK_ASSESSMENT = "risk_assessment"
    MAINTENANCE_OVERVIEW = "maintenance_overview"
    GOVERNANCE = "governance"


@dataclass
class QuestionTemplate:
    """A single question template with context and priority"""
    question: str
    context: str  # Why this question matters
    priority: int  # 1 = highest priority, 5 = lowest
    expected_answer_type: str  # "numeric", "text", "boolean"


@dataclass
class QuestionPackage:
    """A collection of related questions for a specific analysis area"""
    name: str
    description: str
    category: QuestionCategory
    icon: str
    questions: List[QuestionTemplate]
    estimated_time: str  # e.g., "2-3 minuter"


class BRFQuestionTemplates:
    """Pre-built question packages for comprehensive BRF analysis"""
    
    def __init__(self):
        self.packages = self._create_question_packages()
    
    def get_package(self, category: QuestionCategory) -> Optional[QuestionPackage]:
        """Get a specific question package by category"""
        return self.packages.get(category)
    
    def get_all_packages(self) -> Dict[QuestionCategory, QuestionPackage]:
        """Get all available question packages"""
        return self.packages
    
    def get_essential_questions(self) -> List[QuestionTemplate]:
        """Get the most essential questions across all categories (priority 1-2)"""
        essential = []
        for package in self.packages.values():
            essential.extend([q for q in package.questions if q.priority <= 2])
        return essential
    
    def _create_question_packages(self) -> Dict[QuestionCategory, QuestionPackage]:
        """Create all pre-built question packages"""
        
        packages = {}
        
        # Financial Stability Package
        packages[QuestionCategory.FINANCIAL_STABILITY] = QuestionPackage(
            name="Ekonomisk Stabilitet",
            description="Grundläggande analys av föreningens ekonomiska hälsa och stabilitet",
            category=QuestionCategory.FINANCIAL_STABILITY,
            icon="💰",
            estimated_time="3-4 minuter",
            questions=[
                QuestionTemplate(
                    question="Vad är årets resultat för föreningen? Är det positivt eller negativt och vad beror det på?",
                    context="Årets resultat visar om föreningen går med vinst eller förlust. Ett negativt resultat är inte alltid farligt om det beror på avskrivningar.",
                    priority=1,
                    expected_answer_type="numeric"
                ),
                QuestionTemplate(
                    question="Vad är rörelseresultatet? Täcker intäkterna de löpande driftskostnaderna?",
                    context="Rörelseresultatet visar om föreningen kan täcka sina löpande kostnader med avgifterna. Ett negativt rörelseresultat är en varningssignal.",
                    priority=1,
                    expected_answer_type="numeric"
                ),
                QuestionTemplate(
                    question="Hur har föreningens ekonomiska resultat utvecklats de senaste 3-5 åren? Finns det en trend?",
                    context="Trender över tid är viktigare än enstaka års resultat. Visar om föreningen förbättras eller försämras ekonomiskt.",
                    priority=2,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Vad är föreningens soliditet (skuldsättningsgrad)? Hur har den utvecklats över tid?",
                    context="Soliditet över 20% anses bra, under 10% kan vara riskabelt. Visar föreningens finansiella stabilitet.",
                    priority=2,
                    expected_answer_type="numeric"
                ),
                QuestionTemplate(
                    question="Vad är föreningens kassaflöde? Ökar eller minskar kassan över tid?",
                    context="Kassaflödet visar den faktiska förändringen av pengar, vilket är viktigt för framtida betalningsförmåga.",
                    priority=2,
                    expected_answer_type="numeric"
                ),
                QuestionTemplate(
                    question="Hur mycket likvida medel (kassa och bank) har föreningen? Motsvarar det några månaders driftskostnader?",
                    context="Likvida medel ger trygghet för oförutsedda kostnader och visar betalningsförmågan på kort sikt.",
                    priority=3,
                    expected_answer_type="numeric"
                )
            ]
        )
        
        # Cost Analysis Package  
        packages[QuestionCategory.COST_ANALYSIS] = QuestionPackage(
            name="Kostnadsanalys",
            description="Analys av månadsavgifter, kostnadsutveckling och framtida ekonomiska åtaganden",
            category=QuestionCategory.COST_ANALYSIS,
            icon="📊",
            estimated_time="2-3 minuter",
            questions=[
                QuestionTemplate(
                    question="Vad är den aktuella månadsavgiften per kvadratmeter? Hur jämförs detta med liknande föreningar?",
                    context="Månadsavgiften är din största löpande kostnad. Jämför med marknaden för att bedöma om det är rimligt.",
                    priority=1,
                    expected_answer_type="numeric"
                ),
                QuestionTemplate(
                    question="Hur har månadsavgifterna utvecklats de senaste 5 åren? Vilken genomsnittlig ökning per år?",
                    context="Avgiftsutvecklingen visar kostnadstrenden och hjälper förutsäga framtida kostnader.",
                    priority=1,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Finns det planerade avgiftshöjningar de närmaste åren? Vad beror de på?",
                    context="Kända framtida höjningar påverkar din ekonomiska planering och bör faktoras in.",
                    priority=2,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Vad är föreningens största kostnadsposter? Vilka kostnader ökar mest?",
                    context="Förståelse för kostnadsdrivarna hjälper bedöma framtida utveckling och kontrollmöjligheter.",
                    priority=3,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Har föreningen gjort några större investeringar eller kostnadsbesparingar de senaste åren?",
                    context="Visar föreningens förmåga att hantera stora projekt och optimera kostnader.",
                    priority=3,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Vad ingår i månadsavgiften? Finns det extra avgifter för parkering, förråd eller andra tjänster?",
                    context="Viktigt för att förstå den totala kostnadsbilden och jämföra rättvist med andra alternativ.",
                    priority=2,
                    expected_answer_type="text"
                )
            ]
        )
        
        # Risk Assessment Package
        packages[QuestionCategory.RISK_ASSESSMENT] = QuestionPackage(
            name="Riskbedömning", 
            description="Identifiering av potentiella risker och varningssignaler",
            category=QuestionCategory.RISK_ASSESSMENT,
            icon="⚠️",
            estimated_time="3-4 minuter",
            questions=[
                QuestionTemplate(
                    question="Finns det några större renoveringsprojekt planerade de närmaste 5-10 åren? Vad kommer de att kosta?",
                    context="Stora renoveringar kan leda till betydande avgiftshöjningar eller extra uttaxering av medlemmarna.",
                    priority=1,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Vilka är föreningens skulder och vad är räntekostnaderna? Hur påverkar ränteförändringar ekonomin?",
                    context="Hög skuldsättning gör föreningen sårbar för räntehöjningar. Viktigt att förstå ränterisken.",
                    priority=1,
                    expected_answer_type="numeric"
                ),
                QuestionTemplate(
                    question="Finns det pågående eller hotande tvister, försäkringsärenden eller myndighetskrav?",
                    context="Juridiska problem kan medföra oförutsedda kostnader och komplicera framtida beslut.",
                    priority=2,
                    expected_answer_type="boolean"
                ),
                QuestionTemplate(
                    question="Hur är byggnadskonditionen? Finns det kända problem med tak, fasad, stammar eller andra viktiga byggnadsdelar?",
                    context="Dåligt skick kan innebära oförutsedda reparationskostnader och avgiftshöjningar.",
                    priority=2,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Har föreningen någon gång behövt ta ut extra avgifter eller uttaxering från medlemmarna?",
                    context="Historiska uttaxeringar kan indikera bristfällig ekonomisk planering eller oförutsedda problem.",
                    priority=2,
                    expected_answer_type="boolean"
                ),
                QuestionTemplate(
                    question="Finns det några större avvikelser i revisorsberättelsen eller anmärkningar från revisorn?",
                    context="Revisorns anmärkningar kan avslöja ekonomiska problem eller brister i förvaltningen.",
                    priority=3,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Hur fungerar styrelsearbetet? Finns det kontinuitet eller höga omsättning bland styrelsemedlemmar?",
                    context="Stabil styrelsestyrning är viktigt för kontinuitet i ekonomisk förvaltning och strategiska beslut.",
                    priority=3,
                    expected_answer_type="text"
                )
            ]
        )
        
        # Maintenance Overview Package
        packages[QuestionCategory.MAINTENANCE_OVERVIEW] = QuestionPackage(
            name="Underhållsöversikt",
            description="Analys av underhållsplanering och framtida renoveringsbehov",
            category=QuestionCategory.MAINTENANCE_OVERVIEW, 
            icon="🔧",
            estimated_time="2-3 minuter",
            questions=[
                QuestionTemplate(
                    question="Finns det en underhållsplan för fastigheten? Vilka större projekt är planerade och när?",
                    context="En välplanerad underhållsplan visar professionell förvaltning och hjälper förutsäga framtida kostnader.",
                    priority=1,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Hur mycket pengar har föreningen avsatt för underhåll och renoveringar? Är det tillräckligt?",
                    context="Underhållsfonden bör vara proportionell mot fastighetens ålder och kommande behov.",
                    priority=1,
                    expected_answer_type="numeric"
                ),
                QuestionTemplate(
                    question="Vilka större renoveringar har gjorts de senaste 10 åren? Vad kostade de?",
                    context="Nyligen genomförda renoveringar minskar risken för närvarande behov men kan påverka ekonomin.",
                    priority=2,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Vilket år byggdes fastigheten och vad är det allmänna skicket?",
                    context="Fastighetens ålder och skick avgör hur snart stora underhållsinsatser kan behövas.",
                    priority=2,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Finns det energieffektiviseringsplaner? Kommer det påverka avgifterna?",
                    context="Energirenovering kan minska driftskostnader långsiktigt men kräver initial investering.",
                    priority=3,
                    expected_answer_type="text"
                )
            ]
        )
        
        # Governance Package
        packages[QuestionCategory.GOVERNANCE] = QuestionPackage(
            name="Förvaltning & Styrning",
            description="Analys av föreningens styrning, beslutprocesser och medlemsengagemang",
            category=QuestionCategory.GOVERNANCE,
            icon="🏛️", 
            estimated_time="2 minuter",
            questions=[
                QuestionTemplate(
                    question="Hur fungerar årsstämman? Är det bra uppslutning och aktiva diskussioner bland medlemmarna?",
                    context="Aktiva medlemmar och bra stämmoprotokoll indikerar en välskött förening med engagerade ägare.",
                    priority=2,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Vem är förvaltare och hur länge har de varit anlitade? Är medlemmarna nöjda?",
                    context="En erfaren och kompetent förvaltare är avgörande för en välskött förening.",
                    priority=3,
                    expected_answer_type="text"
                ),
                QuestionTemplate(
                    question="Finns det några pågående konflikter eller dispyter inom föreningen?",
                    context="Interna konflikter kan påverka beslutfattandet och göra det svårt att driva viktiga frågor framåt.",
                    priority=3,
                    expected_answer_type="boolean"
                ),
                QuestionTemplate(
                    question="Vilka försäkringar har föreningen och är täckningen tillräcklig?",
                    context="Adekvat försäkringsskydd skyddar mot oförutsedda kostnader från skador eller tvister.",
                    priority=3,
                    expected_answer_type="text"
                )
            ]
        )
        
        return packages


def get_quick_assessment_questions() -> List[QuestionTemplate]:
    """Get a curated list of the most critical questions for a quick assessment"""
    templates = BRFQuestionTemplates()
    
    # Select the top priority questions from key categories
    essential_questions = [
        # Financial core
        templates.packages[QuestionCategory.FINANCIAL_STABILITY].questions[0],  # Annual result
        templates.packages[QuestionCategory.FINANCIAL_STABILITY].questions[1],  # Operating result
        
        # Cost essentials  
        templates.packages[QuestionCategory.COST_ANALYSIS].questions[0],  # Monthly fee
        templates.packages[QuestionCategory.COST_ANALYSIS].questions[1],  # Fee development
        
        # Major risks
        templates.packages[QuestionCategory.RISK_ASSESSMENT].questions[0],  # Planned renovations
        templates.packages[QuestionCategory.RISK_ASSESSMENT].questions[1],  # Debt and interest
        
        # Maintenance planning
        templates.packages[QuestionCategory.MAINTENANCE_OVERVIEW].questions[0],  # Maintenance plan
        templates.packages[QuestionCategory.MAINTENANCE_OVERVIEW].questions[1],  # Maintenance reserves
    ]
    
    return essential_questions