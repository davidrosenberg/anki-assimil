# Anki-Assimil V2

Modern Hebrew Assimil-to-Anki integration system that connects Assimil language course materials with Anki spaced repetition flashcards.

## What This System Does

**Creates two things:**
1. **Anki deck of Assimil sentences** - dialogue lines and exercises with audio and English translations
2. **Updated Hebrew vocabulary deck** - adds lesson tags to existing words showing where they first appear

This connects structured lessons with spaced repetition learning.

## Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Edit configuration
vi input/config.yaml  # Update paths as needed
```

## Complete Workflow

### Step 1: Prepare Input Files

1. **Export your Anki Hebrew deck** as tab-separated text to `input/alldecks.txt`
2. **Place Assimil MP3 files** in `test-data/assimil-course/L*/` directories
3. **Configure paths** in `input/config.yaml`

### Step 2: Extract Audio and Text

```bash
python main.py extract-audio --lessons 1-5
```

Generates `generated/assimil-init.csv` with Hebrew text extracted from MP3 metadata and "NA" placeholders for English.

### Step 3: Add English Translations (Manual)

1. Copy `generated/assimil-init.csv` to `data/assimil.csv`
2. Replace "NA" placeholders with English translations

### Step 4: Generate Word Matches

```bash
python main.py match-words
```

Creates `generated/assimil-words-init.csv` with suggestions for matching Hebrew words to your existing vocabulary.

### Step 5: Curate Word Matches (Manual)

1. Review `generated/assimil-words-init.csv` suggestions  
2. Copy good matches to `data/assimil-words.csv`
3. Add manual matches to `data/assimil-words-extra.csv` if needed

### Step 6: Export for Anki

```bash
python main.py export-anki
```

Creates `generated/assimil-tag-update.csv` for importing back into Anki with lesson tags.

### Step 7: Import into Anki

1. **Import phrase cards**: Import `data/assimil.csv` as new deck
2. **Update vocabulary tags**: Import `generated/assimil-tag-update.csv` to add lesson tags

## File Structure

- `input/` - Source files (manually controlled)
  - `config.yaml` - Configuration file
  - `alldecks.txt` - Your Anki export
- `data/` - Human-curated files (most valuable)
  - `assimil.csv` - Phrase translations (generated → human-filled)
  - `assimil-words.csv` - Word matches (generated → human-curated)  
  - `assimil-words-extra.csv` - Additional matches (human-added)
- `generated/` - Auto-generated files (don't edit these)
- `src/` - Source code modules

## Key Files Explained

### assimil.csv - Phrase Cards Content
Contains content for individual Assimil phrase/sentence flashcards.

**How it's created:**
1. Run `python main.py extract-audio` to generate `generated/assimil-init.csv` with "NA" placeholders
2. Copy to `data/assimil.csv` and manually replace "NA" with English translations

**Each row represents:**
- One phrase/sentence from Assimil lessons (dialogue lines, exercises)
- Hebrew text extracted from MP3 metadata  
- Your English translation
- Audio file reference for pronunciation
- Lesson tags for organization

**When imported to Anki, creates cards like:**
- **Front:** "בּוֹקֶר טוֹב!" (with audio)
- **Back:** "Good morning!"
- **Tags:** assimil, assimil-01

## Commands

```bash
python main.py status           # Check file status
python main.py extract-audio    # Extract from MP3s → generated/assimil-init.csv  
python main.py match-words      # Generate word matches → generated/assimil-words-init.csv
python main.py export-anki      # Create final import → generated/assimil-tag-update.csv
```