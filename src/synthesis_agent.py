import os
import sys
import subprocess
import librosa

def escape_windows_path(path):
    # FFmpeg's subtitles filter is notoriously difficult with Windows paths.
    # We need to escape backslashes for the filter and handle the drive colon.
    path = os.path.abspath(path)
    # Replace backslashes with forward slashes
    path = path.replace('\\', '/')
    # Escape colons for the filter
    path = path.replace(':', '\\:')
    return path

def generate_ffmpeg_command():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base_dir, "assets")
    output_dir = os.path.join(base_dir, "output")
    
    music = os.path.join(assets_dir, "music.wav")
    srt = os.path.join(assets_dir, "lyrics.srt")
    output = os.path.join(output_dir, "final_video.mp4")
    
    # Processed images
    img1 = os.path.join(assets_dir, "processed_1.jpg")
    img2 = os.path.join(assets_dir, "processed_2.jpg")
    img3 = os.path.join(assets_dir, "processed_3.jpg")
    rel_ass = os.path.join(assets_dir, "karoke_plain.ass")

    # Validate assets exist
    for fpath, label in [(music, "music.wav"), (img1, "processed_1.jpg"), (img2, "processed_2.jpg"),
                         (img3, "processed_3.jpg"), (rel_ass, "karoke_plain.ass")]:
        if not os.path.exists(fpath):
            print(f"Error: {label} not found at {fpath}")
            return None
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Calculate per-image duration from actual audio length
    audio_dur = librosa.get_duration(path=music)
    dur = audio_dur / 3
    
    # For Windows, the subtitles filter needs special escaping for the path
    escaped_ass = escape_windows_path(rel_ass)
    
    # We use a filter_complex to loop images and concat them
    # Then scale to 720p and overlay subtitles
    cmd = (
        f'ffmpeg -y '
        f'-loop 1 -t {dur} -i "{img1}" '
        f'-loop 1 -t {dur} -i "{img2}" '
        f'-loop 1 -t {dur} -i "{img3}" '
        f'-i "{music}" '
        f'-filter_complex "'
        f'[0:v][1:v][2:v]concat=n=3:v=1:a=0[v_concat]; '
        f'[v_concat]scale=-2:720[v_scaled]; '
        f'[v_scaled]subtitles=\'{escaped_ass}\'[v_out]" '
        f'-map "[v_out]" -map 3:a '
        f'-c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p '
        f'-c:a aac -b:a 320k -shortest '
        f'"{output}"'
    )
    
    return cmd

if __name__ == "__main__":
    command = generate_ffmpeg_command()
    if command is None:
        sys.exit(1)
    print("Executing FFmpeg...")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error: FFmpeg failed with exit code {result.returncode}")
        sys.exit(1)
    print("Done.")
