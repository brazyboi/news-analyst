from datetime import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    value: Any
    written_by: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SharedMemory:
    _store: dict[str, MemoryEntry] = field(default_factory=dict)

    def store(self, key: str, value: Any, written_by: str = "unknown") -> None:
        self._store[key] = MemoryEntry(value=value, written_by=written_by)

    def read(self, key: str) -> Any | None:
        entry = self._store.get(key)
        return entry.value if entry else None

    def read_entry(self, key: str) -> MemoryEntry | None:
        return self._store.get(key)

    def clear(self) -> None:
        self._store.clear()

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            key: {
                "value": entry.value,
                "written_by": entry.written_by,
                "timestamp": entry.timestamp,
            }
            for key, entry in self._store.items()
        }
