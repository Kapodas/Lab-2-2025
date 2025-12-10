from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
import subprocess
import os
import tempfile
import shutil
from pathlib import Path

app = FastAPI()

# Создаем временную директорию
TEMP_DIR = "/tmp/video_processing"
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_file(file_path: str):
    """Очистка файла после отправки"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass

def run_command(cmd):
    """Запуск команды и проверка результата"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {result.stderr}")
    return result

@app.post("/extract-audio")
async def extract_audio(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...)
):
    """Извлечение аудио из видео"""
    try:
        # Создаем уникальное имя файла
        temp_video = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=Path(video_file.filename).suffix,
            dir=TEMP_DIR
        )
        temp_video_path = temp_video.name
        
        # Сохраняем видеофайл
        content = await video_file.read()
        with open(temp_video_path, "wb") as f:
            f.write(content)
        
        # Извлекаем аудио
        audio_filename = f"{Path(temp_video_path).stem}.wav"
        audio_path = os.path.join(TEMP_DIR, audio_filename)
        
        cmd = [
            "ffmpeg", 
            "-i", temp_video_path,
            "-vn",  # без видео
            "-acodec", "pcm_s16le",
            "-ar", "16000",  # 16kHz
            "-ac", "1",  # моно
            "-y",  # overwrite
            audio_path
        ]
        
        run_command(cmd)
        
        # Проверяем, что файл создан
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            raise Exception("Audio file not created")
        
        # Добавляем задачи очистки
        background_tasks.add_task(cleanup_file, temp_video_path)
        background_tasks.add_task(cleanup_file, audio_path)
        
        return FileResponse(
            audio_path,
            media_type="audio/wav",
            filename=audio_filename
        )
        
    except Exception as e:
        # Очистка в случае ошибки
        if 'temp_video_path' in locals() and os.path.exists(temp_video_path):
            cleanup_file(temp_video_path)
        if 'audio_path' in locals() and os.path.exists(audio_path):
            cleanup_file(audio_path)
        return {"error": str(e)}, 500

@app.post("/burn-subtitles")
async def burn_subtitles(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    srt_file: UploadFile = File(...)
):
    """Наложение субтитров на видео (поддержка SRT и LRC)"""
    temp_video_path = None
    temp_sub_path = None
    output_path = None
    
    try:
        print(f"Received files: video={video_file.filename}, subtitles={srt_file.filename}")
        
        # Читаем содержимое субтитров
        sub_content = await srt_file.read()
        await srt_file.seek(0)
        
        try:
            sub_text = sub_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                sub_text = sub_content.decode('utf-8-sig')
            except:
                sub_text = sub_content.decode('latin-1')
        
        # Определяем формат субтитров
        is_srt = ' --> ' in sub_text
        is_lrc = any(line.strip().startswith('[') and ']' in line for line in sub_text.split('\n'))
        
        print(f"Format detection - Is SRT: {is_srt}, Is LRC: {is_lrc}")
        
        # Сохраняем видео
        video_suffix = Path(video_file.filename).suffix or '.mp4'
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=video_suffix,
            dir=TEMP_DIR
        ) as temp_video:
            temp_video_path = temp_video.name
            video_content = await video_file.read()
            temp_video.write(video_content)
            print(f"Video saved to: {temp_video_path}")
        
        # Сохраняем субтитры в правильном формате
        sub_extension = ".lrc" if is_lrc or not is_srt else ".srt"
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=sub_extension,
            dir=TEMP_DIR,
            mode='w',
            encoding='utf-8'
        ) as temp_sub:
            temp_sub_path = temp_sub.name
            
            # Если это SRT, но FFmpeg видит как LRC, конвертируем в LRC
            if is_srt and not is_lrc:
                print("Converting SRT to LRC format...")
                lrc_content = convert_srt_to_lrc(sub_text)
                temp_sub.write(lrc_content)
                print("Converted SRT to LRC")
            else:
                temp_sub.write(sub_text)
            
            print(f"Subtitles saved to: {temp_sub_path}")
        
        # Создаем выходной файл
        output_filename = f"subtitled_{Path(video_file.filename).stem}.mp4"
        output_path = os.path.join(TEMP_DIR, output_filename)
        
        # Команда FFmpeg для LRC субтитров
        cmd = [
            'ffmpeg',
            '-i', temp_video_path,
            '-vf', f"subtitles='{temp_sub_path}'",
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            output_path
        ]
        
        print(f"\nFFmpeg command: {' '.join(cmd)}")
        
        # Запускаем FFmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        print(f"\nFFmpeg return code: {process.returncode}")
        
        if process.returncode != 0:
            print(f"FFmpeg errors:\n{stderr}")
            raise Exception(f"FFmpeg failed: {stderr[:500]}")
        
        # Проверяем результат
        if not os.path.exists(output_path):
            raise Exception(f"Output video not created")
        
        print(f"\n✓ Video created: {output_path} ({os.path.getsize(output_path)} bytes)")
        
        # Отправляем файл
        response = FileResponse(
            path=output_path,
            media_type="video/mp4",
            filename=output_filename,
            background=background_tasks
        )
        
        # Очистка
        background_tasks.add_task(cleanup_file, temp_video_path)
        background_tasks.add_task(cleanup_file, temp_sub_path)
        background_tasks.add_task(cleanup_file, output_path)
        
        return response
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Очистка при ошибке
        for file_path in [temp_video_path, temp_sub_path, output_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except:
                    pass
        
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed: {str(e)}"}
        )


def convert_srt_to_lrc(srt_content: str) -> str:
    """Конвертирует SRT формат в LRC формат"""
    lrc_lines = []
    lines = srt_content.strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Пропускаем номер субтитра
        if line.isdigit():
            i += 1
            continue
        
        # Обрабатываем временную метку
        if ' --> ' in line:
            start_time = line.split(' --> ')[0]
            # Конвертируем SRT время (00:00:00,000) в LRC время ([00:00.00])
            try:
                # Формат: HH:MM:SS,mmm
                if ',' in start_time:
                    time_part, ms = start_time.split(',')
                else:
                    time_part = start_time
                    ms = '000'
                
                h, m, s = time_part.split(':')
                seconds = int(h) * 3600 + int(m) * 60 + float(s)
                lrc_time = f"[{int(seconds // 60):02d}:{seconds % 60:05.2f}]"
                
                # Читаем текст субтитра
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit() and ' --> ' not in lines[i]:
                    text_lines.append(lines[i].strip())
                    i += 1
                
                if text_lines:
                    text = ' '.join(text_lines)
                    lrc_lines.append(f"{lrc_time}{text}")
            except:
                i += 1
        else:
            i += 1
    
    return '\n'.join(lrc_lines)

@app.get("/clear")
async def clear_temp():
    """Очистка временных файлов"""
    try:
        for item in os.listdir(TEMP_DIR):
            item_path = os.path.join(TEMP_DIR, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Warning: Could not delete {item_path}: {e}")
        
        return {"status": "cleaned", "directory": TEMP_DIR}
    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)