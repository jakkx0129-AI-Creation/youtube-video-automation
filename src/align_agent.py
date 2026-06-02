import json
import os
from fugashi import Tagger
import sys

def get_hira(text, tagger):
    clean = text.replace(" ", "").replace("　", "").replace("、", "").replace("。", "").strip()
    res = []
    for word in tagger(clean):
        kana = word.feature.kana
        if kana == '*':
            kana = word.surface
        hira = ''.join(chr(ord(c) - 96) if 'ァ' <= c <= 'ヴ' else c for c in kana)
        res.append(hira)
    return "".join(res)

def main():
    tagger = Tagger()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    
    segments_path = os.path.join(assets_dir, "audio_segments.json")
    jp_path = os.path.join(assets_dir, "lyrics_jp.txt")
    cn_path = os.path.join(assets_dir, "lyrics.txt")
    output_json = os.path.join(assets_dir, "lyrics_alignment.json")
    
    if not os.path.exists(segments_path): return
    with open(segments_path, 'r', encoding='utf-8') as f: segments = json.load(f)
    with open(jp_path, 'r', encoding='utf-8') as f: jp_lines = f.read().splitlines()
    with open(cn_path, 'r', encoding='utf-8') as f: cn_lines = f.read().splitlines()

    stanzas_jp = []
    stanzas_cn = []
    curr_jp, curr_cn = [], []
    for j, c in zip(jp_lines, cn_lines):
        if j.strip():
            curr_jp.append(j.strip()); curr_cn.append(c.strip())
        elif curr_jp:
            stanzas_jp.append(curr_jp); stanzas_cn.append(curr_cn)
            curr_jp, curr_cn = [], []
    if curr_jp: stanzas_jp.append(curr_jp); stanzas_cn.append(curr_cn)

    # REFINED: Convert segments to Hiragana AS A WHOLE for semantic accuracy
    whisper_words = []
    for seg in segments:
        full_text = seg['text']
        hira_full = get_hira(full_text, tagger)
        if not hira_full: continue
        
        duration = seg['end'] - seg['start']
        char_dur = duration / len(hira_full)
        for idx, char in enumerate(hira_full):
            whisper_words.append({
                "time": seg['start'] + idx * char_dur,
                "hira": char
            })

    print(f"Establishing boundaries for {len(stanzas_jp)} stanzas...")
    stanza_boundaries = []
    last_end_idx = 0

    for i in range(len(stanzas_jp)):
        stanza_full_text = "".join(stanzas_jp[i])
        stanza_hira = get_hira(stanza_full_text, tagger)
        head_anchor = stanza_hira[:2]
        tail_anchor = stanza_hira[-2:]
        
        limit_idx = len(whisper_words)
        if i < len(stanzas_jp) - 1:
            next_head = get_hira(stanzas_jp[i+1][0][:2], tagger)
            for j in range(last_end_idx, len(whisper_words)):
                win = "".join([w['hira'] for w in whisper_words[j:j+5]])
                if next_head in win:
                    limit_idx = j
                    break
        
        search_stream = "".join([w['hira'] for w in whisper_words[last_end_idx:limit_idx]])
        
        start_time = None
        end_time = None
        
        head_pos = search_stream.find(head_anchor)
        if head_pos != -1:
            start_time = whisper_words[last_end_idx + head_pos]['time']
        
        tail_pos = search_stream.rfind(tail_anchor)
        if tail_pos != -1:
            end_time = whisper_words[last_end_idx + tail_pos]['time'] + 0.3
            last_end_idx = last_end_idx + tail_pos + 1
        
        if start_time is None and end_time is None:
            # Fallback for failed anchors: try to find any part of the stanza
            # or just use the gap between previous end and next limit
            print(f"WARNING: Stanza {i+1} ('{stanzas_jp[i][0]}') anchors not found. Using gap interpolation.")
            start_time = whisper_words[last_end_idx]['time'] if last_end_idx < len(whisper_words) else 0
            end_time = whisper_words[limit_idx-1]['time'] if limit_idx > 0 else start_time + 5.0
        
        # Final safety check
        if start_time is None: start_time = 0.0
        if end_time is None: end_time = start_time + 5.0
        
        stanza_boundaries.append((start_time, end_time))
        print(f"Stanza {i+1} anchored: {start_time:.2f}s -> {end_time:.2f}s")

    # Internal 1:1 Syllable Mapping
    final_results = []
    for i, (b_start, b_end) in enumerate(stanza_boundaries):
        jp_block, cn_block = stanzas_jp[i], stanzas_cn[i]
        chars = [c for line in jp_block for c in line if c.strip() and c not in "、。　"]
        dur = (b_end - b_start) / len(chars)
        words_json = []
        for idx, char in enumerate(chars):
            words_json.append({"word": char, "start": b_start + idx * dur, "end": b_start + (idx+1) * dur})
        final_results.append({"start": b_start, "end": b_end, "jp": "\\N".join(jp_block), "cn": "\\N".join(cn_block), "words": words_json})

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    print("\n[SUCCESS] Semantic-Aware Sandwich Alignment completed.")

if __name__ == "__main__":
    main()
