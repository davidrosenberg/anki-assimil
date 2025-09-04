# Anki-Assimil Version 3 (Planned)

Future modernized version of the Hebrew Assimil-to-Anki integration system.

## Status
🚧 **In Development** - V2 is obsolete due to Anki export format changes

## Planned Improvements

Version 3 will build on V2's foundation with modern enhancements:

### Architecture
- Enhanced modular design
- Improved error handling and validation
- Better configuration management
- Plugin architecture for extensibility

### User Experience  
- Interactive CLI with guided workflows
- Progress tracking and resume capability
- Better validation and error messages
- Automated backup and recovery

### Technical Improvements
- **Direct Anki integration via AnkiConnect API**
  - Read vocabulary via SQLite (read-only, efficient)
  - Write tags via AnkiConnect (safe, validated)
  - Eliminate export/import cycle entirely
- Type hints throughout codebase
- Comprehensive test suite
- CI/CD pipeline integration
- Performance optimizations

### Features
- Support for multiple language courses
- Advanced matching algorithms
- Batch processing capabilities
- Integration with multiple SRS systems
- **Auto-generate vocabulary cards for unmatched Assimil words**
  - Identify words in lessons not present in existing Anki deck
  - Extract/lookup definitions for new vocabulary
  - Create new Anki cards with proper lesson tagging
  - Complete vocabulary coverage for each lesson

## Future Enhancements

### English Translation Matching (V1 Feature)
V1 implemented a sophisticated dual matching approach using both Hebrew-Hebrew similarity and English translation context that V3 currently lacks:

- **Cross-language validation**: Used lesson English translations to find Hebrew candidates via reverse lookup
- **Context-aware matching**: English words like "morning" → Hebrew candidates ["בוקר", ...] 
- **Higher confidence matches**: Hebrew similarity + English context validation

This approach provided better match quality by leveraging semantic context, but was omitted from V3 to focus on architectural improvements. Could be reintroduced as an optional matching strategy to improve precision.

## Migration from V2

When V3 is ready, migration from V2 will include:
- Automated configuration conversion
- Data format compatibility
- Step-by-step migration guide

## Development

V3 development will begin after V2 reaches feature completeness. See [Version 2](../v2/) for current development.