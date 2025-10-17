import logging
from typing import Dict, Optional, Any
from brf_helper.llm.rag_interface import BRFQueryInterface
from brf_helper.database.db import BRFDatabase

logger = logging.getLogger(__name__)


class BRFMetricsExtractor:
    """
    Extracts RAW financial metrics from BRF reports using LLM queries.
    Does NOT compute analysis - only extracts numbers and text.
    """
    
    def __init__(self, query_interface: BRFQueryInterface):
        self.query_interface = query_interface
        
        # Queries to extract RAW metrics (no analysis/interpretation)
        # IMPORTANT: Strict prompts to avoid extracting wrong values (e.g. report year instead of building year)
        self.metric_queries = {
            # Income statement
            "annual_result": "Vad är årets resultat enligt resultaträkningen? Ange ENDAST siffran i kronor från den senaste räkenskapsperioden. Om du inte hittar det exakta värdet, svara 'OKÄNT'.",
            "operating_result": "Vad är rörelseresultatet enligt resultaträkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            "total_income": "Vad är de totala intäkterna enligt resultaträkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            "total_expenses": "Vad är de totala kostnaderna enligt resultaträkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Costs breakdown
            "interest_costs": "Hur mycket betalar föreningen i räntekostnader per år enligt resultaträkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            "maintenance_costs": "Vad är underhållskostnaderna enligt resultaträkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            "operation_costs": "Vad är driftskostnaderna enligt resultaträkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Cash flow
            "cash_flow": "Vad är föreningens kassaflöde för året enligt kassaflödesanalysen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Assets
            "liquid_assets": "Hur mycket likvida medel (kassa och bank) har föreningen enligt balansräkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            "total_assets": "Vad är föreningens totala tillgångar enligt balansräkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Liabilities
            "total_debt": "Vad är föreningens totala skulder enligt balansräkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            "long_term_debt": "Vad är de långfristiga skulderna enligt balansräkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Equity
            "equity": "Vad är föreningens egna kapital enligt balansräkningen? Ange ENDAST beloppet i kronor. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Ratios (if stated in report)
            "solvency_ratio": "Vad är föreningens soliditet i procent? Ange ENDAST siffran om den uttryckligen anges i rapporten. Beräkna INTE och gissa INTE. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Per-apartment metrics
            "annual_fee_per_sqm": "Vad är den genomsnittliga årsavgiften per kvadratmeter i kronor? Leta efter 'avgift per kvm' eller liknande. Ange ENDAST siffran om den uttryckligen anges. Beräkna INTE och gissa INTE. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Reserves
            "maintenance_reserves": "Hur mycket har föreningen avsatt för underhåll och renoveringar (underhållsfond eller renoveringsfond)? Ange ENDAST beloppet i kronor om det finns en specifik fond. Om du inte hittar det, svara 'OKÄNT'.",
            
            # Building info - be very specific to avoid confusing with report year
            "building_info": "Vilket år byggdes/färdigställdes fastigheten ursprungligen (INTE rapportåret, utan när byggnaden konstruerades)? Hur många lägenheter/bostadsrätter finns det? Vad är den totala bostadsarean i kvadratmeter? Om någon information saknas, skriv 'OKÄNT' för den delen.",
        }
        
        # Queries for boolean/text extracts
        self.extract_queries = {
            "has_auditor_remarks": "Finns det några anmärkningar från revisorn i revisionsberättelsen? Svara endast JA eller NEJ.",
            "has_ongoing_disputes": "Finns det några pågående tvister, rättsliga processer eller försäkringsärenden? Svara endast JA eller NEJ.",
            "has_previous_assessments": "Har föreningen tidigare behövt ta ut extra avgifter eller uttaxering från medlemmarna? Svara endast JA eller NEJ.",
            "major_renovations_planned": "Vilka större renoveringar eller underhållsprojekt är planerade de närmaste 5-10 åren?",
            "auditor_report": "Vad står det i revisorns berättelse? Citerar gärna relevanta delar.",
        }
    
    def extract_and_store(self, brf_name: str, database: BRFDatabase) -> bool:
        """Extract all metrics and store them in database"""
        logger.info(f"Starting metrics extraction for {brf_name}")
        
        try:
            # Get BRF from database
            brf = database.get_brf_by_name(brf_name)
            if not brf:
                logger.error(f"BRF {brf_name} not found in database")
                return False
            
            # Extract financial metrics
            logger.info(f"Extracting financial metrics...")
            metrics = self._extract_financial_metrics(brf_name)
            
            # Extract building info and add to BRF table
            building_info = self._extract_building_info(brf_name)
            if building_info:
                database.create_or_update_brf(brf_name, **building_info)
            
            # Save financial metrics
            database.save_financial_metrics(brf.id, metrics)
            
            # Extract report text/booleans
            logger.info(f"Extracting report extracts...")
            extracts = self._extract_report_data(brf_name)
            
            # Save report extracts
            database.save_report_extracts(brf.id, extracts)
            
            logger.info(f"✓ Metrics extraction complete for {brf_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract metrics for {brf_name}: {e}", exc_info=True)
            return False
    
    def _extract_financial_metrics(self, brf_name: str) -> Dict[str, Any]:
        """Extract all financial metrics"""
        metrics = {}
        
        for metric_key, query in self.metric_queries.items():
            if metric_key == "building_info":
                continue  # Handled separately
                
            try:
                logger.debug(f"Extracting {metric_key}...")
                
                result = self.query_interface.query(
                    question=query,
                    brf_name=brf_name,
                    include_sources=False
                )
                
                answer = result.get("answer", "")
                value = self._extract_numeric_value(answer)
                metrics[metric_key] = value
                
                if value is not None:
                    logger.debug(f"  {metric_key}: {value}")
                
            except Exception as e:
                logger.warning(f"Failed to extract {metric_key}: {e}")
                metrics[metric_key] = None
        
        return metrics
    
    def _extract_building_info(self, brf_name: str) -> Dict[str, Any]:
        """Extract building information (year, apartments, area)"""
        try:
            result = self.query_interface.query(
                question=self.metric_queries["building_info"],
                brf_name=brf_name,
                include_sources=False
            )
            
            answer = result.get("answer", "")
            return self._parse_building_info(answer)
            
        except Exception as e:
            logger.warning(f"Failed to extract building info: {e}")
            return {}
    
    def _extract_report_data(self, brf_name: str) -> Dict[str, Any]:
        """Extract text sections and boolean flags"""
        extracts = {}
        
        for key, query in self.extract_queries.items():
            try:
                logger.debug(f"Extracting {key}...")
                
                result = self.query_interface.query(
                    question=query,
                    brf_name=brf_name,
                    include_sources=False
                )
                
                answer = result.get("answer", "")
                
                # Parse based on type
                if key.startswith("has_"):
                    # Boolean field
                    value = self._parse_boolean(answer)
                else:
                    # Text field
                    value = answer if answer else None
                
                extracts[key] = value
                
            except Exception as e:
                logger.warning(f"Failed to extract {key}: {e}")
                extracts[key] = None
        
        return extracts
    
    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text response"""
        if not text:
            return None
        
        import re
        
        # Check if model explicitly said it doesn't know
        text_lower = text.lower().strip()
        if text_lower in ['okänt', 'vet ej', 'uppgift saknas', 'finns inte', 'ej angiven', 'unknown']:
            return None
        
        # Remove common Swedish currency and formatting
        text = text.replace(" kr", "").replace(" kronor", "").replace(" SEK", "")
        text = text.replace(" ", "").replace(",", ".")
        
        # Look for numbers (including negative)
        patterns = [
            r'-?\d+\.?\d*',
            r'-?\d{1,3}(?:\.\d{3})*(?:,\d{2})?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    value = float(matches[0].replace(",", "."))
                    # Sanity check: if value looks like a year (1900-2100), it's probably wrong
                    if 1900 <= value <= 2100:
                        logger.warning(f"Suspicious value that looks like a year: {value}. Returning None.")
                        return None
                    return value
                except ValueError:
                    continue
        
        return None
    
    def _parse_building_info(self, text: str) -> Dict[str, Any]:
        """Parse building information from text"""
        import re
        
        info = {}
        
        if not text:
            return info
        
        # Extract building year
        year_match = re.search(r'19\d{2}|20\d{2}', text)
        if year_match:
            info['building_year'] = int(year_match.group())
        
        # Extract number of apartments
        apt_patterns = [
            r'(\d+)\s*(?:lägenheter|lägenhet)',
            r'(\d+)\s*(?:apartements|apt)',
        ]
        for pattern in apt_patterns:
            match = re.search(pattern, text.lower())
            if match:
                info['num_apartments'] = int(match.group(1))
                break
        
        # Extract total area
        area_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:kvm|m2|kvadratmeter)',
            r'(\d+(?:[.,]\d+)?)\s*(?:sqm|square)',
        ]
        for pattern in area_patterns:
            match = re.search(pattern, text.lower().replace(" ", ""))
            if match:
                info['total_area'] = float(match.group(1).replace(",", "."))
                break
        
        return info
    
    def _parse_boolean(self, text: str) -> Optional[bool]:
        """Parse boolean from text answer"""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        # Check for explicit yes/no
        if text_lower.startswith("ja"):
            return True
        if text_lower.startswith("nej"):
            return False
        
        # Check for keywords
        positive_keywords = ["ja", "finns", "har", "tidigare", "pågående"]
        negative_keywords = ["nej", "inte", "inga", "aldrig"]
        
        if any(word in text_lower for word in positive_keywords):
            return True
        if any(word in text_lower for word in negative_keywords):
            return False
        
        return None
