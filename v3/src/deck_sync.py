"""
Deck synchronization module for Anki-Assimil V3
Handles syncing CSV data to Anki decks via AnkiConnect
"""
from pathlib import Path
from typing import List, Dict, Set, Optional
from rich.console import Console
import csv
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

def get_existing_cards_by_media(deck_name: str) -> Dict[str, int]:
    """
    Get existing cards mapped by media filename to note ID for updates
    Uses sound field media filename as unique identifier

    Args:
        deck_name: Name of the Anki deck

    Returns:
        Dictionary mapping media filename to note ID
    """
    import re
    
    # Find all notes in the deck (don't filter by tag since we're fixing the tags)
    note_ids = anki_request("findNotes", {"query": f'deck:"{deck_name}"'})
    if not note_ids:
        console.print(f"[yellow]No existing cards in deck: {deck_name}[/yellow]")
        return {}

    # Get note details to extract media filename for matching
    notes_info = anki_request("notesInfo", {"notes": note_ids})
    if not notes_info:
        return {}

    existing_cards = {}
    processed_count = 0

    for note in notes_info:
        note_id = note.get('noteId')
        fields = note.get('fields', {})

        if note_id and fields:
            # Extract media filename from front field sound tag
            front_field = fields.get('Front', {}).get('value', '')
            
            # Look for [sound:filename.mp3] pattern
            sound_match = re.search(r'\[sound:([^\]]+)\]', front_field)
            if sound_match:
                media_filename = sound_match.group(1)
                existing_cards[media_filename] = note_id
                processed_count += 1

    console.print(f"[green]✓[/green] Found {processed_count} existing cards in {deck_name}")
    return existing_cards

def sync_phrase_cards(translations: List[Dict], deck_name: str, note_type: str = "Basic (and reversed card)") -> Dict[str, int]:
    """
    Sync phrase cards in Anki (create missing cards only)
    
    Assumes existing cards are immutable - only creates missing cards.
    To update a card, delete it manually in Anki and re-sync.

    Args:
        translations: List of translation dictionaries
        deck_name: Target deck name
        note_type: Anki note type to use

    Returns:
        Dictionary with count of created cards
    """
    if not translations:
        return {"created": 0}

    # Get existing cards mapped by media filename
    existing_cards = get_existing_cards_by_media(deck_name)
    existing_media_files = set(existing_cards.keys())

    # Find translations that need cards created
    missing_translations = []
    import re
    
    for translation in translations:
        # Extract media filename from sound field [sound:L001.S01.mp3] -> L001.S01.mp3
        sound_match = re.search(r'\[sound:([^\]]+)\]', translation['sound'])
        if sound_match:
            media_filename = sound_match.group(1)
            if media_filename not in existing_media_files:
                missing_translations.append(translation)
        else:
            # No sound field, treat as missing
            missing_translations.append(translation)

    # Sort by lesson ID to ensure proper order
    missing_translations.sort(key=lambda x: x['id'])
    created_count = 0
    existing_count = len(translations) - len(missing_translations)

    if existing_count > 0:
        console.print(f"[green]✓[/green] {existing_count} cards already exist")

    # Create missing cards
    if missing_translations:
        console.print(f"[bold blue]Creating {len(missing_translations)} missing phrase cards...[/bold blue]")

        for translation in missing_translations:
            # Prepare card fields
            fields = {
                "Front": f"{translation['hebrew']}<br>{translation['sound']}",
                "Back": translation['english']
            }

            # Generate standardized tags using centralized system
            from .tags import generate_lesson_tags
            
            # Extract lesson number from ID (L001.S01 -> 1)
            lesson_id = translation['id']
            lesson_num = int(lesson_id.split('.')[0][1:])  # L001 -> 1
            
            # Generate standardized lesson tags (assimil, assimil::L01)
            tags = generate_lesson_tags('assimil', lesson_num)

            # Create the card
            note_id = create_note(deck_name, note_type, fields, tags)

            if note_id:
                created_count += 1
                console.print(f"  ✓ {translation['id']}: {translation['hebrew'][:30]}...")
            else:
                console.print(f"  ✗ Failed: {translation['id']}")
    else:
        console.print("[green]All phrase cards already exist[/green]")

    if created_count > 0:
        console.print(f"\n[green]✓[/green] Created {created_count} new phrase cards")

    return {"created": created_count}


def get_media_mapping_file(course_dir: Path) -> Path:
    """Get path to the media mapping file for this course directory"""
    # Create mapping file in data directory, named after course directory
    course_name = course_dir.name.replace(" ", "_").replace("/", "_")
    return Path("data") / f"media_mapping_{course_name}.json"

