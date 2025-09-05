"""
AnkiConnect API integration for direct Anki communication
"""
import os
import requests
from typing import Dict, List, Optional, Any
from rich.console import Console

console = Console()

def _anki_url() -> str:
    """Resolve AnkiConnect URL from env with sensible default."""
    return os.getenv("ANKI_CONNECT_URL", "http://localhost:8765")

def anki_request(action: str, params: Dict = None) -> Optional[Any]:
    """
    Make a request to AnkiConnect API

    Args:
        action: AnkiConnect action name
        params: Parameters for the action

    Returns:
        Response data or None if failed
    """
    if params is None:
        params = {}

    payload = {
        "action": action,
        "version": 6,
        "params": params
    }

    try:
        response = requests.post(_anki_url(), json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        if result.get("error"):
            console.print(f"[red]AnkiConnect error:[/red] {result['error']}")
            return None

        return result.get("result")

    except requests.exceptions.RequestException as e:
        console.print(f"[red]Failed to connect to AnkiConnect:[/red] {e}")
        return None

def check_anki_connection() -> bool:
    """Check if AnkiConnect is available"""
    result = anki_request("version")
    return result is not None

def get_deck_info(deck_name: str) -> Optional[Dict]:
    """
    Get information about a specific deck

    Args:
        deck_name: Name of the deck

    Returns:
        Deck info dictionary or None if not found
    """
    # Verify deck exists
    deck_names = anki_request("deckNames")
    if not deck_names or deck_name not in deck_names:
        return None

    # Compute counts via findCards queries
    total_cards = anki_request("findCards", {"query": f"deck:\"{deck_name}\""}) or []
    new_cards = anki_request("findCards", {"query": f"deck:\"{deck_name}\" is:new"}) or []
    review_cards = anki_request("findCards", {"query": f"deck:\"{deck_name}\" is:review"}) or []

    return {
        "name": deck_name,
        "card_count": len(total_cards),
        "new_count": len(new_cards),
        "review_count": len(review_cards),
    }


def add_tags_to_notes(note_ids: List[int], tags: List[str]) -> bool:
    """
    Add tags to existing notes

    Args:
        note_ids: List of note IDs to update
        tags: List of tags to add

    Returns:
        True if successful
    """
    import requests

    # Make request directly to properly handle null vs error
    payload = {
        "action": "addTags",
        "version": 6,
        "params": {
            "notes": note_ids,
            "tags": " ".join(tags)
        }
    }
    
    try:
        response = requests.post(_anki_url(), json=payload, timeout=10)
        response.raise_for_status()

        result = response.json()
        # Check for AnkiConnect errors
        if result.get("error"):
            console.print(f"[red]AnkiConnect error:[/red] {result['error']}")
            return False

        # If we got here, the request succeeded (even if result is null)
        return True

    except requests.exceptions.RequestException as e:
        console.print(f"[red]Failed to connect to AnkiConnect:[/red] {e}")
        return False

def update_note_tags(note_id: int, tags: List[str]) -> bool:
    """
    Replace all tags on a note

    Args:
        note_id: Note ID to update
        tags: List of tags to set (replaces existing tags)

    Returns:
        True if successful or no change needed
    """
    # Get the current note info to see existing tags
    note_info = anki_request("notesInfo", {"notes": [note_id]})
    if not note_info:
        return False

    current_tags = set(note_info[0].get("tags", []))
    target_tags = set(tags)

    # Check if tags are already correct
    if current_tags == target_tags:
        return True  # No change needed

    # Remove existing tags from this note
    if current_tags:
        anki_request("removeTags", {
            "notes": [note_id],
            "tags": " ".join(current_tags)
        })

    # Add new tags
    if tags:
        result = anki_request("addTags", {
            "notes": [note_id],
            "tags": " ".join(tags)
        })
        return result is not None

    return True

def create_deck(deck_name: str) -> bool:
    """
    Create a new deck in Anki

    Args:
        deck_name: Name of the deck to create

    Returns:
        True if successful or deck already exists
    """
    # Check if deck already exists
    deck_names = anki_request("deckNames")
    if deck_names and deck_name in deck_names:
        console.print(f"[yellow]Deck '{deck_name}' already exists[/yellow]")
        return True

    # Create the deck
    result = anki_request("createDeck", {"deck": deck_name})

    if result is not None:
        console.print(f"[green]✓[/green] Created deck: {deck_name}")
        return True
    else:
        console.print(f"[red]Failed to create deck: {deck_name}[/red]")
        return False

def add_tags_to_cards(card_ids: List[int], tags: List[str]) -> bool:
    """
    Add tags to cards by converting to note IDs

    Args:
        card_ids: List of card IDs to update
        tags: List of tags to add

    Returns:
        True if successful
    """
    if not card_ids:
        return True

    # Get card info to find note IDs
    cards_info = anki_request("cardsInfo", {"cards": card_ids})
    if not cards_info:
        return False

    # Extract unique note IDs
    note_ids = list(set(card_info["note"] for card_info in cards_info))

    # Add tags to notes
    return add_tags_to_notes(note_ids, tags)

def create_note(deck_name: str, model_name: str, fields: Dict[str, str],
                tags: List[str] = None) -> Optional[int]:
    """
    Create a new note in Anki

    Args:
        deck_name: Target deck name
        model_name: Note type name
        fields: Dictionary of field name -> field value
        tags: List of tags to add

    Returns:
        Note ID if successful, None if failed
    """
    if tags is None:
        tags = []

    note_data = {
        "deckName": deck_name,
        "modelName": model_name,
        "fields": fields,
        "tags": tags
    }

    result = anki_request("addNote", {"note": note_data})
    return result
