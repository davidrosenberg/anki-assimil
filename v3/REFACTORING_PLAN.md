# Anki-Assimil V3: Three-Piece Architecture Refactoring Plan

## Overview

This document outlines a comprehensive refactoring plan to transform the current monolithic Anki-Assimil V3 system into three distinct, loosely-coupled components. This architectural shift will improve modularity, reusability, and extensibility while maintaining current functionality.

## Current System Analysis

### Existing Architecture Issues
- **Monolithic Design**: All functionality tightly coupled in single workflow
- **Mixed Concerns**: Course processing, word analysis, and Anki integration intermingled
- **Hard to Extend**: Adding new course types or matching algorithms requires deep changes
- **Difficult to Test**: Components can't be tested in isolation

### Current Module Structure
```
src/
├── audio.py              # MP3 scanning, metadata extraction
├── deck_sync.py          # Card creation, media upload  
├── word_extraction.py    # Hebrew text processing from lessons
├── word_matching.py      # Complete matching pipeline
├── anki_matcher.py       # Vocabulary fuzzy matching
├── tokenizer.py          # Hebrew tokenization
├── anki_api.py           # AnkiConnect communication
├── tags.py               # Centralized tag generation
└── persistence.py        # Match storage, state management
```

## Three-Piece Architecture Vision

### Piece 1: Course-to-Anki Deck Converter
**Purpose**: Extract course content and create corresponding Anki deck  
**Input**: Course materials (MP3 files, structured content)  
**Output**: Anki deck with lesson cards + media files  
**Scope**: Course-specific initially (Hebrew Assimil), designed for future generalization

#### Responsibilities
- Scan and parse course material structure
- Extract lesson content and metadata
- Create standardized lesson cards in Anki
- Upload associated media files
- Apply course-specific tagging

#### Current Modules → New Structure
```python
class CourseProcessor:
    """Generic interface for processing language courses"""
    
    def scan_course_content(self, course_dir: Path) -> List[Lesson]:
        """Scan course directory and extract lesson structure"""
    
    def create_anki_deck(self, lessons: List[Lesson], deck_name: str) -> AnkiDeck:
        """Create Anki deck from lesson content"""
    
    def upload_media(self, lessons: List[Lesson]) -> MediaUploadResults:
        """Upload course media files to Anki"""

class HebrewAssimilProcessor(CourseProcessor):
    """Hebrew Assimil-specific implementation"""
    # Integrates: audio.py + deck_sync.py (course creation parts)
```

### Piece 2: Hebrew Content → Word List Extractor
**Purpose**: Analyze Hebrew content and extract vocabulary for matching  
**Input**: Hebrew text from any source (lessons, documents, etc.)  
**Output**: Structured word list with metadata (context, translations, source info)  
**Scope**: Hebrew-specific text analysis and vocabulary extraction

#### Responsibilities
- Tokenize Hebrew text with proper handling of nikud
- Extract unique vocabulary from content
- Preserve context and source information
- Generate normalized forms for matching
- Support multiple content sources

#### Current Modules → New Structure
```python
class HebrewAnalyzer:
    """Hebrew text analysis and vocabulary extraction"""
    
    def tokenize_text(self, hebrew_text: str) -> List[HebrewToken]:
        """Tokenize Hebrew text with linguistic awareness"""
    
    def extract_vocabulary(self, content: HebrewContent) -> WordList:
        """Extract vocabulary with context and metadata"""
    
    def normalize_words(self, words: List[str]) -> List[NormalizedWord]:
        """Normalize Hebrew words for matching"""

class ContentSource:
    """Abstract base for different content sources"""
    # Implementations: AssimilSource, TextFileSource, etc.
```

#### Extracted Vocabulary Format
```python
@dataclass
class ExtractedWord:
    original_text: str          # "בּוֹקֶר"
    normalized_text: str        # "בוקר"
    context: str               # Full sentence/phrase
    source_id: str             # "L001.S02"
    source_type: str           # "assimil_lesson"
    metadata: Dict[str, Any]   # Additional context
```

### Piece 3: Hebrew Word → Anki Card Tagger
**Purpose**: Match Hebrew word lists against existing Anki vocabulary and apply tags  
**Input**: Word list + target Anki deck(s)  
**Output**: Tagged Anki cards with source/lesson metadata  
**Scope**: Generic Hebrew word matching and flexible tagging

#### Responsibilities
- Load and cache existing Hebrew Anki decks
- Perform fuzzy matching using multiple algorithms
- Apply tags based on configurable schemes
- Track matching statistics and confidence
- Support multiple Hebrew deck sources

