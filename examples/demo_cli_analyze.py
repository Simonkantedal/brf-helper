from brf_helper.analysis.brf_analyzer import BRFMetrics
from brf_helper.analysis.red_flag_detector import RedFlagDetector
from rich.console import Console
from rich.table import Table

console = Console()


problematic_metrics = BRFMetrics(
    brf_name="Demo Problematic BRF",
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

console.print("\n[bold cyan]Demo: BRF Analysis with Red Flags[/bold cyan]\n")
console.print("This demonstrates what the 'brf analyze' command shows for a BRF with problems:\n")

detector = RedFlagDetector()
report = detector.detect_red_flags(problematic_metrics)

console.print(f"[bold yellow]Red Flag Analysis[/bold yellow]")
console.print(f"Overall Risk Level: [bold red]{report.overall_risk_level}[/bold red]")
console.print(f"Total Red Flags: {report.total_red_flags}")
console.print(f"  🔴 Critical: {report.critical_count}")
console.print(f"  🟠 High: {report.high_count}")
console.print(f"  🟡 Medium: {report.medium_count}")
console.print(f"  🟢 Low: {report.low_count}\n")

console.print("[bold red]⚠️  Detected Red Flags[/bold red]\n")

for i, flag in enumerate(report.red_flags[:5], 1):
    emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[flag.severity.value]
    style = {"critical": "red bold", "high": "red", "medium": "yellow", "low": "green"}[flag.severity.value]
    
    console.print(f"{emoji} [bold]{i}. {flag.title}[/bold] [{style}]({flag.severity.value.upper()})[/{style}]")
    console.print(f"   [dim]Category: {flag.category.value}[/dim]")
    console.print(f"   {flag.description}")
    console.print(f"   [yellow]Impact:[/yellow] {flag.impact}")
    console.print(f"   [green]Recommendation:[/green] {flag.recommendation}")
    if flag.evidence:
        console.print(f"   [dim]Evidence: {flag.evidence}[/dim]")
    console.print()

if report.immediate_actions:
    console.print("[bold cyan]⚡ Immediate Actions Required[/bold cyan]\n")
    for action in report.immediate_actions:
        console.print(f"  • {action}")

console.print("\n[bold green]Try it yourself with:[/bold green]")
console.print("  brf analyze <brf_name>")
console.print("  brf analyze <brf_name> --full")
console.print("  brf analyze <brf_name> --red-flags-only\n")
