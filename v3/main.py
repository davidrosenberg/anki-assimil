#!/usr/bin/env python3
"""
Anki-Assimil V3 - Direct Anki integration via AnkiConnect
"""
import typer
from rich.console import Console

app = typer.Typer(help="Hebrew Assimil to Anki integration via AnkiConnect API")
console = Console()

def load_config() -> dict:
    """Load configuration from YAML file"""
    import yaml
    from pathlib import Path

    config_path = Path("config.yaml")
    if not config_path.exists():
        console.print(f"[red]Error:[/red] Config file not found: {config_path}")
        raise typer.Exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)

@app.command()
def status():
    """Check AnkiConnect connection and deck status"""
    from src.anki_api import check_anki_connection, get_deck_info

    console.print("[bold blue]Anki-Assimil V3 Status[/bold blue]")

    config = load_config()
    hebrew_deck = config['anki']['hebrew_deck']

    # Check AnkiConnect
    if check_anki_connection():
        console.print("[green]✓[/green] AnkiConnect is available")

        # Check Hebrew deck
        deck_info = get_deck_info(hebrew_deck)
        if deck_info:
            console.print(f"[green]✓[/green] {hebrew_deck} deck found: {deck_info['card_count']} cards")
        else:
            console.print(f"[yellow]⚠[/yellow] {hebrew_deck} deck not found")
    else:
        console.print("[red]✗[/red] AnkiConnect not available - install AnkiConnect add-on")

@app.command()
def extract_audio(
    lessons: str = typer.Option("1-5", help="Lesson range (e.g., '1-5' or '1,3,5')")
):
    """Extract audio files and generate init file for new lessons only"""
    from src.audio import extract_audio_incremental, generate_init_csv, copy_audio_files

    console.print(f"[bold blue]Extracting audio for lessons: {lessons}[/bold blue]")

    config = load_config()

    # Extract only new lessons
    new_lessons = extract_audio_incremental(config)

    if not new_lessons:
        console.print("\n[green]🎉 No new lessons to extract - all lessons already translated![/green]")
        return

    # Generate init file for new lessons
    from pathlib import Path
    data_dir = Path("data")
    init_path = data_dir / "assimil-init.csv"

    if generate_init_csv(new_lessons, init_path):
        console.print(f"\n[green]✓[/green] Generated init file with {len(new_lessons)} new lessons")

    # Copy audio files
    media_dir = Path(config['paths']['anki_media_dir'])
    copy_audio_files(new_lessons, media_dir)

    console.print(f"\n[green]🎉 Extraction complete![/green]")
    console.print(f"[dim]Next: Add English translations to {init_path}, then merge into data/assimil.csv[/dim]")

@app.command()
def sync_phrases():
    """Sync completed phrase translations to Anki deck"""
    from src.deck_sync import sync_phrases_to_anki

    config = load_config()
    deck_name = config['anki']['assimil_deck']

    console.print(f"[bold blue]Syncing phrases to '{deck_name}' deck...[/bold blue]")

    success = sync_phrases_to_anki(config)

    if not success:
        console.print("[red]Sync failed[/red]")

@app.command()
def match_words(
    lessons: str = typer.Option("1-5", help="Lesson range to process"),
    max_candidates: int = typer.Option(3, help="Maximum match candidates per word"),
    output_file: str = typer.Option("data/assimil-words-init.csv", help="Output CSV file")
):
    """Generate word match suggestions for human review"""
    console.print("[bold blue]Matching lesson words to Anki vocabulary...[/bold blue]")

    from src.csv_export import export_word_matches

    config = load_config()

    # Parse lesson range
    max_lessons = None
    if lessons and lessons != "all":
        try:
            if '-' in lessons:
                start, end = lessons.split('-')
                max_lessons = int(end)
            else:
                max_lessons = int(lessons)
        except ValueError:
            console.print(f"[red]Invalid lesson range: {lessons}[/red]")
            raise typer.Exit(1)

    # Export word matches for human review
    success = export_word_matches(config, max_lessons, output_file, max_candidates)

    if success:
        console.print(f"\n[green]✓[/green] Exported word matches to {output_file}")
        console.print(f"[dim]Next: Review the CSV file and copy approved rows to data/assimil-words.csv[/dim]")
    else:
        console.print("[red]Failed to export word matches[/red]")

