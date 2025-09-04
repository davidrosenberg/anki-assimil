# Anki-Assimil Integration

Hebrew language learning integration system that connects Assimil language course materials with Anki spaced repetition flashcards.

## Versions

This repository contains multiple versions of the integration system:

### [Version 2](./v2/) - Modern Python CLI  
- **Status**: ⚠️ **Obsolete** - Anki export format has changed
- **Features**: Typer CLI, modular architecture, rich terminal output
- **Issue**: Relies on file exports that no longer work with current Anki
- **Commands**: `python main.py extract-audio`, `python main.py match-words`, `python main.py export-anki`

### [Version 1 (Legacy)](./v1/) - Original Scripts
- **Status**: 📦 Archived for reference
- **Features**: Individual Python scripts, basic functionality
- **Best for**: Understanding original implementation
- **Files**: `anki-assimil.py`, `update-assimil.py`, `write-data-file.py`

### [Version 3 (Current)](./v3/) - Direct Anki Integration
- **Status**: 🚧 **In Development** - Direct API integration
- **Features**: AnkiConnect API, SQLite read access, no export/import needed
- **Best for**: Current usage with modern Anki versions

## Quick Start

For new users, start with **Version 3**:

```bash
cd v3
# Setup instructions coming soon
```

See the [Version 3 README](./v3/README.md) for development progress.

## What This System Does

1. **Extracts** Hebrew text and audio from Assimil MP3 files
2. **Matches** Hebrew words to your existing Anki vocabulary using similarity algorithms
3. **Tags** vocabulary cards with lesson numbers for organized study
4. **Creates** new flashcards for phrases with audio

This creates a powerful connection between structured lessons and spaced repetition learning.

## Repository Structure

```
anki-assimil/
├── README.md           # This file - version navigation
├── CLAUDE.md           # Development guidance
├── v1/                 # Original implementation
├── v2/                 # Current modern version
└── v3/                 # Future development
```

## Contributing

When working on this codebase:
- Use Version 2 for current development
- Preserve Version 1 for historical reference
- Plan Version 3 for major architectural changes
- See [CLAUDE.md](./CLAUDE.md) for development guidance