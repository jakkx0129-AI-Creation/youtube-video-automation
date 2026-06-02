# 歌詞對齊影片自動生成

Automated bilingual-subtitle video pipeline: separate vocals → ASR → lyrics alignment → FFmpeg synthesis.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1. Vocals | `src/separate_vocals_fix.py` | `separated/htdemucs/music_vocals.wav` |
| 2. ASR | `src/run_whisper_enhanced.py` | `assets/audio_segments_enhanced.json` |
| 3. Alignment | `src/align_by_stanza_v4.py` | `assets/lyrics_alignment.json` |
| 4. ASS Gen | `src/generate_plain_ass.py` | `assets/karoke_plain.ass` |
| 5. Images | `src/visual_agent.py` | `assets/processed_*.jpg` |
| 6. Render | `src/synthesis_agent.py` | `output/final_video.mp4` |

## Quick Start

```bash
pip install -r requirements.txt
python -m unidic download  # fugashi dictionary
# Put lyrics_jp.txt + lyrics.txt (line-by-line, blank-line stanza separator)
# Put any .jpg files in assets/ (e.g. master_1.jpg, photo_a.jpg...)
# Put music.wav in assets/

python src/separate_vocals_fix.py assets/music.wav assets/music_vocals.wav
python src/run_whisper_enhanced.py
python src/align_by_stanza_v4.py
python src/generate_plain_ass.py
python src/visual_agent.py
python src/synthesis_agent.py
```

See `AGENTS.md` for detailed conventions and environment setup.

## Convention

- `src/` — formal pipeline scripts only
- `scratch/` — one-off tests / deprecated scripts (not tracked in git)
