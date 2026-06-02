import json
import os
import sys

def format_time(seconds):
    """Convert seconds to ASS format H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    json_path = os.path.join(assets_dir, "lyrics_alignment.json")
    output_ass = os.path.join(assets_dir, "karaoke_lyrics.ass")
    
    if not os.path.exists(json_path):
        print(f"Error: lyrics_alignment.json not found at {json_path}")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # ASS Header & Styles
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JP_Main,Noto Sans CJK JP,75,&H00FFFFFF,&H00FFB7FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,2,2,10,10,80,1
Style: CN_Sub,Noto Sans CJK JP,60,&H00EEEEEE,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [ass_header]
    for item in data:
        start_t = format_time(item['start'])
        end_t = format_time(item['end'])
        
        # Construct Karaoke Text
        k_text = ""
        prev_end = item['words'][0]['start'] if item.get('words') else item['start']
        
        # If the JP text has \\N from the alignment process, we need to handle it.
        # But we must insert \k tags between words.
        # We'll reconstruct the line by line display
        
        current_word_idx = 0
        jp_lines_list = item['jp'].split("\\N")
        
        final_line_parts = []
        for line in jp_lines_list:
            line_k = ""
            # Find words belonging to this line
            line_chars = [c for c in line if c.strip() and c not in "、。　"]
            for _ in range(len(line_chars)):
                if current_word_idx < len(item['words']):
                    w = item['words'][current_word_idx]
                    duration_cs = int(round((w['end'] - w['start']) * 100))
                    gap_cs = int(round((w['start'] - prev_end) * 100))
                    total_cs = duration_cs + max(0, gap_cs)
                    if total_cs < 1:
                        total_cs = 1
                    line_k += f"{{\\k{total_cs}}}{w['word']}"
                    prev_end = w['end']
                    current_word_idx += 1
            final_line_parts.append(line_k)
        
        combined_k_text = "\\N".join(final_line_parts)

        # JP Main Line (Karaoke with Line Breaks)
        lines.append(f"Dialogue: 0,{start_t},{end_t},JP_Main,,0,0,0,,{combined_k_text}\n")
        # CN Sub Line (Bigger Font)
        lines.append(f"Dialogue: 0,{start_t},{end_t},CN_Sub,,0,0,0,,{item['cn']}\n")

    with open(output_ass, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"\n[SUCCESS] Final Karaoke ASS file generated: {output_ass}")

if __name__ == "__main__":
    main()
