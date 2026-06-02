import json
import os
import sys
from fugashi import Tagger
import wave
import numpy as np

def get_hira_list(text, tagger):
    res = []
    for word in tagger(text):
        kana = word.feature.kana
        if kana == '*':
            kana = word.surface
        hira = ''.join(chr(ord(c) - 96) if 'ァ' <= c <= 'ヴ' else c for c in kana)
        res.extend(list(hira))
    return res

def trim_vocal_tail(wav_path, start_t, end_t):
    """
    Finds the quietest valley in the second half of the segment to split bleeding stanzas,
    then scans backwards to find where active vocals drop below the threshold (Normalized RMS < 0.15).
    """
    try:
        with wave.open(wav_path, 'rb') as wr:
            fs = wr.getframerate()
            n_channels = wr.getnchannels()
            sampwidth = wr.getsampwidth()
            
            wr_frames = wr.getnframes()
            start_frame = max(0, int(start_t * fs))
            end_frame = min(wr_frames, int(end_t * fs))
            n_frames = end_frame - start_frame
            
            if n_frames <= 100:
                return end_t
            
            wr.setpos(start_frame)
            frames = wr.readframes(n_frames)
            
            if sampwidth == 2:
                dtype = np.int16
            elif sampwidth == 1:
                dtype = np.uint8
            else:
                return end_t
                
            samples = np.frombuffer(frames, dtype=dtype).astype(np.float32)
            if n_channels > 1:
                samples = samples.reshape(-1, n_channels).mean(axis=1)
                
            # Normalize
            max_val = np.max(np.abs(samples)) if np.max(np.abs(samples)) > 0 else 1.0
            samples /= max_val
            
            # Slide window (50ms window, 20ms steps)
            win_size = int(0.05 * fs)
            hop_size = int(0.02 * fs)
            
            rms_list = []
            for i in range(0, len(samples) - win_size, hop_size):
                t = start_t + (i + win_size/2) / fs
                window = samples[i : i + win_size]
                r = np.sqrt(np.mean(window**2))
                rms_list.append((t, r))
                
            if not rms_list:
                return end_t
                
            # 1. Find the Quiet Valley (minimum RMS) in the second half of the segment
            # This isolates this word from any bleeding vocals of the NEXT stanza
            mid_idx = len(rms_list) // 2
            second_half = rms_list[mid_idx:]
            
            valley_t, valley_rms = min(second_half, key=lambda x: x[1])
            
            # 2. Scan backwards from the Valley to find the active vocal drop-off (threshold = 0.15)
            threshold = 0.15
            active_list = [item for item in rms_list if item[0] <= valley_t]
            
            corrected_end = valley_t
            for t, r in reversed(active_list):
                if r >= threshold:
                    # Singing was active here. Return this point with a tiny safety buffer (150ms)
                    corrected_end = min(valley_t, t + 0.15)
                    break
                    
            return corrected_end
            
    except Exception as e:
        print(f"[VVBT Error]: {e}")
        return end_t

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tagger = Tagger()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    
    whisper_path = os.path.join(assets_dir, "audio_segments_enhanced.json")
    jp_path = os.path.join(assets_dir, "lyrics_jp.txt")
    cn_path = os.path.join(assets_dir, "lyrics.txt")
    output_json = os.path.join(assets_dir, "lyrics_alignment.json")
    
    # Validate assets exist
    for path, label in [(whisper_path, "audio_segments_enhanced.json"), (jp_path, "lyrics_jp.txt"), (cn_path, "lyrics.txt")]:
        if not os.path.exists(path):
            print(f"Error: {label} not found at {path}")
            return

    with open(whisper_path, 'r', encoding='utf-8') as f:
        whisper_data = json.load(f)
    with open(jp_path, 'r', encoding='utf-8') as f:
        stanzas_jp = f.read().strip().split('\n\n')
    with open(cn_path, 'r', encoding='utf-8') as f:
        stanzas_cn = f.read().strip().split('\n\n')
    if len(stanzas_jp) != len(stanzas_cn):
        print(f"Warning: Stanza count mismatch (JP: {len(stanzas_jp)}, CN: {len(stanzas_cn)})")

    # 1. Build Lyric Hiragana Stream (L) with comprehensive tracking info
    L = []
    lyric_chars = []
    
    for s_idx, stanza in enumerate(stanzas_jp):
        lines = stanza.splitlines()
        for l_idx, line in enumerate(lines):
            for c_idx, char in enumerate(line):
                # Skip space and standard punctuation
                if not char.strip() or char in " 、　。，.,?!?!「」()（）":
                    continue
                hira_chars = get_hira_list(char, tagger)
                if not hira_chars:
                    continue
                
                char_entry = {
                    "char": char,
                    "stanza_idx": s_idx,
                    "line_idx": l_idx,
                    "char_idx": c_idx,
                    "hira_indices": []
                }
                char_pos = len(lyric_chars)
                lyric_chars.append(char_entry)
                
                for sub_idx, h in enumerate(hira_chars):
                    hira_entry = {
                        "hira": h,
                        "char_pos": char_pos,
                        "char": char,
                        "stanza_idx": s_idx,
                        "line_idx": l_idx,
                        "sub_idx": sub_idx,
                        "sub_len": len(hira_chars)
                    }
                    char_entry["hira_indices"].append(len(L))
                    L.append(hira_entry)

    # 2. Build Whisper Hiragana Stream (W)
    W = []
    for seg in whisper_data:
        for w in seg.get('words', []):
            w_text = w['word'].strip()
            if not w_text:
                continue
            hira_chars = get_hira_list(w_text, tagger)
            if not hira_chars:
                continue
            
            dur = (w['end'] - w['start']) / len(hira_chars)
            for idx, h in enumerate(hira_chars):
                W.append({
                    "hira": h,
                    "start": w['start'] + idx * dur,
                    "end": w['start'] + (idx + 1) * dur,
                    "word": w_text
                })

    N = len(L)
    M = len(W)
    print(f"[DTW] Aligning {N} lyric syllables to {M} Whisper ASR syllables...")

    # 3. Dynamic Programming Alignment (Symbolic Levenshtein Distance)
    cost_delete = 1.2
    cost_insert = 1.2
    cost_replace_match = 0.0
    cost_replace_diff = 3.0
    
    dp = [[0.0] * (M + 1) for _ in range(N + 1)]
    
    for i in range(1, N + 1):
        dp[i][0] = i * cost_delete
    for j in range(1, M + 1):
        dp[0][j] = j * cost_insert
        
    for i in range(1, N + 1):
        for j in range(1, M + 1):
            if L[i-1]["hira"] == W[j-1]["hira"]:
                rep_cost = cost_replace_match
            else:
                rep_cost = cost_replace_diff
                
            dp[i][j] = min(
                dp[i-1][j-1] + rep_cost,
                dp[i-1][j] + cost_delete,
                dp[i][j-1] + cost_insert
            )

    print(f"[DTW] Optimal alignment path distance cost: {dp[N][M]:.2f}")

    # 4. Backtracking to recover alignment path
    i, j = N, M
    path = []
    
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            if L[i-1]["hira"] == W[j-1]["hira"]:
                rep_cost = cost_replace_match
            else:
                rep_cost = cost_replace_diff
                
            if abs(dp[i][j] - (dp[i-1][j-1] + rep_cost)) < 1e-5:
                path.append((i-1, j-1))
                i -= 1
                j -= 1
                continue
                
        if i > 0 and abs(dp[i][j] - (dp[i-1][j] + cost_delete)) < 1e-5:
            path.append((i-1, None))
            i -= 1
            continue
            
        if j > 0 and abs(dp[i][j] - (dp[i][j-1] + cost_insert)) < 1e-5:
            path.append((None, j-1))
            j -= 1
            continue
            
        if i > 0 and j > 0:
            path.append((i-1, j-1))
            i -= 1
            j -= 1
        elif i > 0:
            path.append((i-1, None))
            i -= 1
        else:
            path.append((None, j-1))
            j -= 1

    path.reverse()
    
    matches = [p for p in path if p[0] is not None and p[1] is not None]
    print(f"[DTW] Successfully matched {len(matches)} / {N} syllables ({len(matches)/N*100:.1f}%)")

    # 5. Project Whisper timestamps onto Lyric Stream L
    L_times = [None] * N
    for l_idx, w_idx in path:
        if l_idx is not None and w_idx is not None:
            L_times[l_idx] = {
                "start": W[w_idx]["start"],
                "end": W[w_idx]["end"]
            }

    # Linear interpolation for skipped (deleted) syllables
    for k in range(N):
        if L_times[k] is None:
            left_time = 0.0
            left_idx = -1
            for l_scan in range(k - 1, -1, -1):
                if L_times[l_scan] is not None:
                    left_time = L_times[l_scan]["end"]
                    left_idx = l_scan
                    break
            
            right_time = 240.0 
            right_idx = N
            for r_scan in range(k + 1, N):
                if L_times[r_scan] is not None:
                    right_time = L_times[r_scan]["start"]
                    right_idx = r_scan
                    break
            
            gap_size = right_idx - left_idx
            step = (right_time - left_time) / gap_size
            pos_in_gap = k - left_idx
            
            L_times[k] = {
                "start": left_time + (pos_in_gap - 0.5) * step,
                "end": left_time + (pos_in_gap + 0.5) * step
            }
            if L_times[k]["start"] < left_time:
                L_times[k]["start"] = left_time
            if L_times[k]["end"] > right_time:
                L_times[k]["end"] = right_time

    # 6. Reconstruct character-level timestamps
    for char_entry in lyric_chars:
        hira_indices = char_entry["hira_indices"]
        c_times = [L_times[idx] for idx in hira_indices if L_times[idx] is not None]
        if c_times:
            char_entry["start"] = min(t["start"] for t in c_times)
            char_entry["end"] = max(t["end"] for t in c_times)
        else:
            char_entry["start"] = 0.0
            char_entry["end"] = 0.0

    # 7. Apply Vocal Valley-based Backwards Trimming (VVBT) for long-vowel overflows
    # (specifically targeting words like "花" and other bleeding terminal characters)
    wav_path = os.path.join(assets_dir, "music_vocals.wav")
    if os.path.exists(wav_path):
        print("\n[VVBT] Applying Vocal Valley-based Backwards Trimming to long syllables (> 1.0s)...")
        trimmed_count = 0
        for c in lyric_chars:
            c_dur = c["end"] - c["start"]
            if c_dur > 1.0:
                old_end = c["end"]
                new_end = trim_vocal_tail(wav_path, c["start"], c["end"])
                if new_end < old_end - 0.05:
                    c["end"] = new_end
                    trimmed_count += 1
                    print(f"  -> Trimmed '{c['char']}' (Stanza {c['stanza_idx']+1}): {old_end:.2f}s -> {new_end:.2f}s (Reduced by {old_end - new_end:.2f}s)")
        print(f"[VVBT] Finished trimming. Optimized {trimmed_count} long-vowel timing overflows.\n")

    # 8. Group back into 10 Stanzas
    final_results = []
    
    for s_idx, (stanza_jp, stanza_cn) in enumerate(zip(stanzas_jp, stanzas_cn)):
        stanza_chars = [c for c in lyric_chars if c["stanza_idx"] == s_idx]
        
        if not stanza_chars:
            print(f"[WARNING] Stanza {s_idx+1} has no aligned characters!")
            continue
            
        stanza_words_json = []
        for c in stanza_chars:
            stanza_words_json.append({
                "word": c["char"],
                "start": c["start"],
                "end": c["end"]
            })
            
        jp_lines = stanza_jp.splitlines()
        jp_text_with_newline = "\\N".join(jp_lines)
        cn_text_with_newline = stanza_cn.replace('\n', '\\N')
        
        final_results.append({
            "start": stanza_chars[0]["start"],
            "end": stanza_chars[-1]["end"],
            "jp": jp_text_with_newline,
            "cn": cn_text_with_newline,
            "words": stanza_words_json
        })
        
        print(f"Stanza {s_idx+1} synced: {stanza_chars[0]['start']:.2f}s -> {stanza_chars[-1]['end']:.2f}s | Words: {len(stanza_chars)}")

    # Write alignment file
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=2)
        
    print(f"[SUCCESS] DTW-Based Alignment completed. Saved to: {output_json}")

if __name__ == "__main__":
    main()
