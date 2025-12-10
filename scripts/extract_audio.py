import subprocess
import sys
import os

def extract_audio(video_path, audio_path):
    """Извлечение аудиодорожки из видео"""
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # без видео
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',  # overwrite output
            audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"FFmpeg error: {result.stderr}"
        
        # Проверяем, что файл создан и не пустой
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            return True, audio_path
        else:
            return False, "Audio file not created"
            
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: extract_audio.py <video_path> <audio_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    audio_path = sys.argv[2]
    
    success, result = extract_audio(video_path, audio_path)
    if success:
        print(f"Audio extracted to: {result}")
    else:
        print(f"Error: {result}", file=sys.stderr)
        sys.exit(1)