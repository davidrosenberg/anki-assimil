"""
Complete word matching pipeline that connects lesson words with Anki cards
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from src.word_extraction import WordExtractor, LessonWord, extract_words_from_config
from src.anki_matcher import AnkiMatcher, WordMatch, create_matcher_from_config
from src.anki_api import anki_request
from src.persistence import PersistenceManager, StoredMatch, create_persistence_manager


@dataclass
class LessonWordMatch:
    """Represents a complete match between lesson word and Anki card with tagging info"""
    lesson_word: LessonWord
    word_match: WordMatch
    lesson_tag: str
    should_tag: bool = True


class WordMatchingPipeline:
    """Complete pipeline for matching lesson words to Anki cards and managing tags"""

    def __init__(self, config: dict):
        self.config = config
        self.word_extractor = extract_words_from_config(config)
        self.anki_matcher = create_matcher_from_config(config)
        self.persistence = create_persistence_manager(config)
        self.lesson_matches: Dict[int, List[LessonWordMatch]] = {}

    def process_lessons(self, max_lessons: Optional[int] = None) -> Dict[int, List[LessonWordMatch]]:
        """
        Process lessons and match words to Anki cards

        Args:
            max_lessons: Maximum number of lessons to process

        Returns:
            Dictionary mapping lesson numbers to word matches
        """
        print("Processing lessons and extracting words...")

        # Extract words from lessons
        lessons_data = self.word_extractor.process_lessons_sequential(max_lessons)

        print(f"Extracted words from {len(lessons_data)} lessons")
        print("Word extraction stats:", self.word_extractor.get_word_stats())

        # Match each new word to Anki cards, skipping already processed words
        for lesson_num, lesson_data in lessons_data.items():
            print(f"\nProcessing lesson {lesson_num}...")

            lesson_matches = []
            new_words = self.word_extractor.get_new_words_by_lesson(lesson_num)

            # Filter out already processed words
            unprocessed_words = [
                word for word in new_words
                if not self.persistence.is_word_processed(word.lesson, word.word)
            ]

            skipped_count = len(new_words) - len(unprocessed_words)
            if skipped_count > 0:
                print(f"  Skipped {skipped_count} already-processed words")
            print(f"  Found {len(unprocessed_words)} new words to match")

            for lesson_word in unprocessed_words:
                matches = self.anki_matcher.find_matches(
                    lesson_word.word,
                    max_candidates=self.config['processing'].get('similarity_candidates', 3)
                )

                if matches:
                    # Use best match (first one after sorting)
                    best_match = matches[0]
                    lesson_tag = self._generate_lesson_tag(lesson_num)

                    lesson_word_match = LessonWordMatch(
                        lesson_word=lesson_word,
                        word_match=best_match,
                        lesson_tag=lesson_tag,
                        should_tag=self._should_tag_card(best_match, lesson_tag)
                    )

                    lesson_matches.append(lesson_word_match)

                    print(f"    {lesson_word.word} -> {best_match.anki_card.hebrew} ({best_match.match_type}, score: {best_match.similarity_score})")
                else:
                    # Track unmatched words
                    self.persistence.add_unmatched_word(
                        lesson_num,
                        lesson_word.word,
                        lesson_word.context
                    )
                    print(f"    {lesson_word.word} -> NO MATCH FOUND (saved to unmatched)")

            self.lesson_matches[lesson_num] = lesson_matches

        return self.lesson_matches

    def _generate_lesson_tag(self, lesson_num: int) -> str:
        """Generate lesson tag in consistent format (assimil::LNN)"""
        from .tags import generate_lesson_tag
        return generate_lesson_tag('assimil', lesson_num)

    def _should_tag_card(self, word_match: WordMatch, lesson_tag: str) -> bool:
        """Determine if card should be tagged (avoid duplicate tags)"""
        return lesson_tag not in word_match.anki_card.tags

    def apply_tags_to_anki(self, dry_run: bool = True) -> Dict[str, int]:
        """
        Apply lesson tags to matched Anki cards

        Args:
            dry_run: If True, only show what would be tagged without applying

        Returns:
            Statistics about tagging operation
        """
        stats = {
            'cards_to_tag': 0,
            'cards_already_tagged': 0,
            'tags_applied': 0,
            'errors': 0
        }

        for lesson_num, matches in self.lesson_matches.items():
            print(f"\nLesson {lesson_num} tagging:")

            for match in matches:
                if match.should_tag:
                    stats['cards_to_tag'] += 1
                    card_id = match.word_match.anki_card.card_id
                    tag = match.lesson_tag

                    print(f"  {'[DRY RUN] ' if dry_run else ''}Tag card {card_id} ({match.word_match.anki_card.hebrew}) with '{tag}'")

                    if not dry_run:
                        # Apply tag to card's note
                        try:
                            result = anki_request('addTags', {
                                'notes': [match.word_match.anki_card.note_id],
                                'tags': tag
                            })
                            if result is None:  # AnkiConnect returns None on success
                                stats['tags_applied'] += 1
                            else:
                                stats['errors'] += 1
                                print(f"    ERROR: Failed to tag card {card_id}")
                        except Exception as e:
                            stats['errors'] += 1
                            print(f"    ERROR: {e}")
                else:
                    stats['cards_already_tagged'] += 1
                    print(f"  SKIP: {match.word_match.anki_card.hebrew} already has tag '{match.lesson_tag}'")

        return stats


    def get_matching_summary(self) -> Dict[str, any]:
        """Get summary of matching results"""
        total_matches = sum(len(matches) for matches in self.lesson_matches.values())

        # Count by match type
        exact_matches = 0
        fuzzy_matches = 0

        for matches in self.lesson_matches.values():
            for match in matches:
                if match.word_match.match_type == 'exact':
                    exact_matches += 1
                else:
                    fuzzy_matches += 1

        return {
            'lessons_processed': len(self.lesson_matches),
            'total_word_matches': total_matches,
            'exact_matches': exact_matches,
            'fuzzy_matches': fuzzy_matches,
            'word_extraction_stats': self.word_extractor.get_word_stats(),
            'anki_deck_stats': self.anki_matcher.get_deck_stats(),
            'persistence_stats': self.persistence.get_statistics()
        }

