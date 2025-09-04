# Anki-Assimil Version 1 (Legacy)

Original implementation of the Hebrew Assimil-to-Anki integration system.

## Status
📦 **Archived** - Preserved for reference and comparison

## Files

### Core Scripts
- `anki-assimil.py` - Main processing script
- `update-assimil.py` - Anki deck update functionality  
- `write-data-file.py` - Data file generation
- `hebtokenizer.py` - Hebrew text tokenization
- `other-stuff.py` - Additional utilities

### Data Files
- `alldecks.txt` - Anki vocabulary export
- `assimil*.csv` - Various CSV files for processing
- `wordlist.txt` - Hebrew vocabulary list
- `lookup.txt` - Word lookup data

### Documentation
- `README.org` - Original documentation in Org format

## Usage

This version uses individual Python scripts:

```bash
python anki-assimil.py        # Main processing
python update-assimil.py      # Update functionality
python write-data-file.py     # Generate data files
```

## Migration to V2

For current usage, please use [Version 2](../v2/) which provides:
- Modern CLI interface with Typer
- Better error handling and progress display
- Modular architecture for easier maintenance
- Rich terminal output with colors and tables

## Historical Context

This version represents the original proof-of-concept implementation that established the core workflow for integrating Assimil course materials with Anki flashcards.