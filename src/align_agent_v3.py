import json
import os
from fugashi import Tagger
import sys

def get_hira_list(text, tagger):
    """Semantic-aware conversion to hiragana characters using morphological analysis."""
    res = []
    for word in tagger(text):
        kana = word.feature.kana
        if kana == '*':
            kana = word.surface
        hira = ''.join(chr(ord(c) - 96) if 'ァ' <= c <= 'ヴ' else c for c in kana)
        res.extend(list(hira))
    return res

def main():
    tagger = Tagger()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    
    segments_path = os.path.join(assets_dir, "audio_segments_enhanced.json")
    jp_path = os.path.join(assets_dir, "lyrics_jp.txt")
    cn_path = os.path.join(assets_dir, "lyrics.txt")
    output_json = os.path.join(assets_dir, "lyrics_alignment.json")
    
    if not os.path.exists(segments_path):
        print(f"Error: {segments_path} not found.")
        return
        
    with open(segments_path, 'r', encoding='utf-8') as f: segments = json.load(f)
    with open(jp_path, 'r', encoding='utf-8') as f: jp_lines = f.read().splitlines()
    with open(cn_path, 'r', encoding='utf-8') as f: cn_lines = f.read().splitlines()

    # 1. Process Whisper Syllable Stream (Protocol: Semantic Restoration)
    whisper_syllables = []
    for seg in segments:
        # Convert whole segment text for correct context readings
        seg_hira_list = get_hira_list(seg['text'], tagger)
        
        # Mapping back to words to get timestamps
        for w in seg.get('words', []):
            w_text = w['word'].strip()
            if not w_text: continue
            # Re-convert word in context (not individually, but we need its length)
            h_chars = get_hira_list(w_text, tagger)
            if not h_chars: continue
            
            dur = (w['end'] - w['start']) / len(h_chars)
            for idx, c in enumerate(h_chars):
                whisper_syllables.append({
                    "hira": c, 
                    "start": w['start'] + idx * dur, 
                    "end": w['start'] + (idx+1) * dur
                })

    # 2. Group Lyrics into Stanzas
    stanzas_jp, stanzas_cn = [], []
    curr_jp, curr_cn = [], []
    for j, c in zip(jp_lines, cn_lines):
        if j.strip():
            curr_jp.append(j.strip()); curr_cn.append(c.strip())
        elif curr_jp:
            stanzas_jp.append(curr_jp); stanzas_cn.append(curr_cn)
            curr_jp, curr_cn = [], []
    if curr_jp: stanzas_jp.append(curr_jp); stanzas_cn.append(curr_cn)

    # 3. Alignment with Syllable Slot Filling
    final_results = []
    syll_ptr = 0
    
    print("\n--- [TECH PROTOCOL v1.1] Alignment Report ---")
    
    for i in range(len(stanzas_jp)):
        stanza_text = "".join(stanzas_jp[i]).replace(" ", "").replace("　", "")
        s_hira = get_hira_list(stanza_text, tagger)
        hira_str = "".join(s_hira)
        
        head_anchor = hira_str[:2]
        tail_anchor = hira_str[-2:]
        
        # Search window: up to 250 syllables (~30-40s)
        search_limit = min(syll_ptr + 250, len(whisper_syllables))
        
        found_start_idx = -1
        found_end_idx = -1
        
        # Find Head Anchor
        for j in range(syll_ptr, search_limit):
            win = "".join([w['hira'] for w in whisper_syllables[j:j+2]])
            if head_anchor == win:
                found_start_idx = j
                break
        
        # Find Tail Anchor (must be after found_start or after current ptr)
        search_start_for_tail = max(syll_ptr, found_start_idx if found_start_idx != -1 else syll_ptr)
        for j in range(search_start_for_tail, search_limit):
            win = "".join([w['hira'] for w in whisper_syllables[j:j+2]])
            if tail_anchor == win:
                found_end_idx = j + 2 
                break
        
        # Protocol: Syllable Slot Filling (Fallback logic)
        status = "OK"
        if found_start_idx == -1 and found_end_idx != -1:
            found_start_idx = max(syll_ptr, found_end_idx - len(s_hira))
            status = "FIXED (Tail-match)"
        elif found_start_idx != -1 and found_end_idx == -1:
            found_end_idx = min(len(whisper_syllables), found_start_idx + len(s_hira))
            status = "FIXED (Head-match)"
        elif found_start_idx == -1 and found_end_idx == -1:
            found_start_idx = syll_ptr
            found_end_idx = min(len(whisper_syllables), syll_ptr + len(s_hira))
            status = "FALLBACK (Linear)"

        # Map actual lyric characters to the determined window
        words_json = []
        lyric_chars_orig = [c for c in "".join(stanzas_jp[i]) if c.strip() and c not in "、。　"]
        
        local_ptr = found_start_idx
        for char in lyric_chars_orig:
            c_hira = get_hira_list(char, tagger)
            c_len = len(c_hira)
            if c_len == 0: continue
            
            c_start = whisper_syllables[local_ptr]['start'] if local_ptr < len(whisper_syllables) else (words_json[-1]['end'] if words_json else 0)
            local_ptr += c_len
            c_end = whisper_syllables[local_ptr-1]['end'] if local_ptr-1 < len(whisper_syllables) else c_start + 0.3
            
            words_json.append({"word": char, "start": c_start, "end": c_end})
            
        syll_ptr = found_end_idx
        
        if words_json:
            s_time = words_json[0]['start']
            e_time = words_json[-1]['end']
            final_results.append({
                "start": s_time,
                "end": e_time,
                "jp": "\\N".join(stanzas_jp[i]),
                "cn": "\\N".join(stanzas_cn[i]),
                "words": words_json
            })
            print(f"Stanza {i+1} [{status}]: {s_time:>6.2f}s -> {e_time:>6.2f}s | {stanzas_jp[i][0][:10]}...")

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
    print("\n[SUCCESS] V3.1 Precision Alignment completed.")

if __name__ == "__main__":
    main()
