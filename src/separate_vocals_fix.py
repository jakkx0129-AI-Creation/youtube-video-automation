import os
import sys
import torch
import soundfile as sf
import numpy as np
from demucs.pretrained import get_model
from demucs.apply import apply_model

def separate_vocals(input_path, output_path):
    print(f"Loading pretrained Demucs model (htdemucs)...")
    model = get_model("htdemucs")
    model.cpu()
    model.eval()
    
    print(f"Loading audio with soundfile: {input_path}")
    wav_np, sr = sf.read(input_path)
    # soundfile returns (samples, channels), Demucs needs (channels, samples)
    if len(wav_np.shape) == 1:
        wav_np = wav_np[:, np.newaxis]
    
    wav = torch.from_numpy(wav_np.T).float()
    
    # Normalize
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()

    print(f"Applying model (this may take a moment)...")
    sources = apply_model(model, wav[None], device="cpu")[0]
    
    vocal_idx = model.sources.index('vocals')
    vocals = sources[vocal_idx]

    # Convert to numpy (samples, channels)
    vocals_np = vocals.cpu().numpy().T
    
    print(f"Saving vocals to: {output_path}")
    sf.write(output_path, vocals_np, model.samplerate)
    print("Success!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python separate_vocals_fix.py <input_wav> <output_wav>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    separate_vocals(input_path, output_path)
