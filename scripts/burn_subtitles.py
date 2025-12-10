#!/usr/bin/env python3
import subprocess
import sys
import os

def burn_subtitles(video_path, srt_path, output_path):
    """Наложение субтитров на видео"""
    try:
        # Создаем фильтр для субтитров
        filter_complex = (
            f"subtitles='{srt_path}':force_style="
            "'FontName=Arial,FontSize=24,PrimaryColour=&HFFFFFF,"
            "OutlineColour=&H000000,BackColour=&H80000000,BorderStyle=4,"
            "Outline=2,Shadow=1,MarginV=30'"
        )
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vf', filter_complex,
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',  # overwrite output
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"FFmpeg error: {result.stderr}"
        
        # Проверяем результат
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, output_path
        else:
            return False, "Output video not created"
            
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: burn_subtitles.py <video_path> <srt_path> <output_path>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    srt_path = sys.argv[2]
    output_path = sys.argv[3]
    
    success, result = burn_subtitles(video_path, srt_path, output_path)
    if success:
        print(f"Video with subtitles: {result}")
    else:
        print(f"Error: {result}", file=sys.stderr)
        sys.exit(1)