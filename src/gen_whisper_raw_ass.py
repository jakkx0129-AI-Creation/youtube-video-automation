import json
import os
import sys

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    json_path = os.path.join(assets_dir, "audio_segments_enhanced.json")
    output_ass = os.path.join(assets_dir, "karaoke_whisper_raw.ass")

    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JP_Main,Noto Sans CJK JP,75,&H00FFFFFF,&H00FFB7FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,2,2,10,10,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [ass_header]
    for seg in data:
        words = seg.get('words', [])
        if not words:
            continue

        start_t = format_time(seg['start'])
        end_t = format_time(seg['end'])

        k_text = ""
        for w in words:
            word = w['word'].strip()
            if not word:
                continue
            dur_s = w['end'] - w['start']
            cs = max(1, int(round(dur_s * 100)))
            k_text += f"{{\\k{cs}}}{word}"

        lines.append(f"Dialogue: 0,{start_t},{end_t},JP_Main,,0,0,0,,{k_text}\n")

    with open(output_ass, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"[OK] Whisper raw ASS -> {output_ass}")
    print(f"     Total segments: {len(data)}")

if __name__ == "__main__":
    main()
