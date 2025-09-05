"""
Persistent deck cache system to avoid slow AnkiConnect downloads
"""

import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import hashlib

from src.anki_api import anki_request
from src.tokenizer import normalize_hebrew_word


class DeckCache:
    """Persistent cache for Anki deck data"""

    def __init__(self, cache_dir: Path = Path("cache")):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_path(self, deck_name: str) -> Path:
        """Get cache file path for deck"""
        # Create safe filename from deck name
        safe_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        return self.cache_dir / f"{safe_name}_cache.pkl"

    def _get_metadata_path(self, deck_name: str) -> Path:
        """Get metadata file path for deck"""
        safe_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        return self.cache_dir / f"{safe_name}_meta.json"

    def is_cache_valid(self, deck_name: str, max_age_hours: int = None) -> bool:
        """Check if cached deck exists (never expires unless max_age_hours specified)"""
        cache_path = self._get_cache_path(deck_name)
        meta_path = self._get_metadata_path(deck_name)

        if not cache_path.exists() or not meta_path.exists():
            return False

        # If no max_age_hours specified, cache never expires (manual management only)
        if max_age_hours is None:
            return True

        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            cached_time = datetime.fromisoformat(metadata['cached_at'])
            max_age = timedelta(hours=max_age_hours)

            return datetime.now() - cached_time < max_age

        except Exception as e:
            print(f"Error checking cache validity: {e}")
            return False

    def cache_deck(self, deck_name: str) -> Dict[str, any]:
        """Download and cache deck from AnkiConnect"""
        print(f"Downloading and caching deck: {deck_name}")

        try:
            # Get all card IDs from deck
            card_ids = anki_request('findCards', {'query': f'deck:"{deck_name}"'})
            if not card_ids:
                print("No cards found in deck")
                return {'success': False, 'error': 'No cards found'}

            print(f"Found {len(card_ids)} cards, downloading details...")

            # Get detailed card information in batches
            batch_size = 500
            all_cards = []

            for i in range(0, len(card_ids), batch_size):
                batch = card_ids[i:i + batch_size]
                cards_info = anki_request('cardsInfo', {'cards': batch})
                if cards_info:
                    all_cards.extend(cards_info)
                print(f"Downloaded {min(i + batch_size, len(card_ids))}/{len(card_ids)} cards")

            # Process and cache cards
            processed_cards = self._process_cards(all_cards)

            cache_path = self._get_cache_path(deck_name)
            meta_path = self._get_metadata_path(deck_name)

            # Save processed cards
            with open(cache_path, 'wb') as f:
                pickle.dump(processed_cards, f)

            # Save metadata
            metadata = {
                'deck_name': deck_name,
                'cached_at': datetime.now().isoformat(),
                'card_count': len(all_cards),
                'hebrew_cards': len(processed_cards),
                'cache_version': '1.0'
            }

            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            print(f"✓ Cached {len(processed_cards)} Hebrew cards from {len(all_cards)} total cards")

            return {
                'success': True,
                'total_cards': len(all_cards),
                'hebrew_cards': len(processed_cards)
            }

        except Exception as e:
            print(f"Error caching deck: {e}")
            return {'success': False, 'error': str(e)}

    def _process_cards(self, cards_info: List[Dict]) -> List[Dict]:
        """Process raw card data into searchable format"""
        processed_cards = []

        for card_info in cards_info:
            hebrew_field = card_info['fields'].get('Hebrew', {}).get('value', '')
            english_field = card_info['fields'].get('English', {}).get('value', '')

            # Skip cards without Hebrew text
            if not hebrew_field or not any('\u05d0' <= c <= '\u05ea' for c in hebrew_field):
                continue

            # Clean and normalize Hebrew text
            hebrew_clean = self._clean_field_text(hebrew_field)
            normalized = normalize_hebrew_word(hebrew_clean)

            if not normalized:
                continue

            processed_card = {
                'card_id': card_info['cardId'],
                'note_id': card_info['note'],
                'hebrew': hebrew_clean,
                'english': self._clean_field_text(english_field),
                'normalized_hebrew': normalized,
                'tags': card_info.get('tags', []),
                'fields': {name: data['value'] for name, data in card_info['fields'].items()}
            }

            processed_cards.append(processed_card)

        return processed_cards

    def _clean_field_text(self, text: str) -> str:
        """Clean HTML and formatting from Anki field text"""
        if not text:
            return ""

        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        clean = ' '.join(clean.split())
        return clean.strip()

    def load_cached_deck(self, deck_name: str) -> Optional[List[Dict]]:
        """Load deck from cache"""
        cache_path = self._get_cache_path(deck_name)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading cached deck: {e}")
            return None

    def get_cached_deck(self, deck_name: str, max_age_hours: int = None, auto_refresh: bool = False) -> Optional[List[Dict]]:
        """
        Get deck data, using cache if valid or refreshing if needed

        Args:
            deck_name: Name of Anki deck
            max_age_hours: Maximum cache age in hours (None = never expires)
            auto_refresh: Whether to automatically refresh stale cache

        Returns:
            List of processed card dictionaries, or None if unavailable
        """
        # Check if cache is valid (never expires by default)
        if self.is_cache_valid(deck_name, max_age_hours):
            print(f"Using cached deck: {deck_name}")
            return self.load_cached_deck(deck_name)

        # Cache is stale or missing
        if auto_refresh:
            print(f"Cache missing/stale, refreshing deck: {deck_name}")
            result = self.cache_deck(deck_name)
            if result['success']:
                return self.load_cached_deck(deck_name)
        else:
            print(f"Cache missing for deck: {deck_name}")
            print(f"Run 'python main.py cache-deck' to create cache")

        return None

    def refresh_cache(self, deck_name: str) -> Dict[str, any]:
        """Force refresh of deck cache"""
        print(f"Force refreshing cache for: {deck_name}")
        return self.cache_deck(deck_name)

    def clear_cache(self, deck_name: Optional[str] = None):
        """Clear cache for specific deck or all decks"""
        if deck_name:
            cache_path = self._get_cache_path(deck_name)
            meta_path = self._get_metadata_path(deck_name)

            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            print(f"Cleared cache for deck: {deck_name}")
        else:
            # Clear all cache files
            for file_path in self.cache_dir.glob("*_cache.pkl"):
                file_path.unlink()
            for file_path in self.cache_dir.glob("*_meta.json"):
                file_path.unlink()
            print("Cleared all deck caches")

    def get_cache_info(self, deck_name: str) -> Optional[Dict]:
        """Get information about cached deck"""
        meta_path = self._get_metadata_path(deck_name)

        if not meta_path.exists():
            return None

        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            cached_time = datetime.fromisoformat(metadata['cached_at'])
            age_hours = (datetime.now() - cached_time).total_seconds() / 3600

            return {
                **metadata,
                'age_hours': age_hours,
                'is_stale': False  # Never stale with manual management
            }

        except Exception as e:
            print(f"Error reading cache metadata: {e}")
            return None

    def list_cached_decks(self) -> List[Dict]:
        """List all cached decks with their info"""
        cached_decks = []

        for meta_file in self.cache_dir.glob("*_meta.json"):
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)

                cached_time = datetime.fromisoformat(metadata['cached_at'])
                age_hours = (datetime.now() - cached_time).total_seconds() / 3600

                cached_decks.append({
                    **metadata,
                    'age_hours': age_hours,
                    'is_stale': False  # Never stale with manual management
                })

            except Exception:
                continue

        return cached_decks


if __name__ == "__main__":
    # Test cache system
    cache = DeckCache()

    # List existing caches
    cached = cache.list_cached_decks()
    print(f"Found {len(cached)} cached decks")

    for deck_info in cached:
        print(f"  {deck_info['deck_name']}: {deck_info['hebrew_cards']} cards, {deck_info['age_hours']:.1f}h old")