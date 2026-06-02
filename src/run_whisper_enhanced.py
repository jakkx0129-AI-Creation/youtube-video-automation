from faster_whisper import WhisperModel
import json
import os

def main():
    model_size = "large-v3"
    # Use GPU if possible, else CPU
    model = WhisperModel(model_size, device="cpu", compute_type="float32")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    audio_path = os.path.join(base_dir, "assets", "music_vocals.wav")
    output_path = os.path.join(base_dir, "assets", "audio_segments_enhanced.json")

    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found: {audio_path}")
        return

    print(f"Running faster-whisper on ENHANCED VOCALS...")
    # beam_size 5 is standard, word_timestamps is a must
    # Increase sensitivity: no_speech_threshold=0.1 to catch weak trailing sounds
    segments, info = model.transcribe(
        audio_path, 
        beam_size=5, 
        word_timestamps=True,
        no_speech_threshold=0.1,
        condition_on_previous_text=False
    )

    results = []
    for segment in segments:
        words = []
        if segment.words:
            for word in segment.words:
                words.append({
                    "start": word.start,
                    "end": word.end,
                    "word": word.word,
                    "probability": word.probability
                })
        
        results.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": words
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Transcription completed. Data saved to: {output_path}")

if __name__ == "__main__":
    main()
