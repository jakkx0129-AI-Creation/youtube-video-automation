import json
import os
import sys

def adjust_long_gaps(align_path, gap_multiplier=3.0, extend_s=3.0):
    """
    If gap between consecutive stanzas is significantly longer than average,
    extend the current stanza's end time by `extend_s` seconds.

    gap = next.stanza.start - current.stanza.end
    If gap > avg_gap * gap_multiplier, extend current.end by extend_s.

    Returns (adjusted count, overlap errors).
    """
    with open(align_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if len(data) < 2:
        return 0, []

    # Compute gaps
    gaps = []
    for i in range(len(data) - 1):
        gap = data[i + 1]['start'] - data[i]['end']
        gaps.append(gap)

    avg_gap = sum(gaps) / len(gaps)

    print(f"[Adjust] {len(data)} stanzas, avg gap: {avg_gap:.2f}s")
    print(f"[Adjust] Raw gaps: {[f'{g:.2f}' for g in gaps]}")

    threshold = avg_gap * gap_multiplier
    print(f"[Adjust] Threshold (avg * {gap_multiplier}): {threshold:.2f}s")

    adjusted = 0
    overlaps = []

    for i in range(len(data) - 1):
        gap = gaps[i]
        new_end = data[i]['end'] + extend_s

        if gap > threshold:
            if new_end > data[i + 1]['start']:
                overlaps.append(i)
                print(f"[OVERLAP] Stanza {i+1}: current.end {data[i]['end']:.2f}s "
                      f"+ {extend_s}s = {new_end:.2f}s > "
                      f"stanza {i+2}.start ({data[i+1]['start']:.2f}s)")
            else:
                data[i]['end'] = new_end
                adjusted += 1
                print(f"[Adjust] Stanza {i+1}: end {data[i]['end'] - extend_s:.2f}s -> {new_end:.2f}s "
                      f"(gap={gap:.2f}s, >{threshold:.2f}s)")

    if overlaps:
        print(f"\n[ERROR] {len(overlaps)} overlap(s) detected. Exiting.")
        for idx in overlaps:
            print(f"  Stanza {idx+1} -> Stanza {idx+2}")
        sys.exit(1)

    if adjusted == 0:
        print("[Adjust] No long gaps detected.")
        return adjusted, overlaps

    # Also shift all words within affected stanzas so the extra time is
    # distributed proportionally to the last word(s)
    for i in range(len(data) - 1):
        gap = gaps[i]
        if not (gap > threshold):
            continue
        stanza = data[i]
        if not stanza['words']:
            continue
        diff = extend_s  # extra time we added
        last_word = stanza['words'][-1]
        last_word['end'] += diff

    with open(align_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[Adjust] Extended {adjusted} stanza(s). Saved.")
    return adjusted, overlaps

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    align_path = os.path.join(base_dir, "assets", "lyrics_alignment.json")
    adjust_long_gaps(align_path)
