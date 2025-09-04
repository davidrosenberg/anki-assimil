"""
Word matching module for Anki-Assimil
Handles Hebrew tokenization and vocabulary matching
"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rich.console import Console
import csv
import pandas as pd
import Levenshtein
from queue import PriorityQueue
import hebtokenizer

console = Console()

def load_anki_vocabulary(anki_export_path: Path) -> Tuple[Dict[str, Dict], List[str]]:
    """
    Load vocabulary from Anki export file
    
    Args:
        anki_export_path: Path to alldecks.txt (Anki export)
        
    Returns:
        Tuple of (anki_dict, wordlist) where:
        - anki_dict: Dict mapping Hebrew words to their definitions
        - wordlist: List of Hebrew vocabulary words
    """
    if not anki_export_path.exists():
        console.print(f"[red]Error:[/red] Anki export file not found: {anki_export_path}")
        return {}, []
        
    try:
        anki_dict = {}
        wordlist = []
        
        # Define expected headers (from original code)
        headers = ['Hebrew', 'Definition', 'Gender', 'PartOfSpeech', 
                  'Shoresh', 'Audio', 'Inflections', 'Extended', 'Image', 'Tags']
        
        with open(anki_export_path, 'r', encoding='utf-8') as tsvfile:
            reader = csv.DictReader(tsvfile, fieldnames=headers, delimiter='\t')
            
            for row in reader:
                hebrew_word = row['Hebrew'].strip()
                if hebrew_word:
                    anki_dict[hebrew_word] = row
                    wordlist.append(hebrew_word)
        
        console.print(f"[green]✓[/green] Loaded {len(wordlist)} vocabulary words from Anki export")
        return anki_dict, wordlist
        
    except Exception as e:
        console.print(f"[red]Error loading Anki vocabulary:[/red] {e}")
        return {}, []

def load_translations(translations_path: Path) -> Dict[str, Dict]:
    """
    Load existing translations from working CSV file
    
    Args:
        translations_path: Path to assimil.csv with translations
        
    Returns:
        Dictionary mapping lesson IDs to translation data
    """
    if not translations_path.exists():
        console.print(f"[yellow]Warning:[/yellow] Translations file not found: {translations_path}")
        return {}
        
    try:
        translations = {}
        with open(translations_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['english'] and row['english'] != 'NA':
                    translations[row['id']] = row
        
        console.print(f"[green]✓[/green] Loaded {len(translations)} translations")
        return translations
        
    except Exception as e:
        console.print(f"[red]Error loading translations:[/red] {e}")
        return {}

def tokenize_hebrew_text(hebrew_text: str) -> List[str]:
    """
    Tokenize Hebrew text using the existing tokenizer
    
    Args:
        hebrew_text: Hebrew text to tokenize
        
    Returns:
        List of Hebrew words (tokens marked as 'HEB')
    """
    try:
        # Use the existing Hebrew tokenizer
        tokenized = hebtokenizer.tokenize(hebrew_text)
        
        # Extract only Hebrew words (tokens marked with 'HEB')
        hebrew_words = [token for token_type, token in tokenized if token_type == 'HEB']
        
        return hebrew_words
        
    except Exception as e:
        console.print(f"[red]Error tokenizing Hebrew text '{hebrew_text}':[/red] {e}")
        return []

def find_word_matches(hebrew_word: str, wordlist: List[str], 
                     anki_dict: Dict[str, Dict], max_distance: int = 5, 
                     num_candidates: int = 2) -> List[Dict]:
    """
    Find matching vocabulary words using Levenshtein distance
    
    Args:
        hebrew_word: Hebrew word to match
        wordlist: List of vocabulary words to match against
        anki_dict: Dictionary with word definitions
        max_distance: Maximum Levenshtein distance to consider
        num_candidates: Number of top candidates to return
        
    Returns:
        List of matching candidates with metadata
    """
    if not hebrew_word or not wordlist:
        return []
        
    try:
        # Use priority queue to find closest matches
        pq = PriorityQueue()
        
        for vocab_word in wordlist:
            distance = Levenshtein.distance(hebrew_word, vocab_word)
            if distance <= max_distance:
                pq.put((distance, vocab_word))
        
        # Extract top candidates
        matches = []
        count = 0
        while not pq.empty() and count < num_candidates:
            distance, vocab_word = pq.get()
            
            match_info = {
                'heb_word': hebrew_word,
                'match_word': vocab_word,
                'match_word_def': anki_dict.get(vocab_word, {}).get('Definition', ''),
                'levenshtein_distance': distance
            }
            matches.append(match_info)
            count += 1
        
        return matches
        
    except Exception as e:
        console.print(f"[red]Error finding matches for '{hebrew_word}':[/red] {e}")
        return []

def process_lesson_text(lesson_id: str, hebrew_text: str, english_text: str,
                       wordlist: List[str], anki_dict: Dict[str, Dict],
                       max_distance: int = 5, num_candidates: int = 2) -> List[Dict]:
    """
    Process a single lesson text and generate word matches
    
    Args:
        lesson_id: Lesson identifier (e.g., 'L001.S01')
        hebrew_text: Hebrew text to process
        english_text: English translation
        wordlist: Vocabulary word list
        anki_dict: Vocabulary definitions
        max_distance: Maximum Levenshtein distance
        num_candidates: Number of candidates per word
        
    Returns:
        List of word match suggestions
    """
    # Tokenize Hebrew text
    hebrew_words = tokenize_hebrew_text(hebrew_text)
    
    if not hebrew_words:
        return []
    
    # Generate matches for each Hebrew word
    all_matches = []
    for hebrew_word in hebrew_words:
        matches = find_word_matches(hebrew_word, wordlist, anki_dict, 
                                  max_distance, num_candidates)
        
        # Add lesson context to each match
        for match in matches:
            match['id'] = lesson_id
            match['eng_text'] = english_text
            all_matches.append(match)
    
    return all_matches

def generate_word_matches(config: Dict) -> bool:
    """
    Generate word matching suggestions for all lesson content
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if successful, False otherwise
    """
    paths = config['paths']
    processing = config['processing']
    
    # Load data
    input_dir = Path(paths['input_dir'])
    data_dir = Path(paths['data_dir'])
    generated_dir = Path(paths['generated_dir'])
    
    console.print("[bold blue]Loading vocabulary and translations...[/bold blue]")
    
    # Load Anki vocabulary
    anki_export_path = input_dir / paths['anki_export_file']
    anki_dict, wordlist = load_anki_vocabulary(anki_export_path)
    
    if not wordlist:
        console.print("[red]Cannot proceed without vocabulary data[/red]")
        return False
    
    # Load existing translations
    translations_path = data_dir / paths['translations_file']
    translations = load_translations(translations_path)
    
    if not translations:
        console.print("[yellow]No translations found - using generated data[/yellow]")
        # Try to load from generated directory if data doesn't exist
        generated_init_path = generated_dir / 'assimil-init.csv'
        if generated_init_path.exists():
            translations = load_translations(generated_init_path)
    
    if not translations:
        console.print("[red]No lesson data found to process[/red]")
        return False
    
    # Process each translation
    console.print(f"[bold blue]Processing {len(translations)} lessons for word matching...[/bold blue]")
    
    all_matches = []
    max_distance = processing.get('word_match_threshold', 5)
    num_candidates = processing.get('similarity_candidates', 2)
    
    for lesson_id, lesson_data in translations.items():
        hebrew_text = lesson_data['hebrew']
        english_text = lesson_data.get('english', 'NA')
        
        # Skip if no Hebrew text
        if not hebrew_text or hebrew_text == 'NA':
            continue
            
        # Process this lesson
        matches = process_lesson_text(
            lesson_id, hebrew_text, english_text,
            wordlist, anki_dict, max_distance, num_candidates
        )
        
        all_matches.extend(matches)
        
        if matches:
            console.print(f"  ✓ {lesson_id}: Found {len(matches)} word matches")
        else:
            console.print(f"  - {lesson_id}: No matches found")
    
    if not all_matches:
        console.print("[yellow]No word matches generated[/yellow]")
        return False
    
    # Generate CSV output in generated directory for review
    generated_dir = Path(paths['generated_dir'])
    output_path = generated_dir / 'assimil-words-init.csv'
    return generate_matches_csv(all_matches, output_path)

def generate_matches_csv(matches: List[Dict], output_path: Path) -> bool:
    """
    Generate CSV file with word matching suggestions
    
    Args:
        matches: List of word match dictionaries
        output_path: Path where CSV should be saved
        
    Returns:
        True if successful, False otherwise
    """
    if not matches:
        console.print("[yellow]No matches to write to CSV[/yellow]")
        return False
        
    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Define CSV fieldnames (matching original structure)
        fieldnames = ['id', 'eng_text', 'heb_word', 'match_word', 'match_word_def', 'Levensht']
        
        # Prepare rows for CSV
        csv_rows = []
        for match in matches:
            csv_row = {
                'id': match['id'],
                'eng_text': match['eng_text'],
                'heb_word': match['heb_word'],
                'match_word': match['match_word'],
                'match_word_def': match['match_word_def'],
                'Levensht': match['levenshtein_distance']
            }
            csv_rows.append(csv_row)
        
        # Write CSV file
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        
        console.print(f"[green]✓[/green] Word matching suggestions created: {output_path}")
        console.print(f"[dim]Contains {len(csv_rows)} word matches for manual review[/dim]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]Error generating matches CSV:[/red] {e}")
        return False