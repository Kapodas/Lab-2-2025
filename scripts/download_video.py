#!/usr/bin/env python3
import os
import sys
import yt_dlp
import requests
from urllib.parse import urlparse
import tempfile

def download_video(url, output_path):
    """Скачивание видео по URL"""
    try:
        # Проверяем, является ли URL YouTube
        if 'youtube.com' in url or 'youtu.be' in url:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        else:
            # Простое скачивание по HTTP
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        return True, output_path
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: download_video.py <url> <output_path>")
        sys.exit(1)
    
    url = sys.argv[1]
    output_path = sys.argv[2]
    
    success, result = download_video(url, output_path)
    if success:
        print(f"Video downloaded to: {result}")
    else:
        print(f"Error: {result}", file=sys.stderr)
        sys.exit(1)