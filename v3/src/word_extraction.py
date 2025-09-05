"""
Word extraction module for sequential lesson processing
Identifies new Hebrew words when they first appear in Assimil lessons
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError

from src.tokenizer import extract_hebrew_words, normalize_hebrew_word


@dataclass
class LessonWord:
    """Represents a word found in a lesson"""
    word: str
    normalized: str
    lesson: int
    first_occurrence: bool
    context: str  # The full phrase/sentence where word appears


@dataclass
class LessonData:
    """Represents data extracted from a lesson"""
    lesson_num: int
    phrases: List[str]
    words: List[LessonWord]
    audio_files: List[str]


class WordExtractor:
    """Extracts and tracks Hebrew words across sequential lessons"""

    def __init__(self, course_dir: Path):
        self.course_dir = Path(course_dir)
        self.seen_words: Set[str] = set()  # Normalized words we've seen
        self.lesson_words: Dict[int, List[LessonWord]] = {}

    def extract_text_from_mp3(self, mp3_path: Path) -> Optional[str]:
        """Extract Hebrew text from MP3 metadata"""
        try:
            audio = MP3(mp3_path)
            # Try different ID3 tags that might contain Hebrew text
            for tag in ['TIT2', 'TPE1', 'TALB', 'TPOS']:
                if tag in audio:
                    text = str(audio[tag])
                    if text and any('\u05d0' <= c <= '\u05ea' for c in text):
                        return text.strip()
        except (ID3NoHeaderError, Exception):
            pass
        return None

    def get_lesson_number(self, lesson_dir: Path) -> Optional[int]:
        """Extract lesson number from directory name"""
        match = re.search(r'L(\d+)', lesson_dir.name)
        return int(match.group(1)) if match else None

    def process_lesson_directory(self, lesson_dir: Path) -> Optional[LessonData]:
        """Process a single lesson directory and extract all Hebrew text"""
        lesson_num = self.get_lesson_number(lesson_dir)
        if lesson_num is None:
            return None

        phrases = []
        audio_files = []

        # Process all MP3 files in lesson directory
        mp3_files = sorted(lesson_dir.glob('*.mp3'))

        for mp3_file in mp3_files:
            # Skip translation files as specified in config
            if 'T00-TRANSLATE' in mp3_file.name:
                continue

            hebrew_text = self.extract_text_from_mp3(mp3_file)
            if hebrew_text:
                phrases.append(hebrew_text)
                audio_files.append(mp3_file.name)

        # Extract words from all phrases
        lesson_words = self._extract_lesson_words(phrases, lesson_num)

        return LessonData(
            lesson_num=lesson_num,
            phrases=phrases,
            words=lesson_words,
            audio_files=audio_files
        )

    def _extract_lesson_words(self, phrases: List[str], lesson_num: int) -> List[LessonWord]:
        """Extract and classify words from lesson phrases"""
        lesson_words = []

        for phrase in phrases:
            hebrew_words = extract_hebrew_words(phrase)

            for word in hebrew_words:
                normalized = normalize_hebrew_word(word)

                # Skip very short words (likely particles/prepositions)
                if len(normalized) < 2:
                    continue

                # Check if this is first occurrence
                first_occurrence = normalized not in self.seen_words

                lesson_word = LessonWord(
                    word=word,
                    normalized=normalized,
                    lesson=lesson_num,
                    first_occurrence=first_occurrence,
                    context=phrase
                )

                lesson_words.append(lesson_word)

                # Mark as seen
                self.seen_words.add(normalized)

        return lesson_words

    def process_lessons_sequential(self, max_lessons: Optional[int] = None) -> Dict[int, LessonData]:
        """
        Process lessons sequentially to track word first occurrences

        Args:
            max_lessons: Maximum number of lessons to process (None for all)

        Returns:
            Dictionary mapping lesson numbers to LessonData
        """
        lessons_data = {}

        # Get sorted lesson directories
        lesson_dirs = sorted([d for d in self.course_dir.iterdir()
                             if d.is_dir() and re.match(r'L\d+', d.name)])

        if max_lessons:
            lesson_dirs = lesson_dirs[:max_lessons]

        for lesson_dir in lesson_dirs:
            lesson_data = self.process_lesson_directory(lesson_dir)
            if lesson_data:
                lessons_data[lesson_data.lesson_num] = lesson_data
                self.lesson_words[lesson_data.lesson_num] = lesson_data.words

        return lessons_data

    def get_new_words_by_lesson(self, lesson_num: int) -> List[LessonWord]:
        """Get all words that first appeared in a specific lesson"""
        if lesson_num not in self.lesson_words:
            return []

        return [word for word in self.lesson_words[lesson_num]
                if word.first_occurrence]

    def get_all_new_words(self) -> List[LessonWord]:
        """Get all words that were first occurrences across all processed lessons"""
        new_words = []
        for lesson_words in self.lesson_words.values():
            new_words.extend([word for word in lesson_words if word.first_occurrence])
        return new_words

    def get_word_stats(self) -> Dict[str, int]:
        """Get statistics about processed words"""
        total_words = sum(len(words) for words in self.lesson_words.values())
        unique_words = len(self.seen_words)
        new_words = len(self.get_all_new_words())

        return {
            'total_words': total_words,
            'unique_words': unique_words,
            'new_words': new_words,
            'lessons_processed': len(self.lesson_words)
        }


def extract_words_from_config(config: dict) -> WordExtractor:
    """Create WordExtractor from configuration"""
    course_dir = Path(config['paths']['assimil_course_dir'])
    return WordExtractor(course_dir)


if __name__ == "__main__":
    # Test with sample data
    import yaml

    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    extractor = extract_words_from_config(config)
    lessons = extractor.process_lessons_sequential(max_lessons=3)

    print("Word extraction stats:", extractor.get_word_stats())

    for lesson_num, lesson_data in lessons.items():
        new_words = extractor.get_new_words_by_lesson(lesson_num)
        print(f"\nLesson {lesson_num}: {len(new_words)} new words")
        for word in new_words[:5]:  # Show first 5
            print(f"  {word.word} ({word.normalized}) - '{word.context}'")