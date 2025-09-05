"""
Anki export module for Anki-Assimil
Handles generation of Anki import files with updated tags
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rich.console import Console
import csv
import pandas as pd

console = Console()

def load_curated_word_matches(data_dir: Path, extra_matches_file: str,
                             word_matches_file: str) -> Dict[str, str]:
    """
    Load curated word matches from working directory

    Args:
        data_dir: Path to data directory
        extra_matches_file: Name of extra matches CSV file
        word_matches_file: Name of main word matches CSV file

    Returns:
        Dictionary mapping Anki words to their first lesson appearance
    """
    first_match = {}

    # Load main word matches
    main_matches_path = data_dir / word_matches_file
    if main_matches_path.exists():
        try:
            with open(main_matches_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    lesson = row['id'].split('.')[0][2:]  # Extract lesson number (e.g., L001 -> 01)
                    anki_word = row['match_word']
                    first_match = add_word_match(first_match, anki_word, lesson)

            console.print(f"[green]✓[/green] Loaded {len(first_match)} matches from {word_matches_file}")
        except Exception as e:
            console.print(f"[red]Error loading {word_matches_file}:[/red] {e}")
    else:
        console.print(f"[yellow]Warning:[/yellow] {word_matches_file} not found")

    # Load extra matches
    extra_matches_path = data_dir / extra_matches_file
    if extra_matches_path.exists():
        try:
            with open(extra_matches_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    lesson = row['Lesson']
                    anki_word = row['AnkiID']
                    first_match = add_word_match(first_match, anki_word, lesson)

            console.print(f"[green]✓[/green] Added extra matches from {extra_matches_file}")
        except Exception as e:
            console.print(f"[red]Error loading {extra_matches_file}:[/red] {e}")
    else:
        console.print(f"[yellow]Info:[/yellow] {extra_matches_file} not found (optional)")

    return first_match

def add_word_match(first_match: Dict[str, str], anki_word: str, lesson: str) -> Dict[str, str]:
    """
    Add a word match, keeping track of the first lesson where it appears

    Args:
        first_match: Current dictionary of word matches
        anki_word: The Anki vocabulary word
        lesson: Lesson number (e.g., '01', '02')

    Returns:
        Updated first_match dictionary
    """
    if anki_word in first_match:
        prev_lesson = first_match[anki_word]
        console.print(f"  Found {anki_word} in lesson {prev_lesson}, current lesson: {lesson}")
        # Keep the earlier lesson
        if lesson < prev_lesson:
            first_match[anki_word] = lesson
    else:
        console.print(f"  New word {anki_word} in lesson: {lesson}")
        first_match[anki_word] = lesson

    return first_match

def load_anki_vocabulary_dict(anki_export_path: Path) -> Dict[str, Dict]:
    """
    Load Anki vocabulary as a dictionary for tag updates

    Args:
        anki_export_path: Path to alldecks.txt (Anki export)

    Returns:
        Dictionary mapping Hebrew words to their full Anki card data
    """
    if not anki_export_path.exists():
        console.print(f"[red]Error:[/red] Anki export file not found: {anki_export_path}")
        return {}

    try:
        anki_dict = {}

        # Define expected headers (from original code)
        headers = ['Hebrew', 'Definition', 'Gender', 'PartOfSpeech',
                  'Shoresh', 'Audio', 'Inflections', 'Extended', 'Image', 'Tags']

        with open(anki_export_path, 'r', encoding='utf-8') as tsvfile:
            reader = csv.DictReader(tsvfile, fieldnames=headers, delimiter='\t')

            for row in reader:
                hebrew_word = row['Hebrew'].strip()
                if hebrew_word:
                    anki_dict[hebrew_word] = row

        console.print(f"[green]✓[/green] Loaded {len(anki_dict)} vocabulary cards for tag updates")
        return anki_dict

    except Exception as e:
        console.print(f"[red]Error loading Anki vocabulary:[/red] {e}")
        return {}

def generate_tag_update_csv(first_match: Dict[str, str], anki_dict: Dict[str, Dict],
                           output_path: Path, tag_prefix: str = 'assimil-') -> bool:
    """
    Generate CSV file for updating Anki card tags

    Args:
        first_match: Dictionary mapping words to their first lesson
        anki_dict: Dictionary of Anki card data
        output_path: Path where CSV should be saved
        tag_prefix: Prefix for lesson tags (e.g., 'assimil-')

    Returns:
        True if successful, False otherwise
    """
    if not first_match or not anki_dict:
        console.print("[yellow]No data available for tag update generation[/yellow]")
        return False

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Define CSV headers (same as Anki export format)
        headers = ['Hebrew', 'Definition', 'Gender', 'PartOfSpeech',
                  'Shoresh', 'Audio', 'Inflections', 'Extended', 'Image', 'Tags']

        updated_rows = []
        not_found_count = 0

        for word, lesson in first_match.items():
            if word in anki_dict:
                # Copy the original row
                row = anki_dict[word].copy()

                # Add the lesson tag
                lesson_tag = f"{tag_prefix}{lesson}"
                existing_tags = row.get('Tags', '')

                if existing_tags:
                    row['Tags'] = f"{existing_tags} {lesson_tag}"
                else:
                    row['Tags'] = lesson_tag

                updated_rows.append(row)
            else:
                console.print(f"[yellow]Warning:[/yellow] Word not found in Anki: {word}")
                not_found_count += 1

        if not updated_rows:
            console.print("[yellow]No valid rows to write to tag update file[/yellow]")
            return False

        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers, delimiter='\t')
            writer.writeheader()
            writer.writerows(updated_rows)

        console.print(f"[green]✓[/green] Tag update file created: {output_path}")
        console.print(f"[dim]Updated {len(updated_rows)} cards with lesson tags[/dim]")

        if not_found_count > 0:
            console.print(f"[yellow]Warning:[/yellow] {not_found_count} words not found in Anki vocabulary")

        return True

    except Exception as e:
        console.print(f"[red]Error generating tag update CSV:[/red] {e}")
        return False

def export_anki_files(config: Dict) -> bool:
    """
    Generate all Anki export files

    Args:
        config: Configuration dictionary

    Returns:
        True if successful, False otherwise
    """
    paths = config['paths']
    anki_config = config['anki']

    # Setup paths
    input_dir = Path(paths['input_dir'])
    data_dir = Path(paths['data_dir'])
    generated_dir = Path(paths['generated_dir'])

    console.print("[bold blue]Generating Anki export files...[/bold blue]")

    # Load curated word matches
    console.print("\n[bold blue]Loading curated word matches...[/bold blue]")
    first_match = load_curated_word_matches(
        data_dir,
        paths['extra_matches_file'],
        paths['word_matches_file']
    )

    if not first_match:
        console.print("[red]No curated word matches found. Please review and curate word matches first.[/red]")
        return False

    # Load Anki vocabulary
    console.print("\n[bold blue]Loading Anki vocabulary for tag updates...[/bold blue]")
    anki_export_path = input_dir / paths['anki_export_file']
    anki_dict = load_anki_vocabulary_dict(anki_export_path)

    if not anki_dict:
        console.print("[red]Cannot load Anki vocabulary[/red]")
        return False

    # Generate tag update file
    console.print("\n[bold blue]Generating tag update file...[/bold blue]")
    tag_update_path = generated_dir / 'assimil-tag-update.csv'
    tag_prefix = anki_config.get('tag_prefix', 'assimil-')

    success = generate_tag_update_csv(first_match, anki_dict, tag_update_path, tag_prefix)

    if success:
        console.print(f"\n[green]🎉 Anki export complete![/green]")
        console.print(f"[dim]Import {tag_update_path} into Anki to update vocabulary tags[/dim]")
        return True
    else:
        console.print(f"\n[red]Anki export failed[/red]")
        return False