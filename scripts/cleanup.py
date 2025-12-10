#!/usr/bin/env python3
import os
import sys
import shutil
from pathlib import Path

def cleanup_temp_files(temp_dir):
    """Очистка временных файлов"""
    try:
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"Warning: Could not delete {item_path}: {e}")
        
        return True, "Cleanup completed"
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: cleanup.py <temp_dir>")
        sys.exit(1)
    
    temp_dir = sys.argv[1]
    
    success, result = cleanup_temp_files(temp_dir)
    if success:
        print(result)
    else:
        print(f"Error: {result}", file=sys.stderr)
        sys.exit(1)