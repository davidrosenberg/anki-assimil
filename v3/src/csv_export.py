"""
CSV export system for human review of word matches
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# Imports handled in functions to avoid circular imports


@dataclass
class MatchSuggestion:
    """Single match suggestion for CSV export"""
    lesson: int               # Lesson number
    heb_word: str             # Original Hebrew word from lesson
    match_word: str           # Matched Hebrew word from Anki
    match_word_def: str       # English definition from Anki
    score: int                # Similarity score (0=exact, higher=worse)
    card_id: int              # Anki card ID for reference


class CSVExporter:
    """Exports word matches to CSV for human review"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        
    def generate_match_suggestions(self, max_candidates_per_word: int = 3) -> List[MatchSuggestion]:
        """
        Generate all match suggestions for CSV export
        
        Args:
            max_candidates_per_word: Maximum match candidates to show per word
            
        Returns:
            List of MatchSuggestion objects
        """
        suggestions = []
        
        for lesson_num in sorted(self.pipeline.lesson_matches.keys()):
            lesson_matches = self.pipeline.lesson_matches[lesson_num]
            
            for lesson_match in lesson_matches:
                lesson_word = lesson_match.lesson_word
                
                # Get multiple match candidates for this word
                all_matches = self.pipeline.anki_matcher.find_matches(
                    lesson_word.word, 
                    max_candidates=max_candidates_per_word
                )
                
                # Generate suggestions for each match candidate
                for match in all_matches:
                    suggestion = MatchSuggestion(
                        lesson=lesson_num,
                        heb_word=lesson_word.word,
                        match_word=match.anki_card.hebrew,
                        match_word_def=match.anki_card.english,
                        score=match.similarity_score,
                        card_id=match.anki_card.card_id
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def export_to_csv(self, output_path: Path, max_candidates_per_word: int = 3) -> bool:
        """
        Export match suggestions to CSV file
        
        Args:
            output_path: Path to output CSV file
            max_candidates_per_word: Max candidates per word
            
        Returns:
            True if export successful
        """
        suggestions = self.generate_match_suggestions(max_candidates_per_word)
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Simplified header for human review
                writer.writerow([
                    'lesson', 'heb_word', 'match_word', 'match_word_def', 'score', 'card_id'
                ])
                
                # Write all suggestions
                for suggestion in suggestions:
                    writer.writerow([
                        suggestion.lesson,
                        suggestion.heb_word,
                        suggestion.match_word,
                        suggestion.match_word_def,
                        suggestion.score,
                        suggestion.card_id,
                    ])
            
            print(f"Exported {len(suggestions)} match suggestions to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False
    
    def print_export_summary(self, suggestions: List[MatchSuggestion]):
        """Print summary of exported suggestions"""
        # Group by lesson
        by_lesson = {}
        for suggestion in suggestions:
            lesson = f"L{suggestion.lesson:03d}"
            if lesson not in by_lesson:
                by_lesson[lesson] = []
            by_lesson[lesson].append(suggestion)
        
        print("\nEXPORT SUMMARY:")
        print("-" * 40)
        
        total_words = len(set(s.heb_word for s in suggestions))
        exact_matches = len([s for s in suggestions if s.score == 0])
        fuzzy_matches = len([s for s in suggestions if s.score > 0])
        
        print(f"Total unique words: {total_words}")
        print(f"Total suggestions: {len(suggestions)}")
        print(f"  - Exact matches: {exact_matches}")
        print(f"  - Fuzzy matches: {fuzzy_matches}")
        print()
        
        for lesson in sorted(by_lesson.keys()):
            lesson_suggestions = by_lesson[lesson]
            unique_words = len(set(s.heb_word for s in lesson_suggestions))
            print(f"{lesson}: {unique_words} words, {len(lesson_suggestions)} suggestions")


class CSVImporter:
    """Imports human-reviewed matches from CSV"""
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        
    def load_approved_matches(self, csv_path: Path) -> List[MatchSuggestion]:
        """
        Load human-approved matches from CSV
        
        Args:
            csv_path: Path to reviewed CSV file
            
        Returns:
            List of approved MatchSuggestion objects
        """
        approved_matches = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Any row present in CSV is considered approved
                    suggestion = MatchSuggestion(
                        lesson=int(row['lesson']),
                        heb_word=row['heb_word'],
                        match_word=row['match_word'],
                        match_word_def=row['match_word_def'],
                        score=int(row['score']),
                        card_id=int(row['card_id']),
                    )
                    approved_matches.append(suggestion)
            
            print(f"Loaded {len(approved_matches)} approved matches from {csv_path}")
            return approved_matches
            
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return []
    
    def apply_approved_matches(self, approved_matches: List[MatchSuggestion], dry_run: bool = True) -> Dict[str, int]:
        """
        Apply approved matches by adding tags to Anki cards
        
        Args:
            approved_matches: List of human-approved matches
            dry_run: If True, show what would be tagged
            
        Returns:
            Statistics about tagging operation
        """
        from src.anki_api import anki_request
        
        stats = {
            'cards_to_tag': 0,
            'tags_applied': 0,
            'errors': 0
        }
        
        # Group by lesson for consistent tagging
        by_lesson = {}
        for match in approved_matches:
            lesson_num = match.lesson
            lesson_tag = f"assimil::lesson{lesson_num:02d}"
            
            if lesson_num not in by_lesson:
                by_lesson[lesson_num] = []
            by_lesson[lesson_num].append((match, lesson_tag))
        
        print(f"\n{'DRY RUN: ' if dry_run else ''}Applying approved matches:")
        
        for lesson_num in sorted(by_lesson.keys()):
            lesson_matches = by_lesson[lesson_num]
            print(f"\nLesson {lesson_num}:")
            
            for match, lesson_tag in lesson_matches:
                stats['cards_to_tag'] += 1
                
                print(f"  {'[DRY RUN] ' if dry_run else ''}Tag card {match.card_id} ({match.match_word}) with '{lesson_tag}'")
                print(f"    Word: {match.heb_word} -> {match.match_word} (score: {match.score})")
                
                if not dry_run:
                    try:
                        # Get the note ID for this card
                        card_info = anki_request('cardsInfo', {'cards': [match.card_id]})
                        if card_info:
                            note_id = card_info[0]['note']
                            
                            # Add tag to note
                            result = anki_request('addTags', {
                                'notes': [note_id],
                                'tags': lesson_tag
                            })
                            
                            if result is None:  # Success
                                stats['tags_applied'] += 1
                            else:
                                stats['errors'] += 1
                                print(f"    ERROR: Failed to tag card")
                        else:
                            stats['errors'] += 1
                            print(f"    ERROR: Could not find card info")
                            
                    except Exception as e:
                        stats['errors'] += 1
                        print(f"    ERROR: {e}")
        
        return stats


def export_word_matches(config: dict, max_lessons: Optional[int] = None, 
                       output_file: str = "data/assimil-words-init.csv",
                       max_candidates: int = 3) -> bool:
    """
    Complete workflow: extract words, match, and export to CSV for human review
    
    Args:
        config: Configuration dictionary
        max_lessons: Maximum lessons to process
        output_file: Output CSV file path
        max_candidates: Max match candidates per word
        
    Returns:
        True if successful
    """
    from src.word_matching import WordMatchingPipeline
    
    # Run matching pipeline
    print("Running word matching pipeline...")
    pipeline = WordMatchingPipeline(config)
    pipeline.process_lessons(max_lessons)
    
    # Export to CSV
    exporter = CSVExporter(pipeline)
    output_path = Path(output_file)
    
    success = exporter.export_to_csv(output_path, max_candidates)
    
    if success:
        suggestions = exporter.generate_match_suggestions(max_candidates)
        exporter.print_export_summary(suggestions)
        
        print(f"\nNext steps:")
        print(f"1. Review {output_path} and delete unwanted rows or copy/paste the ones you want to keep")
        print(f"2. Copy/paste approved rows to 'data/assimil-words.csv'")
        print(f"3. Run 'apply-tags data/assimil-words.csv' to tag Anki cards")
    
    return success


if __name__ == "__main__":
    import yaml
    
    with open("config.yaml") as f:
        config = yaml.safe_load(f)
    
    # Export matches for first 2 lessons
    export_word_matches(config, max_lessons=2, max_candidates=3)