@app.command()
def apply_tags(
    csv_file: str = typer.Argument(..., help="CSV file with approved matches"),
    dry_run: bool = typer.Option(True, help="Show what would be tagged without applying")
):
    """Apply lesson tags to Anki cards based on approved matches"""
    console.print(f"[bold blue]Applying tags from {csv_file}...[/bold blue]")

    from src.word_matching import WordMatchingPipeline
    from pathlib import Path
    import csv

    config = load_config()

    if not Path(csv_file).exists():
        console.print(f"[red]Error:[/red] File not found: {csv_file}")
        raise typer.Exit(1)

    # Load approved matches directly from CSV
    approved_matches = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                approved_matches.append({
                    'lesson': int(row['lesson']),
                    'heb_word': row['heb_word'],
                    'card_id': int(row['card_id'])
                })
    except Exception as e:
        console.print(f"[red]Error loading CSV: {e}[/red]")
        return

    if not approved_matches:
        console.print("[yellow]No approved matches found in CSV file[/yellow]")
        return

    console.print(f"Loaded {len(approved_matches)} approved matches")

    # Apply tags using AnkiConnect
    from src.anki_api import add_tags_to_cards

    tags_applied = 0
    errors = 0

    for match in approved_matches:
        lesson_tag = f"assimil::L{match['lesson']:02d}"

        if not dry_run:
            try:
                console.print(f"Tagging card {match['card_id']} ({match['heb_word']}) with {lesson_tag}")
                success = add_tags_to_cards([match['card_id']], [lesson_tag])
                if success:
                    console.print(f"  ✓ Success")
                    tags_applied += 1
                else:
                    console.print(f"  ✗ Failed")
                    errors += 1
            except Exception as e:
                console.print(f"  ✗ Error tagging card {match['card_id']}: {e}")
                errors += 1
        else:
            console.print(f"Would tag card {match['card_id']} ({match['heb_word']}) with {lesson_tag}")

    if dry_run:
        console.print(f"\n[green]Dry run complete[/green]")
        console.print(f"Use --no-dry-run to actually apply tags to {len(approved_matches)} cards")
    else:
        console.print(f"\n[green]Applied {tags_applied} tags successfully[/green]")
        if errors > 0:
            console.print(f"[yellow]Errors: {errors}[/yellow]")


@app.command()
def storage_status():
    """Show status of persistent storage (approved matches, unmatched words, etc.)"""
    from src.persistence import PersistenceManager

    console.print("[bold blue]Persistent Storage Status[/bold blue]")

    pm = PersistenceManager()
    pm.print_status()

    # Show sample unmatched words if any exist
    if pm.unmatched_words:
        console.print("\n[yellow]Sample unmatched words:[/yellow]")
        for i, (key, unmatched) in enumerate(pm.unmatched_words.items()):
            if i >= 5:  # Show first 5
                break
            console.print(f"  L{unmatched.lesson:02d}: {unmatched.heb_word} (attempts: {unmatched.attempts})")

@app.command()
def create_extra_template():
    """Create template file for manual extra matches"""
    from src.persistence import PersistenceManager

    console.print("[bold blue]Creating extra matches template...[/bold blue]")

    pm = PersistenceManager()
    success = pm.create_extra_matches_template()

    if success:
        console.print(f"[green]✓[/green] Template created at {pm.extra_file}")
        console.print("[dim]Edit the file to add manual matches, then run 'match-words' again[/dim]")

