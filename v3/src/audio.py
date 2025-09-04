"""
Audio processing module for Anki-Assimil V3
Handles scanning MP3 files and incremental extraction
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from rich.console import Console
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import shutil
import csv

console = Console()

def load_existing_translations(csv_path: Path) -> Set[str]:
    """
    Load existing lesson IDs from assimil.csv to avoid regenerating
    
    Args:
        csv_path: Path to existing assimil.csv file
        
    Returns:
        Set of lesson IDs that already have translations
    """
    existing_ids = set()
    
    if not csv_path.exists():
        console.print(f"[yellow]No existing translations found at {csv_path}[/yellow]")
        return existing_ids
        
    try:
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('english') and row['english'] != 'NA':
                    existing_ids.add(row['id'])
        
        console.print(f"[green]✓[/green] Found {len(existing_ids)} existing translations")
        return existing_ids
        
    except Exception as e:
        console.print(f"[red]Error loading existing translations:[/red] {e}")
        return existing_ids

def scan_lesson_directories(base_dir: Path, max_lessons: int = 20) -> List[Path]:
    """
    Scan for lesson directories (starting with 'L') in the base directory
    """
    if not base_dir.exists():
        console.print(f"[red]Error:[/red] Base directory not found: {base_dir}")
        return []
    
    lesson_dirs = [d for d in base_dir.iterdir() 
                   if d.is_dir() and d.name.startswith('L')]
    
    lesson_dirs.sort(key=lambda d: d.name)
    limited_dirs = lesson_dirs[:max_lessons]
    
    console.print(f"[green]Found {len(lesson_dirs)} lesson directories, processing first {len(limited_dirs)}[/green]")
    
    return limited_dirs

def scan_mp3_files(lesson_dir: Path, skip_files: List[str] = None) -> List[Path]:
    """
    Scan a lesson directory for MP3 files
    """
    if skip_files is None:
        skip_files = ['T00-TRANSLATE.mp3']
    
    if not lesson_dir.exists():
        console.print(f"[yellow]Warning:[/yellow] Lesson directory not found: {lesson_dir}")
        return []
    
    mp3_files = [f for f in lesson_dir.iterdir() 
                 if f.is_file() and f.suffix.lower() == '.mp3']
    
    filtered_files = [f for f in mp3_files if f.name not in skip_files]
    filtered_files.sort(key=lambda f: f.name)
    
    console.print(f"  [dim]{lesson_dir.name}:[/dim] Found {len(filtered_files)} MP3 files")
    
    return filtered_files

def extract_mp3_metadata(mp3_file: Path) -> Optional[Dict[str, str]]:
    """
    Extract metadata from an MP3 file
    """
    try:
        audio = MP3(str(mp3_file), ID3=EasyID3)
        
        title = audio.get('title', [''])[0] if 'title' in audio else ''
        album = audio.get('album', [''])[0] if 'album' in audio else ''
        
        if not title or not album:
            console.print(f"[yellow]Warning:[/yellow] Missing metadata in {mp3_file.name}")
            return None
            
        # Parse lesson info from album
        lesson = album.split(' - ')[-1] if ' - ' in album else album
        lesson_num = lesson[2:] if lesson.startswith('L') else lesson
        
        # Parse title and clean Hebrew text
        title_parts = title.split('-', 1)
        if len(title_parts) < 2:
            console.print(f"[yellow]Warning:[/yellow] Unexpected title format in {mp3_file.name}: {title}")
            return None
            
        section_id = title_parts[0]
        hebrew_text = title_parts[1].strip().rstrip('٭')  # Remove Arabic asterisk
        
        # Generate unique ID
        unique_id = f"{lesson}.{section_id}"
        lesson_tag = f"assimil-{lesson_num}"
        new_filename = f"{unique_id}.mp3"
        
        return {
            'id': unique_id,
            'hebrew': hebrew_text,
            'english': 'NA',
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

def extract_audio_incremental(config: Dict) -> List[Dict]:
    """
    Extract audio files, but only for lessons not already translated
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of new lesson data that needs translation
    """
    paths = config['paths']
    processing = config['processing']
    
    # Check for existing translations
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    existing_csv = data_dir / "assimil.csv"
    existing_ids = load_existing_translations(existing_csv)
    
    base_dir = Path(paths['assimil_course_dir'])
    max_lessons = processing.get('max_lessons', 20)
    skip_files = processing.get('skip_files', ['T00-TRANSLATE.mp3'])
    
    console.print(f"[bold blue]Scanning audio files in:[/bold blue] {base_dir}")
    
    # Scan for all audio files
    lesson_dirs = scan_lesson_directories(base_dir, max_lessons)
    
    all_files = []
    for lesson_dir in lesson_dirs:
        mp3_files = scan_mp3_files(lesson_dir, skip_files)
        for mp3_file in mp3_files:
            all_files.append((lesson_dir, mp3_file))
    
    # Process files and filter out existing translations
    new_lessons = []
    skipped_count = 0
    
    for lesson_dir, mp3_file in all_files:
        metadata = extract_mp3_metadata(mp3_file)
        if metadata:
            if metadata['id'] in existing_ids:
                skipped_count += 1
                continue
                
            new_lessons.append(metadata)
            console.print(f"  ✓ NEW: {metadata['id']}: {metadata['hebrew'][:50]}...")
        else:
            console.print(f"  ✗ Failed to process: {mp3_file.name}")
    
    console.print(f"\n[green]✓[/green] Found {len(new_lessons)} new lessons to translate")
    console.print(f"[dim]Skipped {skipped_count} already translated lessons[/dim]")
    
    return new_lessons

def generate_init_csv(new_lessons: List[Dict], output_path: Path) -> bool:
    """
    Generate assimil-init.csv with only new lessons
    """
    if not new_lessons:
        console.print("[yellow]No new lessons to generate[/yellow]")
        return False
        
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = ['id', 'hebrew', 'english', 'sound', 'tags']
        
        csv_rows = []
        for lesson in new_lessons:
            csv_row = {
                'id': lesson['id'],
                'hebrew': lesson['hebrew'],
                'english': lesson['english'],  # 'NA'
                'sound': lesson['sound'],
                'tags': lesson['tags']
            }
            csv_rows.append(csv_row)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        
        console.print(f"[green]✓[/green] Generated init file: {output_path}")
        console.print(f"[dim]Contains {len(csv_rows)} new lessons for translation[/dim]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error generating init CSV:[/red] {e}")
        return False

def copy_audio_files(new_lessons: List[Dict], media_dir: Path) -> int:
    """
    Copy new audio files to Anki media directory
    """
    if not new_lessons:
        return 0
        
    console.print(f"[bold blue]Copying {len(new_lessons)} audio files...[/bold blue]")
    
    media_dir.mkdir(parents=True, exist_ok=True)
    success_count = 0
    
    for lesson in new_lessons:
        try:
            original_file = Path(lesson['original_file'])
            dest_path = media_dir / lesson['new_filename']
            shutil.copy2(original_file, dest_path)
            success_count += 1
        except Exception as e:
            console.print(f"[red]Error copying {lesson['new_filename']}:[/red] {e}")
    
    console.print(f"[green]✓[/green] Copied {success_count}/{len(new_lessons)} audio files")
    return success_count