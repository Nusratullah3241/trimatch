"""THE AUTOMATION TRIGGER.

Watches data/inbox for PDFs. As soon as a complete set arrives
(a PO, a GRN, and an Invoice sharing the same PO number in the filename),
it runs the match by itself - no human clicks anything.

Naming convention for dropped files:
    PO-2026-1000.pdf        -> purchase order
    GRN-2026-1000.pdf       -> goods received note
    INV-2026-1000.pdf       -> invoice

Anything after the type prefix is the group key, so all three
files of one set share it.
"""
import re
import shutil
import time
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.config import settings
from app.database import SessionLocal
from app.services import match_service

INBOX = Path(settings.inbox_dir)
PROCESSED = Path(settings.processed_dir)
INBOX.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

TYPE_PATTERNS = {
    "PO": re.compile(r"^PO[-_]", re.I),
    "GRN": re.compile(r"^GRN[-_]", re.I),
    "INVOICE": re.compile(r"^(INV|INVOICE)[-_]", re.I),
}

_processing_lock = threading.Lock()


def classify(filename: str) -> str | None:
    """Works out which of the three document types a file is."""
    for doc_type, pattern in TYPE_PATTERNS.items():
        if pattern.match(filename):
            return doc_type
    return None


def group_key(filename: str) -> str:
    """Strips the type prefix and extension, leaving the shared set id."""
    stem = Path(filename).stem
    return re.sub(r"^(PO|GRN|INV|INVOICE)[-_]", "", stem, flags=re.I)


def scan_inbox() -> dict[str, dict[str, Path]]:
    """Groups everything currently in the inbox by set id."""
    groups: dict[str, dict[str, Path]] = {}

    for path in INBOX.glob("*.pdf"):
        doc_type = classify(path.name)
        if not doc_type:
            continue
        key = group_key(path.name)
        groups.setdefault(key, {})[doc_type] = path

    return groups


def process_complete_sets() -> int:
    """Finds and processes every complete set in the inbox."""
    with _processing_lock:
        processed_count = 0

    for key, files in scan_inbox().items():
        if not all(t in files for t in ("PO", "GRN", "INVOICE")):
            continue   # incomplete - wait for the rest to arrive

        print(f"\n>> Complete set detected: {key}")
        db = SessionLocal()
        try:
            run = match_service.run_match(
                db,
                str(files["PO"]),
                str(files["GRN"]),
                str(files["INVOICE"]),
                source="WATCHER",
            )

            print(f"   Status     : {run.status}")
            print(f"   Variance   : {run.total_variance:,.2f}")
            print(f"   Exceptions : {len(run.exceptions)}")
            print(f"   Time       : {run.processing_ms} ms")

            for exc in run.exceptions:
                print(f"     - [{exc.severity}] {exc.exception_type}: "
                      f"{exc.line_description[:40]}")

            # Move the handled files out so they are not processed twice
            dest = PROCESSED / key
            dest.mkdir(parents=True, exist_ok=True)
            for path in files.values():
                shutil.move(str(path), str(dest / path.name))

            processed_count += 1

        except Exception as e:
            print(f"   FAILED: {e}")
        finally:
            db.close()

    return processed_count


class InboxHandler(FileSystemEventHandler):
    """Reacts whenever a file lands in the inbox."""

    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith(".pdf"):
            return
        print(f"   [detected] {Path(event.src_path).name}")
        time.sleep(1.5)          # let the file finish being written
        process_complete_sets()


def watch():
    print("=" * 60)
    print("TriMatch watcher running")
    print(f"Watching : {INBOX.resolve()}")
    print("Drop PO-xxx.pdf, GRN-xxx.pdf and INV-xxx.pdf to trigger a match.")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    # Handle anything already sitting there before we started
    already = process_complete_sets()
    if already:
        print(f"\nProcessed {already} set(s) already in the inbox.\n")

    observer = Observer()
    observer.schedule(InboxHandler(), str(INBOX), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nWatcher stopped.")
    observer.join()


if __name__ == "__main__":
    watch()
