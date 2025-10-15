import logging
from brf_helper.analysis.red_flag_detector import RedFlagDetector
from brf_helper.analysis.brf_analyzer import BRFMetrics

logging.basicConfig(level=logging.INFO)


def test_red_flag_detection():
    
    print("\n" + "="*80)
    print("Testing Red Flag Detection System")
    print("="*80 + "\n")
    
    detector = RedFlagDetector()
    
    print("\n--- Test Case 1: Healthy BRF ---")
    healthy_metrics = BRFMetrics(
        brf_name="Healthy BRF Test",
        annual_result=500000,
        operating_result=300000,
        interest_costs=-200000,
        cash_flow=150000,
        liquid_assets=2000000,
        monthly_fee_per_sqm=45,
        total_debt=10000000,
        equity=8000000,
        solvency_ratio=44,
        maintenance_reserves=3000000,
        num_apartments=50,
        building_year=2005,
        total_area=3500
    )
    
    report = detector.detect_red_flags(healthy_metrics)
    print_report(report)
    
    print("\n--- Test Case 2: BRF with Financial Problems ---")
    problematic_metrics = BRFMetrics(
        brf_name="Problematic BRF Test",
        annual_result=-800000,
        operating_result=-300000,
        interest_costs=-1500000,
        cash_flow=-400000,
        liquid_assets=400000,
        monthly_fee_per_sqm=75,
        total_debt=30000000,
        equity=5000000,
        solvency_ratio=8,
        maintenance_reserves=500000,
        num_apartments=40,
        building_year=1920,
        total_area=2800
    )
    
    report = detector.detect_red_flags(problematic_metrics)
    print_report(report)
    
    print("\n--- Test Case 3: Old Building with Low Reserves ---")
    old_building_metrics = BRFMetrics(
        brf_name="Old Building Test",
        annual_result=100000,
        operating_result=50000,
        interest_costs=-300000,
        cash_flow=20000,
        liquid_assets=800000,
        monthly_fee_per_sqm=52,
        total_debt=8000000,
        equity=4000000,
        solvency_ratio=18,
        maintenance_reserves=600000,
        num_apartments=30,
        building_year=1935,
        total_area=2100
    )
    
    report = detector.detect_red_flags(old_building_metrics)
    print_report(report)
    
    print("\n--- Test Case 4: High Debt BRF ---")
    high_debt_metrics = BRFMetrics(
        brf_name="High Debt Test",
        annual_result=-200000,
        operating_result=100000,
        interest_costs=-2000000,
        cash_flow=-100000,
        liquid_assets=1500000,
        monthly_fee_per_sqm=65,
        total_debt=40000000,
        equity=8000000,
        solvency_ratio=12,
        maintenance_reserves=2000000,
        num_apartments=50,
        building_year=1995,
        total_area=3500
    )
    
    report = detector.detect_red_flags(high_debt_metrics)
    print_report(report)


def print_report(report):
    print(f"\nBRF: {report.brf_name}")
    print(f"Overall Risk Level: {report.overall_risk_level}")
    print(f"Total Red Flags: {report.total_red_flags}")
    print(f"  - Critical: {report.critical_count}")
    print(f"  - High: {report.high_count}")
    print(f"  - Medium: {report.medium_count}")
    print(f"  - Low: {report.low_count}")
    
    print(f"\n{report.summary}")
    
    if report.red_flags:
        print("\n📋 Detected Red Flags:\n")
        for i, flag in enumerate(report.red_flags, 1):
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }
            emoji = severity_emoji.get(flag.severity.value, "⚪")
            
            print(f"{i}. {emoji} [{flag.severity.value.upper()}] {flag.title}")
            print(f"   Category: {flag.category.value}")
            print(f"   Description: {flag.description}")
            print(f"   Impact: {flag.impact}")
            print(f"   Recommendation: {flag.recommendation}")
            if flag.evidence:
                print(f"   Evidence: {flag.evidence}")
            print()
    
    if report.immediate_actions:
        print("⚡ Immediate Actions Required:")
        for action in report.immediate_actions:
            print(f"  • {action}")
    
    print("\n" + "-"*80)


if __name__ == "__main__":
    test_red_flag_detection()
