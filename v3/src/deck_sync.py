"""
Deck synchronization module for Anki-Assimil V3
Handles syncing CSV data to Anki decks via AnkiConnect
"""
from pathlib import Path
from typing import List, Dict, Set
from rich.console import Console
import csv
import unicodedata
from .anki_api import anki_request, create_note, create_deck

console = Console()

def load_assimil_translations(csv_path: Path) -> List[Dict]:
    """
    Load completed translations from assimil.csv
    
    Args:
        csv_path: Path to assimil.csv file
        
    Returns:
        List of lesson dictionaries with translations
    """
    if not csv_path.exists():
        console.print(f"[red]Error:[/red] Translations file not found: {csv_path}")
        return []
        
    try:
        translations = []
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Only include rows with actual English translations
                if row.get('english') and row['english'] != 'NA':
                    translations.append(row)
        
        console.print(f"[green]✓[/green] Loaded {len(translations)} completed translations")
        return translations
        
    except Exception as e:
        console.print(f"[red]Error loading translations:[/red] {e}")
        return []

def get_existing_cards_by_id(deck_name: str) -> Dict[str, int]:
    """
    Get existing cards mapped by lesson ID to note ID for updates
    
    Args:
        deck_name: Name of the Anki deck
        
    Returns:
        Dictionary mapping lesson ID to note ID
    """
    # Find all notes in the deck with assimil tag
    note_ids = anki_request("findNotes", {"query": f'deck:"{deck_name}" tag:assimil'})
    if not note_ids:
        console.print(f"[yellow]No existing assimil cards in deck: {deck_name}[/yellow]")
        return {}
    
    # Get note details to extract lesson ID from tags
    notes_info = anki_request("notesInfo", {"notes": note_ids})
    if not notes_info:
        return {}
    
    existing_cards = {}
    missing_id_count = 0
    
    for note in notes_info:
        note_id = note.get('noteId')
        tags = note.get('tags', [])
        
        if note_id:
            # Look for lesson ID in tags (format: L001.S01, L002.N2, etc.)
            lesson_id = None
            for tag in tags:
                if tag.startswith('L') and '.' in tag and len(tag) >= 6:  # L001.S01 format
                    lesson_id = tag
                    break
            
            if lesson_id:
                existing_cards[lesson_id] = note_id
            else:
                missing_id_count += 1
    
    if missing_id_count > 0:
        console.print(f"[yellow]Warning: {missing_id_count} cards missing lesson ID tags[/yellow]")
    
    console.print(f"[green]✓[/green] Found {len(existing_cards)} existing cards with IDs in {deck_name}")
    return existing_cards

def sync_phrase_cards(translations: List[Dict], deck_name: str, note_type: str = "Basic") -> Dict[str, int]:
    """
    Sync phrase cards in Anki (create new, update existing)
    
    Args:
        translations: List of translation dictionaries
        deck_name: Target deck name
        note_type: Anki note type to use
        
    Returns:
        Dictionary with counts of created and updated cards
    """
    if not translations:
        return {"created": 0, "updated": 0}
    
    from .anki_api import update_note_tags
    
    # Get existing cards mapped by lesson ID to note ID
    existing_cards = get_existing_cards_by_id(deck_name)
    
    # Separate new and existing cards based on lesson ID
    new_translations = []
    update_translations = []
    
    for t in translations:
        lesson_id = t['id']  # Use lesson ID as primary key
        
        if lesson_id in existing_cards:
            update_translations.append((t, existing_cards[lesson_id]))
        else:
            new_translations.append(t)
    
    # Sort by lesson ID to ensure proper order
    new_translations.sort(key=lambda x: x['id'])
    update_translations.sort(key=lambda x: x[0]['id'])
    
    created_count = 0
    updated_count = 0
    
    # Create new cards
    if new_translations:
        console.print(f"[bold blue]Creating {len(new_translations)} new phrase cards...[/bold blue]")
        
        
        for translation in new_translations:
            # Prepare card fields
            fields = {
                "Front": f"{translation['hebrew']}<br>{translation['sound']}",
                "Back": translation['english']
            }
            
            # Parse tags and include lesson ID
            tags = translation['tags'].split() if translation['tags'] else []
            # Add lesson ID as a tag for future lookups
            if translation['id'] not in tags:
                tags.append(translation['id'])
            
            # Create the card
            note_id = create_note(deck_name, note_type, fields, tags)
            
            if note_id:
                created_count += 1
                console.print(f"  ✓ {translation['id']}: {translation['hebrew'][:30]}...")
            else:
                console.print(f"  ✗ Failed: {translation['id']}")
    
    # Update existing cards with new tags (test with just first few)
    if update_translations:
        console.print(f"[bold blue]Updating tags on {len(update_translations)} existing cards...[/bold blue]")
        
        for translation, note_id in update_translations:
            # Parse tags (use lesson-level tags, not individual phrase IDs)
            tags = translation['tags'].split() if translation['tags'] else []
            
            # Update the card tags
            if update_note_tags(note_id, tags):
                updated_count += 1
                console.print(f"  ✓ {translation['id']}: Updated tags")
            else:
                console.print(f"  ✗ Failed: {translation['id']}")
    
    if created_count == 0 and updated_count == 0:
        console.print("[green]All phrase cards are up to date[/green]")
    else:
        console.print(f"\n[green]✓[/green] Created {created_count}, Updated {updated_count} phrase cards")
    
    return {"created": created_count, "updated": updated_count}

def sync_phrases_to_anki(config: Dict) -> bool:
    """
    Sync completed phrase translations to Anki deck
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if successful
    """
    # Load translations
    data_dir = Path("data")
    csv_path = data_dir / "assimil.csv"
    translations = load_assimil_translations(csv_path)
    
    if not translations:
        console.print("[red]No completed translations found to sync[/red]")
        return False
    
    # Get deck configuration
    deck_name = config['anki']['assimil_deck']
    
    # Ensure deck exists
    if not create_deck(deck_name):
        console.print(f"[red]Failed to create/access deck: {deck_name}[/red]")
        return False
    
    # Sync phrase cards (create new, update existing)
    results = sync_phrase_cards(translations, deck_name)
    
    total_changes = results["created"] + results["updated"]
    if total_changes > 0:
        console.print(f"\n[green]🎉 Sync complete![/green]")
        console.print(f"[dim]Created {results['created']}, Updated {results['updated']} cards in '{deck_name}' deck[/dim]")
    else:
        console.print(f"\n[green]Deck is up to date[/green]")
    
    return True