# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Anki-Assimil is a Hebrew language learning integration system that connects Assimil language course materials with Anki spaced repetition flashcards. The system extracts Hebrew text and audio from MP3 files, matches words to existing vocabulary, and generates Anki import files with lesson-specific tags.

## Repository Structure

The project is organized into versioned directories:

### Version 2 (v2/) - Current Active Version
- **main.py**: CLI entry point using Typer with commands: `status`, `extract-audio`, `match-words`, `export-anki`
- **src/audio.py**: MP3 metadata extraction, audio file processing, CSV generation
- **src/matching.py**: Hebrew tokenization using hebtokenizer, vocabulary matching with Levenshtein distance
- **src/anki_export.py**: Anki import file generation with tag updates
- **src/hebtokenizer.py**: Hebrew text tokenization utility

### Version 1 (v1/) - Legacy Implementation
Contains original Python scripts preserved for reference

### Version 3 (v3/) - Future Development
Planned modernization with enhanced architecture

## Common Commands

### Setup
```bash
cd v2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Core Workflow
```bash
python main.py status                          # Check file status
python main.py extract-audio --lessons 1-5    # Extract audio and create initial CSV
python main.py match-words                     # Generate word matching suggestions  
python main.py export-anki                     # Create Anki import files
```

### Testing Commands
No automated tests present. Validation is done through:
- `python main.py status` to verify file structure
- Manual review of generated CSV files in generated/ directory

## Key File Structure

### Input Files (User-provided)
- `v2/input/config.yaml`: Configuration with paths and processing settings
- `v2/input/alldecks.txt`: Anki vocabulary export (tab-separated)
- `v2/test-data/assimil-course/L*/`: MP3 files with Hebrew metadata

### Human-Curated Files
- `v2/data/assimil.csv`: Lesson phrases with English translations
- `v2/data/assimil-words.csv`: Curated word matches
- `v2/data/assimil-words-extra.csv`: Additional manual matches

### Generated Files
- `v2/generated/assimil-init.csv`: Initial extraction for translation
- `v2/generated/assimil-words-init.csv`: Word matching suggestions
- `v2/generated/assimil-tag-update.csv`: Final Anki import file

Note: Some older references use `working/` (≈ `data/`) and `output/` (≈ `generated/`). Prefer the canonical names above in new contributions.

## Data Flow

1. **Audio Extraction**: Scans MP3 files → extracts Hebrew text from metadata → creates standardized audio files → generates initial CSV
2. **Word Matching**: Tokenizes Hebrew text → matches against existing vocabulary using similarity → generates suggestions for manual review
3. **Export**: Loads curated matches → updates vocabulary tags → creates Anki import files

## Configuration

All settings managed through `v2/input/config.yaml`:
- File paths for input/output directories
- Processing parameters (similarity thresholds, lesson limits)
- Anki-specific settings (tag prefixes, field mappings)

## Dependencies

Key Python libraries:
- typer: CLI framework
- rich: Terminal output formatting  
- pandas: Data manipulation
- mutagen: MP3 metadata extraction
- python-Levenshtein: String similarity matching
- nltk: Text processing support
