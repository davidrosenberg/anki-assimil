#!/usr/bin/env python3
"""
Anki-Assimil V2 - Modern Hebrew language learning integration
"""
import typer
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Hebrew Assimil to Anki integration tool")
console = Console()

def load_config() -> dict:
    """Load configuration from YAML file"""
    config_path = Path("input/config.yaml")
    if not config_path.exists():
        console.print(f"[red]Error:[/red] Config file not found: {config_path}")
        raise typer.Exit(1)
    
    with open(config_path) as f:
        return yaml.safe_load(f)

@app.command()
def status():
    """Show current status of files and directories"""
    console.print("[bold blue]Anki-Assimil V2 Status[/bold blue]")
    
    try:
        config = load_config()
    except:
        console.print("[red]✗[/red] Cannot load config file")
        return
    
    # Check directory structure
    dirs = ["input", "working", "output", "src", "old-code"]
    table = Table(title="Directory Structure")
    table.add_column("Directory", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Files", style="dim")
    
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            files = list(dir_path.glob("*"))
            file_count = len([f for f in files if f.is_file()])
            table.add_row(dir_name, "✓ Exists", f"{file_count} files")
        else:
            table.add_row(dir_name, "✗ Missing", "")
    
    console.print(table)
    
    # Check key files from config
    paths = config.get('paths', {})
    input_dir = Path(paths.get('input_dir', './input'))
    working_dir = Path(paths.get('working_dir', './working'))
    
    key_files = [
        (input_dir / paths.get('anki_export_file', 'alldecks.txt'), "Anki export"),
        (working_dir / paths.get('translations_file', 'assimil.csv'), "Translations"),
        (working_dir / paths.get('word_matches_file', 'assimil-words.csv'), "Word matches"),
    ]
    
    console.print("\n[bold]Key Files:[/bold]")
    for file_path, description in key_files:
        if file_path.exists():
            console.print(f"[green]✓[/green] {description}: {file_path}")
        else:
            console.print(f"[red]✗[/red] {description}: {file_path}")

@app.command() 
def extract_audio(
    lessons: str = typer.Option("1-5", help="Lesson range (e.g., '1-5' or '1,3,5')")
):
    """Extract audio files and create initial CSV structure"""
    config = load_config()
    
    # Import audio module
    import sys
    sys.path.append('src')
    from audio import extract_audio_info, extract_mp3_metadata, generate_csv_output, copy_audio_files
    
    console.print(f"[bold blue]Extracting audio for lessons: {lessons}[/bold blue]")
    
    # Scan for audio files
    audio_files = extract_audio_info(config)
    
    if not audio_files:
        console.print("[yellow]No audio files found to process[/yellow]")
        return
    
    # Extract metadata from each file
    console.print(f"\n[bold blue]Extracting metadata from {len(audio_files)} files...[/bold blue]")
    
    processed_rows = []
    for lesson_dir, mp3_file in audio_files:
        metadata = extract_mp3_metadata(mp3_file)
        if metadata:
            processed_rows.append(metadata)
            console.print(f"  ✓ {metadata['id']}: {metadata['hebrew'][:50]}...")
        else:
            console.print(f"  ✗ Failed to process: {mp3_file.name}")
    
    console.print(f"\n[green]✓[/green] Metadata extraction complete!")
    console.print(f"Successfully processed: {len(processed_rows)} files")
    
    if not processed_rows:
        console.print("[yellow]No data to export[/yellow]")
        return
    
    # Generate CSV output
    paths = config['paths']
    generated_dir = Path(paths['generated_dir'])
    csv_path = generated_dir / 'assimil-init.csv'
    media_dir = Path(paths['anki_media_dir'])
    
    console.print(f"\n[bold blue]Generating output files...[/bold blue]")
    
    # Create CSV file
    if generate_csv_output(processed_rows, csv_path):
        console.print(f"✓ Initial CSV created for manual translation")
    
    # Copy audio files
    copy_audio_files(processed_rows, media_dir)
    
    console.print(f"\n[green]🎉 Audio extraction complete![/green]")
    console.print(f"[dim]Next: Edit {csv_path} to add English translations[/dim]")

@app.command()
def match_words():
    """Generate word matching suggestions"""
    config = load_config()
    
    # Import matching module
    import sys
    sys.path.append('src')
    from matching import generate_word_matches
    
    console.print("[bold blue]Generating word matching suggestions...[/bold blue]")
    
    # Generate word matches
    success = generate_word_matches(config)
    
    if success:
        console.print(f"\n[green]🎉 Word matching complete![/green]")
        console.print(f"[dim]Next: Review generated/assimil-words-init.csv and copy good matches to data/assimil-words.csv[/dim]")
    else:
        console.print(f"\n[red]Word matching failed[/red]")

@app.command()
def export_anki():
    """Export files for Anki import"""
    config = load_config()
    
    # Import anki export module
    import sys
    sys.path.append('src')
    from anki_export import export_anki_files
    
    console.print("[bold blue]Creating Anki import files...[/bold blue]")
    
    # Generate Anki export files
    success = export_anki_files(config)
    
    if success:
        console.print(f"\n[green]🎉 Ready for Anki import![/green]")
    else:
        console.print(f"\n[red]Export failed - check word matches are curated[/red]")

if __name__ == "__main__":
    app()