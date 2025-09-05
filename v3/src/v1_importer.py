"""
Import V1 match data into V3 persistence system
"""

import csv
import re
from pathlib import Path
from typing import List, Dict, Optional

from src.persistence import PersistenceManager, StoredMatch
from src.anki_api import anki_request


def extract_lesson_number(lesson_id: str) -> Optional[int]:
    """Extract lesson number from V1 format ID (L001.S01 -> 1)"""
    match = re.search(r'L(\d+)', lesson_id)
    return int(match.group(1)) if match else None


def find_anki_card_id(hebrew_word: str) -> Optional[int]:
    """Find Anki card ID for Hebrew word using AnkiConnect"""
    try:
        # Search for cards with this Hebrew text
        cards = anki_request('findCards', {
            'query': f'deck:"Hebrew from Scratch" Hebrew:"{hebrew_word}"'
        })

        if cards:
            return cards[0]  # Return first match

        # Try without nikud/punctuation for broader search
        clean_word = re.sub(r'[^\u05d0-\u05ea\s]', '', hebrew_word)
        if clean_word != hebrew_word:
            cards = anki_request('findCards', {
                'query': f'deck:"Hebrew from Scratch" Hebrew:"{clean_word}"'
            })
            if cards:
                return cards[0]

        return None

    except Exception as e:
        print(f"Error finding card for {hebrew_word}: {e}")
        return None


class V1Importer:
    """Import V1 match data into V3 persistence system"""

    def __init__(self, v1_dir: Path = Path("../v1"), target_deck: str = "Hebrew from Scratch"):
        self.v1_dir = Path(v1_dir)
        self.target_deck = target_deck
        self.persistence = PersistenceManager()

    def import_approved_matches(self, dry_run: bool = True) -> Dict[str, int]:
        """
        Import V1 approved matches from assimil-words.csv

        Args:
            dry_run: If True, show what would be imported without saving

        Returns:
            Import statistics
        """
        v1_file = self.v1_dir / "assimil-words.csv"
        if not v1_file.exists():
            print(f"V1 file not found: {v1_file}")
            return {}

        stats = {
            'total_rows': 0,
            'valid_lessons': 0,
            'card_ids_found': 0,
            'card_ids_missing': 0,
            'imported': 0,
            'skipped_existing': 0
        }

        imported_matches = []

        print(f"{'[DRY RUN] ' if dry_run else ''}Importing V1 approved matches...")

        try:
            with open(v1_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    stats['total_rows'] += 1

                    # Extract lesson number
                    lesson_num = extract_lesson_number(row['id'])
                    if not lesson_num:
                        continue

                    stats['valid_lessons'] += 1

                    # Check if already processed
                    if self.persistence.is_word_processed(lesson_num, row['heb_word']):
                        stats['skipped_existing'] += 1
                        print(f"  Skip existing: L{lesson_num:02d} {row['heb_word']}")
                        continue

                    # Try to find Anki card ID
                    card_id = find_anki_card_id(row['match_word'])

                    if card_id:
                        stats['card_ids_found'] += 1

                        # Preserve the Levenshtein score from V1
                        score = int(row.get('Levensht', 0))

                        stored_match = StoredMatch(
                            lesson=lesson_num,
                            heb_word=row['heb_word'],
                            anki_hebrew=row['match_word'],
                            anki_english=row['match_word_def'],
                            card_id=card_id,
                            match_type='v1_import',
                            score=score
                        )
                        imported_matches.append(stored_match)
                        stats['imported'] += 1

                        print(f"  Import: L{lesson_num:02d} {row['heb_word']} -> {row['match_word']} (card:{card_id})")
                    else:
                        stats['card_ids_missing'] += 1
                        print(f"  Missing card: L{lesson_num:02d} {row['heb_word']} -> {row['match_word']}")

            # Save imported matches
            if imported_matches and not dry_run:
                success = self.persistence.save_approved_matches(imported_matches)
                if success:
                    print(f"✓ Saved {len(imported_matches)} V1 matches to persistence")
                else:
                    print("✗ Failed to save V1 matches")

            return stats

        except Exception as e:
            print(f"Error importing V1 matches: {e}")
            return stats

    def import_extra_matches(self, dry_run: bool = True) -> Dict[str, int]:
        """
        Import V1 extra matches from assimil-words-extra.csv

        Args:
            dry_run: If True, show what would be imported without saving

        Returns:
            Import statistics
        """
        v1_file = self.v1_dir / "assimil-words-extra.csv"
        if not v1_file.exists():
            print(f"V1 extra file not found: {v1_file}")
            return {}

        stats = {
            'total_rows': 0,
            'valid_lessons': 0,
            'card_ids_found': 0,
            'imported': 0
        }

        print(f"{'[DRY RUN] ' if dry_run else ''}Importing V1 extra matches...")

        # Read current extra matches to avoid duplicates
        extra_matches = []

        try:
            with open(v1_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    stats['total_rows'] += 1

                    lesson_num = int(row['Lesson'])
                    hebrew_word = row['AnkiID']

                    stats['valid_lessons'] += 1

                    # Try to find card ID
                    card_id = find_anki_card_id(hebrew_word)

                    if card_id:
                        stats['card_ids_found'] += 1
                        stats['imported'] += 1

                        # Add to V3 extra file format
                        extra_match = {
                            'lesson': lesson_num,
                            'heb_word': hebrew_word,
                            'card_id': card_id,
                            'notes': f'V1 import'
                        }
                        extra_matches.append(extra_match)

                        print(f"  Import extra: L{lesson_num:02d} {hebrew_word} (card:{card_id})")
                    else:
                        print(f"  Missing card: L{lesson_num:02d} {hebrew_word}")

            # Append to V3 extra file
            if extra_matches and not dry_run:
                extra_file = self.persistence.extra_file

                # Write/append to extra file
                mode = 'a' if extra_file.exists() else 'w'
                with open(extra_file, mode, newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['lesson', 'heb_word', 'card_id', 'notes'])
                    if mode == 'w':
                        writer.writeheader()
                    writer.writerows(extra_matches)

                print(f"✓ Added {len(extra_matches)} V1 extra matches to {extra_file}")

            return stats

        except Exception as e:
            print(f"Error importing V1 extra matches: {e}")
            return stats

    def import_all(self, dry_run: bool = True) -> Dict[str, any]:
        """Import all V1 data"""
        print("="*60)
        print("V1 DATA IMPORT")
        print("="*60)

        approved_stats = self.import_approved_matches(dry_run)
        extra_stats = self.import_extra_matches(dry_run)

        total_stats = {
            'approved_matches': approved_stats,
            'extra_matches': extra_stats,
            'total_imported': approved_stats.get('imported', 0) + extra_stats.get('imported', 0)
        }

        print(f"\nV1 IMPORT SUMMARY:")
        print(f"Approved matches: {approved_stats.get('imported', 0)}")
        print(f"Extra matches: {extra_stats.get('imported', 0)}")
        print(f"Total imported: {total_stats['total_imported']}")

        if dry_run:
            print(f"\n[DRY RUN] Use --no-dry-run to actually import")

        return total_stats


def import_v1_data(dry_run: bool = True) -> Dict[str, any]:
    """Convenience function to import V1 data"""
    importer = V1Importer()
    return importer.import_all(dry_run)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import V1 match data into V3")
    parser.add_argument("--no-dry-run", action="store_true", help="Actually import data")
    args = parser.parse_args()

    import_v1_data(dry_run=not args.no_dry_run)