# Anki-Assimil V3

Modern Hebrew language learning integration with Anki via AnkiConnect API.

## Quick Start

### 1. Setup Virtual Environment
```bash
cd v3
python3 -m venv .venv
source .venv/bin/activate
pip install typer rich pyyaml requests mutagen python-Levenshtein pandas
```

### 2. Check Status
```bash
python3 main.py status
```
This will show you what files are available and the current state of your setup.

### 3. Basic Workflow
```bash
# Extract audio from new lessons
python3 main.py extract-audio --lessons "1-5"

# Sync completed translations to Anki (creates bidirectional cards + uploads audio)
python3 main.py sync-phrases
```

**Note**: Make sure Anki is running with the AnkiConnect addon installed for syncing to work.

## Features

### ✅ Implemented
- **Direct Anki integration via AnkiConnect API** - no more manual imports!
- **Automatic audio file upload** - media files sync directly to Anki
- **Bidirectional cards** - practice Hebrew → English and English → Hebrew
- **Incremental processing** - only process new lessons
- **Word matching with fuzzy search** - find Hebrew vocabulary in your existing deck
- **Interactive CLI** with rich formatting and progress tracking

### Architecture Improvements
- Modular design with clear separation of concerns
- Enhanced error handling and validation
- Configuration management via YAML
- Type hints throughout codebase
- Eliminated manual export/import cycles

## Commands

```bash
python3 main.py status                    # Check file status
python3 main.py extract-audio            # Extract audio and create CSV
python3 main.py sync-phrases             # Sync to Anki (cards + audio)
python3 main.py match-words              # Generate word matching suggestions  
python3 main.py apply-tags               # Apply vocabulary tags to Anki cards
```

## Migration from V2

V3 is now fully functional and provides significant improvements over V2:
- No more manual CSV imports - everything syncs automatically
- Audio files upload directly to Anki's media directory
- Better error handling and user feedback
- Simplified workflow with fewer manual steps

See the [main project documentation](../CLAUDE.md) for detailed usage patterns.