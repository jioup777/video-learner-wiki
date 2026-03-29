# Changelog

All notable changes to the Video Learner skill will be documented in this file.

## [1.0.0] - 2026-03-12

### Added
- Full video processing pipeline
- Bilibili and YouTube support
- Whisper transcription integration
- Intelligent note generation
  - Keyword extraction (15 keywords)
  - Core points extraction (3-5 points)
  - Practice tips extraction (3-5 tips)
  - Core quotes extraction (5 quotes)
- Feishu knowledge base integration
  - Automatic document creation
  - Content upload
  - Link generation
- Bilibili cookies support
- Automatic file cleanup
- Progress tracking and reporting

### Scripts
- `video_with_feishu.sh` - Full pipeline (download → transcript → note → upload)
- `video_processor.sh` - Basic pipeline (download → transcript → note)
- `smart_note_generator.py` - Intelligent note extraction
- `upload_feishu.sh` - Feishu upload helper

### Documentation
- SKILL.md - Complete documentation
- README.md - Quick reference guide
- COOKIES.md - Bilibili cookies setup guide
- CHANGELOG.md - This file

### Performance
- 2 min video: ~36s total
- 3 min video: ~53s total
- 5 min video: ~86s total

### Dependencies
- yt-dlp (video download)
- openai-whisper (transcription)
- Python 3.8+
- Feishu API (for upload)

---

## [Unreleased] - Future Improvements

### Planned
- [ ] Local LLM integration for better note extraction
- [ ] Batch processing support
- [ ] Resume/pause functionality
- [ ] Code snippet extraction
- [ ] Table and data extraction
- [ ] YouTube subtitle support (preferred over Whisper)
- [ ] Custom note templates
- [ ] Export to other formats (PDF, DOCX)

### Optimization
- [ ] Improve keyword extraction accuracy
- [ ] Better core points detection
- [ ] Faster Whisper model selection
- [ ] Multi-threaded processing for batch

---

## Version Format

- Major.Minor.Patch (e.g., 1.0.0)
- Major: Incompatible API changes
- Minor: Backwards-compatible functionality
- Patch: Backwards-compatible bug fixes

---

Last Updated: 2026-03-12
