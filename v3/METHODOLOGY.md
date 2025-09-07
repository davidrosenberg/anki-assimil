# Anki-Assimil V3: System Methodology & Architecture

This document details the algorithmic approaches, data structures, and architectural decisions that enable the Hebrew Assimil-to-Anki integration system. It serves as a comprehensive reference for understanding, refactoring, and extending the system.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Card Identification Strategy](#card-identification-strategy)
3. [Word Matching Algorithms](#word-matching-algorithms)
4. [Tagging & Organization System](#tagging--organization-system)
5. [File Processing Pipeline](#file-processing-pipeline)
6. [Persistence & State Management](#persistence--state-management)
7. [AnkiConnect Integration](#ankiconnect-integration)
8. [Extensibility Patterns](#extensibility-patterns)

---

## System Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MP3 Files     │───▶│   Extraction    │───▶│   CSV Data      │
│ (Course Audio)  │    │   & Metadata    │    │ (Translations)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Anki Deck     │◀───│   Sync Engine   │◀───│ Word Matching   │
│ (Cards+Media)   │    │ (Cards+Audio)   │    │  & Tagging      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       ▲
                                ▼                       │
                        ┌─────────────────┐    ┌─────────────────┐
                        │ AnkiConnect API │    │ Hebrew Deck     │
                        │ (Remote Control)│    │ (Vocabulary)    │
                        └─────────────────┘    └─────────────────┘
```

### Data Flow

1. **Extraction Phase**
   - Scan MP3 files in lesson directories
   - Extract Hebrew text and lesson metadata
   - Generate standardized filenames and IDs
   - Create initial CSV for human translation

2. **Human Curation Phase**
   - User adds English translations to CSV
   - System provides word matching suggestions
   - User approves/rejects vocabulary matches

3. **Sync Phase**
   - Create bidirectional Anki cards from completed translations
   - Upload audio files directly from course directory
   - Apply hierarchical tags for organization

### Module Responsibilities

- **`audio.py`**: MP3 scanning, metadata extraction, filename standardization
- **`deck_sync.py`**: Card creation, media upload, duplicate detection
- **`word_matching.py`**: Hebrew tokenization, vocabulary fuzzy matching
- **`anki_api.py`**: AnkiConnect communication, API error handling
- **`tags.py`**: Centralized tag generation and parsing
- **`persistence.py`**: Match storage, statistics, state management

---

## Card Identification Strategy

### Unique Card Identity

**Primary Key**: Media filename extracted from sound field

```python
# Example: [sound:L001.S02.mp3] -> "L001.S02.mp3"
def extract_media_filename(sound_field: str) -> str:
    match = re.search(r'\[sound:([^\]]+)\]', sound_field)
    return match.group(1) if match else None
```

**Why Media Filename?**
- Immutable: Once set, never changes
- Unique: Each lesson phrase has distinct audio
- Reliable: Survives card edits and note type changes
- Human-readable: Easy to debug and trace

### Alternative Approaches (Rejected)

1. **Lesson ID Tags**: Fragile - users can modify tags
2. **Text Content**: Unreliable - Hebrew text may have variants  
3. **Anki Note IDs**: Unstable - change when cards are reimported
4. **Custom Fields**: Requires specific note type

### Duplicate Detection Algorithm

```python
def get_existing_cards_by_media(deck_name: str) -> Dict[str, int]:
    """Map media filename -> note ID for all existing cards"""
    
    # 1. Get all notes in target deck
    note_ids = anki_request("findNotes", {"query": f'deck:"{deck_name}"'})
    
    # 2. Extract media filename from each card's front field
    notes_info = anki_request("notesInfo", {"notes": note_ids})
    
    # 3. Build mapping table
    media_to_note = {}
    for note in notes_info:
        front_field = note['fields']['Front']['value']
        media_file = extract_media_filename(front_field)
        if media_file:
            media_to_note[media_file] = note['noteId']
    
    return media_to_note
```

---

## Word Matching Algorithms

### Hebrew Text Processing

#### Tokenization Strategy

Uses specialized Hebrew tokenizer (`hebtokenizer.py`) that handles:
- Hebrew letters (א-ת) with nikud (vowel points)
- Mixed Hebrew-Latin text
- Punctuation and numeric content
- Word boundaries in Hebrew text

```python
def tokenize_hebrew_text(text: str) -> List[Tuple[str, str]]:
    """Returns [(token_type, token_text), ...]"""
    tokens = hebtokenizer.tokenize(text)
    hebrew_words = [token for token_type, token in tokens if token_type == 'HEB']
    return hebrew_words
```

#### Text Normalization

```python
def normalize_hebrew_word(word: str) -> str:
    """Normalize Hebrew word for matching"""
    # Remove nikud (vowel points)
    normalized = re.sub(r'[\u05b0-\u05c4]', '', word)
    # Remove punctuation
    normalized = re.sub(r'[^\u05d0-\u05ea]', '', normalized)
    # Strip whitespace
    return normalized.strip()
```

### Fuzzy Matching Algorithm

#### Similarity Calculation

Uses Levenshtein distance for character-level similarity:

```python
def calculate_similarity(word1: str, word2: str) -> int:
    """Returns edit distance (lower = more similar)"""
    normalized1 = normalize_hebrew_word(word1)
    normalized2 = normalize_hebrew_word(word2)
    return levenshtein_distance(normalized1, normalized2)
```

#### Match Classification

```python
def classify_match(lesson_word: str, anki_word: str, distance: int) -> str:
    """Classify match quality"""
    if distance == 0:
        return 'exact'
    elif distance <= 2:
        return 'high_confidence'
    elif distance <= 5:
        return 'fuzzy'
    else:
        return 'low_confidence'
```

#### Candidate Selection

```python
def find_word_matches(lesson_word: str, vocabulary: Dict[str, AnkiCard], 
                     max_distance: int = 5, max_candidates: int = 3) -> List[WordMatch]:
    """Find top matching candidates using priority queue"""
    
    candidates = PriorityQueue()
    normalized_lesson = normalize_hebrew_word(lesson_word)
    
    for anki_word, card in vocabulary.items():
        distance = calculate_similarity(normalized_lesson, card.normalized_hebrew)
        
        if distance <= max_distance:
            match = WordMatch(
                lesson_word=lesson_word,
                normalized_word=normalized_lesson,
                anki_card=card,
                similarity_score=distance,
                match_type=classify_match(lesson_word, anki_word, distance)
            )
            candidates.put((distance, match))
    
    # Return top N candidates
    return [candidates.get()[1] for _ in range(min(max_candidates, candidates.qsize()))]
```

### Performance Optimization

#### Anki Deck Caching

```python
class DeckCache:
    """Persistent cache to avoid repeated AnkiConnect queries"""
    
    def get_cached_deck(self, deck_name: str) -> Optional[List[Dict]]:
        """Load deck from disk cache (never expires)"""
        # Implementation uses pickle serialization
        # Manual refresh only via cache_deck() command
        
    def cache_deck(self, deck_name: str) -> Dict[str, any]:
        """Fetch deck via AnkiConnect and cache to disk"""
        # Stores normalized Hebrew words for fast matching
```

---

## Tagging & Organization System

### Hierarchical Tag Structure

Uses Anki's `::` convention for tag hierarchies:

```
assimil                    # Base deck tag
├── assimil::L01          # Lesson 1 tag
├── assimil::L02          # Lesson 2 tag
├── ...
└── assimil::L20          # Lesson 20 tag
```

### Tag Generation API

```python
# Centralized in tags.py module

def generate_lesson_tags(deck_name: str, lesson_num: int) -> List[str]:
    """Generate complete tag set for a lesson"""
    return [
        deck_name.lower(),                           # 'assimil'
        f"{deck_name.lower()}::L{lesson_num:02d}"   # 'assimil::L01'
    ]

def parse_lesson_from_tags(tags: List[str], deck_name: str) -> Optional[int]:
    """Extract lesson number from tag hierarchy"""
    pattern = rf"^{re.escape(deck_name.lower())}::L(\d+)$"
    for tag in tags:
        match = re.match(pattern, tag)
        if match:
            return int(match.group(1))
    return None
```

### Benefits of Hierarchical Tags

1. **Organization**: Easy filtering by `assimil::L01` in Anki
2. **Scalability**: Supports unlimited lessons and decks
3. **Migration**: Old formats (`assimil-01`) can be automatically converted
4. **Consistency**: Centralized generation prevents format drift

---

## File Processing Pipeline

### MP3 Metadata Extraction

#### File Structure Assumptions

```
Course Directory/
├── L001-Hebrew ASSIMIL/
│   ├── S01.mp3  (Hebrew: בּוֹקֶר טוֹב)
│   ├── S02.mp3  (Hebrew: שָׁלוֹם)
│   └── T01.mp3  (Hebrew: בוקר)
├── L002-Hebrew ASSIMIL/
│   └── ...
```

#### Metadata Processing

```python
def extract_mp3_metadata(mp3_file: Path) -> Optional[Dict[str, str]]:
    """Extract lesson data from MP3 ID3 tags"""
    
    audio = MP3(str(mp3_file), ID3=EasyID3)
    title = audio.get('title', [''])[0]      # "S01-בּוֹקֶר טוֹב"
    album = audio.get('album', [''])[0]      # "Hebrew Course - L001"
    
    # Parse lesson: "Hebrew Course - L001" -> "L001"
    lesson = album.split(' - ')[-1]          # "L001"
    
    # Parse Hebrew: "S01-בּוֹקֶר טוֹב" -> "בּוֹקֶר טוֹב"
    title_parts = title.split('-', 1)
    section_id = title_parts[0]              # "S01"
    hebrew_text = title_parts[1].strip().rstrip('٭')  # Remove Arabic asterisk
    
    # Generate standardized ID: "L001.S01"
    unique_id = f"{lesson}.{section_id}"
    new_filename = f"{unique_id}.mp3"        # "L001.S01.mp3"
    
    return {
        'id': unique_id,
        'hebrew': hebrew_text,
        'sound': f'[sound:{new_filename}]',
        'new_filename': new_filename,
        'original_file': str(mp3_file)
    }
```

### Media File Mapping

#### Direct Course Directory Access

Instead of staging files, map standardized filenames to original paths:

```python
def build_media_lookup_table(course_dir: Path) -> Dict[str, Path]:
    """Build lookup table: anki filename -> original file path"""
    
    lookup_table = {}
    
    # Scan all MP3 files recursively
    mp3_files = list(course_dir.rglob("*.mp3"))
    
    for mp3_file in mp3_files:
        parent_dir = mp3_file.parent.name     # "L001-Hebrew ASSIMIL"
        filename = mp3_file.stem              # "S01" (without .mp3)
        
        # Parse lesson: "L001-Hebrew ASSIMIL" -> "001"
        lesson_match = re.match(r'L(\d{3})-Hebrew ASSIMIL', parent_dir)
        if lesson_match:
            lesson_num = lesson_match.group(1)  # "001"
            
            # Skip translate files
            if filename == 'T00-TRANSLATE':
                continue
                
            # Map: "L001.S01.mp3" -> /path/to/L001-Hebrew ASSIMIL/S01.mp3
            anki_filename = f"L{lesson_num}.{filename}.mp3"
            lookup_table[anki_filename] = mp3_file
    
    return lookup_table
```

---

## Persistence & State Management

### Match Storage Strategy

#### Approved Matches

```python
@dataclass
class StoredMatch:
    """Persistent record of human-approved word match"""
    lesson: str          # "L001"
    heb_word: str       # "בוקר"
    anki_hebrew: str    # "בּוֹקֶר" (with nikud)
    anki_english: str   # "morning"
    card_id: int        # Anki card ID
    match_type: str     # "approved", "exact", "fuzzy"
```

#### Statistics Tracking

```python
def get_statistics(self) -> Dict[str, any]:
    """Track matching progress across lessons"""
    return {
        'lessons_processed': len(self.lesson_matches),
        'total_word_matches': sum(len(matches) for matches in self.lesson_matches.values()),
        'exact_matches': count_by_type('exact'),
        'fuzzy_matches': count_by_type('fuzzy'),
        'unmatched_words': len(self.unmatched_words)
    }
```

### State Files

- **`data/assimil.csv`**: Human-curated translations (immutable once created)
- **`working/assimil-words.csv`**: Approved word matches
- **`working/assimil-words-extra.csv`**: Manual word additions
- **`cache/Hebrew_cache.pkl`**: Cached Anki vocabulary

---

## AnkiConnect Integration

### Card Creation Strategy

#### Bidirectional Cards

Uses `"Basic (and reversed card)"` note type:

```python
def create_bidirectional_card(translation: Dict) -> int:
    """Create card with Hebrew→English and English→Hebrew directions"""
    
    fields = {
        "Front": f"{translation['hebrew']}<br>{translation['sound']}",
        "Back": translation['english']
    }
    
    # Results in two cards:
    # Card 1: Hebrew text + audio → English (recognition)
    # Card 2: English text → Hebrew text + audio (recall)
    
    return create_note(deck_name, "Basic (and reversed card)", fields, tags)
```

#### Audio Behavior

- **Hebrew → English**: Audio plays (listening comprehension)
- **English → Hebrew**: Audio on answer side only (production practice)

### Media Upload Protocol

```python
def store_media_file(filename: str, file_path: Path) -> Optional[str]:
    """Upload file directly to Anki's media directory"""
    
    params = {
        "filename": filename,           # "L001.S01.mp3"
        "path": str(file_path.absolute()),  # Original file path
        "deleteExisting": False         # Don't overwrite existing
    }
    
    return anki_request("storeMediaFile", params)
```

### Error Handling

```python
def anki_request(action: str, params: Dict = None) -> any:
    """Robust AnkiConnect communication with error handling"""
    
    try:
        response = requests.post(ANKI_URL, json={
            "action": action,
            "version": 6,
            "params": params or {}
        }, timeout=10)
        
        result = response.json()
        
        if result.get('error'):
            console.print(f"[red]AnkiConnect error:[/red] {result['error']}")
            return None
            
        return result.get('result')
        
    except requests.exceptions.RequestException as e:
        console.print(f"[red]Failed to connect to AnkiConnect:[/red] {e}")
        return None
```

---

## Extensibility Patterns

### Multiple Hebrew Deck Support

#### Current Limitation
System assumes single Hebrew vocabulary deck (`Hebrew from Scratch`).

#### Extension Strategy

```python
class MultiDeckMatcher:
    """Support matching against multiple Hebrew decks"""
    
    def __init__(self, deck_configs: Dict[str, DeckConfig]):
        self.decks = {}
        for name, config in deck_configs.items():
            self.decks[name] = AnkiMatcher(
                deck_name=config.deck_name,
                similarity_threshold=config.threshold,
                field_mapping=config.field_mapping
            )
    
    def find_best_match(self, hebrew_word: str) -> Optional[WordMatch]:
        """Find best match across all configured decks"""
        all_matches = []
        
        for deck_name, matcher in self.decks.items():
            matches = matcher.find_matches(hebrew_word)
            # Add deck source to each match
            for match in matches:
                match.source_deck = deck_name
            all_matches.extend(matches)
        
        # Return best match across all decks
        return min(all_matches, key=lambda m: m.similarity_score) if all_matches else None
```

#### Configuration Extension

```yaml
# config.yaml
hebrew_decks:
  primary:
    name: "Hebrew from Scratch"
    fields:
      hebrew: "Hebrew"
      english: "Definition"
    weight: 1.0
  
  secondary:
    name: "Biblical Hebrew"  
    fields:
      hebrew: "Word"
      english: "Meaning"
    weight: 0.8
```

### Multi-Language Course Support

#### Abstraction Layer

```python
class CourseProcessor:
    """Generic course processing interface"""
    
    def extract_lessons(self, course_dir: Path) -> List[LessonData]:
        raise NotImplementedError
        
    def normalize_text(self, text: str) -> str:
        raise NotImplementedError
        
    def generate_tags(self, lesson_num: int) -> List[str]:
        raise NotImplementedError

class HebrewAssimilProcessor(CourseProcessor):
    """Hebrew-specific implementation"""
    # Current implementation

class ArabicAssimilProcessor(CourseProcessor):
    """Arabic-specific implementation"""
    # Future implementation
```

### Plugin Architecture

#### Matcher Plugins

```python
class MatcherPlugin:
    """Plugin interface for custom matching algorithms"""
    
    def match_words(self, lesson_words: List[str], vocabulary: Dict) -> List[WordMatch]:
        raise NotImplementedError

class FuzzyMatcher(MatcherPlugin):
    """Current Levenshtein-based matcher"""
    
class PhoneticMatcher(MatcherPlugin):
    """Future phonetic similarity matcher"""
    
class SemanticMatcher(MatcherPlugin):  
    """Future embedding-based semantic matcher"""
```

### Performance Scaling

#### Batch Processing

```python
class BatchProcessor:
    """Process multiple lessons efficiently"""
    
    def process_lesson_batch(self, lessons: List[int], batch_size: int = 5):
        """Process lessons in batches to manage memory"""
        for i in range(0, len(lessons), batch_size):
            batch = lessons[i:i+batch_size]
            yield self.process_batch(batch)
```

#### Parallel Processing

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_word_matching(lesson_words: List[str], vocabulary: Dict) -> List[WordMatch]:
    """Match words in parallel threads"""
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(find_word_matches, word, vocabulary)
            for word in lesson_words
        ]
        
        results = []
        for future in futures:
            results.extend(future.result())
        
    return results
```

---

## Implementation Guidelines

### Adding New Features

1. **Extend, don't modify**: Create new modules rather than changing core logic
2. **Use dependency injection**: Pass configurations and dependencies explicitly  
3. **Maintain backward compatibility**: Support existing data formats
4. **Add comprehensive logging**: Use rich console for user feedback
5. **Write integration tests**: Test against real Anki decks

### Performance Considerations

1. **Cache aggressively**: Avoid repeated AnkiConnect queries
2. **Batch operations**: Group related API calls
3. **Use generators**: Process large datasets lazily
4. **Profile bottlenecks**: Measure before optimizing

### Error Recovery

1. **Graceful degradation**: Continue processing when individual items fail
2. **Rollback support**: Allow undoing changes
3. **State preservation**: Save progress incrementally  
4. **User guidance**: Provide actionable error messages

---

This methodology document provides the foundation for understanding, maintaining, and extending the Anki-Assimil system. Each algorithmic decision is driven by reliability, performance, and user experience considerations.