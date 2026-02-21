import os
import shutil
from pathlib import Path
from typing import Any

class GCCStorage:
    @staticmethod
    def atomic_write(file_path: str, content: Any, mode: str = 'w'):
        """Writes content to a temporary file and atomically renames it to the target.
        Supports both text ('w') and binary ('wb') modes.
        """
        path = Path(file_path)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        open_args = {'mode': mode}
        if 'b' not in mode:
            open_args['encoding'] = 'utf-8'

        with open(temp_path, **open_args) as f:
            f.write(content)
        
        # Atomic rename (replace existing)
        os.replace(temp_path, path)

    @staticmethod
    def atomic_append(file_path: str, content: str):
        """Appends content with file locking for thread/process safety."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'a', encoding='utf-8') as f:
            # BUG-11 FIX: File locking to prevent interleaved writes
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    f.write(content)
                finally:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.write(content)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
