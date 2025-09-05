"""
Persistent storage system for word matches and processing state
Similar to V2's approach with approved matches, extra matches, and unmatched tracking
"""

import csv
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass

from src.tokenizer import normalize_hebrew_word


@dataclass
class StoredMatch:
    """Represents a stored word match"""
    lesson: int
    heb_word: str
    anki_hebrew: str
    anki_english: str
    card_id: int
    match_type: str = "approved"  # approved, extra, manual
    score: int = 0  # Similarity score (Levenshtein distance)


@dataclass
class UnmatchedWord:
    """Represents a word that couldn't be matched"""
    lesson: int
    heb_word: str
    context: str
    attempts: int = 1


class PersistenceManager:
    """Manages persistent storage of word matching state"""

    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # File paths
        self.approved_file = self.data_dir / "assimil-words.csv"
        self.extra_file = self.data_dir / "assimil-words-extra.csv"
        self.unmatched_file = self.data_dir / "assimil-words-unmatched.csv"

        # In-memory storage
        self.approved_matches: Dict[str, StoredMatch] = {}
        self.extra_matches: Dict[str, StoredMatch] = {}
        self.unmatched_words: Dict[str, UnmatchedWord] = {}

        # Load existing data
        self._load_all_files()

    def _load_all_files(self):
        """Load all persistent files into memory"""
        self._load_approved_matches()
        self._load_extra_matches()
        self._load_unmatched_words()

        total_stored = len(self.approved_matches) + len(self.extra_matches)
        print(f"Loaded {total_stored} stored matches, {len(self.unmatched_words)} unmatched words")

    def _load_approved_matches(self):
        """Load human-approved matches"""
        if not self.approved_file.exists():
            return

        try:
            with open(self.approved_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = self._make_word_key(int(row['lesson']), row['heb_word'])
                    # Handle both old format (no score) and new format (with score)
                    score = int(row.get('score', 0))  # Default to 0 if no score column

                    match = StoredMatch(
                        lesson=int(row['lesson']),
                        heb_word=row['heb_word'],
                        anki_hebrew=row['match_word'],
                        anki_english=row['match_word_def'],
                        card_id=int(row['card_id']),
                        match_type='approved',
                        score=score
                    )
                    self.approved_matches[key] = match

        except Exception as e:
            print(f"Error loading approved matches: {e}")

    def _load_extra_matches(self):
        """Load manually added extra matches (V2 style)"""
        if not self.extra_file.exists():
            return

        try:
            with open(self.extra_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lesson = int(row.get('Lesson', row.get('lesson', 0)))
                    hebrew = row.get('AnkiID', row.get('heb_word', ''))

                    if lesson and hebrew:
                        key = self._make_word_key(lesson, hebrew)
                        match = StoredMatch(
                            lesson=lesson,
                            heb_word=hebrew,
                            anki_hebrew=hebrew,  # For extra matches, assume direct mapping
                            anki_english="(manual entry)",
                            card_id=0,  # Unknown card ID for manual entries
                            match_type='extra'
                        )
                        self.extra_matches[key] = match

        except Exception as e:
            print(f"Error loading extra matches: {e}")

    def _load_unmatched_words(self):
        """Load words that couldn't be matched"""
        if not self.unmatched_file.exists():
            return

        try:
            with open(self.unmatched_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = self._make_word_key(int(row['lesson']), row['heb_word'])
                    unmatched = UnmatchedWord(
                        lesson=int(row['lesson']),
                        heb_word=row['heb_word'],
                        context=row.get('context', ''),
                        attempts=int(row.get('attempts', 1))
                    )
                    self.unmatched_words[key] = unmatched

        except Exception as e:
            print(f"Error loading unmatched words: {e}")

    def _make_word_key(self, lesson: int, heb_word: str) -> str:
        """Create unique key for word+lesson combination"""
        normalized = normalize_hebrew_word(heb_word)
        return f"L{lesson:03d}:{normalized}"

    def is_word_processed(self, lesson: int, heb_word: str) -> bool:
        """Check if word has already been processed (approved, extra, or marked unmatched)"""
        key = self._make_word_key(lesson, heb_word)
        return (key in self.approved_matches or
                key in self.extra_matches or
                key in self.unmatched_words)

    def get_processed_words(self) -> Set[str]:
        """Get all processed word keys to filter suggestions"""
        processed = set()
        processed.update(self.approved_matches.keys())
        processed.update(self.extra_matches.keys())
        processed.update(self.unmatched_words.keys())
        return processed

    def save_approved_matches(self, matches: List[StoredMatch]) -> bool:
        """Save approved matches to CSV"""
        try:
            # Merge new matches with existing
            for match in matches:
                key = self._make_word_key(match.lesson, match.heb_word)
                self.approved_matches[key] = match

            # Write all approved matches
            with open(self.approved_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['lesson', 'heb_word', 'match_word', 'match_word_def', 'score', 'card_id'])

                for match in self.approved_matches.values():
                    writer.writerow([
                        match.lesson,
                        match.heb_word,
                        match.anki_hebrew,
                        match.anki_english,
                        match.score,
                        match.card_id
                    ])

            print(f"Saved {len(self.approved_matches)} approved matches to {self.approved_file}")
            return True

        except Exception as e:
            print(f"Error saving approved matches: {e}")
            return False

    def add_unmatched_word(self, lesson: int, heb_word: str, context: str = "") -> bool:
        """Add a word that couldn't be matched"""
        key = self._make_word_key(lesson, heb_word)

        if key in self.unmatched_words:
            # Increment attempts
            self.unmatched_words[key].attempts += 1
        else:
            # New unmatched word
            self.unmatched_words[key] = UnmatchedWord(
                lesson=lesson,
                heb_word=heb_word,
                context=context,
                attempts=1
            )

        return self._save_unmatched_words()

    def _save_unmatched_words(self) -> bool:
        """Save unmatched words to CSV"""
        try:
            with open(self.unmatched_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['lesson', 'heb_word', 'context', 'attempts'])

                for unmatched in self.unmatched_words.values():
                    writer.writerow([
                        unmatched.lesson,
                        unmatched.heb_word,
                        unmatched.context,
                        unmatched.attempts
                    ])

            return True

        except Exception as e:
            print(f"Error saving unmatched words: {e}")
            return False

    def create_extra_matches_template(self) -> bool:
        """Create template file for manual extra matches"""
        if self.extra_file.exists():
            print(f"Extra matches file already exists: {self.extra_file}")
            return True

        try:
            with open(self.extra_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['lesson', 'heb_word', 'card_id', 'notes'])
                writer.writerow(['1', 'שלום', '1234567890', 'Manual match example'])

            print(f"Created extra matches template: {self.extra_file}")
            print("Add manual matches in format: lesson,heb_word,card_id,notes")
            return True

        except Exception as e:
            print(f"Error creating extra matches template: {e}")
            return False

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about stored data"""
        return {
            'approved_matches': len(self.approved_matches),
            'extra_matches': len(self.extra_matches),
            'unmatched_words': len(self.unmatched_words),
            'total_processed': len(self.get_processed_words())
        }

    def print_status(self):
        """Print current status of persistent storage"""
        stats = self.get_statistics()

        print("\nPERSISTENT STORAGE STATUS:")
        print("-" * 40)
        print(f"Approved matches: {stats['approved_matches']}")
        print(f"Extra matches: {stats['extra_matches']}")
        print(f"Unmatched words: {stats['unmatched_words']}")
        print(f"Total processed: {stats['total_processed']}")

        print(f"\nFiles:")
        print(f"  Approved: {self.approved_file}")
        print(f"  Extra: {self.extra_file}")
        print(f"  Unmatched: {self.unmatched_file}")


def create_persistence_manager(config: dict) -> PersistenceManager:
    """Create PersistenceManager from configuration"""
    data_dir = Path("data")  # Always use local data directory
    return PersistenceManager(data_dir)


if __name__ == "__main__":
    # Test persistence manager
    pm = PersistenceManager()
    pm.create_extra_matches_template()
    pm.print_status()

    # Test adding unmatched word
    pm.add_unmatched_word(1, "בוקר", "Good morning context")
    pm.print_status()