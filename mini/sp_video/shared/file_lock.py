import os
import time
from contextlib import contextmanager


try:
    import fcntl
except ImportError:
    fcntl = None


@contextmanager
def file_lock(lock_path, poll_sec=0.2):
    os.makedirs(os.path.dirname(lock_path), exist_ok=True) if os.path.dirname(lock_path) else None

    if fcntl is not None:
        with open(lock_path, "a", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        return

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            time.sleep(poll_sec)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        yield
    finally:
        try:
            os.remove(lock_path)
        except FileNotFoundError:
            pass

