"""
Anki card matching system for Hebrew words using fuzzy matching
"""

import re
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from Levenshtein import distance as levenshtein_distance

from src.anki_api import anki_request
from src.tokenizer import normalize_hebrew_word
from src.deck_cache import DeckCache


@dataclass
class AnkiCard:
    """Represents an Anki card with relevant fields"""
    card_id: int
    note_id: int
    hebrew: str
    english: str
    normalized_hebrew: str
    tags: List[str]
    fields: Dict[str, str]  # All fields for reference


@dataclass
class WordMatch:
    """Represents a match between lesson word and Anki card"""
    lesson_word: str
    normalized_word: str
    anki_card: AnkiCard
    similarity_score: int  # Levenshtein distance (lower = better)
    match_type: str  # 'exact', 'normalized', 'fuzzy'


class AnkiMatcher:
    """Matches Hebrew words against Anki deck using fuzzy matching with persistent cache"""

    def __init__(self, deck_name: str, similarity_threshold: int = 3, use_cache: bool = True):
        self.deck_name = deck_name
        self.similarity_threshold = similarity_threshold
        self.use_cache = use_cache
        self.cards: List[AnkiCard] = []
        self.hebrew_lookup: Dict[str, List[AnkiCard]] = {}  # Normalized Hebrew -> Cards
        self.cache = DeckCache() if use_cache else None

    def load_deck_cards(self) -> bool:
        """Load all cards from the target deck (cached or live)"""
        if self.use_cache and self.cache:
            return self._load_from_cache()
        else:
            return self._load_from_anki_connect()

    def _load_from_cache(self) -> bool:
        """Load cards from persistent cache"""
        print(f"Loading cards from cache: {self.deck_name}")

        # Get cached deck data (never expires, manual refresh only)
        cached_cards = self.cache.get_cached_deck(self.deck_name, max_age_hours=None, auto_refresh=False)

        if not cached_cards:
            print("Failed to load from cache, falling back to AnkiConnect")
            return self._load_from_anki_connect()

        # Convert cached data to AnkiCard objects
        self.cards = []
        self.hebrew_lookup = {}

        for card_data in cached_cards:
            anki_card = AnkiCard(
                card_id=card_data['card_id'],
                note_id=card_data['note_id'],
                hebrew=card_data['hebrew'],
                english=card_data['english'],
                normalized_hebrew=card_data['normalized_hebrew'],
                tags=card_data['tags'],
                fields=card_data['fields']
            )

            self.cards.append(anki_card)

            # Build lookup table for fast matching
            normalized = card_data['normalized_hebrew']
            if normalized not in self.hebrew_lookup:
                self.hebrew_lookup[normalized] = []
            self.hebrew_lookup[normalized].append(anki_card)

        print(f"Loaded {len(self.cards)} Hebrew cards from cache")
        return True

    def _load_from_anki_connect(self) -> bool:
        """Load cards directly from AnkiConnect (slow fallback)"""
        print(f"Loading cards from AnkiConnect: {self.deck_name}")

        # Get all card IDs from deck
        card_ids = anki_request('findCards', {'query': f'deck:"{self.deck_name}"'})
        if not card_ids:
            print("No cards found in deck")
            return False

        print(f"Found {len(card_ids)} cards, retrieving details...")

        # Get detailed card information in batches (AnkiConnect can be slow)
        batch_size = 500
        all_cards = []

        for i in range(0, len(card_ids), batch_size):
            batch = card_ids[i:i + batch_size]
            cards_info = anki_request('cardsInfo', {'cards': batch})
            if cards_info:
                all_cards.extend(cards_info)
            print(f"Processed {min(i + batch_size, len(card_ids))}/{len(card_ids)} cards")

        # Process cards and build lookup tables
        self.cards = []
        self.hebrew_lookup = {}

        for card_info in all_cards:
            hebrew_field = card_info['fields'].get('Hebrew', {}).get('value', '')
            english_field = card_info['fields'].get('English', {}).get('value', '')

            # Skip cards without Hebrew text
            if not hebrew_field or not any('\u05d0' <= c <= '\u05ea' for c in hebrew_field):
                continue

            # Clean Hebrew text (remove HTML tags, etc.)
            hebrew_clean = self._clean_field_text(hebrew_field)
            normalized = normalize_hebrew_word(hebrew_clean)

            if not normalized:
                continue

            anki_card = AnkiCard(
                card_id=card_info['cardId'],
                note_id=card_info['note'],
                hebrew=hebrew_clean,
                english=self._clean_field_text(english_field),
                normalized_hebrew=normalized,
                tags=card_info.get('tags', []),
                fields={name: data['value'] for name, data in card_info['fields'].items()}
            )

            self.cards.append(anki_card)

            # Build lookup table for fast matching
            if normalized not in self.hebrew_lookup:
                self.hebrew_lookup[normalized] = []
            self.hebrew_lookup[normalized].append(anki_card)

        print(f"Loaded {len(self.cards)} Hebrew cards for matching")
        return True

    def _clean_field_text(self, text: str) -> str:
        """Clean HTML and formatting from Anki field text"""
        if not text:
            return ""

        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        clean = ' '.join(clean.split())
        return clean.strip()

    def find_matches(self, lesson_word: str, max_candidates: int = 3) -> List[WordMatch]:
        """
        Find matching Anki cards for a lesson word using fuzzy matching

        Args:
            lesson_word: Hebrew word from lesson
            max_candidates: Maximum number of matches to return

        Returns:
            List of WordMatch objects sorted by similarity score
        """
        normalized_word = normalize_hebrew_word(lesson_word)
        matches = []

        # Phase 1: Exact normalized match
        if normalized_word in self.hebrew_lookup:
            for card in self.hebrew_lookup[normalized_word]:
                matches.append(WordMatch(
                    lesson_word=lesson_word,
                    normalized_word=normalized_word,
                    anki_card=card,
                    similarity_score=0,
                    match_type='exact'
                ))

        # Phase 2: Fuzzy matching if no exact matches or we want more candidates
        if len(matches) < max_candidates:
            fuzzy_matches = self._fuzzy_match(normalized_word, max_candidates - len(matches))
            for card, distance in fuzzy_matches:
                # Avoid duplicates from exact matches
                if not any(m.anki_card.card_id == card.card_id for m in matches):
                    matches.append(WordMatch(
                        lesson_word=lesson_word,
                        normalized_word=normalized_word,
                        anki_card=card,
                        similarity_score=distance,
                        match_type='fuzzy'
                    ))

        # Sort by similarity score (exact matches first, then by distance)
        matches.sort(key=lambda m: (m.similarity_score, m.anki_card.hebrew))
        return matches[:max_candidates]

    def _fuzzy_match(self, normalized_word: str, max_results: int) -> List[Tuple[AnkiCard, int]]:
        """Find fuzzy matches using Levenshtein distance"""
        candidates = []

        for card in self.cards:
            distance = levenshtein_distance(normalized_word, card.normalized_hebrew)

            # Only consider matches within threshold
            if distance <= self.similarity_threshold:
                candidates.append((card, distance))

        # Sort by distance and return top candidates
        candidates.sort(key=lambda x: x[1])
        return candidates[:max_results]

    def get_deck_stats(self) -> Dict[str, int]:
        """Get statistics about loaded deck"""
        return {
            'total_cards': len(self.cards),
            'unique_words': len(self.hebrew_lookup),
            'deck_name': self.deck_name
        }


def create_matcher_from_config(config: dict, use_cache: bool = True) -> AnkiMatcher:
    """Create AnkiMatcher from configuration"""
    deck_name = config['anki']['hebrew_deck']
    threshold = config['processing'].get('word_match_threshold', 3)

    matcher = AnkiMatcher(deck_name, threshold, use_cache=use_cache)
    matcher.load_deck_cards()
    return matcher


if __name__ == "__main__":
    # Test the matcher
    import yaml

    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    matcher = create_matcher_from_config(config)
    print("Deck stats:", matcher.get_deck_stats())

    # Test with some sample words
    test_words = ["שלום", "בוקר", "טוב"]

    for word in test_words:
        print(f"\nMatching '{word}':")
        matches = matcher.find_matches(word, max_candidates=3)

        for match in matches:
            print(f"  {match.match_type}: {match.anki_card.hebrew} -> {match.anki_card.english}")
            print(f"    Score: {match.similarity_score}, Card ID: {match.anki_card.card_id}")