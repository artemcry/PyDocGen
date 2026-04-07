"""File watcher with debounced rebuild for slop-doc live server."""

import os
import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Extensions that trigger a rebuild
_WATCH_EXTS = {'.md', '.css', '.js', '.json', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf'}


class _DebouncedHandler(FileSystemEventHandler):
    """Fires a callback at most once per *delay* seconds."""

    def __init__(self, output_dir: str, rebuild_fn, on_rebuild, delay: float = 0.4):
        super().__init__()
        self._output_dir = os.path.normpath(output_dir)
        self._rebuild_fn = rebuild_fn
        self._on_rebuild = on_rebuild
        self._delay = delay
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    # ── watchdog callbacks ──────────────────────────────────
    def on_any_event(self, event):
        # Ignore changes inside the output directory
        src = os.path.normpath(event.src_path)
        if src.startswith(self._output_dir):
            return
        # Ignore irrelevant extensions (for file events)
        if not event.is_directory:
            _, ext = os.path.splitext(src)
            if ext.lower() not in _WATCH_EXTS:
                return
        self._schedule()

    # ── debounce logic ──────────────────────────────────────
    def _schedule(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._run)
            self._timer.daemon = True
            self._timer.start()

    def _run(self):
        try:
            self._rebuild_fn()
            self._on_rebuild()
        except Exception as exc:
            print(f"  rebuild error: {exc}")


class DocsWatcher:
    """Watch a docs folder and trigger rebuilds on changes.

    Args:
        docs_root: Path to the documentation root.
        output_dir: Build output directory (ignored by the watcher).
        rebuild_fn: Callable that performs the build (no args).
        on_rebuild: Callable invoked after a successful rebuild.
    """

    def __init__(self, docs_root: str, output_dir: str, rebuild_fn, on_rebuild):
        self._handler = _DebouncedHandler(output_dir, rebuild_fn, on_rebuild)
        self._observer = Observer()
        self._observer.schedule(self._handler, docs_root, recursive=True)

    def start(self):
        self._observer.daemon = True
        self._observer.start()

    def stop(self):
        self._observer.stop()
        self._observer.join(timeout=2)