#### Current Modules → New Structure
```python
class VocabularyTagger:
    """Generic Hebrew vocabulary matching and tagging"""
    
    def load_anki_vocabulary(self, deck_configs: List[DeckConfig]) -> VocabularyIndex:
        """Load and index Hebrew vocabulary from multiple decks"""
    
    def match_words(self, word_list: WordList, vocab_index: VocabularyIndex) -> List[WordMatch]:
        """Find matches using configured algorithms"""
    
    def apply_tags(self, matches: List[WordMatch], tagging_scheme: TaggingScheme) -> TaggingResults:
        """Apply tags to matched Anki cards"""

class MatchingAlgorithm:
    """Plugin interface for different matching strategies"""
    # Implementations: LevenshteinMatcher, PhoneticMatcher, SemanticMatcher
```

## Interface Definitions

### Data Flow Interfaces
```python
# Piece 1 Output → Piece 2 Input
@dataclass 
class CourseContent:
    lessons: List[Lesson]
    hebrew_texts: List[str]
    metadata: Dict[str, Any]

# Piece 2 Output → Piece 3 Input  
@dataclass
class WordList:
    words: List[ExtractedWord]
    source_info: SourceInfo
    extraction_stats: ExtractionStats

# Piece 3 Output
@dataclass
class TaggingResults:
    matched_cards: List[TaggedCard]
    unmatched_words: List[ExtractedWord]
    confidence_stats: MatchingStats
```

### Configuration Interface
```python
@dataclass
class SystemConfig:
    course_config: CourseConfig
    analysis_config: AnalysisConfig  
    matching_config: MatchingConfig
    
    # Allows flexible workflows:
    # - Full pipeline: Course → Words → Tags
    # - Partial: Words → Tags (external content)
    # - Analysis only: Course → Words (no tagging)
```

## Module Mapping: Current → Future

### Piece 1: CourseProcessor
| Current Module | Future Location | Responsibilities |
|---------------|-----------------|------------------|
| `audio.py` | `CourseProcessor.scan_course_content()` | MP3 scanning, metadata extraction |
| `deck_sync.py` | `CourseProcessor.create_anki_deck()` | Card creation, deck management |
| `deck_sync.py` | `CourseProcessor.upload_media()` | Media file upload |

### Piece 2: HebrewAnalyzer  
| Current Module | Future Location | Responsibilities |
|---------------|-----------------|------------------|
| `word_extraction.py` | `HebrewAnalyzer.extract_vocabulary()` | Word extraction from lessons |
| `tokenizer.py` | `HebrewAnalyzer.tokenize_text()` | Hebrew tokenization |

### Piece 3: VocabularyTagger
| Current Module | Future Location | Responsibilities |
|---------------|-----------------|------------------|
| `anki_matcher.py` | `VocabularyTagger.match_words()` | Fuzzy matching algorithms |
| `word_matching.py` | `VocabularyTagger` orchestration | Complete matching pipeline |
| `deck_cache.py` | `VocabularyTagger.load_anki_vocabulary()` | Anki deck caching |

### Shared Infrastructure
| Current Module | Future Location | Responsibilities |
|---------------|-----------------|------------------|
| `anki_api.py` | Shared utility | AnkiConnect communication |
| `tags.py` | Shared utility | Tag generation and parsing |
| `persistence.py` | Shared utility | State management |

## Implementation Phases

### Phase 1: Interface Design & Module Structure
**Duration**: 1-2 days  
**Goals**: 
- Create new module structure with clean interfaces
- Define data classes and configuration schemas
- Create abstract base classes for extensibility

**Deliverables**:
```
src/
├── course_processing/
│   ├── __init__.py
│   ├── course_processor.py      # Abstract base
│   └── hebrew_assimil.py        # Concrete implementation
├── hebrew_analysis/
│   ├── __init__.py  
│   ├── hebrew_analyzer.py       # Main analyzer class
│   └── content_sources.py       # Source abstractions
├── vocabulary_tagging/
│   ├── __init__.py
│   ├── vocabulary_tagger.py     # Main tagger class
│   └── matching_algorithms.py   # Algorithm plugins
└── shared/
    ├── data_models.py           # Shared data classes
    ├── config_models.py         # Configuration schemas
    └── interfaces.py            # Abstract interfaces
```

### Phase 2: Code Migration
**Duration**: 2-3 days  
**Goals**:
- Migrate existing functionality into new structure
- Maintain backward compatibility with current CLI
- Add comprehensive tests for new interfaces

