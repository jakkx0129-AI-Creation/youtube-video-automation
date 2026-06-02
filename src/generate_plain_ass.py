import json
import os
import sys

from lyrics_color import pick_lyrics_color, color_to_ass

def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    json_path = os.path.join(assets_dir, "lyrics_alignment.json")
    output_ass = os.path.join(assets_dir, "karoke_plain.ass")

    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # AI lyric color analysis: pick a mood-based color for Japanese text
    full_jp = ' '.join(item['jp'] for item in data)
    r, g, b = pick_lyrics_color(full_jp)
    jp_color = color_to_ass(r, g, b)
    print(f"[Color] Lyrics analysis -> RGB({r},{g},{b}) = {jp_color}")

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JP_Main,Noto Sans CJK JP,75,{jp_color},&H00FFB7FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,2,2,10,10,80,1
Style: CN_Sub,Noto Sans CJK JP,60,&H00EEEEEE,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [ass_header]
    for item in data:
        start_t = format_time(item['start'])
        end_t = format_time(item['end'])
        jp_text = item['jp'].replace('\\N', '\\N')
        cn_text = item['cn'].replace('\n', '\\N')
        lines.append(f"Dialogue: 0,{start_t},{end_t},JP_Main,,0,0,0,,{jp_text}\n")
        lines.append(f"Dialogue: 0,{start_t},{end_t},CN_Sub,,0,0,0,,{cn_text}\n")

    with open(output_ass, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"[OK] Plain ASS (no karaoke) -> {output_ass}")

if __name__ == "__main__":
    main()
