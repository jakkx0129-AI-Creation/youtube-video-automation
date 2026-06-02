# AGENTS.md — Karaoke Video Automation

## Must-Read First
- `TECH_PROTOCOLS.md` — 5 core alignment protocols (semantic hiragana, sandwich boundary, syllable slot filling, word-level mapping, RMS conflict resolution). All alignment code must follow these.

## Pipeline (sequential stages)
1. **Vocals Separation**: `python src/separate_vocals_fix.py <input.wav> <output.wav>` — Demucs htdemucs on CPU
2. **ASR**: `python src/run_whisper_enhanced.py` — faster-whisper large-v3 on CPU, `word_timestamps=True`, `no_speech_threshold=0.1`
3. **Lyrics Alignment**: `python src/align_by_stanza_v4.py` — DTW-based with VVBT (vocals valley trimming); reads `audio_segments_enhanced.json` + `lyrics_jp.txt` + `lyrics.txt`, writes `lyrics_alignment.json`
4. **ASS Subtitle Gen**: `python src/generate_plain_ass.py` — reads `lyrics_alignment.json`, writes `karoke_plain.ass` (no karaoke tags)
5. **Image Processing**: `python src/visual_agent.py` — resizes `master_m/n/o.jpg` → `processed_1/2/3.jpg` at 1920×1080
6. **Final Synthesis**: `python src/synthesis_agent.py` — runs ffmpeg (images + audio + ASS) → `output/final_video.mp4`

## Entry Point Scripts

| Directory | File | Purpose |
|---|---|---|
| `src/` | `separate_vocals_fix.py` | Demucs voice separation |
| `src/` | `run_whisper_enhanced.py` | ASR → `audio_segments_enhanced.json` |
| `src/` | `align_by_stanza_v4.py` | DTW alignment (current) |
| `src/` | `generate_plain_ass.py` | Static ASS (no karaoke) |
| `src/` | `adjust_long_gaps.py` | Extend stanzas with long gaps |
| `src/` | `lyrics_color.py` | AI color picker for JP subs |
| `src/` | `visual_agent.py` | Image resize + letterbox |
| `src/` | `synthesis_agent.py` | FFmpeg final render |
| `scratch/` | *(all old/obsolete scripts)* | Kept for reference, not in pipeline |

## Project Layout
- `assets/` — all input/output artifacts (audio, lyrics, images, segment JSONs, subtitle files)
- `output/` — final `final_video.mp4`
- `separated/htdemucs/` — Demucs output (intermediate)
- `src/` — **正式 pipeline 程式碼**（只放會用到的）
- `scratch/` — **測試用/已棄用的腳本**，一律不加 git

## Key Conventions
- **`src/` vs `scratch/`**: pipeline 正式腳本放 `src/`，試過就丟的測試碼放 `scratch/`。上 GitHub 只加 `src/`，跳過 `scratch/`。
- All scripts use `os.path.dirname(os.path.abspath(__file__))` × 2 to resolve project root; run from any cwd
- No test framework, no linter, no type checker
- Input lyrics format: `lyrics_jp.txt` + `lyrics.txt` (line-by-line parallel, blank lines separate stanzas)
- All segments JSONs have `word_timestamps` with `{start, end, word}` per word
- Alignment output format: list of stanzas with `{start, end, jp, cn, words: [{word, start, end}]}`
- Demucs `separate_vocals_fix.py` was created to work around `torchcodec` import errors

## Environment
- CPU-only (`device="cpu"` for both whisper and Demucs)
- All dependencies in `requirements.txt` (fugashi + unidic-lite, faster-whisper, demucs, torch, pillow, librosa, numpy, soundfile)
- fugashi + unidic-lite replaces pykakasi for hiragana conversion (morphological analysis correctly handles compound words like 桜吹雪→さくらふぶき)
- Also needs: `ffmpeg` (system install)

## Verification (Manual)
- No test framework exists. Verify output by checking for files in `output/` or `assets/` and inspecting logs.
- For alignment, inspect `lyrics_alignment.json`.
- For ASS generation, inspect `karaoke_lyrics.ass` for `{\k}` tags.
