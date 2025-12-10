#!/usr/bin/env python3
import requests
import json
import sys
import os
import time
from pathlib import Path

def generate_subtitles(audio_path, output_srt_path, api_url):
    """Генерация субтитров через Whisper API"""
    try:
        # Отправка аудиофайла на обработку
        with open(audio_path, 'rb') as audio_file:
            files = {'audio_file': audio_file}
            data = {
                'task': 'transcribe',
                'language': 'en',
                'output': 'srt'
            }
            
            response = requests.post(
                f"{api_url}/asr",
                files=files,
                data=data,
                timeout=300  # 5 минут таймаут
            )
        
        if response.status_code == 200:
            # Сохраняем SRT файл
            with open(output_srt_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return True, output_srt_path
        else:
            return False, f"API error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: generate_subtitles.py <audio_path> <output_srt_path> <api_url>")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    output_srt_path = sys.argv[2]
    api_url = sys.argv[3]
    
    success, result = generate_subtitles(audio_path, output_srt_path, api_url)
    if success:
        print(f"Subtitles generated: {result}")
    else:
        print(f"Error: {result}", file=sys.stderr)
        sys.exit(1)