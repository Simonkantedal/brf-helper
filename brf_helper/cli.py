import logging
from pathlib import Path
from typing import List
import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown


from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings
from brf_helper.llm.rag_interface import BRFQueryInterface
from brf_helper.analysis.brf_analyzer import BRFAnalyzer
from brf_helper.analysis.red_flag_detector import RedFlagDetector, RedFlagSeverity

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logging.getLogger("chromadb").setLevel(logging.ERROR)

app = typer.Typer(help="BRF Helper - AI-powered Swedish BRF report analysis")
console = Console()


def get_query_interface() -> BRFQueryInterface:
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    processor = DocumentProcessor(embeddings, vector_store, chunker)
    return BRFQueryInterface(processor)


@app.command()
def query(
    question: str = typer.Argument(..., help="Question about BRF reports"),
    brf_name: str | None = typer.Option(None, "--brf", "-b", help="Filter by specific BRF"),
    sources: bool = typer.Option(True, "--sources/--no-sources", help="Show source citations")
):
    """
    Ask a question about BRF reports and get an AI-generated answer.
    """
    with console.status("[bold green]Processing query...", spinner="dots"):
        query_interface = get_query_interface()
        result = query_interface.query(
            question=question,
            brf_name=brf_name,
            include_sources=sources
        )
    
    console.print("\n[bold cyan]Question:[/bold cyan]", question)
    console.print("\n[bold green]Answer:[/bold green]")
    console.print(Markdown(result["answer"]))
    
    if sources and result.get("sources"):
        console.print("\n[bold yellow]Sources:[/bold yellow]")
        table = Table(show_header=True)
        table.add_column("BRF", style="cyan")
        table.add_column("Page", style="magenta")
        table.add_column("Relevance", style="green")
        
        for source in result["sources"]:
            table.add_row(
                source["brf_name"],
                str(source.get("page_number", "N/A")),
                f"{source['relevance_score']:.1%}"
            )
        
        console.print(table)


@app.command()
def chat(
    brf_name: str | None = typer.Option(None, "--brf", "-b", help="Filter by specific BRF")
):
    """
    Start an interactive chat session about BRF reports.
    """
    console.print("[bold cyan]BRF Helper Chat[/bold cyan]")
    console.print("Type your questions about BRF reports. Type 'exit' or 'quit' to end.\n")
    
    query_interface = get_query_interface()
    
    while True:
        try:
            message = typer.prompt("\n[You]")
            
            if message.lower() in ["exit", "quit", "q"]:
                console.print("\n[bold green]Goodbye![/bold green]")
                break
            
            with console.status("[bold green]Thinking...", spinner="dots"):
                response = query_interface.chat(message=message, brf_name=brf_name)
            
            console.print(f"\n[bold cyan][Assistant][/bold cyan]")
            console.print(Markdown(response))
        
        except KeyboardInterrupt:
            console.print("\n\n[bold green]Goodbye![/bold green]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")