def create_media_mapping_file(course_dir: Path) -> Dict[str, str]:
    """
    Create a complete media mapping file for the entire Assimil directory
    Maps Anki filenames to relative paths from course directory
    
    Args:
        course_dir: Base course directory path
        
    Returns:
        Dictionary mapping anki filename to relative path
    """
    import re
    import json
    
    console.print(f"[bold blue]Creating media mapping file for {course_dir}...[/bold blue]")
    
    mapping = {}
    mp3_files = list(course_dir.rglob("*.mp3"))
    
    console.print(f"Found {len(mp3_files)} MP3 files")
    
    for mp3_file in mp3_files:
        # Get relative path from course directory
        relative_path = str(mp3_file.relative_to(course_dir))
        
        parent_dir = mp3_file.parent.name
        filename = mp3_file.stem  # filename without .mp3
        
        # Match lesson directory pattern: L001-Hebrew ASSIMIL
        lesson_match = re.match(r'L(\d{3})-Hebrew ASSIMIL', parent_dir)
        if lesson_match:
            lesson_num = lesson_match.group(1)  # 001
            
            # Skip T00-TRANSLATE files
            if filename == 'T00-TRANSLATE':
                continue
                
            # Handle different filename patterns:
            # S00-TITLE.mp3 -> assimil-L003.S00.mp3
            # S01.mp3 -> assimil-L003.S01.mp3
            # N3.mp3 -> assimil-L003.N3.mp3
            # T05.mp3 -> assimil-L003.T05.mp3
            
            base_filename = filename
            if '-' in filename:
                # Remove suffix like -TITLE, -TRANSLATE
                base_filename = filename.split('-')[0]
            
            # Build prefixed anki filename: assimil-L003.S00.mp3
            anki_filename = f"assimil-L{lesson_num}.{base_filename}.mp3"
            mapping[anki_filename] = relative_path
    
    # Save mapping to file
    mapping_file = get_media_mapping_file(course_dir)
    mapping_file.parent.mkdir(exist_ok=True)
    
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    
    console.print(f"[green]✓[/green] Created mapping file with {len(mapping)} entries: {mapping_file}")
    return mapping

def load_media_mapping(course_dir: Path) -> Dict[str, Path]:
    """
    Load media mapping from file, creating it if it doesn't exist
    
    Args:
        course_dir: Base course directory path
        
    Returns:
        Dictionary mapping anki filename to absolute file path
    """
    import json
    
    mapping_file = get_media_mapping_file(course_dir)
    
    # Create mapping file if it doesn't exist
    if not mapping_file.exists():
        console.print(f"[yellow]Media mapping file not found, creating: {mapping_file}[/yellow]")
        relative_mapping = create_media_mapping_file(course_dir)
    else:
        # Load existing mapping
        with open(mapping_file, 'r', encoding='utf-8') as f:
            relative_mapping = json.load(f)
        console.print(f"[green]✓[/green] Loaded media mapping with {len(relative_mapping)} entries")
    
    # Convert relative paths to absolute paths
    absolute_mapping = {}
    for anki_filename, relative_path in relative_mapping.items():
        absolute_path = course_dir / relative_path
        if absolute_path.exists():
            absolute_mapping[anki_filename] = absolute_path
        else:
            console.print(f"[yellow]Warning:[/yellow] File not found: {relative_path}")
    
    return absolute_mapping


def sync_media_files(translations: List[Dict], config: Dict) -> Dict[str, int]:
    """
    Upload media files directly from course directory to Anki using AnkiConnect
    Uses batch existence check with set difference for optimal performance
    
    Args:
        translations: List of translation dictionaries with sound fields
        config: Configuration with course directory path
        
    Returns:
        Dictionary with counts of uploaded, skipped, and failed files
    """
    from .anki_api import store_media_file, get_existing_assimil_media
    import re
    import os
    
    course_dir = Path(os.path.expanduser(config['paths']['assimil_course_dir']))
    uploaded_count = 0
    skipped_count = 0
    failed_count = 0
    
    console.print(f"[bold blue]Syncing media files from {course_dir}...[/bold blue]")
    
    # Load media mapping (creates it if needed)
    media_lookup = load_media_mapping(course_dir)
    
    # Extract unique audio files from sound fields (with assimil- prefix)
    needed_files = set()
    for translation in translations:
        sound_field = translation.get('sound', '')
        if sound_field and '[sound:' in sound_field:
            # Extract filename from [sound:assimil-filename.mp3] format
            match = re.search(r'\[sound:([^\]]+)\]', sound_field)
            if match:
                filename = match.group(1)  # Already has assimil- prefix
                needed_files.add(filename)
    
    # Get existing assimil media files in one batch call
    existing_files = get_existing_assimil_media()
    
    # Fast set difference to find missing files
    missing_files = needed_files - existing_files
    skipped_count = len(needed_files) - len(missing_files)
    
    console.print(f"Needed: {len(needed_files)}, Existing: {len(existing_files)}, Missing: {len(missing_files)}")
    
    if skipped_count > 0:
        console.print(f"[green]✓[/green] {skipped_count} files already exist, skipping")
    
    # Upload only missing files
    for prefixed_filename in sorted(missing_files):
        # Look up the original file path using prefixed filename
        original_path = media_lookup.get(prefixed_filename)
        
        if not original_path:
            console.print(f"  ⚠ Missing: {prefixed_filename}")
            failed_count += 1
            continue
            
        # Store in Anki using AnkiConnect with the prefixed filename
        result = store_media_file(prefixed_filename, original_path, delete_existing=False)
        
        if result:
            uploaded_count += 1
            console.print(f"  ✓ {prefixed_filename} <- {original_path.name}")
        else:
            failed_count += 1
            console.print(f"  ✗ Failed: {prefixed_filename}")
    
    console.print(f"\n[green]✓[/green] Media sync: {uploaded_count} uploaded, {skipped_count} skipped, {failed_count} failed")
    
    return {"uploaded": uploaded_count, "skipped": skipped_count, "failed": failed_count}

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

    # Sync phrase cards (create missing only)
    results = sync_phrase_cards(translations, deck_name)

    # Sync media files to Anki's media directory
    media_results = sync_media_files(translations, config)

    # Summary
    cards_created = results["created"]
    media_uploaded = media_results["uploaded"]
    
    if cards_created > 0 or media_uploaded > 0:
        console.print(f"\n[green]🎉 Sync complete![/green]")
        console.print(f"[dim]Cards: {cards_created} created[/dim]")
        console.print(f"[dim]Media: {media_uploaded} uploaded, {media_results['failed']} failed[/dim]")
    else:
        console.print(f"\n[green]Everything is up to date[/green]")

    return True