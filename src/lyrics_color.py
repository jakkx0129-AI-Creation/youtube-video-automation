import re

# Keyword-to-color mapping for mood-based lyric analysis
# Each entry: keyword regex -> (R, G, B) as 0-255
MOOD_COLORS = [
    (r'桜|さくら', (255, 182, 193)),       # sakura pink
    (r'春|はる', (255, 200, 180)),          # spring peach
    (r'恋|こい', (255, 150, 150)),          # love red-pink
    (r'花|はな|咲', (255, 192, 203)),       # flower pink
    (r'空|そら|風|かぜ', (180, 220, 255)),  # sky blue
    (r'夢|ゆめ', (200, 180, 255)),          # dream purple
    (r'幸|しあわせ|輝|かがや', (255, 215, 150)),  # happiness gold
    (r'雪|ゆき', (200, 220, 255)),          # snow ice blue
    (r'涙|なみだ|泣', (180, 200, 230)),     # tear blue-grey
    (r'夕|ゆう|暮', (255, 160, 120)),       # sunset orange
]

DEFAULT_COLOR = (255, 255, 255)  # white fallback

def pick_lyrics_color(jp_text):
    """Analyze Japanese lyrics text and pick a mood-matching color."""
    scores = []
    for pattern, color in MOOD_COLORS:
        matches = re.findall(pattern, jp_text)
        if matches:
            scores.append((len(matches), color))

    if not scores:
        return DEFAULT_COLOR

    # Pick the color with the most keyword matches
    scores.sort(key=lambda x: -x[0])
    return scores[0][1]

def color_to_ass(r, g, b):
    """Convert RGB to ASS color format &H00BBGGRR."""
    return f"&H00{b:02X}{g:02X}{r:02X}"
