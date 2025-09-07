"""
Centralized tag generation utilities for Anki-Assimil V3
Ensures consistent tagging format across all modules
"""
from typing import List, Optional
import re


def generate_deck_tag(deck_name: str) -> str:
    """
    Generate the base deck tag
    
    Args:
        deck_name: Name like 'assimil', 'pimsleur', etc.
        
    Returns:
        Deck tag like 'assimil'
    """
    return deck_name.lower()


def generate_lesson_tag(deck_name: str, lesson_num: int) -> str:
    """
    Generate hierarchical lesson tag using Anki's :: convention
    
    Args:
        deck_name: Name like 'assimil', 'pimsleur', etc.
        lesson_num: Lesson number (1-99)
        
    Returns:
        Hierarchical tag like 'assimil::L01'
    """
    deck_tag = generate_deck_tag(deck_name)
    return f"{deck_tag}::L{lesson_num:02d}"


def generate_lesson_tags(deck_name: str, lesson_num: int) -> List[str]:
    """
    Generate complete tag set for a lesson (both base and hierarchical)
    
    Args:
        deck_name: Name like 'assimil', 'pimsleur', etc.  
        lesson_num: Lesson number (1-99)
        
    Returns:
        List of tags: ['assimil', 'assimil::L01']
    """
    deck_tag = generate_deck_tag(deck_name)
    lesson_tag = generate_lesson_tag(deck_name, lesson_num)
    return [deck_tag, lesson_tag]


def parse_lesson_from_tags(tags: List[str], deck_name: str) -> Optional[int]:
    """
    Extract lesson number from tag list
    
    Args:
        tags: List of tags to search
        deck_name: Deck name to look for
        
    Returns:
        Lesson number if found, None otherwise
    """
    deck_tag = generate_deck_tag(deck_name)
    pattern = rf"^{re.escape(deck_tag)}::L(\d+)$"
    
    for tag in tags:
        match = re.match(pattern, tag)
        if match:
            return int(match.group(1))
    
    return None


def parse_lesson_number_from_tags(tags: List[str], deck_name: str) -> Optional[int]:
    """
    Extract lesson number from hierarchical tag
    
    Args:
        tags: List of tags to search  
        deck_name: Deck name to look for
        
    Returns:
        Lesson number if found, None otherwise
    """
    return parse_lesson_from_tags(tags, deck_name)


def format_tags_for_anki(tags: List[str]) -> str:
    """
    Format tag list for AnkiConnect API (space-separated string)
    
    Args:
        tags: List of tags
        
    Returns:
        Space-separated string for Anki API
    """
    return " ".join(tags)


def migrate_old_lesson_tag(old_tag: str, deck_name: str) -> Optional[str]:
    """
    Migrate old tag format to new hierarchical format
    
    Args:
        old_tag: Old format like 'assimil-01' or 'assimil01'
        deck_name: Target deck name
        
    Returns:
        New hierarchical tag like 'assimil::L01', or None if not recognized
    """
    deck_tag = generate_deck_tag(deck_name)
    
    # Match patterns like 'assimil-01', 'assimil01', 'assimil_01'
    pattern = rf"^{re.escape(deck_tag)}[-_]?(\d+)$"
    match = re.match(pattern, old_tag)
    
    if match:
        lesson_num = int(match.group(1))
        return generate_lesson_tag(deck_name, lesson_num)
    
    return None