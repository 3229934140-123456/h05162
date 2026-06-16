"""Storage layer with thread-safe file-based persistence.

Architecture:
    - Thread-safe using file locking and threading.RLock
    - JSON-based storage with optional pretty printing
    - Index-based lookup for fast queries
    - Atomic writes using temp file + rename pattern

Concurrency safety:
    - Read lock for queries (shared)
    - Write lock for modifications (exclusive)
    - Cross-process safety using fcntl (Unix) or msvcrt (Windows)
"""
import os
import json
import uuid
import time
import threading
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from contextlib import contextmanager

from noteman.core.errors import StorageError, NotFoundError, ValidationError


class Note:
    """Data model representing a note."""

    def __init__(
        self,
        title: str,
        content: str = "",
        tags: Optional[List[str]] = None,
        note_id: Optional[str] = None,
        created_at: Optional[float] = None,
        updated_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = note_id or uuid.uuid4().hex[:12]
        self.title = title
        self.content = content
        self.tags = sorted(set(tags or []))
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert note to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Note":
        """Create note from dictionary."""
        return cls(
            title=data["title"],
            content=data.get("content", ""),
            tags=data.get("tags", []),
            note_id=data.get("id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"Note(id={self.id!r}, title={self.title!r}, tags={self.tags!r})"


class NoteStore:
    """Thread-safe note storage with file persistence.

    Storage structure:
        data_dir/
        ├── notes.json          # Main notes database
        ├── notes.json.lock     # Lock file for cross-process sync
        └── index.json          # Optional index for fast lookups

    Usage:
        store = NoteStore(data_dir="~/.noteman/data")
        with store.transaction():
            note = store.create(title="Hello", content="World")
            store.save(note)
    """

    def __init__(self, data_dir: str, pretty_print: bool = True):
        """Initialize the note store.

        Args:
            data_dir: Directory for storing notes data.
            pretty_print: Whether to pretty-print JSON output.
        """
        self.data_dir = Path(data_dir).expanduser()
        self.pretty_print = pretty_print
        self._notes_file = self.data_dir / "notes.json"
        self._lock_file = self.data_dir / "notes.json.lock"
        self._lock = threading.RLock()
        self._ensure_data_dir()
        self._cache = self._read_data()

    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists.

        Raises:
            StorageError: If directory cannot be created.
        """
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise StorageError(
                f"Cannot create data directory: {self.data_dir}",
                hint=f"Check permissions: {e}",
            ) from e

    @contextmanager
    def _cross_process_lock(self, mode: str = "r"):
        """Cross-process file lock context manager.

        Args:
            mode: 'r' for shared read lock, 'w' for exclusive write lock.
        """
        lock_fd = None
        try:
            lock_fd = os.open(
                str(self._lock_file),
                os.O_CREAT | (os.O_RDWR if mode == "w" else os.O_RDONLY),
            )

            if os.name == "nt":
                import msvcrt

                if mode == "w":
                    msvcrt.locking(lock_fd, msvcrt.LK_LOCK, 1)
                else:
                    msvcrt.locking(lock_fd, msvcrt.LK_RLCK, 1)
            else:
                import fcntl

                if mode == "w":
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                else:
                    fcntl.flock(lock_fd, fcntl.LOCK_SH)

            yield
        finally:
            if lock_fd is not None:
                try:
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except Exception:
                    pass
                try:
                    os.close(lock_fd)
                except Exception:
                    pass

    @contextmanager
    def transaction(self, write: bool = False):
        """Thread-safe transaction context manager.

        Args:
            write: Whether this transaction needs write access.

        Yields:
            The store instance.
        """
        with self._lock:
            with self._cross_process_lock("w" if write else "r"):
                try:
                    yield self
                    if write:
                        self._flush()
                except Exception:
                    raise

    def _read_data(self) -> Dict[str, Any]:
        """Read raw data from storage file.

        Returns:
            Dictionary with 'notes' key containing note list.

        Raises:
            StorageError: If file cannot be read or parsed.
        """
        if not self._notes_file.exists():
            return {"notes": [], "version": 1}

        try:
            content = self._notes_file.read_text(encoding="utf-8")
            if not content.strip():
                return {"notes": [], "version": 1}
            data = json.loads(content)
            if "notes" not in data:
                data["notes"] = []
            return data
        except json.JSONDecodeError as e:
            raise StorageError(
                f"Corrupted data file: {self._notes_file}",
                hint=f"JSON parse error: {e}",
            ) from e
        except OSError as e:
            raise StorageError(
                f"Cannot read data file: {self._notes_file}",
                hint=f"Check file permissions: {e}",
            ) from e

    def _write_data(self, data: Dict[str, Any]) -> None:
        """Write data to storage file atomically.

        Uses temp file + rename to ensure atomicity.

        Args:
            data: Data dictionary to write.

        Raises:
            StorageError: If write fails.
        """
        try:
            kwargs = {"indent": 2, "ensure_ascii": False} if self.pretty_print else {}
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=".tmp", dir=str(self.data_dir), prefix=".notes_"
            )

            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, **kwargs)
                    f.flush()
                    os.fsync(f.fileno())

                os.replace(temp_path, str(self._notes_file))
            except Exception:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise
        except OSError as e:
            raise StorageError(
                f"Cannot write data file: {self._notes_file}",
                hint=f"Check disk space and permissions: {e}",
            ) from e

    def _flush(self) -> None:
        """Persist pending changes to disk."""
        self._write_data(self._cache)

    def _load_notes(self) -> List[Note]:
        """Load all notes from storage.

        Returns:
            List of Note objects.
        """
        if not hasattr(self, "_cache"):
            self._cache = self._read_data()

        return [Note.from_dict(n) for n in self._cache.get("notes", [])]

    def _save_notes(self, notes: List[Note]) -> None:
        """Save notes to internal cache.

        Args:
            notes: List of Note objects to save.
        """
        self._cache["notes"] = [n.to_dict() for n in notes]
        self._cache["updated_at"] = time.time()

    def create(self, title: str, content: str = "", tags: Optional[List[str]] = None) -> Note:
        """Create a new note (in-memory only, needs save).

        Args:
            title: Note title.
            content: Note content.
            tags: List of tags.

        Returns:
            New Note object.

        Raises:
            ValidationError: If title is empty.
        """
        if not title.strip():
            raise ValidationError("Note title cannot be empty")

        note = Note(title=title.strip(), content=content, tags=tags)
        return note

    def save(self, note: Note) -> Note:
        """Save a note to storage.

        Args:
            note: Note to save.

        Returns:
            The saved note with updated timestamps.

        Raises:
            ValidationError: If note is invalid.
        """
        if not note.title.strip():
            raise ValidationError("Note title cannot be empty")

        note.updated_at = time.time()
        note.tags = sorted(set(note.tags))

        notes = self._load_notes()
        existing_idx = next((i for i, n in enumerate(notes) if n.id == note.id), None)

        if existing_idx is not None:
            notes[existing_idx] = note
        else:
            notes.append(note)

        self._save_notes(notes)
        return note

    def get(self, note_id: str) -> Note:
        """Get a note by ID.

        Args:
            note_id: Note identifier.

        Returns:
            The Note object.

        Raises:
            NotFoundError: If note doesn't exist.
        """
        notes = self._load_notes()
        for note in notes:
            if note.id == note_id:
                return note
        raise NotFoundError(f"Note not found: {note_id}")

    def list(
        self,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        sort_by: str = "updated_at",
        reverse: bool = True,
    ) -> List[Note]:
        """List notes with optional filtering and sorting.

        Args:
            tag: Filter by tag.
            limit: Maximum number of notes to return.
            sort_by: Field to sort by (created_at, updated_at, title).
            reverse: Whether to reverse sort order.

        Returns:
            List of Note objects.
        """
        notes = self._load_notes()

        if tag:
            notes = [n for n in notes if tag in n.tags]

        sort_key_map = {
            "created_at": lambda n: n.created_at,
            "updated_at": lambda n: n.updated_at,
            "title": lambda n: n.title.lower(),
            "id": lambda n: n.id,
        }
        sort_key = sort_key_map.get(sort_by, sort_key_map["updated_at"])
        notes.sort(key=sort_key, reverse=reverse)

        if limit is not None and limit > 0:
            notes = notes[:limit]

        return notes

    def delete(self, note_id: str) -> None:
        """Delete a note by ID.

        Args:
            note_id: Note identifier.

        Raises:
            NotFoundError: If note doesn't exist.
        """
        notes = self._load_notes()
        new_notes = [n for n in notes if n.id != note_id]

        if len(new_notes) == len(notes):
            raise NotFoundError(f"Note not found: {note_id}")

        self._save_notes(new_notes)

    def search(
        self,
        query: str,
        case_sensitive: bool = False,
        include_content: bool = True,
        include_tags: bool = True,
    ) -> List[Note]:
        """Search notes by keyword.

        Args:
            query: Search query string.
            case_sensitive: Whether search is case-sensitive.
            include_content: Whether to search in content.
            include_tags: Whether to search in tags.

        Returns:
            List of matching Note objects.
        """
        if not case_sensitive:
            query = query.lower()

        notes = self._load_notes()
        results = []

        for note in notes:
            title = note.title if case_sensitive else note.title.lower()
            if query in title:
                results.append(note)
                continue

            if include_content:
                content = note.content if case_sensitive else note.content.lower()
                if query in content:
                    results.append(note)
                    continue

            if include_tags:
                tags = note.tags if case_sensitive else [t.lower() for t in note.tags]
                if any(query in t for t in tags):
                    results.append(note)

        return results

    def add_tag(self, note_id: str, tag: str) -> Note:
        """Add a tag to a note.

        Args:
            note_id: Note identifier.
            tag: Tag to add.

        Returns:
            Updated Note object.

        Raises:
            NotFoundError: If note doesn't exist.
            ValidationError: If tag is empty.
        """
        if not tag.strip():
            raise ValidationError("Tag cannot be empty")

        note = self.get(note_id)
        tag = tag.strip()
        if tag not in note.tags:
            note.tags.append(tag)
            note.tags.sort()
        return self.save(note)

    def remove_tag(self, note_id: str, tag: str) -> Note:
        """Remove a tag from a note.

        Args:
            note_id: Note identifier.
            tag: Tag to remove.

        Returns:
            Updated Note object.

        Raises:
            NotFoundError: If note doesn't exist.
        """
        note = self.get(note_id)
        if tag in note.tags:
            note.tags.remove(tag)
        return self.save(note)

    def all_tags(self) -> List[str]:
        """Get all unique tags across all notes.

        Returns:
            Sorted list of unique tags.
        """
        notes = self._load_notes()
        tags = set()
        for note in notes:
            tags.update(note.tags)
        return sorted(tags)

    def count(self) -> int:
        """Get total number of notes.

        Returns:
            Total note count.
        """
        return len(self._load_notes())