@app.command()
def ingest(
    path: Path = typer.Argument(..., help="Path to PDF file or directory"),
    brf_name: str | None = typer.Option(None, "--name", "-n", help="BRF name"),
    reset: bool = typer.Option(False, "--reset", help="Reset collection before ingesting"),
    extract_metrics: bool = typer.Option(True, "--extract-metrics/--no-extract-metrics", help="Extract financial metrics after ingestion"),
    db_path: str = typer.Option("./data/brf_analysis.db", "--db", help="Path to SQLite database")
):
    """
    Ingest PDF documents into the vector database and extract financial metrics.
    
    By default, extracts metrics using LLM queries (1-2 minutes per BRF).
    Use --no-extract-metrics to skip extraction and only ingest documents.
    """
    from brf_helper.database.db import BRFDatabase
    from brf_helper.analysis.metrics_extractor import BRFMetricsExtractor
    
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports", reset=reset)
    
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    processor = DocumentProcessor(embeddings, vector_store, chunker)
    
    db = BRFDatabase(db_path)
    
    results = []
    
    if path.is_file():
        with console.status(f"[bold green]Processing {path.name}...", spinner="dots"):
            result = processor.process_pdf(path, brf_name)
        results = [result]
        
        console.print(f"\n[bold green]✓[/bold green] Processed: {result['brf_name']}")
        console.print(f"  Pages: {result['num_pages']}")
        console.print(f"  Chunks: {result['num_chunks']}\n")
    
    elif path.is_dir():
        with console.status(f"[bold green]Processing directory...", spinner="dots"):
            results = processor.process_directory(path)
        
        console.print(f"\n[bold green]✓[/bold green] Processed {len(results)} documents:\n")
        
        table = Table(show_header=True)
        table.add_column("BRF Name", style="cyan")
        table.add_column("Pages", style="magenta", justify="right")
        table.add_column("Chunks", style="green", justify="right")
        
        for result in results:
            table.add_row(
                result['brf_name'],
                str(result['num_pages']),
                str(result['num_chunks'])
            )
        
        console.print(table)
        console.print()
    
    else:
        console.print(f"[bold red]Error:[/bold red] {path} is not a valid file or directory")
        raise typer.Exit(1)
    
    for result in results:
        brf_id = db.create_or_update_brf(
            brf_name=result['brf_name'],
            pdf_path=str(result['source']),
            num_pages=result['num_pages'],
            num_chunks=result['num_chunks']
        )
        logger.info(f"Saved {result['brf_name']} to database (ID: {brf_id})")
    
    if extract_metrics and results:
        console.print("[bold cyan]Extracting financial metrics...[/bold cyan]")
        console.print("[dim]This will take 1-2 minutes per BRF...[/dim]\n")
        
        query_interface = get_query_interface()
        extractor = BRFMetricsExtractor(query_interface)
        
        extraction_table = Table(show_header=True)
        extraction_table.add_column("BRF Name", style="cyan")
        extraction_table.add_column("Status", style="green")
        
        for result in results:
            with console.status(f"[bold green]Extracting metrics for {result['brf_name']}...", spinner="dots"):
                success = extractor.extract_and_store(result['brf_name'], db)
            
            status = "✓ Complete" if success else "✗ Failed"
            extraction_table.add_row(result['brf_name'], status)
        
        console.print(extraction_table)
        console.print(f"\n[bold green]✓[/bold green] Metrics extracted. Stored in database.\n")
        console.print(f"[dim]Database location: {db_path}[/dim]\n")
        console.print(f"[dim]Use 'brf analyze <name>' to compute analysis from metrics[/dim]\n")
    elif not extract_metrics:
        console.print("[yellow]Skipped metrics extraction.[/yellow]\n")
        console.print("Use [cyan]brf extract <name>[/cyan] to extract metrics later.\n")
    
    db.close()


@app.command()
def info():
    """
    Show information about the vector database.
    """
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    
    collection_info = vector_store.get_collection_info()
    
    console.print("\n[bold cyan]Vector Database Info[/bold cyan]\n")
    console.print(f"Collection: [green]{collection_info['name']}[/green]")
    console.print(f"Documents: [green]{collection_info['count']}[/green]")
    console.print(f"Location: [green]./chroma_db/[/green]\n")