**Migration Strategy**:
1. **Piece 1**: Extract course-specific logic from `audio.py` + `deck_sync.py`
2. **Piece 2**: Refactor `word_extraction.py` + `tokenizer.py` into `HebrewAnalyzer`  
3. **Piece 3**: Consolidate `anki_matcher.py` + `word_matching.py` into `VocabularyTagger`

### Phase 3: CLI Refactoring  
**Duration**: 1 day  
**Goals**:
- Update CLI to orchestrate three pieces
- Support flexible workflows (full pipeline vs. individual pieces)
- Maintain existing command compatibility

**New CLI Structure**:
```python
# Full pipeline (current behavior)
python main.py sync --config config.yaml

# Individual pieces
python main.py extract-course --course-dir path/ --output course_data.json
python main.py analyze-hebrew --input course_data.json --output word_list.json  
python main.py tag-vocabulary --input word_list.json --anki-decks "Hebrew from Scratch"

# Mixed workflows
python main.py analyze-hebrew --text-file external.txt | python main.py tag-vocabulary --stdin
```

### Phase 4: Configuration & Extensions
**Duration**: 1-2 days  
**Goals**:
- Add flexible configuration system
- Support multiple Hebrew decks
- Add plugin system for new matching algorithms

**Configuration Example**:
```yaml
# Full pipeline config
course_processing:
  type: "hebrew_assimil"
  course_dir: "~/Hebrew/Assimil Hebrew"
  max_lessons: 20

hebrew_analysis:  
  tokenizer: "hebtokenizer"
  normalize_nikud: true
  extract_context: true

vocabulary_tagging:
  target_decks:
    - name: "Hebrew from Scratch" 
      fields: {hebrew: "Hebrew", english: "Definition"}
      weight: 1.0
    - name: "Biblical Hebrew"
      fields: {hebrew: "Word", english: "Meaning"} 
      weight: 0.8
  matching_algorithms: ["levenshtein", "phonetic"]
  tag_scheme: "hierarchical"
```

## Benefits & Design Rationale

### Modularity Benefits
- **Independent Development**: Each piece can be developed and tested separately
- **Clear Interfaces**: Well-defined inputs/outputs between components
- **Easier Debugging**: Issues can be isolated to specific pieces
- **Focused Testing**: Unit tests for individual components

### Reusability Benefits
- **Mix and Match**: Use pieces in different combinations
- **External Integration**: Other tools can use individual pieces
- **Multiple Workflows**: Support various use cases beyond current pipeline

### Extensibility Benefits
- **New Course Types**: Easy to add Arabic, French, etc. processors
- **Multiple Content Sources**: Support text files, PDFs, web content
- **Advanced Matching**: Plugin system for semantic matching, ML-based approaches
- **Flexible Tagging**: Support different tagging schemes and metadata

### Performance Benefits
- **Parallel Processing**: Pieces can run concurrently when appropriate  
- **Selective Processing**: Run only needed pieces for specific tasks
- **Better Caching**: Each piece can optimize its own caching strategy

## Migration Path

### Backward Compatibility
- Current CLI commands continue to work unchanged
- Existing configuration files remain valid
- Generated data formats stay consistent

### Gradual Transition
1. **Week 1**: Implement new structure alongside existing code
2. **Week 2**: Migrate functionality piece by piece  
3. **Week 3**: Update CLI and add new capabilities
4. **Week 4**: Remove old code, finalize documentation

### Risk Mitigation
- **Feature Flags**: Allow switching between old/new implementations
- **Comprehensive Tests**: Ensure new code matches existing behavior exactly
- **Rollback Plan**: Keep old code until new system is fully validated

## Future Extensions Enabled

### Multi-Language Support
```python
class ArabicAssimilProcessor(CourseProcessor):
    """Arabic Assimil course support"""

class ArabicAnalyzer(TextAnalyzer):
    """Arabic text analysis"""
```

### Advanced Matching
```python  
class SemanticMatcher(MatchingAlgorithm):
    """Embedding-based semantic matching"""

class MLMatcher(MatchingAlgorithm):
    """Machine learning-based matching"""
```

### External Integrations
```python
# Use pieces with external content
analyzer = HebrewAnalyzer()
words = analyzer.extract_vocabulary(pdf_content)

tagger = VocabularyTagger()
results = tagger.match_and_tag(words, anki_decks)
```

## Conclusion

This three-piece architecture refactoring will transform the Anki-Assimil system from a monolithic Hebrew course processor into a flexible, extensible toolkit for Hebrew language learning integration. The modular design enables new use cases while maintaining all current functionality.

The clear separation of concerns - course processing, content analysis, and vocabulary tagging - creates a foundation for future enhancements and makes the system much easier to understand, test, and extend.