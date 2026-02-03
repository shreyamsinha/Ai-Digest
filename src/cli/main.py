import typer
from rich import print
from src.config.settings import get_settings
from src.db.database import init_db
from src.workflows.run_digest import run_digest
from src.tools.logging_setup import setup_logging
setup_logging()


app = typer.Typer(help="Local AI intelligence digest system")

@app.command()
def doctor():
    """Check config + DB connectivity."""
    s = get_settings()
    print("[bold green]Config loaded[/bold green]")
    print("Ollama:", s.ollama_base_url, "| Model:", s.ollama_model)
    print("Personas:", s.personas_enabled)
    init_db()
    print("[bold green]DB OK[/bold green]")

@app.command()
def run():
    """Run one digest pipeline execution."""
    try:
        init_db()
        result = run_digest()
        print("[bold green]Run complete[/bold green]")
        print(result)
    except Exception as e:
        print(f"[bold red]Run failed[/bold red]: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    app()