@app.command()
def list():
    """
    List all BRFs available in the database.
    """
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    
    collection = vector_store.collection
    
    if collection.count() == 0:
        console.print("\n[yellow]No BRFs found in database.[/yellow]")
        console.print("Use [cyan]brf ingest <path>[/cyan] to add BRF reports.\n")
        return
    
    results = collection.get(include=["metadatas"])
    
    brf_names = set()
    for metadata in results.get("metadatas", []):
        if metadata and "brf_name" in metadata:
            brf_names.add(metadata["brf_name"])
    
    brf_list = sorted(brf_names)
    
    console.print(f"\n[bold cyan]Available BRFs[/bold cyan] ({len(brf_list)} total)\n")
    
    table = Table(show_header=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("BRF Name", style="cyan")
    
    for i, brf_name in enumerate(brf_list, 1):
        table.add_row(str(i), brf_name)
    
    console.print(table)
    console.print("\n[dim]Use: brf analyze <brf_name> to analyze a specific BRF[/dim]\n")


def get_available_brfs() -> List[str]:
    """Get list of all BRF names in the database"""
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports")
    
    collection = vector_store.collection
    
    if collection.count() == 0:
        return []
    
    results = collection.get(include=["metadatas"])
    
    brf_names = set()
    for metadata in results.get("metadatas", []):
        if metadata and "brf_name" in metadata:
            brf_names.add(metadata["brf_name"])
    
    return sorted(brf_names)


@app.command()
def analyze(
    brf_name: str = typer.Argument(..., help="Name of BRF to analyze"),
    red_flags_only: bool = typer.Option(False, "--red-flags-only", "-r", help="Show only red flags"),
    full: bool = typer.Option(False, "--full", "-f", help="Show full detailed analysis"),
    db_path: str = typer.Option("./data/brf_analysis.db", "--db", help="Path to SQLite database")
):
    """
    Show BRF financial health analysis and red flags.
    
    Computes analysis on-the-fly from stored raw metrics (instant).
    """
    from brf_helper.database.db import BRFDatabase
    
    available_brfs = get_available_brfs()
    
    if not available_brfs:
        console.print("\n[red]Error:[/red] No BRFs found in database.")
        console.print("Use [cyan]brf ingest <path>[/cyan] to add BRF reports.\n")
        raise typer.Exit(1)
    
    if brf_name not in available_brfs:
        console.print(f"\n[red]Error:[/red] BRF '{brf_name}' not found in database.\n")
        console.print("[yellow]Available BRFs:[/yellow]")
        for name in available_brfs:
            console.print(f"  • {name}")
        console.print(f"\n[dim]Tip: Use 'brf list' to see all available BRFs[/dim]\n")
        raise typer.Exit(1)
    
    console.print(f"\n[bold cyan]Analysis for {brf_name}[/bold cyan]\n")
    
    db = BRFDatabase(db_path)
    
    # Get raw metrics from database
    data = db.get_brf_with_metrics(brf_name)
    
    if not data or not data.brf.has_metrics:
        console.print("[yellow]No metrics found for this BRF.[/yellow]")
        console.print("Run [cyan]brf ingest <path> --extract-metrics[/cyan] to extract metrics first.\n")
        db.close()
        raise typer.Exit(1)
    
    # Convert database metrics to BRFMetrics format (only fields that BRFMetrics accepts)
    metrics_dict = {}
    if data.metrics:
        for key in ['annual_result', 'operating_result', 'total_debt', 'equity', 'solvency_ratio',
                    'liquid_assets', 'cash_flow', 'interest_costs', 'annual_fee_per_sqm', 
                    'maintenance_reserves']:
            value = getattr(data.metrics, key, None)
            if value is not None:
                metrics_dict[key] = value
    
    # Add building info from BRF table (BRFMetrics accepts these)
    if data.brf.building_year:
        metrics_dict['building_year'] = data.brf.building_year
    if data.brf.num_apartments:
        metrics_dict['num_apartments'] = data.brf.num_apartments
    if data.brf.total_area:
        metrics_dict['total_area'] = data.brf.total_area
    
    # Compute health scores from raw metrics
    with console.status("[bold green]Computing analysis...", spinner="dots"):
        from brf_helper.analysis.brf_analyzer import BRFMetrics, BRFAnalyzer
        
        # Create BRFMetrics object from dict
        brf_metrics = BRFMetrics(brf_name=brf_name, **metrics_dict)
        
        # Calculate health score (doesn't need query_interface for calculation)
        query_interface = get_query_interface()
        analyzer = BRFAnalyzer(query_interface)
        health_score = analyzer.calculate_health_score(brf_metrics)
        
        # Detect red flags
        detector = RedFlagDetector()
        red_flag_report = detector.detect_red_flags(brf_metrics)
    
    metrics = data.metrics
    
    if not red_flags_only and health_score:
        console.print("[bold green]Financial Health Score[/bold green]")
        
        score_table = Table(show_header=True, title="Health Scores")
        score_table.add_column("Category", style="cyan")
        score_table.add_column("Score", justify="right")
        score_table.add_column("Rating", justify="center")
        
        def get_rating(score: int) -> str:
            if score >= 80:
                return "[green]★★★★★[/green]"
            elif score >= 65:
                return "[green]★★★★☆[/green]"
            elif score >= 50:
                return "[yellow]★★★☆☆[/yellow]"
            elif score >= 35:
                return "[red]★★☆☆☆[/red]"
            else:
                return "[red]★☆☆☆☆[/red]"
        
        score_table.add_row(
            "Overall Health",
            f"[bold]{health_score.overall_score}/100[/bold]",
            get_rating(health_score.overall_score)
        )
        score_table.add_row("Financial Stability", f"{health_score.financial_stability_score}/100", get_rating(health_score.financial_stability_score))
        score_table.add_row("Cost Efficiency", f"{health_score.cost_efficiency_score}/100", get_rating(health_score.cost_efficiency_score))
        score_table.add_row("Liquidity", f"{health_score.liquidity_score}/100", get_rating(health_score.liquidity_score))
        score_table.add_row("Debt Management", f"{health_score.debt_management_score}/100", get_rating(health_score.debt_management_score))
        score_table.add_row("Maintenance Readiness", f"{health_score.maintenance_readiness_score}/100", get_rating(health_score.maintenance_readiness_score))
        
        console.print(score_table)
        console.print()
    
    console.print(f"[bold yellow]Red Flag Analysis[/bold yellow]")
    console.print(f"Overall Risk Level: [bold]{_get_risk_color(red_flag_report.overall_risk_level)}{red_flag_report.overall_risk_level}[/bold]")
    console.print(f"Total Red Flags: {red_flag_report.total_red_flags}")
    
    if red_flag_report.total_red_flags > 0:
        console.print(f"  🔴 Critical: {red_flag_report.critical_count}")
        console.print(f"  🟠 High: {red_flag_report.high_count}")
        console.print(f"  🟡 Medium: {red_flag_report.medium_count}")
        console.print(f"  🟢 Low: {red_flag_report.low_count}")
    
    console.print()
    
    if red_flag_report.red_flags:
        console.print("[bold red]⚠️  Detected Red Flags[/bold red]\n")
        
        for i, flag in enumerate(red_flag_report.red_flags, 1):
            severity_style = _get_severity_style(flag.severity)
            emoji = _get_severity_emoji(flag.severity)
            
            console.print(f"{emoji} [bold]{i}. {flag.title}[/bold] [{severity_style}]({flag.severity.value.upper()})[/{severity_style}]")
            console.print(f"   [dim]Category: {flag.category.value}[/dim]")
            console.print(f"   {flag.description}")
            console.print(f"   [yellow]Impact:[/yellow] {flag.impact}")
            console.print(f"   [green]Recommendation:[/green] {flag.recommendation}")
            if flag.evidence:
                console.print(f"   [dim]Evidence: {flag.evidence[:200]}...[/dim]" if len(flag.evidence) > 200 else f"   [dim]Evidence: {flag.evidence}[/dim]")
            console.print()
    else:
        console.print("✅ [bold green]No red flags detected![/bold green]\n")
    
    if full and not red_flags_only and metrics:
        console.print("[bold cyan]Key Metrics[/bold cyan]\n")
        
        metrics_table = Table(show_header=True)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", justify="right", style="green")
        
        if metrics.annual_result is not None:
            metrics_table.add_row("Årets resultat", f"{metrics.annual_result:,.0f} kr")
        if metrics.operating_result is not None:
            metrics_table.add_row("Rörelseresultat", f"{metrics.operating_result:,.0f} kr")
        if metrics.solvency_ratio is not None:
            metrics_table.add_row("Soliditet", f"{metrics.solvency_ratio:.1f}%")
        if metrics.annual_fee_per_sqm is not None:
            metrics_table.add_row("Årsavgift/kvm", f"{metrics.annual_fee_per_sqm:.0f} kr")
        if metrics.liquid_assets is not None:
            metrics_table.add_row("Likvida medel", f"{metrics.liquid_assets:,.0f} kr")
        if metrics.cash_flow is not None:
            metrics_table.add_row("Kassaflöde", f"{metrics.cash_flow:,.0f} kr")
        if metrics.maintenance_reserves is not None:
            metrics_table.add_row("Underhållsreserver", f"{metrics.maintenance_reserves:,.0f} kr")
        if data.brf.building_year is not None:
            age = 2024 - data.brf.building_year
            metrics_table.add_row("Byggår", f"{data.brf.building_year} ({age} år)")
        
        console.print(metrics_table)
        console.print()
    
    db.close()


def _get_risk_color(risk_level: str) -> str:
    colors = {
        "KRITISK": "red",
        "HÖG": "red",
        "MÅTTLIG": "yellow",
        "LÅG": "green",
        "MINIMAL": "green"
    }
    return f"[{colors.get(risk_level, 'white')}]"


def _get_severity_style(severity: RedFlagSeverity) -> str:
    styles = {
        RedFlagSeverity.CRITICAL: "red bold",
        RedFlagSeverity.HIGH: "red",
        RedFlagSeverity.MEDIUM: "yellow",
        RedFlagSeverity.LOW: "green"
    }
    return styles.get(severity, "white")


def _get_severity_emoji(severity: RedFlagSeverity) -> str:
    emojis = {
        RedFlagSeverity.CRITICAL: "🔴",
        RedFlagSeverity.HIGH: "🟠",
        RedFlagSeverity.MEDIUM: "🟡",
        RedFlagSeverity.LOW: "🟢"
    }
    return emojis.get(severity, "⚪")


def _get_db_severity_style(severity: str) -> str:
    styles = {
        "critical": "red bold",
        "high": "red",
        "medium": "yellow",
        "low": "green"
    }
    return styles.get(severity, "white")


def _get_db_severity_emoji(severity: str) -> str:
    emojis = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢"
    }
    return emojis.get(severity, "⚪")


if __name__ == "__main__":
    app()
