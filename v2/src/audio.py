"""
Audio processing module for Anki-Assimil
Handles scanning MP3 files from Assimil course directories
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rich.console import Console
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import shutil
import csv
import pandas as pd

console = Console()

def scan_lesson_directories(base_dir: Path, max_lessons: int = 20) -> List[Path]:
    """
    Scan for lesson directories (starting with 'L') in the base directory

    Args:
        base_dir: Path to the Assimil course directory
        max_lessons: Maximum number of lessons to process

    Returns:
        List of lesson directory paths, sorted
    """
    if not base_dir.exists():
        console.print(f"[red]Error:[/red] Base directory not found: {base_dir}")
        return []

    # Find all directories starting with 'L'
    lesson_dirs = [d for d in base_dir.iterdir()
                   if d.is_dir() and d.name.startswith('L')]

    # Sort and limit
    lesson_dirs.sort(key=lambda d: d.name)
    limited_dirs = lesson_dirs[:max_lessons]

    console.print(f"[green]Found {len(lesson_dirs)} lesson directories, processing first {len(limited_dirs)}[/green]")

    return limited_dirs

def scan_mp3_files(lesson_dir: Path, skip_files: List[str] = None) -> List[Path]:
    """
    Scan a lesson directory for MP3 files

    Args:
        lesson_dir: Path to lesson directory
        skip_files: List of filenames to skip

    Returns:
        List of MP3 file paths, sorted
    """
    if skip_files is None:
        skip_files = ['T00-TRANSLATE.mp3']

    if not lesson_dir.exists():
        console.print(f"[yellow]Warning:[/yellow] Lesson directory not found: {lesson_dir}")
        return []

    # Find all MP3 files
    mp3_files = [f for f in lesson_dir.iterdir()
                 if f.is_file() and f.suffix.lower() == '.mp3']

    # Filter out skip files
    filtered_files = [f for f in mp3_files if f.name not in skip_files]

    # Sort by filename
    filtered_files.sort(key=lambda f: f.name)

    console.print(f"  [dim]{lesson_dir.name}:[/dim] Found {len(filtered_files)} MP3 files")

    return filtered_files

def extract_audio_info(config: Dict) -> List[Tuple[Path, Path]]:
    """
    Extract audio file information from Assimil course directories

    Args:
        config: Configuration dictionary

    Returns:
        List of (lesson_dir, mp3_file) tuples
    """
    paths = config['paths']
    processing = config['processing']

    base_dir = Path(paths['assimil_course_dir'])
    max_lessons = processing.get('max_lessons', 20)
    skip_files = processing.get('skip_files', ['T00-TRANSLATE.mp3'])

    console.print(f"[bold blue]Scanning audio files in:[/bold blue] {base_dir}")

    # Scan lesson directories
    lesson_dirs = scan_lesson_directories(base_dir, max_lessons)

    # Collect all MP3 files
    all_files = []
    for lesson_dir in lesson_dirs:
        mp3_files = scan_mp3_files(lesson_dir, skip_files)
        for mp3_file in mp3_files:
            all_files.append((lesson_dir, mp3_file))

    console.print(f"[green]Total MP3 files found:[/green] {len(all_files)}")

    return all_files

def extract_mp3_metadata(mp3_file: Path) -> Optional[Dict[str, str]]:
    """
    Extract metadata from an MP3 file

    Args:
        mp3_file: Path to MP3 file

    Returns:
        Dictionary with extracted metadata, or None if extraction fails
    """
    try:
        audio = MP3(str(mp3_file), ID3=EasyID3)

        # Extract key metadata
        title = audio.get('title', [''])[0] if 'title' in audio else ''
        album = audio.get('album', [''])[0] if 'album' in audio else ''

        if not title or not album:
            console.print(f"[yellow]Warning:[/yellow] Missing metadata in {mp3_file.name}")
            return None

        # Parse lesson info from album (e.g., "Course Name - L001")
        lesson = album.split(' - ')[-1] if ' - ' in album else album
        lesson_num = lesson[2:] if lesson.startswith('L') else lesson

        # Parse title (e.g., "S01-Hebrew text here")
        title_parts = title.split('-', 1)
        if len(title_parts) < 2:
            console.print(f"[yellow]Warning:[/yellow] Unexpected title format in {mp3_file.name}: {title}")
            return None

        section_id = title_parts[0]
        hebrew_text = title_parts[1].strip().rstrip('٭')

        # Generate unique ID (e.g., "L001.S01")
        unique_id = f"{lesson}.{section_id}"

        # Generate lesson tag
        lesson_tag = f"assimil-{lesson_num}"

        # Generate new filename for Anki media
        new_filename = f"{unique_id}.mp3"

        return {
            'id': unique_id,
            'hebrew': hebrew_text,
            'english': 'NA',  # To be filled in manually
            'sound': f'[sound:{new_filename}]',
            'tags': f'assimil {lesson_tag}',
            'lesson': lesson,
            'lesson_num': lesson_num,
            'section_id': section_id,
            'new_filename': new_filename,
            'original_file': str(mp3_file)
        }

    except Exception as e:
        console.print(f"[red]Error processing {mp3_file}:[/red] {e}")
        return None

def copy_audio_to_media(mp3_file: Path, new_filename: str, media_dir: Path) -> bool:
    """
    Copy MP3 file to Anki media directory with new name

    Args:
        mp3_file: Source MP3 file path
        new_filename: New filename for the copy
        media_dir: Anki media directory path

    Returns:
        True if copy successful, False otherwise
    """
    try:
        media_dir.mkdir(parents=True, exist_ok=True)
        dest_path = media_dir / new_filename
        shutil.copy2(mp3_file, dest_path)
        return True
    except Exception as e:
        console.print(f"[red]Error copying {mp3_file} to {new_filename}:[/red] {e}")
        return False

def generate_csv_output(processed_rows: List[Dict], output_path: Path) -> bool:
    """
    Generate CSV file from processed audio metadata

    Args:
        processed_rows: List of dictionaries with processed metadata
        output_path: Path where CSV file should be saved

    Returns:
        True if CSV generation successful, False otherwise
    """
    if not processed_rows:
        console.print("[yellow]No data to write to CSV[/yellow]")
        return False

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Define the CSV fieldnames (matching original structure)
        fieldnames = ['id', 'hebrew', 'english', 'sound', 'tags']

        # Extract only the fields we want for the CSV
        csv_rows = []
        for row in processed_rows:
            csv_row = {
                'id': row['id'],
                'hebrew': row['hebrew'],
                'english': row['english'],  # 'NA' for now
                'sound': row['sound'],
                'tags': row['tags']
            }
            csv_rows.append(csv_row)

        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        console.print(f"[green]✓[/green] CSV file created: {output_path}")
        console.print(f"[dim]Contains {len(csv_rows)} rows[/dim]")

        return True

    except Exception as e:
        console.print(f"[red]Error generating CSV:[/red] {e}")
        return False

def copy_audio_files(processed_rows: List[Dict], media_dir: Path) -> int:
    """
    Copy all processed audio files to Anki media directory

    Args:
        processed_rows: List of dictionaries with processed metadata
        media_dir: Target media directory

    Returns:
        Number of files successfully copied
    """
    if not processed_rows:
        return 0

    console.print(f"[bold blue]Copying {len(processed_rows)} audio files to media directory...[/bold blue]")

    success_count = 0
    for row in processed_rows:
        original_file = Path(row['original_file'])
        new_filename = row['new_filename']

        if copy_audio_to_media(original_file, new_filename, media_dir):
            success_count += 1

    console.print(f"[green]✓[/green] Successfully copied {success_count}/{len(processed_rows)} files")

    return success_count