@app.command()
def import_v1(
    dry_run: bool = typer.Option(True, help="Show what would be imported without saving")
):
    """Import V1 approved matches and extra matches into V3 persistence system"""
    from src.v1_importer import import_v1_data

    console.print("[bold blue]Importing V1 match data...[/bold blue]")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]")

    try:
        stats = import_v1_data(dry_run=dry_run)

        if stats['total_imported'] > 0:
            if dry_run:
                console.print(f"\n[green]Would import {stats['total_imported']} matches from V1[/green]")
                console.print("[dim]Use --no-dry-run to actually import[/dim]")
            else:
                console.print(f"\n[green]✓[/green] Successfully imported {stats['total_imported']} matches from V1")

                # Show updated storage status
                from src.persistence import PersistenceManager
                pm = PersistenceManager()
                pm.print_status()
        else:
            console.print("[yellow]No new matches to import from V1[/yellow]")

    except Exception as e:
        console.print(f"[red]Error importing V1 data: {e}[/red]")

@app.command()
def cache_deck(
    deck_name: str = typer.Option(None, help="Specific deck to cache (default: from config)"),
    force: bool = typer.Option(False, help="Force refresh even if cache is valid")
):
    """Cache Anki deck data locally for fast matching"""
    from src.deck_cache import DeckCache

    config = load_config()
    if not deck_name:
        deck_name = config['anki']['hebrew_deck']

    console.print(f"[bold blue]Caching deck: {deck_name}[/bold blue]")

    cache = DeckCache()

    if force or not cache.is_cache_valid(deck_name):
        result = cache.cache_deck(deck_name)

        if result['success']:
            console.print(f"[green]✓[/green] Cached {result['hebrew_cards']} Hebrew cards from {result['total_cards']} total")

            # Show cache info
            info = cache.get_cache_info(deck_name)
            if info:
                console.print(f"[dim]Cache location: cache/{deck_name.replace(' ', '_')}_cache.pkl[/dim]")
        else:
            console.print(f"[red]Failed to cache deck: {result.get('error', 'Unknown error')}[/red]")
    else:
        console.print(f"[yellow]Cache is still valid, use --force to refresh[/yellow]")
        info = cache.get_cache_info(deck_name)
        if info:
            console.print(f"[dim]Cache age: {info['age_hours']:.1f} hours, {info['hebrew_cards']} Hebrew cards[/dim]")

@app.command()
def cache_status():
    """Show status of cached decks"""
    from src.deck_cache import DeckCache

    console.print("[bold blue]Deck Cache Status[/bold blue]")

    cache = DeckCache()
    cached_decks = cache.list_cached_decks()

    if not cached_decks:
        console.print("[yellow]No cached decks found[/yellow]")
        console.print("[dim]Use 'cache-deck' to cache your Hebrew deck[/dim]")
        return

    for deck_info in cached_decks:
        console.print(f"\n{deck_info['deck_name']}: [green]CACHED[/green]")
        console.print(f"  Hebrew cards: {deck_info['hebrew_cards']}")
        console.print(f"  Cache age: {deck_info['age_hours']:.1f} hours")
        console.print(f"  Cached: {deck_info['cached_at']}")
        console.print("[dim]  Cache never expires - use 'clear-cache' or 'cache-deck --force' to refresh[/dim]")

@app.command()
def clear_cache(
    deck_name: str = typer.Option(None, help="Specific deck to clear (default: all)")
):
    """Clear cached deck data"""
    from src.deck_cache import DeckCache

    cache = DeckCache()

    if deck_name:
        console.print(f"[bold blue]Clearing cache for: {deck_name}[/bold blue]")
        cache.clear_cache(deck_name)
        console.print(f"[green]✓[/green] Cleared cache for {deck_name}")
    else:
        console.print("[bold blue]Clearing all cached decks[/bold blue]")
        cache.clear_cache()
        console.print("[green]✓[/green] Cleared all deck caches")

if __name__ == "__main__":
    app()