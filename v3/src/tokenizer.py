#!/usr/bin/env python3
"""
Hebrew tokenizer for Anki-Assimil v3
Based on Yoav Goldberg's Hebrew tokenizer
"""

import re
from typing import List, Tuple, Iterator

# Token types
TokenType = str
Token = Tuple[TokenType, str]

def heb(s: str, t: str) -> Token:
    return ('HEB', t)

def eng(s: str, t: str) -> Token:
    return ('ENG', t)

def num(s: str, t: str) -> Token:
    return ('NUM', t)

def url(s: str, t: str) -> Token:
    return ('URL', t)

def punct(s: str, t: str) -> Token:
    return ('PUNCT', t)

def junk(s: str, t: str) -> Token:
    return ('JUNK', t)

# Unicode ranges for Hebrew text processing
_NIKUD = "\u05b0-\u05c4"  # Hebrew vowel points (nikud)
_TEAMIM = "\u0591-\u05af"  # Hebrew cantillation marks (teamim)

def undigraph(x: str) -> str:
    """Convert Hebrew digraphs to regular letters"""
    return (x.replace("\u05f0", "וו")  # Hebrew ligature Yod Yod
             .replace("\u05f1", "וי")  # Hebrew ligature Vav Yod
             .replace("\u05f2", "יי")  # Hebrew ligature Yod Yod Patah
             .replace("\ufb4f", "אל")  # Hebrew ligature Alef Lamed
             .replace("\u200d", ""))   # Zero width joiner

#### Pattern definitions ####

# Hebrew letter: includes basic Hebrew letters + nikud, plus געדצתט with geresh (')
_heb_letter = r"([\u05d0-\u05ea\u05b0-\u05c4]|[\u05d3\u05d2\u05d6\u05e6\u05ea\u05d8]')"

# Hebrew word - individual words only, no spaces
_heb_word_plus = r'[\u05d0-\u05ea\u05b0-\u05c4][\u05d0-\u05ea\u05b0-\u05c40-9]*'

# English/Latin words (do not care about abbreviations vs. eos for english)
_eng_word = r"[a-zA-Z][a-zA-Z0-9'.-]*"

# Numerical expression (numbers and various separators)
_numeric = r"[+\-]?([0-9][0-9.,/:_-]*)?[0-9]%?"

# URL patterns
_url = r"[a-z]+://\S+"

# Punctuation patterns
_opening_punc = r"[\[('`\"{]"      # Opening punctuation
_closing_punc = r"[\])'`\"}]"      # Closing punctuation
_eos_punct = r"[!?.]+\*?"          # End of sentence punctuation (with optional *)
_internal_punct = r"[,;:&_-]"      # Internal punctuation

# Junk: everything that's not Hebrew, Latin, digits, or basic punctuation
_junk = f"[^א-ת{_NIKUD}a-zA-Z0-9!?.,:;()\\[\\]{{}}_ \\-]+"

#### Regex matchers for token classification ####
is_all_heb = re.compile(f"^{_heb_letter}+$", re.UNICODE).match
is_a_number = re.compile(f"^{_numeric}$", re.UNICODE).match
is_all_lat = re.compile(r"^[a-zA-Z]+$", re.UNICODE).match
is_sep = re.compile(r"^\|+$").match
is_punct = re.compile(r"^[.?!]+").match

#### Scanner for tokenization ####
# Order matters! More specific patterns should come first
scanner = re.Scanner([
    (r"\s+", None),           # Skip whitespace entirely
    (_url, url),              # URLs (before other patterns)
    (_heb_word_plus, heb),    # Hebrew words with punctuation
    (_eng_word, eng),         # English/Latin words
    (_numeric, num),          # Numbers with separators
    (_opening_punc, punct),   # Opening brackets/quotes
    (_closing_punc, punct),   # Closing brackets/quotes
    (_eos_punct, punct),      # End of sentence punctuation
    (_internal_punct, punct), # Commas, colons, etc.
    (_junk, junk),           # Everything else
])

def tokenize(text: str) -> List[Token]:
    """
    Tokenize Hebrew text into typed tokens

    Args:
        text: Hebrew text to tokenize

    Returns:
        List of (type, token) tuples
    """
    tokens, remainder = scanner.scan(text)
    if remainder:
        # If there's unparsed text, treat it as junk
        tokens.append(('JUNK', remainder))
    return tokens

def extract_hebrew_words(text: str) -> List[str]:
    """
    Extract only Hebrew words from text

    Args:
        text: Text to extract Hebrew words from

    Returns:
        List of Hebrew words (normalized)
    """
    tokens = tokenize(text)
    hebrew_words = []

    for token_type, token in tokens:
        if token_type == 'HEB':
            # Clean and normalize the Hebrew word
            cleaned = undigraph(token.strip())
            if cleaned:
                hebrew_words.append(cleaned)

    return hebrew_words

def normalize_hebrew_word(word: str) -> str:
    """
    Normalize Hebrew word for consistent matching

    Args:
        word: Hebrew word to normalize

    Returns:
        Normalized Hebrew word
    """
    # Remove nikud and teamim for base form matching
    normalized = re.sub(f"[{_NIKUD}{_TEAMIM}]", "", word)
    normalized = undigraph(normalized)
    return normalized.strip()

if __name__ == "__main__":
    # Test with sample Hebrew text
    test_text = "בוקר טוב! איך אתה?"
    tokens = tokenize(test_text)
    words = extract_hebrew_words(test_text)

    print("Tokens:", tokens)
    print("Hebrew words:", words)