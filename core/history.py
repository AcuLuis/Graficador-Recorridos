from typing import Any

Snapshot = dict[str, Any]


class History:
    """Pilas de deshacer/rehacer basadas en snapshots completos del modelo."""

    def __init__(self, limit: int = 100):
        self.limit = limit
        self._undo: list[Snapshot] = []
        self._redo: list[Snapshot] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def push(self, snapshot: Snapshot) -> None:
        """Registra el estado previo a una modificación."""
        self._undo.append(snapshot)
        if len(self._undo) > self.limit:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self, current: Snapshot) -> Snapshot | None:
        if not self._undo:
            return None
        self._redo.append(current)
        return self._undo.pop()

    def redo(self, current: Snapshot) -> Snapshot | None:
        if not self._redo:
            return None
        self._undo.append(current)
        return self._redo.pop()

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()
