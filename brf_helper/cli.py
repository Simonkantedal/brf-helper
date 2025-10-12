import logging
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from typing import Optional

from brf_helper.etl.document_processor import DocumentProcessor
from brf_helper.etl.vector_store import BRFVectorStore
from brf_helper.etl.text_chunker import TextChunker
from brf_helper.llm.embeddings import GeminiEmbeddings
from brf_helper.llm.rag_interface import BRFQueryInterface

logging.basicConfig(level=logging.WARNING)
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
    brf_name: Optional[str] = typer.Option(None, "--brf", "-b", help="Filter by specific BRF"),
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
    brf_name: Optional[str] = typer.Option(None, "--brf", "-b", help="Filter by specific BRF")
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
    brf_name: Optional[str] = typer.Option(None, "--name", "-n", help="BRF name"),
    reset: bool = typer.Option(False, "--reset", help="Reset collection before ingesting")
):
    """
    Ingest PDF documents into the vector database.
    """
    embeddings = GeminiEmbeddings()
    vector_store = BRFVectorStore(persist_directory="./chroma_db")
    vector_store.create_collection("brf_reports", reset=reset)
    
    chunker = TextChunker(chunk_size=1000, chunk_overlap=200)
    processor = DocumentProcessor(embeddings, vector_store, chunker)
    
    if path.is_file():
        with console.status(f"[bold green]Processing {path.name}...", spinner="dots"):
            result = processor.process_pdf(path, brf_name)
        
        console.print(f"\n[bold green]✓[/bold green] Processed: {result['brf_name']}")
        console.print(f"  Pages: {result['num_pages']}")
        console.print(f"  Chunks: {result['num_chunks']}")
    
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
    
    else:
        console.print(f"[bold red]Error:[/bold red] {path} is not a valid file or directory")
        raise typer.Exit(1)


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


if __name__ == "__main__":
    app()
