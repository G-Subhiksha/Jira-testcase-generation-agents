#!/usr/bin/env python3
"""
Test Case Generation Multi-Agent System
Main CLI Application
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from llm_client import LLMClient
from document_parser import DocumentParser
from orchestrator import AgentOrchestrator

# Initialize Rich console
console = Console()

def setup_logging():
    """Setup logging configuration"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"execution_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def load_config():
    """Load agent configuration"""
    config_path = "config/agent_config.json"
    
    if not os.path.exists(config_path):
        console.print(f"[red]Error: Configuration file not found: {config_path}[/red]")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return json.load(f)

def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║     Enterprise Test Case Generation Multi-Agent System       ║
║                                                              ║
║     Powered by AI • 8 Specialized Agents                    ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(Panel(banner, style="bold blue"))

def get_user_input():
    """Get input from user via interactive CLI"""
    
    # Step 1: Document Type
    document_type = questionary.select(
        "Select input type:",
        choices=[
            "BRD (Business Requirements Document)",
            "User Story",
            "Epic"
        ]
    ).ask()
    
    if not document_type:
        console.print("[yellow]Operation cancelled[/yellow]")
        sys.exit(0)
    
    doc_type_map = {
        "BRD (Business Requirements Document)": "BRD",
        "User Story": "Story",
        "Epic": "Epic"
    }
    doc_type = doc_type_map[document_type]
    
    # Step 2: Input Method
    input_method = questionary.select(
        "Select input method:",
        choices=[
            "Upload file (.pdf, .docx, .txt, .md)",
            "Paste text content",
            "Enter file path"
        ]
    ).ask()
    
    if not input_method:
        console.print("[yellow]Operation cancelled[/yellow]")
        sys.exit(0)
    
    document_data = None
    
    if input_method == "Upload file (.pdf, .docx, .txt, .md)":
        file_path = questionary.path(
            "Enter file path:",
            validate=lambda p: os.path.exists(p) or "File not found"
        ).ask()
        
        if not file_path:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)
        
        parser = DocumentParser()
        document_data = parser.parse(file_path)
        
    elif input_method == "Paste text content":
        console.print("\n[cyan]Paste your document content (press Ctrl+D or Ctrl+Z when done):[/cyan]")
        
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        content = "\n".join(lines)
        
        if not content.strip():
            console.print("[red]Error: No content provided[/red]")
            sys.exit(1)
        
        parser = DocumentParser()
        document_data = parser.parse_from_text(content, doc_type)
        
    elif input_method == "Enter file path":
        file_path = questionary.text(
            "Enter file path:",
            validate=lambda p: os.path.exists(p) or "File not found"
        ).ask()
        
        if not file_path:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)
        
        parser = DocumentParser()
        document_data = parser.parse(file_path)
    
    # Step 3: Project Name
    project_name = questionary.text(
        "Enter project name (for output folder):",
        default="test_generation"
    ).ask()
    
    if not project_name:
        project_name = "test_generation"
    
    # Clean project name
    project_name = project_name.replace(" ", "_").replace("/", "_")
    
    return {
        "document_type": doc_type,
        "document_data": document_data,
        "project_name": project_name
    }

def print_execution_summary(summary: dict):
    """Print execution summary"""
    console.print("\n")
    console.print(Panel.fit("✓ GENERATION COMPLETE", style="bold green"))
    
    # Summary table
    table = Table(title="Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    # Test suite metrics
    metrics = summary.get("testSuiteMetrics", {})
    table.add_row("Total Test Cases", str(metrics.get("totalTestCases", 0)))
    
    # By category
    by_category = metrics.get("byCategory", {})
    for cat, count in by_category.items():
        table.add_row(f"  {cat}", str(count))
    
    # By priority
    by_priority = metrics.get("byPriority", {})
    for pri, count in by_priority.items():
        table.add_row(f"  {pri}", str(count))
    
    # Coverage
    coverage = summary.get("coverageMetrics", {})
    table.add_row("Requirements Covered", f"{coverage.get('fullyCovered', 0)}/{coverage.get('totalAcceptanceCriteria', 0)}")
    table.add_row("Coverage Percentage", f"{coverage.get('coveragePercentage', 0)}%")
    
    # Optimization
    opt = summary.get("optimizationMetrics", {})
    table.add_row("Duplicates Removed", str(opt.get("duplicatesRemoved", 0)))
    table.add_row("Reduction Percentage", f"{opt.get('reductionPercentage', 0)}%")
    
    # Execution time
    table.add_row("Total Execution Time", f"{summary.get('totalDuration', 0):.2f}s")
    
    console.print(table)
    
    # Output location
    console.print(f"\n📁 [bold cyan]Output Location:[/bold cyan]")
    console.print(f"   {summary.get('outputDirectory')}")
    console.print(f"\n📊 [bold cyan]Excel File:[/bold cyan]")
    console.print(f"   {summary.get('outputFiles', {}).get('excelFile')}")

def main():
    """Main application entry point"""
    try:
        # Setup
        logger = setup_logging()
        print_banner()
        
        # Load configuration
        config = load_config()
        
        # Get user input
        user_input = get_user_input()
        
        document_data = user_input["document_data"]
        
        # Display document info
        console.print(f"\n✓ Document loaded successfully")
        console.print(f"  Type: {user_input['document_type']}")
        console.print(f"  Characters: {document_data['character_count']:,}")
        console.print(f"  Project: {user_input['project_name']}")
        
        # Confirm execution
        proceed = questionary.confirm(
            "\nProceed with test case generation?",
            default=True
        ).ask()
        
        if not proceed:
            console.print("[yellow]Operation cancelled[/yellow]")
            sys.exit(0)
        
        # Initialize LLM client
        console.print("\n[cyan]Initializing LLM client...[/cyan]")
        llm_client = LLMClient()
        
        # Initialize orchestrator
        console.print("[cyan]Initializing agents...[/cyan]")
        orchestrator = AgentOrchestrator(config, llm_client)
        
        # Prepare input
        execution_input = {
            "document_content": document_data["document_content"],
            "document_type": user_input["document_type"],
            "project_name": user_input["project_name"]
        }
        
        # Execute orchestration
        console.print("\n[bold green]Starting agent orchestration...[/bold green]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Processing...", total=None)
            
            summary = orchestrator.execute(execution_input)
            
            progress.update(task, completed=True)
        
        # Print summary
        print_execution_summary(summary)
        
        # Ask to open output folder
        open_folder = questionary.confirm(
            "\nOpen output folder?",
            default=True
        ).ask()
        
        if open_folder:
            output_dir = summary.get("outputDirectory")
            if sys.platform == "darwin":  # macOS
                os.system(f"open '{output_dir}'")
            elif sys.platform == "win32":  # Windows
                os.system(f"start '{output_dir}'")
            else:  # Linux
                os.system(f"xdg-open '{output_dir}'")
        
        console.print("\n[bold green]Thank you for using the Test Case Generation System![/bold green]\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/bold red]")
        logger.exception("Application error")
        sys.exit(1)

if __name__ == "__main__":
    main()
